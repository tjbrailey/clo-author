#!/usr/bin/env python3
# ============================================================
# scripts/cleaning/e3/03_extract_bp_snippets.py
# Title:   Pull dated / classification passages out of SRA business plans
# Author:  data-engineer (PSC Exposure project)
# Date:    2026-09-30
# Purpose: WP5 step 4. Business plans are onset priority 3 (memo s5.4) and the
#          main source for establishment history, term number, consent votes,
#          property mix (residential vs non-residential) and patrol provision.
#          This script only *finds* candidate passages (with page numbers);
#          the coding decisions are made by hand in manual/onset_evidence.csv
#          and manual/sra_classification.csv, each citing a passage found here.
# Inputs:  data/raw/e3/text/bp_*.txt, manual/sra_crosswalk.csv
# Outputs: data/cleaned/e3/intermediate/bp_snippets.csv
# Usage:   py -3.12 scripts/cleaning/e3/03_extract_bp_snippets.py
# ============================================================

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e3_config import INTERMEDIATE, MANUAL, RAW_TEXT  # noqa: E402

PATTERNS = {
    "establishment": r"establish\w*|incorporat\w*|inception|commenc\w*|came into (?:being|operation)"
                     r"|was (?:formed|founded|approved|launched)|since (?:its )?(?:19|20)\d\d",
    "term": r"(?:first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)\s+(?:five[- ]year\s+)?term"
            r"|term of five|renew\w*|further (?:period|term)",
    "consent": r"\d{1,3}(?:[.,]\d+)?\s?%[^.]{0,80}(?:support|consent|in favour|vot)"
               r"|(?:support|consent|vot)\w*[^.]{0,80}\d{1,3}(?:[.,]\d+)?\s?%",
    "property_mix": r"\d{1,3}(?:[.,]\d+)?\s?%[^.]{0,60}(?:residential|non-residential|commercial"
                    r"|business|industrial)|(?:residential|commercial|industrial)[^.]{0,40}"
                    r"\d{1,3}(?:[.,]\d+)?\s?%",
    "patrol": r"patrol\w*|security (?:service|provider|company|officer)|armed response"
              r"|neighbourhood watch|public safety",
}


def main() -> None:
    xw = pd.read_csv(MANUAL / "sra_crosswalk.csv").dropna(subset=["bp_source_id"])
    rows = []
    for r in xw.itertuples():
        text = (RAW_TEXT / f"{r.bp_source_id}.txt").read_text(encoding="utf-8")
        for pg_no, pg in re.findall(r"=== PAGE (\d+) ===\n(.*?)(?==== PAGE|\Z)", text, re.S):
            flat = re.sub(r"\s+", " ", pg)
            for kind, pat in PATTERNS.items():
                for m in re.finditer(pat, flat, re.I):
                    s = flat[max(0, m.start() - 220): m.end() + 220]
                    has_year = bool(re.search(r"\b(19[89]\d|20[0-2]\d)\b", s))
                    if kind in ("establishment", "term") and not has_year:
                        continue
                    rows.append(dict(sra_key=r.sra_key, source_id=r.bp_source_id,
                                     page=int(pg_no), kind=kind, snippet=s))
    df = pd.DataFrame(rows).drop_duplicates(["sra_key", "page", "kind", "snippet"])
    INTERMEDIATE.mkdir(parents=True, exist_ok=True)
    df.to_csv(INTERMEDIATE / "bp_snippets.csv", index=False)
    print(df.groupby("kind").size().to_string())
    print("SRAs with >=1 dated establishment/term snippet:",
          df[df.kind.isin(["establishment", "term"])].sra_key.nunique(), "of", len(xw))


if __name__ == "__main__":
    main()
