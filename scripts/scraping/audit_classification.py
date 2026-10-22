#!/usr/bin/env python3
# ============================================================
# audit_classification.py
# Purpose: Reproducible before/after audit of the 2026-09-29
#          scraper fixes (03 dedup/location + 04 classification),
#          data dictionary, and precision review. Read-only with
#          respect to data; writes one Markdown report. No network.
# Inputs:  data/raw/scraping/listings_archive_*.parquet (raw)
#          data/raw/scraping/.cache/listings_{all,classified}_pre-fix_2026-09-29.parquet
#          data/raw/scraping/listings_all.parquet            (post-fix 03)
#          data/raw/scraping/listing_stubs_listingnumber.parquet (03)
#          data/raw/scraping/listings_classified.parquet     (post-fix 04)
#          scripts/scraping/tests/fixtures/precision_labels_2026-09-29.csv
# Outputs: quality_reports/scrape_audit_2026-09-29.md
#          (--export-samples FILE: full text of the precision samples,
#           used once to produce the label file; not needed to re-run)
# Usage:   python3 scripts/scraping/audit_classification.py [--export-samples FILE]
#          (Windows: py -3.12 ...). Requires Python >= 3.10.
# ============================================================

import argparse
import hashlib
import importlib.util
import logging
import math
import platform
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    RAW_DIR, CACHE_DIR, REPO_ROOT, LISTINGS_CLASSIFIED, ALL_PSC_KEYWORD_GROUPS,
    CONSTRUCT_COMPONENTS, CANDIDATE_PHRASES, ENCLAVE_BROAD_CANDIDATES,
    WEAK_INDICATOR_GROUPS, PSC_COMPANIES, P24_TOWN_TO_METRO,
)
from utils.url_utils import extract_p24_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SEED = 20260929
SNIPPET_CHARS = 300
REPORT_PATH = REPO_ROOT / "quality_reports" / "scrape_audit_2026-09-29.md"
PRE_ALL = CACHE_DIR / "listings_all_pre-fix_2026-09-29.parquet"
PRE_CLS = CACHE_DIR / "listings_classified_pre-fix_2026-09-29.parquet"
STUBS = RAW_DIR / "listing_stubs_listingnumber.parquet"
LABELS = Path(__file__).parent / "tests" / "fixtures" / "precision_labels_2026-09-29.csv"
GROUPS = list(ALL_PSC_KEYWORD_GROUPS)
CONSTRUCTS = ["enclave_flag", "enclave_flag_broad", "guard_service_flag", "hardening_flag"]
LABEL_COLS = ["enclave", "guard_service", "hardening", "commercial"]

# Precision samples: (name, row filter, n). One row per listing, seed SEED.
SAMPLES = [
    ("A_psc_flag_1", lambda d: d["psc_flag"] == 1, 25),
    ("B_psc_flag_0", lambda d: d["psc_flag"] == 0, 25),
    ("C_enclave", lambda d: d["enclave_flag"] == 1, 20),
    ("D_guard_service", lambda d: d["guard_service_flag"] == 1, 20),
    ("E_hardening", lambda d: d["hardening_flag"] == 1, 20),
    ("F_enclave_candidates_only",
     lambda d: (d["enclave_flag_broad"] == 1) & (d["enclave_flag"] == 0), 20),
]


def load_module(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pct(num, den) -> str:
    return f"{100 * num / den:.1f}%" if den else "n/a"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% interval for a binomial proportion."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return (centre - half, centre + half)


def md_table(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row.values) + " |")
    return "\n".join(lines)


def rate_cell(s: pd.Series) -> str:
    n_obs = int(s.notna().sum())
    return f"{int(s.sum()):,} ({pct(s.sum(), n_obs)})" if n_obs else "n/a"


def clean_snippet(text) -> str:
    return re.sub(r"\s+", " ", str(text)).replace("|", "/").strip()


def file_provenance(path: Path) -> str:
    data = path.read_bytes()
    return (f"`{path.relative_to(REPO_ROOT).as_posix()}`: {len(data):,} bytes, "
            f"sha256 {hashlib.sha256(data).hexdigest()[:16]}..., "
            f"{len(pd.read_parquet(path)):,} rows")


