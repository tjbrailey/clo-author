#!/usr/bin/env python3
# ============================================================
# scripts/cleaning/e3/00_download_sources.py
# Title:   Download all public sources for the Cape Town SRA (E3) onset compile
# Author:  data-engineer (PSC Exposure project)
# Date:    2026-09-30
# Purpose: WP5 step 1. Fetch, with provenance (URL, UTC time, SHA-256, bytes),
#          every public document used to date, classify and budget the City of
#          Cape Town Special Rating Areas (SRAs / CIDs):
#            A. SRA polygon layer (ArcGIS REST FeatureServer/4) + item metadata
#            B. Open Data Portal SRA budget workbooks (2015/16, 2016/17,
#               2021/22-2023/24) + item metadata
#            C. City budget annexures, FY2014/15-2026/27: "Annexure 3 - SRA/CID
#               additional rates" and "Annexure 6 - Additional property rates
#               (SRAs)" (discovered from each year's budget page)
#            D. Wayback Machine copies of pre-2014 budget tariff books that list
#               CID levies (FY2006/07-2009/10), and the 2012 SRA By-law
#            E. City CID pages, CID By-law, CID Policy, FAQ, current tariffs
#            F. Current-term SRA business plans (discovered from the City page)
# Inputs:  network only
# Outputs: data/raw/e3/docs/<source_id>.<ext>
#          data/raw/e3/sources_manifest.csv  (what we tried to fetch)
#          data/raw/e3/provenance.csv        (what we got; one row per file)
# Usage:   py -3.12 scripts/cleaning/e3/00_download_sources.py [--refresh]
#          Files already on disk are not re-fetched unless --refresh.
# Notes:   Polite: one request at a time, >= 2.5 s apart, identified UA,
#          retries with backoff. gazettes.africa returns HTTP 403 to scripted
#          clients, so Provincial Gazette notices are NOT fetched (see report).
# ============================================================

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import quote, unquote, urljoin

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e3_config import (  # noqa: E402
    MANIFEST, MAX_RETRIES, MIN_DELAY_S, PROVENANCE, RAW, RAW_DOCS, TIMEOUT_S,
    USER_AGENT,
)

CITY = "https://www.capetown.gov.za"
AGOL_ITEM = "https://www.arcgis.com/sharing/rest/content/items/{id}"
LAYER = ("https://esapqa.capetown.gov.za/agsext/rest/services/Theme_Based/"
         "ODP_SPLIT_5/FeatureServer/4")
WAYBACK = "https://web.archive.org/web/{ts}id_/{url}"

BUDGET_PAGES = {
    2014: "The-Citys-Budget-2014-2015",
    2015: "The-Citys-budget-2015-2016",
    **{y: f"the-citys-budget-{y}-{y + 1}" for y in range(2016, 2027)},
}
BUDGET_BASE = CITY + "/Family%20and%20home/Meet-the-City/the-city-budget/"
BP_PAGE = (CITY + "/Family%20and%20home/City-publications/agreements/"
           "sra-business-plans-and-cid-moas")
CID_PAGE = (CITY + "/Family%20and%20home/residential-property-and-houses/"
            "private-properties/city-improvement-districts")

# Open Data Portal items (owner cctgis), found via the ArcGIS search API.
ODP_ITEMS = {
    "odp_sra_layer_item": "f46ed498b67f44b58d7fddf4d5dbc0c2",
    "odp_budget_2021_24_xlsx": "c412806a1b664918953994fe3370162b",
    "odp_budget_2023_24_zip": "3c335151e1f349d49e3599d9de917478",
    "odp_budget_2021_23_zip": "aaa1f34bfb9f4a5ea459662ce3d6da7a",
    "odp_budget_2016_17_zip": "281ac2aa200c481ebf9c1276eb69e37d",
    "odp_budget_2015_16_zip": "5e7b13a9adb24d348ba2061db34de7d6",
}

