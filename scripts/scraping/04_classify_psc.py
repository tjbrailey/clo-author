#!/usr/bin/env python3
# ============================================================
# 04_classify_psc.py
# Purpose: PSC / gated-community keyword classification of
#          listing descriptions (primary) and titles (separate).
# Inputs:  data/raw/scraping/listings_all.parquet (default)
#          OR --input [file]
# Outputs: data/raw/scraping/listings_classified.parquet
# Usage:   python3 scripts/scraping/04_classify_psc.py [--input FILE] [--output FILE]
#          (Windows: py -3.12 ...). Requires Python >= 3.10.
#
# Output columns (flags nullable Int64; NA = text missing):
#   v1, plan-scope dictionary (config.ALL_PSC_KEYWORD_GROUPS):
#     psc_flag = 1(psc_score > 0); psc_score = keyword matches in the
#     five groups + distinct companies; security_estate, boom_gate,
#     access_controlled, armed_response, electric_fence;
#     psc_companies (pipe-separated string).
#   v2, construct layer (config.CONSTRUCT_COMPONENTS):
#     component columns security_estate_v2, boom_gate_v2,
#     armed_response_v2, electric_fence_v2, access_control_v2;
#     enclave_flag       = security_estate_v2 | boom_gate_v2
#     enclave_flag_broad = enclave_flag | cand_security_complex
#                          | cand_secure_complex | cand_security_village
#     guard_service_flag = armed_response_v2 | any company
#     hardening_flag     = electric_fence_v2 | access_control_v2
#     psc_flag_v2        = enclave_flag | guard_service_flag | hardening_flag
#   Candidate phrases: cand_* (config.CANDIDATE_PHRASES), one 0/1 each.
#   Weak indicators (in no flag or score): intercom, walls.
#   Title: psc_flag_title, psc_score_title (v1 patterns on `title`).
#   psc_flag_any = 1 if psc_flag == 1 or psc_flag_title == 1;
#                  0 if psc_flag == 0 (description observed) and the
#                  title is not flagged; NA otherwise. A title alone
#                  never yields 0, because titles are templated.
#
# Revision 2026-09-29 (scrape audit + coder-critic round 1):
#   - Missing text (utils.text_utils.is_missing_text: NA, blank,
#     punctuation-only, portal placeholders) -> NA, not 0.
#   - Company names: word-boundary regex; a matched span is blanked
#     before later names are tried ("Fidelity ADT" counts once).
#   - Patterns compiled once at import.
# ============================================================

import argparse
import logging
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    RAW_DIR, LISTINGS_CLASSIFIED, PSC_COMPANIES, ALL_PSC_KEYWORD_GROUPS,
    CONSTRUCT_COMPONENTS, CANDIDATE_PHRASES, ENCLAVE_BROAD_CANDIDATES,
    WEAK_INDICATOR_GROUPS,
)
from utils.text_utils import is_missing_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def compile_patterns(keyword_list: list[str]) -> re.Pattern:
    # Wrap each fragment so alternations inside one pattern stay local.
    return re.compile("|".join(f"(?:{k})" for k in keyword_list), re.IGNORECASE)


# ---- Compiled once at import ------------------------------------------------
GROUP_COLS = list(ALL_PSC_KEYWORD_GROUPS)
GROUP_PATTERNS = {g: compile_patterns(kw) for g, kw in ALL_PSC_KEYWORD_GROUPS.items()}

COMPONENT_OF = {comp: construct for construct, comps in CONSTRUCT_COMPONENTS.items()
                for comp in comps}
COMPONENT_COLS = list(COMPONENT_OF)
COMPONENT_PATTERNS = {comp: compile_patterns(kw)
                      for comps in CONSTRUCT_COMPONENTS.values() for comp, kw in comps.items()}
CONSTRUCT_COLS = ["enclave_flag", "enclave_flag_broad", "guard_service_flag",
                  "hardening_flag", "psc_flag_v2"]

CANDIDATE_COLS = list(CANDIDATE_PHRASES)
CANDIDATE_PATTERNS = {c: re.compile(p, re.IGNORECASE) for c, p in CANDIDATE_PHRASES.items()}

WEAK_COLS = list(WEAK_INDICATOR_GROUPS)
WEAK_PATTERNS = {g: compile_patterns(kw) for g, kw in WEAK_INDICATOR_GROUPS.items()}

COMPANY_PATTERNS = [
    (name, re.compile(pattern, re.IGNORECASE if ignore_case else 0))
    for name, pattern, ignore_case in PSC_COMPANIES
]

INT_KEYS = (["psc_flag", "psc_score", *GROUP_COLS, *COMPONENT_COLS, *CONSTRUCT_COLS,
             *CANDIDATE_COLS, *WEAK_COLS])
RESULT_KEYS = INT_KEYS + ["psc_companies"]
TITLE_KEYS = {"psc_flag": "psc_flag_title", "psc_score": "psc_score_title"}


def find_psc_companies(text: str) -> str:
    """Pipe-separated PSC company names in text ('' if none); each span counted once."""
    found = []
    for name, pattern in COMPANY_PATTERNS:
        if pattern.search(text):
            found.append(name)
            # Blank the match so a sub-brand ("ADT" in "Fidelity ADT") is not re-counted
            text = pattern.sub(lambda m: " " * len(m.group(0)), text)
    return "|".join(found)