def rates_by(df: pd.DataFrame, key: str) -> pd.DataFrame:
    rows = []
    for k, g in df.groupby(key, dropna=False):
        res = g[g["is_residential"] == 1]
        rows.append({
            key: "NA" if pd.isna(k) else k,
            "rows": f"{len(g):,}",
            "desc NA": pct(g["psc_flag"].isna().sum(), len(g)),
            "psc_flag": rate_cell(g["psc_flag"]),
            "psc_flag (residential)": rate_cell(res["psc_flag"]),
            "enclave": rate_cell(g["enclave_flag"]),
            "guard service": rate_cell(g["guard_service_flag"]),
            "hardening": rate_cell(g["hardening_flag"]),
        })
    return pd.DataFrame(rows)


def draw_samples(post: pd.DataFrame) -> pd.DataFrame:
    """One row per listing (earliest described capture), then each sample."""
    base = post[post["psc_flag"].notna()].sort_values(["p24_id", "snapshot_date"])
    base = base.drop_duplicates("p24_id")
    parts = []
    for name, rule, n in SAMPLES:
        pool = base[rule(base).fillna(False)]
        parts.append(pool.sample(min(n, len(pool)), random_state=SEED).assign(sample=name))
    return pd.concat(parts, ignore_index=True)


def data_dictionary() -> str:
    lines = ["## 1. Data dictionary\n",
             "Flags are nullable Int64: 1/0 when the text is observed, NA when it is "
             "missing (blank, punctuation-only, or a portal placeholder; "
             "`utils/text_utils.is_missing_text`). All patterns are case-insensitive "
             "regexes from `scripts/scraping/config.py`.\n",
             "### Location and listing columns (03)\n",
             md_table(pd.DataFrame([
                 ("p24_id / listing_id", "Property24 listing number (7+ digit last URL "
                  "segment). listing_id == p24_id; old URL hash kept as url_hash."),
                 ("snapshot_date", "Archive capture date YYYYMMDD (not a listing date)."),
                 ("first_captured / last_captured / n_snapshots", "Min / max capture date "
                  "and number of distinct capture dates per p24_id."),
                 ("city", "Study metro from the URL town slug via P24_TOWN_TO_METRO ("
                  + ", ".join(f"{k}->{v}" for k, v in P24_TOWN_TO_METRO.items()
                              if k.replace("-", " ").title() != v) + "; others identity)."),
                 ("city_target", "Old `city`: the scrape-target label (wrong for Durbanville)."),
                 ("city_url / suburb_url / province_url", "Town / suburb / province parsed "
                  "from the URL by exact segment. Geocoding must use these."),
                 ("suburb_canonical", "Modal suburb_url per p24_id (latest capture breaks ties)."),
                 ("property_use", "residential (apartment, house, townhouse, or title words "
                  "cluster/complex/simplex/duplex/...), commercial (commercial/industrial/"
                  "office/retail/warehouse), farm_land (farm, land, smallholding, plot); NA "
                  "for generic 'Property for sale' titles."),
                 ("is_residential / is_commercial", "0/1 from property_use; NA if it is NA."),
             ], columns=["column", "definition"])) + "\n",
             "### PSC columns (04)\n"]
    rows = [("psc_flag", "v1 plan-scope: 1 if psc_score > 0."),
            ("psc_score", "v1: matches across the five v1 groups + distinct companies.")]
    for g, pats in ALL_PSC_KEYWORD_GROUPS.items():
        rows.append((g, "v1 group: " + "; ".join(f"`{p}`" for p in pats)))
    rows.append(("psc_companies", "Pipe-separated names: "
                 + ", ".join(n for n, _, _ in PSC_COMPANIES)
                 + ". Word boundaries; brand spans counted once."))
    for construct, comps in CONSTRUCT_COMPONENTS.items():
        for comp, pats in comps.items():
            rows.append((comp, f"v2 component of {construct}: "
                         + "; ".join(f"`{p}`" for p in pats)))
    rows += [
        ("enclave_flag", "security_estate_v2 OR boom_gate_v2."),
        ("enclave_flag_broad", "enclave_flag OR " + " OR ".join(ENCLAVE_BROAD_CANDIDATES) + "."),
        ("guard_service_flag", "armed_response_v2 OR any company."),
        ("hardening_flag", "electric_fence_v2 OR access_control_v2."),
        ("psc_flag_v2", "enclave_flag OR guard_service_flag OR hardening_flag."),
    ]
    for cand, pat in CANDIDATE_PHRASES.items():
        rows.append((cand, f"candidate phrase: `{pat}`"))
    for weak, pats in WEAK_INDICATOR_GROUPS.items():
        rows.append((weak, "weak indicator, in no flag or score: "
                     + "; ".join(f"`{p}`" for p in pats)))
    rows += [
        ("psc_flag_title / psc_score_title", "v1 patterns applied to `title`."),
        ("psc_flag_any", "1 if psc_flag == 1 or psc_flag_title == 1; 0 if psc_flag == 0 "
         "and the title is not flagged; NA otherwise (a title alone never gives 0)."),
    ]
    lines.append(md_table(pd.DataFrame(rows, columns=["column", "definition"]).assign(
        definition=lambda d: d["definition"].str.replace("|", "\\|", regex=False))) + "\n")
    return "\n".join(lines)


