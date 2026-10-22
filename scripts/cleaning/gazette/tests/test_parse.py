#!/usr/bin/env python3
# ============================================================
# test_parse.py
# Purpose: Regression tests for 03_parse_notices.parse_notice on real
#          gazette notice texts (one per stage x municipality where
#          available, sampled with seed 20260930 from the pilot output).
#          These pin current parser behaviour; they are not a validity
#          check — parse accuracy comes from the user-checked
#          data/cleaned/gazette/validation_sample.csv.
# Inputs:  tests/fixtures/notice_regression.json
# Usage:   py -3.12 scripts/cleaning/gazette/tests/test_parse.py
# ============================================================

import importlib.util
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG))

spec = importlib.util.spec_from_file_location("parse_notices", PKG / "03_parse_notices.py")
parse_notices = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parse_notices)

FIXTURE = json.loads((HERE / "fixtures" / "notice_regression.json").read_text(encoding="utf-8"))
FIELDS = ["stage", "municipality", "ref_number", "restriction_type", "validity_months"]


def _same(a, b) -> bool:
    missing = lambda x: x is None or (isinstance(x, float) and math.isnan(x))
    if missing(a) and missing(b):
        return True
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return a == b


def test_regression_fixture():
    failures = []
    for case in FIXTURE:
        got = parse_notices.parse_notice(case["text_clean"], case["notice_title"])
        for f in FIELDS:
            if not _same(got.get(f), case[f]):
                failures.append(f"{case['notice_id']}.{f}: expected {case[f]!r}, got {got.get(f)!r}")
    assert not failures, "\n".join(failures)


def test_missing_title_is_tolerated():
    got = parse_notices.parse_notice(FIXTURE[0]["text_clean"], None)
    assert got["stage"] == FIXTURE[0]["stage"]


def test_stage_labels_are_closed_set():
    allowed = {"intent", "final_approval", "extension", "renewal", "removal", "other", "unknown"}
    for case in FIXTURE:
        assert parse_notices.parse_notice(case["text_clean"], case["notice_title"])["stage"] in allowed


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS  {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")
