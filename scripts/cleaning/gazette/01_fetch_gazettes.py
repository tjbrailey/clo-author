#!/usr/bin/env python3
# ============================================================
# 01_fetch_gazettes.py
# Purpose: Enumerate every Gauteng Provincial Gazette issue (ordinary,
#          extraordinary, liquor) in the P-B pilot windows W1 (2017-18) and
#          W2 (Jul 2021 - Jun 2022), download the PDFs to a local cache and
#          record an issue inventory verified against each PDF's cover page.
# Sources: OpenGazettes year listings (to early Dec 2021) and the GPW
#          SharePoint library (2016-2024). Gazettes.Africa is excluded by its
#          robots.txt (see config.py). Listing metadata (filenames) contain
#          typos, so the cover page (vol / no / date / extraordinary) is the
#          authority for issue identity and window membership.
# Inputs:  network (listings + PDFs); cached listings in data/raw/gazettes/listings/
# Outputs: data/raw/gazettes/pdf/<source>/<folder>/<file>.pdf   (PDF cache)
#          data/raw/gazettes/cover_cache.json                   (cover parse cache)
#          data/cleaned/gazette/listing_records.parquet         (all Gauteng listing rows)
#          data/cleaned/gazette/gazette_inventory.parquet       (in-scope files + cover fields)
# Usage:   py -3.12 01_fetch_gazettes.py [--dry-run] [--limit N] [--refresh-listings]
#          Resumable: cached PDFs are skipped; failures are logged and retried
#          on the next run.
# ============================================================

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import config  # noqa: E402
from common import (PoliteSession, near_window, open_pdf, ocr_page,  # noqa: E402
                    parse_cover, setup_logging, window_of)

logger = logging.getLogger("01_fetch_gazettes")

COVER_CACHE = config.RAW_DIR / "cover_cache.json"
WINDOW_YEARS = {y for lo, hi in config.WINDOWS.values() for y in range(lo.year, hi.year + 1)}
OTHER_PROVINCES = re.compile(
    r"nwest|north\s*west|limp|ecape|e\s*cape|kzn|kwazulu|mpum|ncape|wcape|free\s*state|fstate",
    re.I)


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------
def fetch_opengazettes(http: PoliteSession, refresh: bool) -> list[dict]:
    """Parse OpenGazettes ZA-GT year pages into listing records."""
    records = []
    for year in config.OPENGAZETTES_YEARS:
        cache = config.LISTING_DIR / f"opengazettes_ZA-GT_{year}.html"
        status_file = cache.with_suffix(".status")
        if cache.exists() and not refresh:
            html = cache.read_text(encoding="utf-8")
        elif status_file.exists() and not refresh:
            logger.info("OpenGazettes %s: cached status %s", year, status_file.read_text())
            continue
        else:
            resp = http.request("GET", config.OPENGAZETTES_YEAR_URL.format(year=year))
            if resp.status_code != 200:
                logger.warning("OpenGazettes %s: HTTP %s (no listing; logged as a gap)",
                               year, resp.status_code)
                status_file.write_text(f"HTTP {resp.status_code}")
                continue
            html = resp.text
            cache.write_text(html, encoding="utf-8")
        links = re.findall(r'<a href="(https://archive\.opengazettes\.org\.za/archive/ZA-GT/'
                           r'\d{4}/[^"]+\.pdf)">([^<]+)</a>', html)
        for url, title in dict(links).items():
            m = re.search(r"-vol-(\d+)-no-(\d+)-dated-(\d{4})-(\d\d)-(\d\d)(-[a-z-]+)?\.pdf$", url)
            if not m:
                logger.warning("OpenGazettes: unparsed URL %s", url)
                continue
            vol, no, yy, mm, dd, suffix = m.groups()
            label = "liquor" if suffix and "liquor" in suffix else "unlabelled"
            records.append({
                "source": "opengazettes", "folder": str(year),
                "listing_name": url.rsplit("/", 1)[1], "listing_title": title.strip(),
                "url": url, "file_id": None, "drive_id": None, "listing_size": None,
                "listing_vol": int(vol), "listing_issue_no": int(no),
                "listing_date": date(int(yy), int(mm), int(dd)),
                "listing_type": label, "withdrawn_flag": False,
            })
        logger.info("OpenGazettes %s: %d issues listed", year,
                    sum(r["folder"] == str(year) for r in records))
    return records