def precision_section(samples: pd.DataFrame) -> tuple[str, dict]:
    out = ["## 8. Precision review (MODEL-CODED, pending user confirmation)\n"]
    if not LABELS.exists():
        out.append(f"Label file `{LABELS.name}` not found; samples not coded.\n")
        return "\n".join(out), {}
    labels = pd.read_csv(LABELS, dtype={"p24_id": str, "snapshot_date": str})
    s = samples.merge(labels.drop(columns=["sample"], errors="ignore"),
                      on=["p24_id", "snapshot_date"], how="left")
    n_uncoded = int(s["enclave"].isna().sum())
    coder = labels["coder"].iloc[0] if "coder" in labels.columns else "unknown"
    out.append(f"Coder: **{coder}**. Each sampled description was read in full and coded "
               f"for what it actually states: `enclave` (the property is inside a gated / "
               f"access-controlled estate or complex), `guard_service` (guards, "
               f"armed response or a named PSC serve the property), `hardening` (electric "
               f"fence, access-control technology, security walls on the property or "
               f"building), `commercial` (non-residential use). `not PSC` = none of the "
               f"first three. The user should confirm or overturn these codes by editing "
               f"`{LABELS.relative_to(REPO_ROOT).as_posix()}` and re-running this script. "
               f"Uncoded sampled rows: {n_uncoded}.\n")
    out.append("Caveats: (i) coding was **not blind**, since the coder saw the flag values "
               "and wrote the patterns, so the estimates below are upper bounds; (ii) "
               "keyword precision is high by construction ('24 hour security' does state a "
               "guard). The substantive question is **which construct** a flag measures: "
               "compare the enclave and commercial rows; (iii) 'secure complex' / "
               "'security complex' were coded as enclaves on the conventional South African "
               "meaning (a unit complex with a controlled gate), and the user should confirm; "
               "(iv) n = 20-25 per sample, so the intervals are wide.\n")
    for c in LABEL_COLS:
        s[c] = s[c].fillna(0).astype(int)
    s["any_psc"] = s[["enclave", "guard_service", "hardening"]].max(axis=1)

    def row(measure, sample, truth, sub=None):
        d = s[s["sample"] == sample] if sub is None else sub
        k, n = int(d[truth].sum()), len(d)
        lo, hi = wilson(k, n)
        return {"measure": measure, "sample": sample, "n": n, "true": k,
                "rate": pct(k, n), "95% Wilson CI": f"{100 * lo:.0f}-{100 * hi:.0f}%"}

    a = s[s["sample"] == "A_psc_flag_1"]
    a_res_true = a.assign(res_psc=(a["any_psc"] == 1) & (a["commercial"] == 0))
    stats = [
        row("psc_flag precision: any PSC construct", "A_psc_flag_1", "any_psc"),
        row("psc_flag precision: residential PSC (any construct, not commercial)",
            "A_psc_flag_1", "res_psc", a_res_true),
        row("psc_flag precision: enclave", "A_psc_flag_1", "enclave"),
        row("psc_flag == 0: share that are PSC (miss rate)", "B_psc_flag_0", "any_psc"),
        row("enclave_flag precision", "C_enclave", "enclave"),
        row("guard_service_flag precision", "D_guard_service", "guard_service"),
        row("hardening_flag precision", "E_hardening", "hardening"),
        row("candidate-only rows (enclave_flag_broad = 1, enclave_flag = 0): enclave",
            "F_enclave_candidates_only", "enclave"),
        row("share commercial among psc_flag == 1", "A_psc_flag_1", "commercial"),
        row("share commercial among guard_service_flag == 1", "D_guard_service",
            "commercial"),
    ]
    out.append(md_table(pd.DataFrame(stats)) + "\n")
    out.append("Samples: one row per listing (earliest described capture), "
               f"`random_state={SEED}`; A/B are 25 each, C-F 20 each (C-F may overlap A).\n")
    summary = {r["measure"]: r for r in stats}

    out.append("### Coded samples\n")
    for name, _, _ in SAMPLES:
        d = s[s["sample"] == name]
        tab = []
        for i, (_, r) in enumerate(d.iterrows(), 1):
            text = str(r["description"])
            tab.append({"#": i, "p24_id": r["p24_id"], "city": r["city"],
                        "use": r.get("property_use", ""),
                        "flags e/g/h": f"{r['enclave_flag']}/{r['guard_service_flag']}/"
                                       f"{r['hardening_flag']}",
                        "coded e/g/h/c": f"{r['enclave']}/{r['guard_service']}/"
                                         f"{r['hardening']}/{r['commercial']}",
                        "note": "" if pd.isna(r.get("note")) else clean_snippet(r["note"]),
                        "snippet": clean_snippet(text[:SNIPPET_CHARS])
                        + ("..." if len(text) > SNIPPET_CHARS else "")})
        out.append(f"#### {name} (n = {len(d)})\n")
        out.append(md_table(pd.DataFrame(tab)) + "\n")
    return "\n".join(out), summary