# Pre-2014 budget documents survive only in the Wayback Machine. Timestamps
# are the captures listed by the CDX API on 2026-09-30.
WAYBACK_DOCS = [
    ("wb_tariff_rates_cids_fy2007", "20091211101448",
     "http://www.capetown.gov.za:80/en/Budget/Documents/"
     "11Finance-C-Tariff_Rates_and_Cids.pdf",
     "Budget 2007/08 tariff book: Finance - property rates & CID levies "
     "(columns 2006/07 and 2007/08)"),
    ("wb_tariff_rates_cids_fy2009", "20091211102800",
     "http://www.capetown.gov.za:80/en/Budget/Documents/Budget%202009-2010%20final/"
     "Annexure%206/Finance_%20PropertyRates%20and%20CIDS_0910%20May2009.pdf",
     "Budget 2009/10 (May 2009) tariff book: property rates & CID levies "
     "(columns 2008/09 and 2009/10)"),
    ("wb_central_improvement_district", "20091229073737",
     "http://www.capetown.gov.za:80/en/Budget/Documents/Central_Improvement_District.pdf",
     "Budget 2009/10 page: Central Improvement District document"),
    ("wb_sra_bylaw_2012", "20160913032200",
     "https://www.capetown.gov.za/en/Budget/Budget%20201213/"
     "Annexure%204%20-%20Special%20Rating%20Areas%20By-law.pdf",
     "Budget 2012/13 Annexure 4: Special Rating Areas By-law"),
    ("wb_budget_page_fy2007", "20081019031551",
     "http://www.capetown.gov.za:80/en/Budget/Pages/Budget%202007-2008.aspx",
     "Archived budget 2007/08 page (links a CID tariff book 'including Athlone CID')"),
    ("wb_budget_page_fy2009", "20090406010627",
     "http://www.capetown.gov.za:80/en/Budget/Pages/Budget2009-2010.aspx",
     "Archived budget 2009/10 page (links to SRA annexure; annexure itself not archived)"),
    ("wb_budget_page_fy2010", "20110113135120",
     "http://www.capetown.gov.za:80/EN/BUDGET/Pages/Budget2010-2011.aspx",
     "Archived budget 2010/11 page (links to SRA annexure; annexure itself not archived)"),
    ("wb_budget_page_fy2011", "20110707121500",
     "http://www.capetown.gov.za:80/en/Budget/Pages/Budget2011-2012.aspx",
     "Archived budget 2011/12 page (links to SRA annexure; annexure itself not archived)"),
    ("wb_budget_page_fy2013", "20130609150108",
     "http://www.capetown.gov.za:80/en/Budget/Pages/Budget-2013-2014-final.aspx",
     "Archived budget 2013/14 page (links to SRA annexure; annexure itself not archived)"),
]

STATIC_CITY_DOCS = [
    ("city_cid_page", CID_PAGE, "City CID web page (process, consent thresholds)"),
    ("city_bp_page", BP_PAGE, "City page listing SRA business plans and CID MOAs"),
    ("city_cid_bylaw", CITY + "/_documents/resource.capetown.gov.za/documentcentre/"
     "Documents/Bylaws%20and%20policies/CCT_CID_By-law.pdf", "City CID By-law (current)"),
    ("city_cid_policy", CITY + "/_documents/resource.capetown.gov.za/documentcentre/"
     "Documents/Bylaws%20and%20policies/CID_Policy.pdf", "City CID Policy (current)"),
    ("city_cid_faq_en", CITY + "/_documents/resource.capetown.gov.za/documentcentre/"
     "Documents/Procedures,%20guidelines%20and%20regulations/FAQ%20-%20ENGLISH.pdf",
     "City CID FAQ (English)"),
    ("city_cid_tariffs_current", CITY + "/_documents/resource.capetown.gov.za/"
     "documentcentre/Documents/Financial%20documents/City_Improvement_Districts_Tariffs.pdf",
     "City CID tariffs (current year)"),
]

ANNEX_PAT = re.compile(
    r"special rating|\bSRAs?\b|\bCIDs?\b|improvement district", re.I)