def _gpw_folder_items(http: PoliteSession, slug: str) -> dict:
    """List every file in one GPW SharePoint folder via the page's AJAX endpoint."""
    page = http.request("GET", f"{config.GPW_BASE}/{slug}/").text
    cfg = json.loads(re.search(r"var embedConfig = (\{.*?\});\n", page, re.S).group(1))
    ajax = f"{config.GPW_AJAX}?action=mo_doc_lib_embed&nonce={cfg['nonce']}"
    resp = http.request("POST", ajax, data={
        "task": "mo_sps_get_all_folder_items",
        "payload[drive_id]": cfg["drive_id"], "payload[folder_id]": cfg["folder_id"],
        "payload[is_plugin]": "false", "payload[selected_web_url]": cfg["web_url"]}).json()
    docs = list(resp["data"]["all_docs"])
    next_link = resp["data"].get("next_link")
    while next_link:
        resp = http.request("POST", ajax, data={
            "task": "mo_sps_get_all_folder_items_using_next_link",
            "payload[next_link]": next_link, "payload[is_plugin]": "false"}).json()
        if not resp.get("success"):
            raise RuntimeError(f"GPW pagination failed for {slug}: {str(resp)[:200]}")
        docs += resp["data"]["all_docs"]
        next_link = resp["data"].get("next_link")
    # Drop the short-lived tempauth download URLs before caching.
    items = [{"name": d["name"], "id": d["id"], "size": d.get("size"),
              "publication_date": (d.get("fields") or {}).get("PublicationDte"),
              "web_url": d.get("webUrl")} for d in docs if "folder" not in d]
    return {"web_url": cfg["web_url"], "drive_id": cfg["drive_id"],
            "folder_id": cfg["folder_id"], "items": items}


def parse_gpw_name(name: str) -> dict:
    """Issue number, date, type label and withdrawn flag from a GPW filename.

    Examples: '009_19-1-2022_Gauteng.pdf', '229 14-6-2022 GautSeparate.pdf',
    '234_21-7_-2021_GautSeparate.pdf', '121_24-7-20_GautSeparate.pdf'.
    Unparseable parts are returned as None (never guessed).
    """
    out = {"listing_issue_no": None, "listing_date": None, "name_year": None}
    m = re.match(r"^\s*(\d{1,4})\s*[ _-]+\s*(\d{1,2})[-_ ]+(\d{1,2})[-_ ]+(\d{2,4})(?!\d)", name)
    m_no = re.match(r"^\s*(\d{1,4})\s*[ _-]", name)
    if m_no:
        out["listing_issue_no"] = int(m_no.group(1))
    if m:
        dd, mm, yy = int(m.group(2)), int(m.group(3)), int(m.group(4))
        yy = yy + 2000 if yy < 100 else yy
        try:
            out["listing_date"] = date(yy, mm, dd)
        except ValueError:
            pass
    y4 = re.search(r"(?<!\d)(20\d\d)(?!\d)", name)
    out["name_year"] = int(y4.group(1)) if y4 else None
    lower = name.lower()
    if re.search(r"sep[ae]rate|sepelec", lower):
        label = "extraordinary"
    elif "liquor" in lower:
        label = "liquor"
    elif re.search(r"treasury|elect|elec|iec|by-?elek", lower):
        label = "special_other"
    elif re.search(r"g(?:au|u|a)t(?:eng)?\s*(?:\(\d\))?\.pdf$", lower):
        label = "ordinary"
    else:
        label = "unlabelled"
    out["listing_type"] = label
    out["withdrawn_flag"] = bool(re.search(r"withdraw", lower))
    return out


