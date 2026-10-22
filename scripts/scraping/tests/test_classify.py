#!/usr/bin/env python3
# ============================================================
# tests/test_classify.py
# Purpose: Regression tests for the 2026-09-29 scrape-audit fixes in
#          03_merge_deduplicate.py, 04_classify_psc.py, utils/ and 00.
# Inputs:  tests/fixtures/classify_cases.csv (labelled snippets);
#          otherwise synthetic strings/frames only. No network, no data.
# Outputs: PASS lines; exits non-zero on the first failure.
# Usage:   python3 scripts/scraping/tests/test_classify.py
#          (Windows: py -3.12 ...). Requires Python >= 3.10.
# ============================================================

import csv
import importlib.util
import sys
from pathlib import Path

import pandas as pd

SCRAPING_DIR = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "classify_cases.csv"
sys.path.insert(0, str(SCRAPING_DIR))

from utils.text_utils import is_missing_text  # noqa: E402
from utils.url_utils import (  # noqa: E402
    extract_p24_id, extract_embedded_listing_number, normalise_url, parse_location_slugs,
)


def load_module(filename: str, name: str):
    """Import a script whose filename starts with a digit."""
    spec = importlib.util.spec_from_file_location(name, SCRAPING_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


merge = load_module("03_merge_deduplicate.py", "merge_deduplicate")
classify = load_module("04_classify_psc.py", "classify_psc")
discovery = load_module("00_archive_discovery.py", "archive_discovery")

BASE = "www.property24.com/for-sale/durbanville/durbanville/western-cape/9520/101246301"


def rec(text: str) -> dict:
    return classify.classify_record(text)


# ---------------------------------------------------------------------------
# Labelled fixture (~50 snippets): v1 psc_flag and the three v2 constructs
# ---------------------------------------------------------------------------
def test_labelled_fixture():
    with open(FIXTURE, newline="", encoding="utf-8") as f:
        cases = list(csv.DictReader(f))
    assert len(cases) >= 50, len(cases)
    failures = []
    for case in cases:
        r = rec(case["text"])
        for key in ["psc_flag", "enclave_flag", "guard_service_flag", "hardening_flag"]:
            if r[key] != int(case[key]):
                failures.append(f"{key}={r[key]} (want {case[key]}): {case['text']!r}")
    assert not failures, "\n".join(failures)


# ---------------------------------------------------------------------------
# Specific keyword behaviour
# ---------------------------------------------------------------------------
def test_fingerprint_v1_and_v2():
    for s in ["Fingerprint access", "entry by fingerprints only", "fingerprint-access"]:
        r = rec(s)
        assert r["access_controlled"] == 1 and r["psc_flag"] == 1, s
    r = rec("finger print access gate")
    assert r["psc_flag"] == 0 and r["access_control_v2"] == 1 and r["cand_finger_print"] == 1


def test_company_matching():
    f = classify.find_psc_companies
    assert f("strict enforcement of body corporate rules") == ""
    assert f("the HOA will enforce the rules") == ""
    assert f("armed response by Enforce") == "Enforce"
    assert f("ON BEACH ROADThis spacious flat") == ""
    assert f("holds a valid Fidelity Fund Certificate") == ""
    assert f("holds a valid FIDELITY FUND CERTIFICATE") == ""
    assert f("OWN 10% SHARE IN SASCON FARM") == ""
    assert f("coin operated laundry") == ""
    assert f("ADT alarm and Fidelity armed response") == "ADT|Fidelity"
    assert f("adt alarm linked") == "ADT"
    # ALL-CAPS listings and the merged brand
    assert f("FIDELITY ARMED RESPONSE") == "Fidelity"
    assert f("GUARDSMAN PATROLS") == "Guardsman"
    assert f("Fidelity ADT armed response") == "Fidelity ADT"
    assert rec("Fidelity ADT armed response")["psc_score"] == 2  # 1 phrase + 1 company


def test_weak_indicators_excluded():
    r = rec("Two bedroom flat with intercom, boundary wall and high walls")
    assert r["psc_flag"] == 0 and r["psc_score"] == 0 and r["psc_flag_v2"] == 0
    assert r["intercom"] == 1 and r["walls"] == 1


def test_guarded_needs_security_context():
    assert rec("Fully burglar guarded windows")["psc_flag"] == 0
    assert rec("well guarded")["psc_flag"] == 0
    assert rec("24hr guarded security and pool")["guard_service_flag"] == 1
    assert rec("guarded access control at the entrance")["armed_response"] == 1


def test_24h_positive_and_negative():
    for s in ["24hr security", "24 hr security", "24-hour security", "24 hours security",
              "24/7 security", "24 hour manned security", "24h security"]:
        assert rec(s)["guard_service_flag"] == 1, s
    for s in ["open 24 hours", "24 hour access to the gym", "24 hour concierge",
              "24/7 electricity backup", "124 hour security"]:
        r = rec(s)
        assert r["guard_service_flag"] == 0 and r["psc_flag"] == 0, s
    # v1 keeps plan scope: abbreviations are v2 + candidate only
    r = rec("24hr security")
    assert r["psc_flag"] == 0 and r["cand_24h_abbrev_security"] == 1


def test_enclave_broad_candidates():
    r = rec("Townhouse in a secure complex")
    assert r["enclave_flag"] == 0 and r["enclave_flag_broad"] == 1
    assert r["cand_secure_complex"] == 1


def test_missing_text_is_na():
    for missing in [None, pd.NA, float("nan"), "", "   ", ".", "No Description Specified",
                    "No comments"]:
        assert is_missing_text(missing), repr(missing)
        for k, v in rec(missing).items():
            assert v is pd.NA, (repr(missing), k, v)
    assert not is_missing_text("No pets")


def test_flag_any_rules():
    df = pd.DataFrame({
        "description": [pd.NA, pd.NA, "Nice garden", "Security estate living", pd.NA],
        "title": ["House in X", "House in X Security Estate", "House in Y", "House in Z",
                  pd.NA],
    })
    out = classify.classify_frame(df)
    assert out["psc_flag_any"].iloc[0] is pd.NA        # desc NA, title 0 -> NA (not 0)
    assert out["psc_flag_any"].iloc[1] == 1            # title alone can give 1
    assert out["psc_flag_any"].iloc[2] == 0            # desc observed 0
    assert out["psc_flag_any"].iloc[3] == 1            # desc 1
    assert out["psc_flag_any"].iloc[4] is pd.NA        # both missing
    for col in ["psc_flag", "psc_flag_any", "enclave_flag", "psc_flag_title"]:
        assert str(out[col].dtype) == "Int64", col


def test_classify_idempotent():
    df = pd.DataFrame({"description": ["Security estate", pd.NA], "title": ["a", "b"]})
    once = classify.classify_frame(df)
    twice = classify.classify_frame(once)
    pd.testing.assert_frame_equal(once, twice)


# ---------------------------------------------------------------------------
# URLs, dedup, location, stubs
# ---------------------------------------------------------------------------
def test_p24_id_extraction():
    listing = f"http://{BASE.replace('www.property24.com', 'www.property24.com:80')}"
    assert extract_p24_id(listing) == "101246301"
    assert extract_p24_id(listing + "/") == "101246301"
    assert extract_p24_id(listing + "?plId=123&utm_source=x") == "101246301"
    for non_listing in [
        "http://www.property24.com:80/for-sale/pretoria/gauteng/results/1/1",
        "http://www.property24.com:80/for-sale/pretoria/pretoria/gauteng/22",
        "http://www.property24.com:80/for-sale/cape-town/western-cape/432"
        "?ListingNumber=P24-102174749",
        None,
    ]:
        assert extract_p24_id(non_listing) is None, non_listing
    assert extract_embedded_listing_number(
        "http://x/for-sale/y/z/432?ListingNumber=P24-102174749") == "102174749"


def test_normalise_url():
    a = normalise_url("http://www.property24.com:80/to-rent/x/y/z/9138/100321805/")
    b = normalise_url("https://WWW.property24.com/to-rent/x/y/z/9138/100321805?utm=a")
    assert a == b == "https://www.property24.com/to-rent/x/y/z/9138/100321805"


def test_location_exact_segments():
    assert parse_location_slugs(f"http://{BASE}") == (
        "durbanville", "durbanville", "western-cape")
    assert parse_location_slugs(
        "http://www.property24.com/for-sale/durban/1/1") == (None, None, None)


def _raw_frame():
    return pd.DataFrame({
        "listing_id": ["h1", "h2", "h3", "h4", "h5", "h6", "h7"],
        "url": [
            f"http://{BASE}",
            f"https://{BASE}",                    # same listing, same day
            f"http://{BASE.replace('www.property24.com', 'www.property24.com:80')}",
            "http://www.property24.com:80/for-sale/pretoria/gauteng/results/1/1",
            "http://www.property24.com:80/for-sale/x/western-cape/432?ListingNumber=P24-7654321",
            "http://www.property24.com/for-sale/a/durban/kwazulu-natal/1/2222222",
            "http://www.property24.com/for-sale/a/durban/kwazulu-natal/1/3333333",
        ],
        "snapshot_date": ["20130101", "20130101", "20140101", "20130101", "20130101",
                          "20130101", "20130101"],
        "city": ["Durban"] * 7,
        "province": ["Western Cape"] * 5 + ["KwaZulu-Natal"] * 2,
        "title": ["2 Bedroom Apartment / flat for sale in Durbanville"] * 5
                 + ["Listing Not Found", "Commercial property to rent in Durban"],
        "property_type": ["apartment"] * 5 + [pd.NA, "commercial"],
        "description": ["No Description Specified", "has text", "later text",
                        "news teaser", "news teaser", pd.NA, "Office"],
        "price": [1, 1, 1, pd.NA, 999, pd.NA, 5],
    })


def test_clean_listings_drops_dedups_and_relabels():
    out, stubs = merge.clean_listings(_raw_frame())
    assert set(out["p24_id"]) == {"101246301", "3333333"}, out["p24_id"].tolist()
    dv = out[out["p24_id"] == "101246301"]
    assert len(dv) == 2
    # Placeholder loses the tie-break to the real description
    assert dv.loc[dv["snapshot_date"] == "20130101", "description"].iloc[0] == "has text"
    assert set(dv["first_captured"]) == {"20130101"}
    assert set(dv["last_captured"]) == {"20140101"}
    assert set(dv["n_snapshots"]) == {2}
    assert (out["listing_id"] == out["p24_id"]).all() and "url_hash" in out.columns
    # Location repaired from URL; old label kept
    assert set(dv["city"]) == {"Cape Town"} and set(dv["city_target"]) == {"Durban"}
    assert set(dv["city_url"]) == {"Durbanville"}
    # Property use
    assert out.loc[out["p24_id"] == "3333333", "is_commercial"].iloc[0] == 1
    assert set(dv["is_residential"]) == {1}
    # ListingNumber page becomes a stub, not a listing
    assert stubs["p24_id"].tolist() == ["7654321"]
    assert stubs["price"].iloc[0] == 999 and "page_snippet" in stubs.columns


def test_dedup_prefers_https_when_otherwise_equal():
    df = pd.DataFrame({
        "url": [f"http://{BASE}", f"https://{BASE}"],
        "snapshot_date": ["20130101", "20130101"],
        "city": ["Durban", "Durban"], "province": ["Western Cape"] * 2,
        "title": ["Flat"] * 2, "description": ["same text", "same text"],
    })
    out, _ = merge.clean_listings(df)
    assert len(out) == 1 and out["url"].iloc[0].startswith("https")


def test_clean_listings_idempotent():
    once, _ = merge.clean_listings(_raw_frame())
    twice, _ = merge.clean_listings(once)
    assert len(once) == len(twice)
    assert once.sort_values(["p24_id", "snapshot_date"])["city"].tolist() == \
        twice.sort_values(["p24_id", "snapshot_date"])["city"].tolist()


def test_location_assertion_fires():
    df = _raw_frame().iloc[[1]].copy()
    df["province"] = "Gauteng"  # parsed province contradicts the URL
    try:
        merge.clean_listings(df)
    except AssertionError:
        return
    raise AssertionError("province inconsistency was not caught")


def test_discovery_labels_by_exact_segment():
    durban = {"slug": "durban", "name": "Durban", "province": "KwaZulu-Natal"}
    r = discovery.label_location({"url": f"http://{BASE}"}, durban)
    assert r["city"] == "Cape Town" and r["city_target"] == "Durban"
    r = discovery.label_location(
        {"url": "http://www.property24.com/for-sale/durbanville/western-cape/439"}, durban)
    assert r["city"] is None and r["province"] == "Western Cape"
    r = discovery.label_location(
        {"url": "http://www.property24.com/for-sale/durban-north/kwazulu-natal/785"}, durban)
    assert r["city"] == "Durban"


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print(f"PASS  {name}")
    print(f"\nAll {len(tests)} tests passed.")