def classify_record(text) -> dict:
    """All description-level columns for one text. Missing text -> every value NA."""
    if is_missing_text(text):
        return {k: pd.NA for k in RESULT_KEYS}
    text = str(text)
    out = {}

    # v1 (plan scope)
    score = 0
    for group, pattern in GROUP_PATTERNS.items():
        n = len(pattern.findall(text))
        out[group] = int(n > 0)
        score += n
    companies = find_psc_companies(text)
    n_companies = len(companies.split("|")) if companies else 0
    score += n_companies
    out["psc_score"] = score
    out["psc_flag"] = int(score > 0)
    out["psc_companies"] = companies

    # v2 components, candidates, weak indicators
    for comp, pattern in COMPONENT_PATTERNS.items():
        out[comp] = int(bool(pattern.search(text)))
    for cand, pattern in CANDIDATE_PATTERNS.items():
        out[cand] = int(bool(pattern.search(text)))
    for weak, pattern in WEAK_PATTERNS.items():
        out[weak] = int(bool(pattern.search(text)))

    # v2 constructs
    def any_component(construct: str) -> int:
        return int(any(out[c] for c, k in COMPONENT_OF.items() if k == construct))

    out["enclave_flag"] = any_component("enclave")
    out["enclave_flag_broad"] = int(out["enclave_flag"]
                                    or any(out[c] for c in ENCLAVE_BROAD_CANDIDATES))
    out["guard_service_flag"] = int(any_component("guard_service") or n_companies > 0)
    out["hardening_flag"] = any_component("hardening")
    out["psc_flag_v2"] = int(out["enclave_flag"] or out["guard_service_flag"]
                             or out["hardening_flag"])
    return {k: out[k] for k in RESULT_KEYS}


def classify_series(texts: pd.Series) -> pd.DataFrame:
    """Classify a Series of texts into typed columns (Int64 flags, string companies)."""
    out = pd.DataFrame([classify_record(t) for t in texts], index=texts.index,
                       columns=RESULT_KEYS)
    for col in INT_KEYS:
        out[col] = out[col].astype("Int64")
    out["psc_companies"] = out["psc_companies"].astype("string")
    return out


def combine_any(desc_flag: pd.Series, title_flag: pd.Series) -> pd.Series:
    """1 if either source is 1; 0 only if the description is observed and 0; else NA."""
    one = desc_flag.eq(1).fillna(False) | title_flag.eq(1).fillna(False)
    zero = desc_flag.eq(0).fillna(False) & ~one
    out = pd.Series(pd.NA, index=desc_flag.index, dtype="Int64")
    out[one] = 1
    out[zero] = 0
    return out


def classify_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Add description, title and combined PSC columns to a listings frame."""
    drop = RESULT_KEYS + list(TITLE_KEYS.values()) + ["psc_flag_any"]
    df = df.drop(columns=[c for c in drop if c in df.columns]).copy()

    desc_cls = classify_series(df["description"])
    titles = df["title"] if "title" in df.columns else pd.Series(pd.NA, index=df.index)
    title_cls = classify_series(titles)[list(TITLE_KEYS)].rename(columns=TITLE_KEYS)

    out = pd.concat([df, desc_cls, title_cls], axis=1)
    out["psc_flag_any"] = combine_any(out["psc_flag"], out["psc_flag_title"])
    return out


def _rate(s: pd.Series) -> str:
    n_obs = int(s.notna().sum())
    if n_obs == 0:
        return "n/a (all NA)"
    return (f"{int(s.sum()):,} / {n_obs:,} ({100 * s.mean():.1f}%), "
            f"NA {int(s.isna().sum()):,}")


def main():
    parser = argparse.ArgumentParser(
        description="Classify PSC/gated community keywords in listings")
    parser.add_argument("--input", default=str(RAW_DIR / "listings_all.parquet"),
                        help="Input parquet file")
    parser.add_argument("--output", default=str(LISTINGS_CLASSIFIED),
                        help="Output parquet file")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        logger.error("Run 00_archive_discovery.py -> 01_archive_fetch.py -> "
                     "03_merge_deduplicate.py first.")
        sys.exit(1)

    df = pd.read_parquet(input_path)
    logger.info(f"Loaded {len(df):,} records from {input_path}")

    if "description" not in df.columns:
        logger.error("No 'description' column found in input parquet.")
        sys.exit(1)
    if "title" not in df.columns:
        logger.warning("No 'title' column found; title-based flags will be NA.")

    logger.info("Running PSC keyword classification (description + title)...")
    df = classify_frame(df)

    df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")
    logger.info(f"Saved {len(df):,} classified records to {output_path}")

    # Summary (rates over non-missing rows)
    logger.info("=== PSC classification summary ===")
    for col in ["psc_flag", "psc_flag_v2", *CONSTRUCT_COLS[:-1], "psc_flag_title",
                "psc_flag_any"]:
        logger.info(f"  {col:22s}: {_rate(df[col])}")
    logger.info("v1 groups / weak indicators (description):")
    for col in GROUP_COLS + WEAK_COLS:
        tag = "  [weak, excluded]" if col in WEAK_COLS else ""
        logger.info(f"  {col:22s}: {_rate(df[col])}{tag}")
    if "is_residential" in df.columns:
        res = df[df["is_residential"] == 1]
        logger.info(f"Residential only: psc_flag {_rate(res['psc_flag'])}")
    if "city" in df.columns:
        rates = df.groupby("city")["psc_flag"].mean().sort_values(ascending=False)
        logger.info("psc_flag by city (described rows): "
                    + ", ".join(f"{k} {100 * v:.1f}%" for k, v in rates.items()))
    companies = Counter(name for entry in df["psc_companies"].dropna() if entry
                        for name in entry.split("|"))
    if companies:
        logger.info("Companies mentioned: "
                    + ", ".join(f"{k} {v}" for k, v in companies.most_common(10)))


if __name__ == "__main__":
    main()
