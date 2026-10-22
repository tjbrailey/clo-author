#!/usr/bin/env python3
# ============================================================
# scripts/cleaning/e3/01_extract_text.py
# Title:   Extract page-tagged text from every downloaded E3 PDF / HTML page
# Author:  data-engineer (PSC Exposure project)
# Date:    2026-09-30
# Purpose: WP5 step 2. Make every source searchable and citable by page, so the
#          hand-coded onset evidence (manual/onset_evidence.csv) can quote the
#          exact passage and page, and the parsers in 02 can read annexures.
# Inputs:  data/raw/e3/provenance.csv, data/raw/e3/docs/*
# Outputs: data/raw/e3/text/<source_id>.txt  ("=== PAGE n ===" separators)
#          data/raw/e3/text/_extract_log.csv  (pages, chars, sha256 of source)
# Usage:   py -3.12 scripts/cleaning/e3/01_extract_text.py
# ============================================================

from __future__ import annotations

import csv
import re
import sys
from html import unescape
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e3_config import PROVENANCE, RAW, RAW_TEXT  # noqa: E402


def pdf_text(path: Path) -> tuple[str, int]:
    parts = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            # x_tolerance 1.5 keeps table cells apart without splitting words
            txt = page.extract_text(x_tolerance=1.5) or ""
            parts.append(f"=== PAGE {i} ===\n{txt}")
        n = len(pdf.pages)
    return "\n".join(parts), n


def html_text(path: Path) -> str:
    h = path.read_text(encoding="utf-8", errors="ignore")
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    t = unescape(re.sub(r"<[^>]+>", " ", h))
    return "=== PAGE 1 ===\n" + re.sub(r"[ \t\r\f\v]+", " ", re.sub(r"\n\s*\n+", "\n", t))


def main() -> None:
    RAW_TEXT.mkdir(parents=True, exist_ok=True)
    with open(PROVENANCE, newline="", encoding="utf-8") as fh:
        prov = [r for r in csv.DictReader(fh) if r["local_path"]]
    log = []
    for r in prov:
        src = RAW / r["local_path"]
        out = RAW_TEXT / f"{r['source_id']}.txt"
        ext = src.suffix.lower()
        if ext not in (".pdf", ".html"):
            continue
        pages, note = 1, ""
        try:
            if ext == ".pdf":
                text, pages = pdf_text(src)
            else:
                text = html_text(src)
        except Exception as exc:  # corrupt / encrypted PDF: log, don't stop
            text, note = "", f"extract_error: {exc}"[:200]
        out.write_text(text, encoding="utf-8")
        chars = len(re.sub(r"=== PAGE \d+ ===|\s", "", text))
        if ext == ".pdf" and chars < 200 * max(pages, 1) * 0.1 and not note:
            note = "low_text_possibly_scanned"
        log.append(dict(source_id=r["source_id"], pages=pages, chars=chars,
                        sha256=r["sha256"], note=note))
    with open(RAW_TEXT / "_extract_log.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(log[0].keys()))
        w.writeheader()
        w.writerows(log)
    flagged = [x for x in log if x["note"]]
    print(f"extracted {len(log)} documents; flagged {len(flagged)}")
    for x in flagged:
        print(f"  {x['source_id']}: {x['note']}")


if __name__ == "__main__":
    main()