def main():
    parser = argparse.ArgumentParser(description="Write the scrape audit report")
    parser.add_argument("--export-samples", help="Write full-text samples to this CSV")
    args = parser.parse_args()

    merge = load_module("03_merge_deduplicate.py", "merge_deduplicate")
    out = []

    raw_files = sorted(RAW_DIR.glob("listings_archive_*.parquet")) \
        + sorted(RAW_DIR.glob("listings_live_*.parquet"))
    raw = pd.concat([pd.read_parquet(f) for f in raw_files], ignore_index=True)
    raw_pid = raw["url"].map(extract_p24_id)
    kinds = raw.loc[raw_pid.isna(), "url"].map(merge.classify_nonlisting).value_counts()
    pre_all = pd.read_parquet(PRE_ALL)
    pre_cls = pd.read_parquet(PRE_CLS)
    pre_pid = pre_all["url"].map(extract_p24_id)
    post_all = pd.read_parquet(RAW_DIR / "listings_all.parquet")
    post = pd.read_parquet(LISTINGS_CLASSIFIED)
    stubs = pd.read_parquet(STUBS)
    samples = draw_samples(post)
    if args.export_samples:
        samples[["sample", "p24_id", "snapshot_date", "city", "property_use", "psc_flag",
                 "enclave_flag", "enclave_flag_broad", "guard_service_flag", "hardening_flag",
                 "description"]].to_csv(args.export_samples, index=False)
        logger.info(f"Exported {len(samples)} sampled rows to {args.export_samples}")

    # --- Header and provenance ------------------------------------------
    out.append("# Scrape audit: dedup, location and PSC classification fixes (2026-09-29)\n")
    out.append("Generated by `scripts/scraping/audit_classification.py` (no network) with "
               f"Python {platform.python_version()}, pandas {pd.__version__}; pinned "
               "versions in `scripts/scraping/requirements-lock.txt` (Python >= 3.10). "
               "Post-fix figures come from re-running `03_merge_deduplicate.py` then "
               "`04_classify_psc.py` (revision after coder-critic round 1).\n")
    out.append("**Pre-fix backups (provenance).** Copied by the orchestrator at "
               "2026-09-29 18:00 from `data/raw/scraping/listings_all.parquet` "
               "(written 2026-04-01 08:53 by the original 03) and "
               "`listings_classified.parquet` (2026-04-01 10:29, original 04), before any "
               "re-run. Their byte sizes (4,372,307 and 4,383,946) equal those of the two "
               "files as listed on disk before the re-run.\n")
    out.append(f"- {file_provenance(PRE_ALL)}\n- {file_provenance(PRE_CLS)}\n")
    out.append(data_dictionary())

    # --- 2. Row counts -----------------------------------------------------
    n_listing_raw = int(raw_pid.notna().sum())
    not_found = int(raw.loc[raw_pid.notna(), "title"].fillna("")
                    .str.match(merge.NOT_FOUND_TITLE_RE).sum())
    out.append("## 2. Row counts\n")
    out.append(md_table(pd.DataFrame([
        ("Raw archive/live rows (all year files)", f"{len(raw):,}", f"{len(raw):,}"),
        ("Rows in listings_all.parquet", f"{len(pre_all):,}", f"{len(post_all):,}"),
        ("...non-listing pages (no 7+ digit id)", f"{int(pre_pid.isna().sum()):,}",
         f"{int(post_all['p24_id'].isna().sum()):,}"),
        ("Unique listing_id (pre: URL hash; post: p24_id)",
         f"{pre_all['listing_id'].nunique():,}", f"{post_all['listing_id'].nunique():,}"),
        ("Unique p24_id", f"{pre_pid.nunique():,}", f"{post_all['p24_id'].nunique():,}"),
    ], columns=["stage", "pre-fix", "post-fix"])) + "\n")
    out.append(f"Flow: {len(raw):,} raw rows -> remove {int(raw_pid.isna().sum()):,} "
               f"non-listing pages -> {n_listing_raw:,} -> drop {not_found:,} 'Listing Not "
               f"Found' pages (expired; no text or price) -> drop "
               f"{n_listing_raw - not_found - len(post_all):,} duplicate (p24_id, "
               f"snapshot_date) rows -> {len(post_all):,} rows / "
               f"{post_all['p24_id'].nunique():,} listings.\n")
    out.append(md_table(kinds.rename_axis("non-listing page type").reset_index(name="rows"))
               + "\n")
    snaps = post_all.drop_duplicates("p24_id")["n_snapshots"].value_counts().sort_index()
    out.append("Captures per listing: " + ", ".join(f"{k}: {v:,}" for k, v in snaps.items())
               + f" ({pct(snaps.get(1, 0), snaps.sum())} captured once, so this is close "
               f"to a cross-section).\n")

    # ListingNumber stubs (B7)
    st1 = stubs.drop_duplicates("p24_id")
    overlap = stubs.merge(post_all[["p24_id", "price"]].drop_duplicates("p24_id"),
                          on="p24_id", suffixes=("", "_listing"))
    both_price = overlap["price"].notna() & overlap["price_listing"].notna()
    same_price = int((both_price & overlap["price"].eq(overlap["price_listing"])).sum())
    teaser = stubs["page_snippet"].fillna("").str.endswith("...")
    desc_overlap = stubs.merge(
        post_all[["p24_id", "description"]].dropna().drop_duplicates("p24_id"), on="p24_id")
    same_text = int(desc_overlap["page_snippet"].eq(desc_overlap["description"]).sum())
    out.append("### `?ListingNumber=` pages (recovered as stubs, not merged)\n")
    out.append(
        f"{len(stubs):,} capture rows / {st1['p24_id'].nunique():,} listing numbers. "
        f"Only {int(st1['in_listings_all'].sum()):,} "
        f"({pct(st1['in_listings_all'].sum(), len(st1))}) of the embedded numbers are "
        f"already a p24_id in listings_all, so these pages point to ~"
        f"{int((~st1['in_listings_all']).sum()):,} otherwise unseen listings. Where both "
        f"are observed, the page price equals the listing's price in {same_price} of "
        f"{int(both_price.sum())} overlapping rows, so the price belongs to the embedded "
        f"listing. The text does not: {pct(teaser.sum(), stubs['page_snippet'].notna().sum())} "
        f"of non-empty snippets are truncated sidebar teasers ('... ') such as property "
        f"news; the rest are other listings' card headings (e.g. a Mossel Bay house on a "
        f"Pretoria page). {same_text} of {len(desc_overlap)} snippets with a described "
        f"counterpart equal that listing's description. Decision: keep them out of "
        f"listings_all (no usable description, city-level location only) and write them to "
        f"`data/raw/scraping/listing_stubs_listingnumber.parquet` (p24_id, capture date, "
        f"price, target city, page title, page snippet). They can seed a re-fetch of the "
        f"real listing pages if the design needs them.\n")
    ex = stubs[stubs["page_snippet"].notna()].sample(10, random_state=SEED)
    out.append(md_table(pd.DataFrame({
        "p24_id": ex["p24_id"], "in listings_all": ex["in_listings_all"],
        "price": ex["price"], "page_title": ex["page_title"],
        "page_snippet": ex["page_snippet"].map(lambda t: clean_snippet(t)[:160]),
    })) + "\n")

    # --- 3. Location --------------------------------------------------------
    out.append("## 3. Location repair\n")
    corr = post_all[post_all["city"].ne(post_all["city_target"])]
    out.append(f"`city` now comes from the URL town segment. {len(corr):,} rows changed "
               f"from their scrape-target label (`city_target`):\n")
    out.append(md_table(corr.groupby(["city_target", "city_url", "city"]).size()
                        .reset_index(name="rows")) + "\n")
    out.append("Rows by study metro (post-fix `city`) and property use:\n")
    out.append(md_table(pd.crosstab(post_all["city"], post_all["property_use"].fillna("NA"),
                                    margins=True).reset_index()) + "\n")

    # --- 4. Headline rates ------------------------------------------------
    n = len(post)
    na_desc = int(post["psc_flag"].isna().sum())
    res = post[post["is_residential"] == 1]
    out.append("## 4. Headline flag rates (description-based; NA excluded)\n")
    head = []
    for col, label in [("psc_flag", "psc_flag (v1, plan scope)"),
                       ("psc_flag_v2", "psc_flag_v2 (any construct)"),
                       ("enclave_flag", "enclave_flag"),
                       ("enclave_flag_broad", "enclave_flag_broad (+ security/secure complex, "
                        "security village)"),
                       ("guard_service_flag", "guard_service_flag"),
                       ("hardening_flag", "hardening_flag")]:
        head.append({"measure": label, "all listings": rate_cell(post[col]),
                     "residential only": rate_cell(res[col])})
    out.append(md_table(pd.DataFrame(head)) + "\n")
    out.append(f"Rows with NA description flags: {na_desc:,} of {n:,} "
               f"({pct(na_desc, n)}); residential: {int(res['psc_flag'].isna().sum()):,} of "
               f"{len(res):,}. Pre-fix psc_flag coded these as 0 "
               f"({int(pre_cls['psc_flag'].sum()):,} / {len(pre_cls):,} = "
               f"{pct(pre_cls['psc_flag'].sum(), len(pre_cls))} flagged, all rows).\n")
    out.append(f"Title-based `psc_flag_title` is 1 on {int(post['psc_flag_title'].sum())} "
               f"rows (archived titles are templated), so `psc_flag_any` "
               f"({rate_cell(post['psc_flag_any'])}, NA "
               f"{int(post['psc_flag_any'].isna().sum()):,}) equals psc_flag here; it is not "
               f"a headline measure.\n")

    pre_m = pre_cls.assign(p24_id=pre_cls["url"].map(extract_p24_id))
    pre_m = pre_m[pre_m["p24_id"].notna()].drop_duplicates(["p24_id", "snapshot_date"])
    m = post[["p24_id", "snapshot_date", "psc_flag"] + GROUPS].merge(
        pre_m[["p24_id", "snapshot_date", "psc_flag"] + GROUPS],
        on=["p24_id", "snapshot_date"], suffixes=("", "_pre"))
    trans = pd.crosstab(m["psc_flag_pre"].astype("string").fillna("NA"),
                        m["psc_flag"].astype("string").fillna("NA"))
    out.append(f"psc_flag pre (rows) vs post (columns) on {len(m):,} matched rows:\n")
    out.append(md_table(trans.rename_axis(None, axis=1).reset_index()
                        .rename(columns={"psc_flag_pre": "pre \\ post"})) + "\n")
    up = m[(m["psc_flag"] == 1) & (m["psc_flag_pre"] == 0)]
    down = m[(m["psc_flag"] == 0) & (m["psc_flag_pre"] == 1)]
    out.append(md_table(pd.DataFrame([{
        "v1 group": g,
        "0->1 rows, group newly on": int(((up[g] == 1) & (up[f"{g}_pre"] == 0)).sum()),
        "1->0 rows, group newly off": int(((down[g] == 0) & (down[f"{g}_pre"] == 1)).sum()),
    } for g in GROUPS])) + "\n")
    out.append("0->1: the 'fingerprin' fix. 1->0: rows whose only v1 match was intercom, "
               "walls, bare 'guarded' or a false company match, all removed by design.\n")

    # --- 5. Groups, components, candidates ----------------------------------
    out.append("## 5. Rates by group, component, candidate and weak indicator\n")
    comp_cols = [c for comps in CONSTRUCT_COMPONENTS.values() for c in comps]
    rows = []
    for col in GROUPS + comp_cols + list(CANDIDATE_PHRASES) + list(WEAK_INDICATOR_GROUPS):
        kind = ("v1 group" if col in GROUPS else "v2 component" if col in comp_cols
                else "candidate" if col.startswith("cand_") else "weak")
        rows.append({"column": col, "kind": kind, "all": rate_cell(post[col]),
                     "residential": rate_cell(res[col])})
    out.append(md_table(pd.DataFrame(rows)) + "\n")
    comp = Counter(x for e in post["psc_companies"].dropna() if e for x in e.split("|"))
    pre_comp = Counter(x for e in pre_cls["psc_companies"].dropna() if e for x in e.split("|"))
    out.append("Company mentions (rows): pre-fix "
               + (", ".join(f"{k} {v}" for k, v in pre_comp.most_common()) or "none")
               + "; post-fix " + (", ".join(f"{k} {v}" for k, v in comp.most_common())
                                  or "none") + ".\n")

    # --- 6/7. By metro, use, year --------------------------------------------
    out.append("## 6. Rates by study metro and property use\n")
    out.append(md_table(rates_by(post, "city").sort_values("city")) + "\n")
    out.append(md_table(rates_by(post, "property_use")) + "\n")
    out.append("## 7. Rates by capture year\n")
    post_y = post.assign(year=post["snapshot_date"].astype(str).str[:4])
    out.append(md_table(rates_by(post_y, "year").sort_values("year")) + "\n")

    # --- 8. Precision ------------------------------------------------------
    prec_md, prec = precision_section(samples)
    out.append(prec_md)

    # --- 9. Issues ---------------------------------------------------------
    early = post_y["year"].between("2009", "2012")
    out.append("## 9. Issues for downstream users\n")
    out.append(
        f"1. **Missing descriptions cluster in early years**: "
        f"{pct(post_y.loc[early, 'psc_flag'].isna().sum(), early.sum())} of 2009-2012 rows "
        f"vs {pct(post_y.loc[~early, 'psc_flag'].isna().sum(), (~early).sum())} from 2013 "
        f"(older page templates). Year comparisons must use described rows only.\n"
        f"2. **A 0 flag means 'not advertised', not 'absent'.** Flag rates depend on "
        f"description length and portal templates.\n"
        f"3. **Constructs differ.** psc_flag pools enclave, guard-service and hardening "
        f"terms and includes commercial listings; see section 8 for precision by "
        f"construct and residential share. Choosing the construct is a strategist "
        f"decision; all components and candidate phrases are separate columns.\n"
        f"4. **05_geocode.py is blocked** until it queries suburb_canonical + city_url + "
        f"province_url (header note added). The old `city` sent Durbanville to Durban.\n"
        f"5. **00_archive_discovery.py** now labels by exact URL segment; the existing "
        f"url_inventory.jsonl still carries the old labels (03 repairs them).\n")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(out), encoding="utf-8", newline="\n")
    logger.info(f"Wrote {REPORT_PATH}")
    for k, v in prec.items():
        logger.info(f"  {k}: {v['true']}/{v['n']} = {v['rate']} ({v['95% Wilson CI']})")


if __name__ == "__main__":
    main()