def fetch_gpw(http: PoliteSession, refresh: bool) -> list[dict]:
    """GPW listing records for Gauteng files in the folders that cover the windows."""
    records = []
    for slug, label in config.GPW_PAGES.items():
        cache = config.LISTING_DIR / f"gpw_{slug}.json"
        if cache.exists() and not refresh:
            listing = json.loads(cache.read_text(encoding="utf-8"))
        else:
            listing = _gpw_folder_items(http, slug)
            listing["fetched"] = date.today().isoformat()
            cache.write_text(json.dumps(listing, indent=1), encoding="utf-8")
        n_gt = 0
        for it in listing["items"]:
            name = it["name"]
            if not re.search(r"g(?:au|u|a)t", name, re.I) or OTHER_PROVINCES.search(name):
                continue
            n_gt += 1
            parsed = parse_gpw_name(name)
            records.append({
                "source": "gpw", "folder": label, "listing_name": name,
                "listing_title": name, "url": it.get("web_url"),
                "file_id": it["id"], "drive_id": listing["drive_id"],
                "listing_size": it.get("size"), "listing_vol": None,
                **{k: parsed[k] for k in ("listing_issue_no", "listing_date",
                                          "listing_type", "withdrawn_flag")},
                "name_year": parsed["name_year"],
            })
        logger.info("GPW %s (%s): %d items, %d Gauteng", slug, label,
                    len(listing["items"]), n_gt)
    return records


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------
def select_downloads(df: pd.DataFrame) -> pd.DataFrame:
    """Flag listing rows to download.

    In scope: listing date within WINDOW_BUFFER_DAYS of a window, or no
    parseable date and no year outside the window years. Within
    (listing year, issue no) groups the OpenGazettes copy is preferred; a GPW
    copy is also taken when no OpenGazettes copy lies within
    LISTING_DATE_CONFLICT_DAYS of it (then the cover decides).
    """
    df = df.copy()

    def in_scope(row) -> str:
        d = row["listing_date"]
        if isinstance(d, date):
            return "in_scope" if near_window(d, config.WINDOW_BUFFER_DAYS) else "out_of_window"
        ny = row.get("name_year")
        if ny is not None and not pd.isna(ny) and int(ny) not in WINDOW_YEARS:
            return "out_of_window"
        return "in_scope_undated"

    df["scope"] = df.apply(in_scope, axis=1)
    df["download"] = False
    df["skip_reason"] = None
    scoped = df["scope"].str.startswith("in_scope")
    df.loc[~scoped, "skip_reason"] = "out_of_window"

    og = df[scoped & (df["source"] == "opengazettes")]
    df.loc[og.index, "download"] = True
    og_dates = {}
    for _, r in og.iterrows():
        og_dates.setdefault((r["listing_date"].year, r["listing_issue_no"]), []).append(
            r["listing_date"])
    for idx, r in df[scoped & (df["source"] == "gpw")].iterrows():
        d, no = r["listing_date"], r["listing_issue_no"]
        if isinstance(d, date) and no is not None and not pd.isna(no):
            near = [x for x in og_dates.get((d.year, int(no)), [])
                    if abs((x - d).days) <= config.LISTING_DATE_CONFLICT_DAYS]
            if near:
                df.loc[idx, "skip_reason"] = "covered_by_opengazettes"
                continue
        df.loc[idx, "download"] = True
    return df


# ---------------------------------------------------------------------------
# Download and cover verification
# ---------------------------------------------------------------------------
def local_path(r) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", r["listing_name"]).strip("_")
    return config.PDF_DIR / r["source"] / r["folder"] / safe


def is_valid_pdf(path: Path, expected_size=None) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    if expected_size is not None and not pd.isna(expected_size) \
            and path.stat().st_size != int(expected_size):
        return False
    with open(path, "rb") as fh:
        return fh.read(5) == b"%PDF-"