class Fetcher:
    """Single-connection polite fetcher."""

    def __init__(self) -> None:
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        self._last = 0.0

    def get(self, url: str) -> requests.Response:
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            wait = MIN_DELAY_S - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            try:
                r = self.s.get(url, timeout=TIMEOUT_S, allow_redirects=True)
                self._last = time.monotonic()
                if r.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"HTTP {r.status_code}")
                return r
            except Exception as exc:  # network or retryable status
                self._last = time.monotonic()
                last_exc = exc
                time.sleep(5 * (2 ** attempt))
        raise RuntimeError(f"failed after {MAX_RETRIES} tries: {url}: {last_exc}")


def safe_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:90]


def ext_from(url: str, ctype: str) -> str:
    path = unquote(url.split("?")[0]).lower()
    for e in (".pdf", ".xlsx", ".xls", ".zip", ".ods", ".json", ".geojson"):
        if path.endswith(e):
            return e
    if "json" in ctype:
        return ".json"
    if "pdf" in ctype:
        return ".pdf"
    if "html" in ctype or path.endswith(".aspx"):
        return ".html"
    return ".bin"


def page_links(html: str, base: str) -> list[tuple[str, str]]:
    out = []
    for h, t in re.findall(r'href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        txt = re.sub(r"\s+", " ", re.sub(r"<.*?>", "", unescape(t))).strip()
        out.append((urljoin(base, unescape(h)), txt))
    return out


def encode_url(url: str) -> str:
    """Percent-encode spaces etc. in a City URL without double-encoding."""
    return quote(unquote(url), safe=":/?&=%(),_-.~")


def discover(fetch: Fetcher) -> list[dict]:
    rows: list[dict] = []

    def add(source_id, category, url, desc, fy="", wayback_ts="", via="direct"):
        rows.append(dict(source_id=source_id, category=category, fy=fy, url=url,
                         wayback_ts=wayback_ts, via=via, description=desc))

    # A. polygon layer (GeoJSON in WGS84) and its metadata
    add("sra_layer4_meta", "polygons", LAYER + "?f=json",
        "ArcGIS REST layer metadata, Special Rating Areas (layer 4)")
    add("sra_layer4_geojson", "polygons",
        LAYER + "/query?where=1%3D1&outFields=*&outSR=4326&f=geojson",
        "All SRA polygons, GeoJSON, EPSG:4326")

    # B. ODP items: metadata JSON + data file
    for sid, item in ODP_ITEMS.items():
        add(sid + "_meta", "odp_item_meta", AGOL_ITEM.format(id=item) + "?f=json",
            f"ArcGIS Online item metadata {item}")
        if sid != "odp_sra_layer_item":
            add(sid, "budget_workbook", AGOL_ITEM.format(id=item) + "/data",
                f"ODP SRA budget workbook, item {item}")

    # C. annual budget annexures (current City site)
    for y, slug in BUDGET_PAGES.items():
        url = BUDGET_BASE + slug
        add(f"city_budget_page_fy{y}", "budget_page", url, f"City budget page FY{y}", fy=str(y))
        r = fetch.get(url)
        if r.status_code != 200:
            print(f"  ! budget page {y}: HTTP {r.status_code}")
            continue
        seen = set()
        for link, txt in page_links(r.text, url):
            if not link.lower().endswith(".pdf"):
                continue
            both = txt + " " + unquote(link)
            if not ANNEX_PAT.search(both) or re.search(r"ward|subcouncil", both, re.I):
                continue
            if link in seen:
                continue
            seen.add(link)
            fname = unquote(link.rsplit("/", 1)[-1])
            if re.search(r"Additional[ _]Property[ _]Rates", both, re.I):
                cat = "annex6_tariffs"
            elif re.search(r"additional[ _]rates|add[ _]?rates", both, re.I):
                # FY2017/18 bundles policy + additional rates in one PDF
                cat = "annex3_additional_rates"
            elif re.search(r"policy|by-?law", both, re.I):
                cat = "sra_policy_bylaw"
            else:
                cat = "annex3_additional_rates"
            add(f"fy{y}_{cat}_{safe_id(fname)[:40]}", cat, encode_url(link), txt, fy=str(y))

    # D. Wayback
    for sid, ts, url, desc in WAYBACK_DOCS:
        add(sid, "wayback", url, desc, wayback_ts=ts, via="wayback")

    # E. static City docs
    for sid, url, desc in STATIC_CITY_DOCS:
        add(sid, "city_doc", url, desc)

    # F. business plans
    r = fetch.get(BP_PAGE)
    seen = set()
    for link, txt in page_links(r.text, BP_PAGE):
        if link.lower().endswith(".pdf") and link not in seen:
            seen.add(link)
            fname = unquote(link.rsplit("/", 1)[-1]).rsplit(".", 1)[0]
            add("bp_" + safe_id(fname), "business_plan", encode_url(link), txt)
    return rows


def download(fetch: Fetcher, rows: list[dict], refresh: bool) -> list[dict]:
    RAW_DOCS.mkdir(parents=True, exist_ok=True)
    prov_old = {}
    if PROVENANCE.exists():
        with open(PROVENANCE, newline="", encoding="utf-8") as fh:
            prov_old = {r["source_id"]: r for r in csv.DictReader(fh)}
    prov = []
    for i, row in enumerate(rows, 1):
        sid = row["source_id"]
        old = prov_old.get(sid)
        if old and not refresh and old.get("local_path") and (RAW / old["local_path"]).exists():
            # keep fetch facts; refresh descriptive fields from the manifest
            old.update(category=row["category"], fy=row["fy"], description=row["description"])
            prov.append(old)
            continue
        url = row["url"]
        get_url = WAYBACK.format(ts=row["wayback_ts"], url=url) if row["via"] == "wayback" else url
        try:
            r = fetch.get(get_url)
            status, content = r.status_code, r.content
            ctype = r.headers.get("Content-Type", "")
            final_url = r.url
        except RuntimeError as exc:
            status, content, ctype, final_url = -1, b"", "", str(exc)[:200]
        local = ""
        sha = ""
        if status == 200 and content:
            ext = ".geojson" if sid.endswith("_geojson") else ext_from(url, ctype)
            if ext == ".bin" and content[:4] == b"PK\x03\x04":
                ext = ".zip" if "zip" in sid else ".xlsx"
            path = RAW_DOCS / f"{sid}{ext}"
            path.write_bytes(content)
            local = str(path.relative_to(RAW)).replace("\\", "/")
            sha = hashlib.sha256(content).hexdigest()
        prov.append(dict(
            source_id=sid, category=row["category"], fy=row["fy"], url=url,
            fetched_url=get_url, final_url=final_url, via=row["via"],
            wayback_ts=row["wayback_ts"], http_status=status, content_type=ctype,
            bytes=len(content), sha256=sha, local_path=local,
            retrieved_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            description=row["description"],
        ))
        print(f"[{i}/{len(rows)}] {status} {len(content):>9,d} {sid}")
    return prov


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-download everything")
    args = ap.parse_args()
    fetch = Fetcher()
    rows = discover(fetch)
    ids = [r["source_id"] for r in rows]
    dup = {x for x in ids if ids.count(x) > 1}
    if dup:
        raise SystemExit(f"duplicate source_ids: {sorted(dup)}")
    write_csv(MANIFEST, rows)
    prov = download(fetch, rows, args.refresh)
    write_csv(PROVENANCE, prov)
    ok = sum(1 for p in prov if str(p["http_status"]) == "200")
    print(f"\nmanifest rows: {len(rows)}; fetched OK: {ok}; failed: {len(prov) - ok}")
    for p in prov:
        if str(p["http_status"]) != "200":
            print(f"  FAILED {p['http_status']} {p['source_id']} {p['url']}")
    # Keep the layer metadata's 'count' next to the provenance for the report.
    meta = RAW_DOCS / "sra_layer4_geojson.geojson"
    if meta.exists():
        n = len(json.loads(meta.read_text(encoding="utf-8"))["features"])
        print(f"SRA polygons downloaded: {n}")


if __name__ == "__main__":
    main()
