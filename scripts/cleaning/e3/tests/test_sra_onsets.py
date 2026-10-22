#!/usr/bin/env python3
# ============================================================
# test_sra_onsets.py
# Purpose: Integrity checks on the WP5 outputs (Cape Town SRA onsets).
# Inputs:  data/cleaned/e3/sra_onsets.parquet, sra_polygons.gpkg
# Usage:   py -3.12 scripts/cleaning/e3/tests/test_sra_onsets.py
# ============================================================

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
E3 = REPO_ROOT / "data" / "cleaned" / "e3"
ONSETS = pd.read_parquet(E3 / "sra_onsets.parquet")


def test_one_row_per_sra():
    assert ONSETS["sra_key"].is_unique


def test_onset_fy_plausible_and_ordered():
    g = ONSETS.dropna(subset=["G_fy"])
    assert g["G_fy"].between(1999, 2026).all()
    lo, hi = g["G_fy_min"], g["G_fy_max"]
    ok = lo.isna() | hi.isna() | ((lo <= g["G_fy"]) & (g["G_fy"] <= hi))
    assert ok.all(), g.loc[~ok, ["sra_key", "G_fy_min", "G_fy", "G_fy_max"]]


def test_retimed_onset_precedes_onset():
    g = ONSETS.dropna(subset=["G_fy", "G_tilde_fy"])
    assert (g["G_tilde_fy"] <= g["G_fy"]).all()


def test_every_selected_onset_is_sourced():
    g = ONSETS.dropna(subset=["G_fy"])
    assert g["onset_source"].notna().all() and g["onset_source_ids"].notna().all()
    assert (g["onset_source_ids"].str.len() > 0).all()


def test_g3_candidates_are_residential_with_first_stage():
    c = ONSETS[ONSETS["g3_candidate_with_first_stage"].fillna(False).astype(bool)]
    assert (c["sra_class"] == "residential").all()
    assert c["fs_documented"].fillna(False).astype(bool).all()


def _load_05():
    import importlib.util
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    spec = importlib.util.spec_from_file_location(
        "compile05", Path(__file__).resolve().parents[1] / "05_compile_sra_onsets.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _panel(m, present_fys, parsed_fys=None, basis_prior=()):
    parsed_fys = m.COVERED if parsed_fys is None else parsed_fys
    rows = []
    for fy in m.COVERED:
        pres = fy in present_fys
        b = ("line_present" if pres else "absent_prior_column" if fy in basis_prior
             else "absent_adopted_list")
        rows.append(dict(sra_key="x", fy=fy, levy_present=pres, evidence_basis=b,
                         n_rows_parsed_fy=50 if fy in parsed_fys else 0))
    import pandas as pd
    return pd.DataFrame(rows)


def test_levy_interval_synthetic():
    m = _load_05()
    c = m.COVERED
    i = m.levy_interval(_panel(m, [c[0], c[1]]), "x")
    assert i["lmin"] == float("-inf") and i["lmax"] == c[0]
    i = m.levy_interval(_panel(m, c[3:]), "x")
    assert i["lmax"] == c[3] and i["lmin"] == c[2]
    assert m.levy_interval(_panel(m, []), "x")["lmax"] is None


def test_unparsed_fy_is_not_absence():
    m = _load_05()
    c = m.COVERED
    # FY c[2] unparsed: it must not serve as the 'covered-absent' previous year
    i = m.levy_interval(_panel(m, c[3:], parsed_fys=[f for f in c if f != c[2]]), "x")
    assert i["lmin"] != c[2] and i["lmin"] == c[1]


def test_fy_mapping_and_classify():
    import types
    m = _load_05()
    assert m.city_fy_to_saps_fy(2014) == 2014
    r = types.SimpleNamespace(sra_key="k", res_levy_share=0.6, res_levy_share_fy=2018,
                              residential_rate_ever=True, res_property_share=float("nan"))
    assert m.classify(r)[0] == "residential"
    assert m.classify(r, 0.7)[0] == "mixed"
    r.res_levy_share = float("nan")
    r.residential_rate_ever = False
    assert m.classify(r)[0] == "commercial"


def test_g3_first_stage_uses_onset_window():
    c = ONSETS[ONSETS["g3_candidate_with_first_stage"].fillna(False).astype(bool)]
    assert c["fs_documented_within_onset_plus2"].fillna(False).astype(bool).all()


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS  {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")