def download(http: PoliteSession, r, path: Path) -> dict:
    """Download one PDF to path (via .part). Returns status fields."""
    if r["source"] == "gpw":
        url = (f"{config.GPW_AJAX}?action=mo_sps_download_file"
               f"&drive_id={r['drive_id']}&file_id={r['file_id']}")
    else:
        url = r["url"]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    t0 = time.monotonic()
    try:
        resp = http.request("GET", url, stream=True)
        if resp.status_code != 200:
            return {"fetch_status": "failed", "fetch_error": f"HTTP {resp.status_code}",
                    "download_seconds": round(time.monotonic() - t0, 1)}
        with open(tmp, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                fh.write(chunk)
        tmp.replace(path)
    except Exception as exc:  # logged and retried on the next run
        return {"fetch_status": "failed", "fetch_error": str(exc)[:300],
                "download_seconds": round(time.monotonic() - t0, 1)}
    if not is_valid_pdf(path, r.get("listing_size")):
        return {"fetch_status": "failed", "fetch_error": "not a PDF or size mismatch",
                "download_seconds": round(time.monotonic() - t0, 1)}
    return {"fetch_status": "downloaded", "fetch_error": None,
            "download_seconds": round(time.monotonic() - t0, 1)}


def read_cover(path: Path, cache: dict) -> dict:
    """Pages, sha256 and cover fields for one PDF (cached by path + size)."""
    key = f"{path.relative_to(config.RAW_DIR).as_posix()}|{path.stat().st_size}"
    if key in cache:
        return cache[key]
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    out = {"sha256": sha, "n_pages": None, "cover_ocr_used": False, "cover_error": None}
    try:
        doc = open_pdf(path)
        out["n_pages"] = doc.page_count
        text = doc[0].get_text()
        cov = parse_cover(text)
        # Cover text layers are sometimes image-only or scrambled: OCR once.
        if cov["cover_issue_no"] is None or cov["cover_date"] is None:
            ocr = ocr_page(doc[0], config.COVER_OCR_DPI)
            cov_ocr = parse_cover(ocr)
            out["cover_ocr_used"] = True
            for k, v in cov_ocr.items():
                if cov.get(k) in (None, False) and v not in (None, False):
                    cov[k] = v
        out.update(cov)
    except Exception as exc:
        out["cover_error"] = str(exc)[:300]
    if isinstance(out.get("cover_date"), date):
        out["cover_date"] = out["cover_date"].isoformat()
    cache[key] = out
    return out


def resolve_issue(row) -> pd.Series:
    """Final issue identity: cover first, listing second. Flags conflicts."""
    cover_date = pd.to_datetime(row.get("cover_date")).date() if row.get("cover_date") else None
    ldate = row["listing_date"] if isinstance(row["listing_date"], date) else None
    cno = row.get("cover_issue_no")
    cno = None if cno is None or pd.isna(cno) else int(cno)
    lno = row.get("listing_issue_no")
    lno = None if lno is None or pd.isna(lno) else int(lno)
    issue_date = cover_date or ldate
    issue_no = cno if cno is not None else lno
    if row.get("cover_extraordinary"):
        itype = "extraordinary"
    elif row.get("cover_liquor") or row["listing_type"] == "liquor":
        itype = "liquor"
    elif cover_date is not None and cno is not None:
        itype = "ordinary"
    elif row["listing_type"] in ("ordinary", "extraordinary"):
        itype = row["listing_type"]
    else:
        itype = "unknown"
    conflicts = []
    if cover_date and ldate and abs((cover_date - ldate).days) > 1:
        conflicts.append(f"date listing={ldate} cover={cover_date}")
    if cno is not None and lno is not None and cno != lno:
        conflicts.append(f"no listing={lno} cover={cno}")
    if row["listing_type"] in ("ordinary", "extraordinary") and itype in (
            "ordinary", "extraordinary") and itype != row["listing_type"]:
        conflicts.append(f"type listing={row['listing_type']} cover={itype}")
    return pd.Series({
        "issue_date": issue_date, "issue_no": issue_no, "issue_type": itype,
        "date_source": "cover" if cover_date else ("listing" if ldate else None),
        "meta_conflict": "; ".join(conflicts) or None,
        "window": window_of(issue_date),
    })


def finalise_issues(inv: pd.DataFrame) -> pd.DataFrame:
    """Province check, sequence diagnostics and primary-copy choice.

    - A cover naming another province and not Gauteng (a misfiled listing
      entry) is out of scope.
    - Issue numbers restart each January but are pre-allocated in blocks,
      so dates are only roughly increasing in the number (2022 especially).
      Cover dates are therefore trusted for window membership; an issue that
      is > 30 days out of order against 3+ other issues is only flagged
      (`date_suspect`, or `issue_no_suspect` when its number is > 20 above
      the year's otherwise-consistent maximum). E.g. 2021 no. 274's cover
      reads '20 June 2021' amid August issues.
    - `is_primary_copy`: one file per (cover date, issue no); OpenGazettes
      over GPW, non-withdrawn over withdrawn, first of identical files.
    """
    inv = inv.copy()
    ok = inv["fetch_status"].isin(["cached", "downloaded"]) & inv["issue_no"].notna()         & inv["issue_date"].notna()
    inv["issue_year"] = inv["issue_date"].map(lambda d: d.year if isinstance(d, date) else None)
    inv["not_gauteng"] = inv["cover_other_province"].notna() & ~inv["cover_gauteng"].fillna(False)
    inv.loc[inv["not_gauteng"], "window"] = None
    ok = ok & ~inv["not_gauteng"]
    inv["date_suspect"] = False
    inv["issue_no_suspect"] = False
    tol = pd.Timedelta(days=30)
    for _, g in inv[ok].groupby("issue_year"):
        nos = g["issue_no"].astype(int)
        dates = pd.to_datetime(g["issue_date"])
        counts = {idx: int(((nos > nos[idx]) & (dates < dates[idx] - tol)).sum()
                           + ((nos < nos[idx]) & (dates > dates[idx] + tol)).sum())
                  for idx in g.index}
        clean = [i for i, c in counts.items() if c <= 2]
        max_clean = nos[clean].max() if clean else None
        for idx, c in counts.items():
            if c > 2:
                if max_clean is not None and nos[idx] > max_clean + 20:
                    inv.loc[idx, "issue_no_suspect"] = True
                else:
                    inv.loc[idx, "date_suspect"] = True
    pref = {s: i for i, s in enumerate(config.SOURCE_PREFERENCE)}
    inv["_rank"] = inv["source"].map(pref).fillna(9) + inv["withdrawn_flag"].astype(int) * 10         + inv["duplicate_of_sha"].astype(int) * 100
    inv["is_primary_copy"] = False
    prim = inv[ok].sort_values("_rank").drop_duplicates(["issue_date", "issue_no"], keep="first")
    inv.loc[prim.index, "is_primary_copy"] = True
    return inv.drop(columns=["_rank"])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="list and select only")
    ap.add_argument("--limit", type=int, default=0, help="max new downloads (0 = all)")
    ap.add_argument("--refresh-listings", action="store_true")
    args = ap.parse_args()
    setup_logging("01_fetch_gazettes")

    http = PoliteSession()
    records = fetch_opengazettes(http, args.refresh_listings) + fetch_gpw(http, args.refresh_listings)
    df = pd.DataFrame(records)
    df = select_downloads(df)
    df["listing_date_str"] = df["listing_date"].map(
        lambda d: d.isoformat() if isinstance(d, date) else None)
    df.drop(columns=["listing_date"]).rename(columns={"listing_date_str": "listing_date"}) \
      .to_parquet(config.LISTING_RECORDS, index=False)
    df = df.drop(columns=["listing_date_str"])
    logger.info("Listing rows: %d | scope: %s | to download: %d",
                len(df), df["scope"].value_counts().to_dict(), int(df["download"].sum()))
    if args.dry_run:
        return

    todo = df[df["download"]].copy()
    n_new = 0
    results = []
    for idx, r in todo.iterrows():
        path = local_path(r)
        if is_valid_pdf(path, r.get("listing_size")):
            res = {"fetch_status": "cached", "fetch_error": None, "download_seconds": None}
        elif args.limit and n_new >= args.limit:
            res = {"fetch_status": "not_attempted", "fetch_error": "--limit reached",
                   "download_seconds": None}
        else:
            res = download(http, r, path)
            n_new += 1
            if res["fetch_status"] == "failed":
                logger.warning("FAILED %s %s: %s", r["source"], r["listing_name"], res["fetch_error"])
            if n_new % 25 == 0:
                logger.info("Downloaded %d new files (%d requests so far)", n_new, http.n_requests)
        results.append({"idx": idx, "local_path": path.relative_to(config.REPO_ROOT).as_posix(), **res})
    todo = todo.join(pd.DataFrame(results).set_index("idx"))

    cache = json.loads(COVER_CACHE.read_text()) if COVER_CACHE.exists() else {}
    covers = []
    for idx, r in todo.iterrows():
        path = config.REPO_ROOT / r["local_path"]
        if r["fetch_status"] in ("cached", "downloaded") and path.exists():
            covers.append({"idx": idx, **read_cover(path, cache)})
    COVER_CACHE.write_text(json.dumps(cache, indent=0))
    inv = todo.join(pd.DataFrame(covers).set_index("idx")) if covers else todo
    inv = pd.concat([inv, inv.apply(resolve_issue, axis=1)], axis=1)

    # One primary copy per distinct content; identical files from two
    # listings are duplicates, not separate issues.
    inv["duplicate_of_sha"] = inv.duplicated("sha256", keep="first") & inv["sha256"].notna()
    inv = finalise_issues(inv)
    inv["listing_date"] = inv["listing_date"].map(
        lambda d: d.isoformat() if isinstance(d, date) else None)
    inv["issue_date"] = inv["issue_date"].map(
        lambda d: d.isoformat() if isinstance(d, date) else None)
    inv = inv.sort_values(["issue_date", "issue_no", "source"]).reset_index(drop=True)
    inv.to_parquet(config.INVENTORY, index=False)

    ok = inv["fetch_status"].isin(["cached", "downloaded"])
    logger.info("Inventory: %d files | ok %d | failed %d | not attempted %d",
                len(inv), int(ok.sum()), int((inv["fetch_status"] == "failed").sum()),
                int((inv["fetch_status"] == "not_attempted").sum()))
    logger.info("In-window files by window: %s", inv[ok]["window"].value_counts(dropna=False).to_dict())
    logger.info("Metadata conflicts (listing vs cover): %d", int(inv["meta_conflict"].notna().sum()))
    logger.info("HTTP requests this run: %d", http.n_requests)
    logger.info("Wrote %s", config.INVENTORY.relative_to(config.REPO_ROOT))


if __name__ == "__main__":
    main()
