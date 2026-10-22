# ============================================================
# utils/text_utils.py — shared text helpers for the scraping pipeline
# Used by: 03_merge_deduplicate.py (dedup tie-break), 04_classify_psc.py
#          (NA flags), audit_classification.py. One definition of
#          "missing text" so the steps cannot disagree.
# Requires: Python >= 3.10
# ============================================================

import re

import pandas as pd

# Portal placeholders seen in scraped descriptions. They say nothing about
# the property, so they count as missing, like a blank field.
MISSING_TEXT_PLACEHOLDERS = frozenset({
    "no description specified",
    "no description",
    "no comments",
})

_NON_WORD = re.compile(r"[\W_]+")


def is_missing_text(text) -> bool:
    """True for None/NA/NaN, blank or punctuation-only text, and known placeholders."""
    if text is None:
        return True
    try:
        if pd.isna(text):
            return True
    except (TypeError, ValueError):  # array-like input: not a scalar NA
        pass
    normalised = _NON_WORD.sub(" ", str(text)).strip().lower()
    return not normalised or normalised in MISSING_TEXT_PLACEHOLDERS


def count_informative(row: pd.Series) -> int:
    """Number of fields in a row that are not missing (strings via is_missing_text)."""
    n = 0
    for value in row:
        if isinstance(value, str):
            n += not is_missing_text(value)
        else:
            try:
                n += not pd.isna(value)
            except (TypeError, ValueError):
                n += 1
    return n
