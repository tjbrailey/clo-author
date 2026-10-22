#!/usr/bin/env python3
# ============================================================
# scripts/cleaning/e3/05_compile_sra_onsets.py
# Title:   Compile one row per Cape Town SRA: onset (memo s5.4 hierarchy),
#          class, renewals / dissolution, first-stage security budget, area
# Author:  data-engineer (PSC Exposure project)
# Date:    2026-09-30
# Purpose: WP5 step 6. Combine the parsed levy lines (02), budget lines (04),
#          business-plan property schedules and the hand-coded, quote-verified
#          evidence in manual/ into the E3 analysis inputs. No outcome data are
#          read or merged here.
#
# Onset rule (pre-specified; memo s5.4):
#   Priority 1  levy line: first City FY with an SRA additional-rate line.
#               The levy interval [lmin, lmax] has lmax = first FY observed
#               with a line. lmin = lmax when the previous FY is covered and
#               absent in a *prior-year (approved) column*, which includes
#               mid-year additions. When the previous FY's absence comes only
#               from an adopted list (tariff book or single-period table), a
#               mid-year start in that FY cannot be excluded: lmin = lmax - 1.
#               Across coverage gaps lmin = last covered-absent FY (mid-year
#               start possible). First FY observed = first covered FY
#               (2006/07) -> left-censored.
#               A FY with zero parsed rows (any SRA) carries no absence evidence
#               ('not_parsed'). A verified documented line in a FY without an
#               archived table tightens lmax down and lmin up (assert lmin <=
#               lmax). Athlone's FY2007/08 'including Athlone' quote does not
#               verify, so Athlone keeps the pm1 interval [2007, 2008].
#   Priority 2  council approval / City-recorded application (City budget
#               annexures).
#   Priority 3  business-plan start.
#   Selection:  G = lmax if lmin == lmax. Otherwise intersect the levy interval
#               with the candidate intervals of the highest priority that has
#               at least one consistent candidate; stop at the first priority
#               giving a non-empty intersection. Lower priorities never move G
#               outside the levy interval; inconsistent candidates are flagged.
#               If the result is still an interval, G_fy is left missing and
#               only [G_fy_min, G_fy_max] is reported (no guessing).
#   SAPS FY:    G_saps_fy = City FY start year (City FY Jul-Jun has 9 months in
#               the same-labelled SAPS FY Apr-Mar; e3_config.city_fy_to_saps_fy).
#   Re-timing:  G_tilde = G - 2 (memo s5.2).
#
# Class rule (pre-specified):
#   res_levy_share = residential share of levy budget in the latest two-period
#     annexure (FY<=2019/20) with explicit residential/non-residential rows.
#   Otherwise res_property_share = residential share of rateable properties in
#     the business-plan property schedule (used if >= 50 properties listed).
#   residential: levy share >= 0.5, else (no levy share) property share >= 0.8
#   mixed:       levy share in [0.2, 0.5), else property share in [0.5, 0.8)
#   commercial:  levy share < 0.2, or no residential rate in any year, else
#                property share < 0.5
#   not_service_cid: Claremont Boulevard (road by-pass bond levy)
#   UNVERIFIED: none of the above available.
#   Sensitivity: sra_class_alt07 raises the levy-share residential cut to 0.7.
#
# Inputs:  data/raw/e3/docs/sra_layer4_geojson.geojson, data/raw/e3/text/*.txt,
#          data/cleaned/e3/intermediate/levy_lines.csv,
#          data/cleaned/e3/sra_security_budget.parquet,
#          scripts/cleaning/e3/manual/*.csv
# Outputs: data/cleaned/e3/sra_onsets.parquet          (one row per SRA; 60)
#          data/cleaned/e3/sra_polygons.gpkg           (58 polygons + keys)
#          data/cleaned/e3/sra_onset_candidates.parquet (every candidate)
#          data/cleaned/e3/sra_levy_panel.parquet      (SRA x covered FY)
#          data/cleaned/e3/sra_events.parquet          (renewal/extension/...)
#          data/cleaned/e3/codebook_sra_onsets.csv
# Usage:   py -3.12 scripts/cleaning/e3/05_compile_sra_onsets.py
# ============================================================

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e3_config import (  # noqa: E402
    A3_G_MAX, A3_G_MIN, CLEAN, INTERMEDIATE, MANUAL, RAW, RAW_DOCS, RAW_TEXT,
    RETIME_LAG_FY, city_fy_to_saps_fy, fy_label,
)

LOCAL_CRS = "EPSG:2048"          # Hartebeesthoek94 / Lo19 (City of Cape Town)
COVERED = [2006, 2007, 2008, 2009] + list(range(2013, 2027))
# FYs whose absence is observed in a prior-year (approved) column, which picks
# up mid-year additions: 2008 (FY2009/10 tariff book), 2013..2018 (two-period
# Annexure 3 prior columns in FY2014/15..FY2019/20).
PRIOR_COLUMN_FYS = {2006, 2008} | set(range(2013, 2019))
PRIORITY = {"levy_line": 1, "council_approval": 2, "application": 2,
            "bizplan_start": 3}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("–", "-")
    return re.sub(r"\s+", " ", s).strip()


_TEXT_CACHE: dict[str, list[tuple[int, str]]] = {}


def pages(source_id: str) -> list[tuple[int, str]]:
    if source_id not in _TEXT_CACHE:
        p = RAW_TEXT / f"{source_id}.txt"
        txt = p.read_text(encoding="utf-8") if p.exists() else ""
        parts = re.findall(r"=== PAGE (\d+) ===\n(.*?)(?==== PAGE|\Z)", txt, re.S)
        _TEXT_CACHE[source_id] = [(int(n), norm(t)) for n, t in parts]
    return _TEXT_CACHE[source_id]


def locate(source_id: str, quote: str) -> tuple[bool, int | None]:
    q = norm(quote)
    for n, t in pages(source_id):
        if q in t:
            return True, n
    # quotes may run across a page break
    joined = " ".join(t for _, t in pages(source_id))
    return (q in joined), None


def source_urls() -> dict[str, str]:
    prov = pd.read_csv(RAW / "provenance.csv")
    return dict(zip(prov.source_id, prov.url))


# ---------------------------------------------------------------------------
# levy panel and priority-1 candidate
# ---------------------------------------------------------------------------
def levy_panel(xw: pd.DataFrame) -> pd.DataFrame:
    d = pd.read_csv(INTERMEDIATE / "levy_lines.csv")
    d["present_b"] = d.present.map({True: True, False: False, "True": True, "False": False})
    rows = []
    # A FY counts as covered only if the parser returned rows for it (any SRA).
    # Otherwise "absent" would just mean "table failed to parse" (review WP5-MH1).
    n_fy = d.groupby("fy").size().to_dict()
    unparsed = [fy for fy in COVERED if n_fy.get(fy, 0) == 0]
    if unparsed:
        print("WARNING: covered FYs with 0 parsed rows (no absence evidence):", unparsed)
    for key in xw.sra_key:
        s = d[d.sra_key == key]
        for fy in COVERED:
            f = s[s.fy == fy]
            obs_prior = f[f.column_role == "prior"]
            obs_cur = f[f.column_role == "current"]
            present = bool((f.present_b == True).any())  # noqa: E712
            if present:
                basis = "line_present"
            elif n_fy.get(fy, 0) == 0:
                basis = "not_parsed"
            elif (obs_prior.present_b == False).any():  # noqa: E712
                basis = "absent_prior_column"
            else:
                basis = "absent_adopted_list"
            src = f[f.present_b == True].source_id.iloc[0] if present else (  # noqa: E712
                f.source_id.iloc[0] if len(f) else "")
            res = f[(f.category == "residential") & (f.present_b == True)]  # noqa: E712
            rows.append(dict(sra_key=key, fy=fy, fy_label=fy_label(fy), levy_present=present,
                             evidence_basis=basis, source_id=src,
                             residential_category_present=bool(len(res)),
                             n_rows_parsed=len(obs_prior) + len(obs_cur),
                             n_rows_parsed_fy=int(n_fy.get(fy, 0))))
    return pd.DataFrame(rows)


def levy_interval(panel: pd.DataFrame, key: str) -> dict:
    p = panel[panel.sra_key == key].set_index("fy")
    # only FYs with parsed rows can carry absence evidence
    cov = [fy for fy in COVERED if p.at[fy, "n_rows_parsed_fy"] > 0]
    pres = [fy for fy in cov if p.at[fy, "levy_present"]]
    if not pres:
        return dict(lmin=None, lmax=None, note="no levy line in any covered FY")
    first = min(pres)
    last = max(pres)
    if first == cov[0]:
        return dict(lmin=-np.inf, lmax=first, first=first, last=last,
                    note="left-censored: levy line in first covered FY (2006/07)")
    prev = max(fy for fy in cov if fy < first)
    if prev == first - 1:
        if prev in PRIOR_COLUMN_FYS and p.at[prev, "evidence_basis"] == "absent_prior_column":
            return dict(lmin=first, lmax=first, first=first, last=last,
                        note=f"FY{fy_label(prev)} absent in a prior-year approved column")
        return dict(lmin=prev, lmax=first, first=first, last=last,
                    note=f"FY{fy_label(prev)} absent only from the adopted list: "
                         f"mid-year start in FY{fy_label(prev)} not excluded")
    return dict(lmin=prev, lmax=first, first=first, last=last,
                note=f"coverage gap FY{fy_label(prev + 1)}..FY{fy_label(first - 1)}; "
                     f"FY{fy_label(prev)} absent from the adopted list only")


# ---------------------------------------------------------------------------
# classification inputs
# ---------------------------------------------------------------------------
def levy_res_share() -> pd.DataFrame:
    d = pd.read_csv(INTERMEDIATE / "levy_lines.csv")
    c = d[(d.column_role == "current") & d.source_id.str.startswith("fy")
          & (d.fy <= 2019) & d.budget.notna()
          & d.category.isin(["residential", "non_residential", "non_residential_gt50"])]
    piv = c.pivot_table(index=["sra_key", "fy"], columns="category", values="budget",
                        aggfunc="sum").fillna(0.0)
    piv["total"] = piv.sum(axis=1)
    res = piv["residential"] if "residential" in piv else 0.0
    piv["res_levy_share"] = res / piv.total
    last = piv.reset_index().sort_values("fy").groupby("sra_key").tail(1)
    return last.set_index("sra_key")[["fy", "res_levy_share"]].rename(
        columns={"fy": "res_levy_share_fy"})


def bp_property_counts(xw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in xw.dropna(subset=["bp_source_id"]).itertuples():
        f = RAW_TEXT / f"{r.bp_source_id}.txt"
        if not f.exists():
            rows.append(dict(sra_key=r.sra_key, bp_n_res_properties=np.nan,
                             bp_n_nonres_properties=np.nan))
            continue
        t = f.read_text(encoding="utf-8")
        n_res = len(re.findall(r"(?m)^\s*(?:RESIDENTIAL|Residential)\s+\S", t))
        n_non = len(re.findall(r"(?m)^\s*(?:NON[- ]?RESIDENTIAL|Non[- ]?[Rr]esidential)\s+\S", t))
        rows.append(dict(sra_key=r.sra_key, bp_n_res_properties=n_res,
                         bp_n_nonres_properties=n_non))
    df = pd.DataFrame(rows).set_index("sra_key")
    tot = df.bp_n_res_properties + df.bp_n_nonres_properties
    df["res_property_share"] = np.where(tot >= 50, df.bp_n_res_properties / tot.replace(0, 1),
                                        np.nan)
    return df


def classify(row, levy_res_thr: float = 0.5) -> tuple[str, str]:
    if row.sra_key == "claremont_boulevard":
        return "not_service_cid", "road by-pass bond-repayment levy"
    s = row.res_levy_share
    if pd.notna(s):
        cls = "residential" if s >= levy_res_thr else ("mixed" if s >= 0.2 else "commercial")
        return cls, f"levy budget share FY{fy_label(int(row.res_levy_share_fy))} = {s:.2f}"
    if not row.residential_rate_ever:
        return "commercial", "no residential additional rate in any FY"
    p = row.res_property_share
    if pd.notna(p):
        cls = "residential" if p >= max(0.8, levy_res_thr) else ("mixed" if p >= 0.5 else "commercial")
        return cls, f"business-plan property schedule share = {p:.2f}"
    return "UNVERIFIED", "residential rate levied; no budget split or property schedule"


# ---------------------------------------------------------------------------
def main() -> None:
    xw = pd.read_csv(MANUAL / "sra_crosswalk.csv")
    urls = source_urls()

    # --- levy panel -------------------------------------------------------
    panel = levy_panel(xw)
    panel.to_parquet(CLEAN / "sra_levy_panel.parquet", index=False)

    # --- candidates --------------------------------------------------------
    ev = pd.read_csv(MANUAL / "onset_evidence.csv", dtype={"date_stated": str})
    ver = [locate(r.source_id, r.quote) for r in ev.itertuples()]
    ev["quote_verified"] = [v[0] for v in ver]
    ev["page"] = [v[1] for v in ver]
    ev["priority"] = ev.candidate_type.map(PRIORITY)
    auto = []
    for key in xw.sra_key:
        li = levy_interval(panel, key)
        if li["lmax"] is None:
            continue
        first_src = panel[(panel.sra_key == key) & (panel.fy == li["lmax"])].source_id.iloc[0]
        auto.append(dict(sra_key=key, candidate_type="levy_line",
                         source_class="city_budget_levy_table",
                         date_stated=f"first levy line FY{fy_label(int(li['lmax']))}",
                         implied_levy_fy_min=li["lmin"], implied_levy_fy_max=li["lmax"],
                         source_id=first_src, quote="", coding_note=li["note"],
                         quote_verified=True, page=None, priority=1))
    cand = pd.concat([pd.DataFrame(auto), ev], ignore_index=True)
    cand["source_url"] = cand.source_id.map(urls)
    cand["implied_levy_fy_min"] = cand.implied_levy_fy_min.astype(float)
    cand["implied_levy_fy_max"] = cand.implied_levy_fy_max.astype(float)

    # --- selection ---------------------------------------------------------
    out = []
    for key in xw.sra_key:
        c = cand[cand.sra_key == key]
        lv = c[c.candidate_type == "levy_line"]
        auto_lv = lv[lv.source_class == "city_budget_levy_table"]
        extra_lv = lv[lv.source_class != "city_budget_levy_table"]
        if auto_lv.empty:
            lo, hi = -np.inf, np.inf
        else:
            lo = float(auto_lv.implied_levy_fy_min.iloc[0])
            hi = float(auto_lv.implied_levy_fy_max.iloc[0])
        # a documented levy line in an FY without an archived table (Athlone
        # FY2007/08) tightens the priority-1 upper bound
        for r in extra_lv.itertuples():
            if r.quote_verified:
                # a verified documented line can only tighten both bounds
                # (Athlone FY2007/08 quote is unverified, so it is not applied)
                hi = min(hi, r.implied_levy_fy_max)
                lo = max(lo, r.implied_levy_fy_min)
        assert lo <= hi, f"{key}: inconsistent levy interval [{lo}, {hi}]"

        sel_src, sel_ids = "levy_line", list(lv.source_id)
        conflicts = []
        g_lo, g_hi = lo, hi
        if lo != hi:
            for pr in (2, 3):
                cp = c[(c.priority == pr) & c.quote_verified]
                cons = [r for r in cp.itertuples()
                        if r.implied_levy_fy_max >= lo and r.implied_levy_fy_min <= hi]
                if not cons:
                    continue
                a = max([lo] + [r.implied_levy_fy_min for r in cons])
                b = min([hi] + [r.implied_levy_fy_max for r in cons])
                if a <= b:
                    g_lo, g_hi = a, b
                    sel_src = f"levy_line+{cons[0].candidate_type}"
                    sel_ids = list(lv.source_id) + [r.source_id for r in cons]
                    break
        for r in c[c.priority > 1].itertuples():
            if r.implied_levy_fy_max < g_lo or r.implied_levy_fy_min > g_hi:
                conflicts.append(f"{r.candidate_type}:{r.date_stated}")
        g = g_hi if g_lo == g_hi and np.isfinite(g_hi) else np.nan
        width = (g_hi - g_lo + 1) if np.isfinite(g_lo) and np.isfinite(g_hi) else np.inf
        precision = ("fy_exact" if width == 1 else "fy_pm1" if width == 2 else
                     "left_censored" if not np.isfinite(g_lo) else "interval")
        if np.isfinite(g_hi) and g_hi < A3_G_MIN:
            window = "pre_window"
        elif np.isfinite(g_lo) and g_lo > A3_G_MAX:
            window = "post_window"
        elif np.isfinite(g_lo) and g_lo >= A3_G_MIN and g_hi <= A3_G_MAX:
            window = "in_window"
        else:
            window = "straddles_window"
        li = levy_interval(panel, key)
        appl = c[c.candidate_type.isin(["council_approval", "application"])]
        out.append(dict(
            sra_key=key,
            G_fy=g, G_fy_min=g_lo if np.isfinite(g_lo) else np.nan,
            G_fy_max=g_hi if np.isfinite(g_hi) else np.nan,
            G_fy_label=fy_label(int(g)) if pd.notna(g) else None,
            onset_precision=precision, onset_source=sel_src,
            onset_source_ids=";".join(dict.fromkeys(sel_ids)),
            onset_conflicts=";".join(conflicts),
            first_levy_fy_observed=li.get("first", np.nan),
            last_levy_fy_observed=li.get("last", np.nan),
            levy_interval_note=li.get("note", ""),
            council_approval_date=";".join(appl[appl.candidate_type == "council_approval"]
                                           .date_stated.astype(str)),
            application_record=";".join(appl[appl.candidate_type == "application"]
                                        .date_stated.astype(str)),
            a3_window_status=window,
        ))
    on = pd.DataFrame(out)
    on["G_saps_fy"] = on.G_fy.map(lambda v: city_fy_to_saps_fy(int(v)) if pd.notna(v) else np.nan)
    on["G_tilde_fy"] = on.G_fy - RETIME_LAG_FY
    on["G_tilde_saps_fy"] = on.G_saps_fy - RETIME_LAG_FY

    # --- events -------------------------------------------------------------
    d = pd.read_csv(INTERMEDIATE / "levy_lines.csv")
    fl = d[d.flag_meaning.fillna("").str.contains("renewal")].drop_duplicates(["sra_key", "fy"])
    ev_rows = [dict(sra_key=r.sra_key, event_type="renewal", effective_fy=int(r.fy),
                    source_id=r.source_id, quote=f"row flag '{r.flag_raw}'",
                    coding_note=r.flag_meaning, quote_verified=True, page=None)
               for r in fl.itertuples()]
    mev = pd.read_csv(MANUAL / "events.csv")
    for r in mev.itertuples():
        ok, pg = locate(r.source_id, r.quote)
        for k in r.sra_keys.split(";"):
            ev_rows.append(dict(sra_key=k, event_type=r.event_type,
                                effective_fy=int(r.effective_fy), source_id=r.source_id,
                                quote=r.quote, coding_note=r.coding_note,
                                quote_verified=ok, page=pg))
    events = pd.DataFrame(ev_rows).drop_duplicates(["sra_key", "event_type", "effective_fy"])
    events["source_url"] = events.source_id.map(urls)
    events.to_parquet(CLEAN / "sra_events.parquet", index=False)
    agg = events.groupby("sra_key").apply(
        lambda e: pd.Series(dict(
            renewal_fys=";".join(str(x) for x in sorted(e[e.event_type == "renewal"].effective_fy)),
            extension_fys=";".join(str(x) for x in
                                   sorted(e[e.event_type == "boundary_extension"].effective_fy)),
            dissolution_fy=(e[e.event_type.isin(["dissolution", "levy_ended"])]
                            .effective_fy.min()),
        )), include_groups=False)
    on = on.merge(agg, left_on="sra_key", right_index=True, how="left")

    # --- pre-existing provision --------------------------------------------
    pe = pd.read_csv(MANUAL / "pre_existing_provision.csv")
    pe["quote_verified"] = [locate(r.source_id, r.quote)[0] for r in pe.itertuples()]
    on = on.merge(pe[["sra_key", "provision_type", "since_year"]].rename(
        columns={"provision_type": "pre_existing_provision",
                 "since_year": "pre_existing_since"}), on="sra_key", how="left")
    on["pre_existing_provision"] = on.pre_existing_provision.fillna("not_coded")

    # --- classification -----------------------------------------------------
    rs = levy_res_share()
    bp = bp_property_counts(xw)
    rate_ever = panel.groupby("sra_key").residential_category_present.any().rename(
        "residential_rate_ever")
    on = (on.merge(rs, left_on="sra_key", right_index=True, how="left")
            .merge(bp, left_on="sra_key", right_index=True, how="left")
            .merge(rate_ever, left_on="sra_key", right_index=True, how="left"))
    cls = [classify(r) for r in on.itertuples()]
    on["sra_class"] = [c[0] for c in cls]
    on["sra_class_basis"] = [c[1] for c in cls]
    # sensitivity: stricter residential levy-share threshold
    on["sra_class_alt07"] = [classify(r, 0.7)[0] for r in on.itertuples()]

    # --- first stage ----------------------------------------------------------
    sb = pd.read_parquet(CLEAN / "sra_security_budget.parquet")
    fs = []
    for r in on.itertuples():
        s = sb[sb.sra_key == r.sra_key]
        near = s[(s.fy >= (r.G_fy_min if pd.notna(r.G_fy_min) else 9999))
                 & (s.fy <= (r.G_fy_max + 2 if pd.notna(r.G_fy_max) else -1))]
        fs.append(dict(
            sra_key=r.sra_key, fs_n_budget_years=len(s),
            fs_budget_fys=";".join(str(x) for x in sorted(s.fy)),
            fs_security_share_mean=s.security_share.mean() if len(s) else np.nan,
            fs_security_share_first_obs=(s.sort_values("fy").security_share.iloc[0]
                                         if len(s) else np.nan),
            fs_security_amount_first_obs=(s.sort_values("fy").security_total.iloc[0]
                                          if len(s) else np.nan),
            fs_documented=bool((s.security_total > 0).any()),
            fs_documented_within_onset_plus2=bool((near.security_total > 0).any()),
        ))
    on = on.merge(pd.DataFrame(fs), on="sra_key", how="left")

    # --- polygons, area, dwellings hook -------------------------------------
    gj = json.loads((RAW_DOCS / "sra_layer4_geojson.geojson").read_text(encoding="utf-8"))
    g = gpd.GeoDataFrame.from_features(gj["features"], crs="EPSG:4326")
    g = g.rename(columns={"OBJECTID": "polygon_id", "SRA_NAME": "polygon_name"})
    g = g.merge(xw[["sra_key", "polygon_name"]], on="polygon_name", how="left")
    assert g.sra_key.notna().all(), "unmapped polygon"
    g_local = g.to_crs(LOCAL_CRS)
    g["area_km2"] = g_local.area / 1e6
    g["geometry_valid"] = g_local.is_valid
    on = on.merge(g[["sra_key", "polygon_id", "polygon_name", "area_km2"]],
                  on="sra_key", how="left")
    on["has_polygon"] = on.polygon_id.notna()
    # Hook for WP2: residential dwellings inside each polygon (Census 2011 SAL /
    # Open Buildings) will be joined here once WP2 publishes unit outputs.
    on["dwellings_wp2"] = np.nan
    on["dwellings_wp2_status"] = "pending_WP2"
    on = on.merge(xw[["sra_key", "sra_name", "bp_source_id"]], on="sra_key", how="left")
    on["bp_url"] = on.bp_source_id.map(urls)

    # --- G3 feasibility flags -----------------------------------------------
    on["is_service_sra"] = on.sra_class != "not_service_cid"
    on["pending_approval"] = on.sra_key.eq("signal_hill")
    on["g3_candidate"] = ((on.sra_class == "residential") & on.has_polygon
                          & (on.onset_precision == "fy_exact")
                          & on.G_fy.between(A3_G_MIN, A3_G_MAX))
    on["g3_candidate_alt07"] = ((on.sra_class_alt07 == "residential") & on.has_polygon
                                & (on.onset_precision == "fy_exact")
                                & on.G_fy.between(A3_G_MIN, A3_G_MAX))
    on["g3_candidate_alt07_with_first_stage"] = (on.g3_candidate_alt07
                                                 & on.fs_documented_within_onset_plus2)
    # first stage must fall within [G_min, G_max + 2] (review WP5-M1)
    on["g3_candidate_with_first_stage"] = (on.g3_candidate
                                           & on.fs_documented_within_onset_plus2)

    cols_first = ["sra_key", "sra_name", "polygon_id", "polygon_name", "has_polygon",
                  "sra_class", "sra_class_basis", "G_fy", "G_fy_label", "G_fy_min",
                  "G_fy_max", "onset_precision", "onset_source", "onset_source_ids",
                  "onset_conflicts", "G_saps_fy", "G_tilde_fy", "G_tilde_saps_fy",
                  "a3_window_status"]
    on = on[cols_first + [c for c in on.columns if c not in cols_first]]
    on = on.sort_values("sra_key").reset_index(drop=True)
    on.to_parquet(CLEAN / "sra_onsets.parquet", index=False)
    cand.to_parquet(CLEAN / "sra_onset_candidates.parquet", index=False)

    gout = g.merge(on[["sra_key", "sra_class", "G_fy", "G_fy_min", "G_fy_max",
                       "onset_precision", "a3_window_status", "g3_candidate"]],
                   on="sra_key", how="left")
    gpkg = CLEAN / "sra_polygons.gpkg"
    if gpkg.exists():
        gpkg.unlink()
    gout.to_file(gpkg, layer="sra_polygons", driver="GPKG")

    write_codebook(on)
    print(on.onset_precision.value_counts().to_string())
    print(on.sra_class.value_counts().to_string())
    print("G3 candidates:", int(on.g3_candidate.sum()),
          "| with first stage (onset+2):", int(on.g3_candidate_with_first_stage.sum()))
    print("alt 0.7: residential", int((on.sra_class_alt07 == "residential").sum()),
          "| G3 candidates", int(on.g3_candidate_alt07.sum()),
          "| with first stage", int(on.g3_candidate_alt07_with_first_stage.sum()))
    print("fs_documented (any FY) among g3_candidate:",
          int((on.g3_candidate & on.fs_documented).sum()))
    bad = cand[~cand.quote_verified.astype(bool)]
    if len(bad):
        print("UNVERIFIED QUOTES:\n", bad[["sra_key", "source_id", "quote"]].to_string())


DESCR = {
    "sra_key": "Project key (manual/sra_crosswalk.csv)",
    "sra_name": "SRA / CID name",
    "polygon_id": "OBJECTID in City layer ODP_SPLIT_5/FeatureServer/4 (NA: no current polygon)",
    "polygon_name": "SRA_NAME in City layer",
    "has_polygon": "SRA has a polygon in the current City layer",
    "sra_class": "residential / mixed / commercial / not_service_cid / UNVERIFIED (rule in 05 header)",
    "sra_class_basis": "Evidence used for sra_class",
    "G_fy": "Onset: first City FY of levy-funded services (start year; e.g. 2014 = 2014/15); NA if only an interval is known",
    "G_fy_label": "G_fy as 'YYYY/YY'",
    "G_fy_min": "Lower bound of onset FY (NA = left-censored)",
    "G_fy_max": "Upper bound of onset FY",
    "onset_precision": "fy_exact (12 months) / fy_pm1 (24 months) / interval / left_censored",
    "onset_source": "Hierarchy level(s) that fixed the onset (memo s5.4)",
    "onset_source_ids": "provenance.csv source_ids supporting the onset",
    "onset_conflicts": "Lower-priority candidates inconsistent with the selected onset",
    "G_saps_fy": "SAPS FY start year containing >= 9 months of the first levy year",
    "G_tilde_fy": "Re-timed onset G - 2 (campaign + approval; memo s5.2)",
    "G_tilde_saps_fy": "G_tilde on the SAPS FY scale",
    "a3_window_status": "Relative to A3 window G in FY2011/12..FY2023/24",
    "first_levy_fy_observed": "First covered FY with a levy line",
    "last_levy_fy_observed": "Last covered FY with a levy line",
    "levy_interval_note": "How the priority-1 interval was bounded",
    "council_approval_date": "Council approval date(s) stated in City budget annexures",
    "application_record": "City-recorded pending application (budget in which it appears)",
    "renewal_fys": "FYs in which a new term started (City annexures)",
    "extension_fys": "FYs of boundary extensions (dose increments)",
    "dissolution_fy": "First FY without levy after dissolution / end of levy",
    "pre_existing_provision": "Pre-SRA voluntary security stated in the business plan (not_coded if none found)",
    "pre_existing_since": "Start year of pre-existing provision, where stated",
    "res_levy_share_fy": "FY of the budget split used for res_levy_share",
    "res_levy_share": "Residential share of levy budget (two-period annexures)",
    "bp_n_res_properties": "Residential properties in business-plan property schedule",
    "bp_n_nonres_properties": "Non-residential properties in business-plan property schedule",
    "res_property_share": "Residential share of scheduled properties (>= 50 listed)",
    "residential_rate_ever": "A residential additional rate is levied in some FY",
    "fs_n_budget_years": "FYs with an ODP category budget (2015/16, 2016/17, 2021/22-2023/24)",
    "fs_budget_fys": "Those FYs",
    "fs_security_share_mean": "Mean security (+LEO) share of expenditure over observed FYs",
    "fs_security_share_first_obs": "Security share in first observed budget FY",
    "fs_security_amount_first_obs": "Security (+LEO) Rand in first observed budget FY",
    "fs_documented": "Security spend > 0 documented in some FY",
    "fs_documented_within_onset_plus2": "Security spend documented within [G_min, G_max + 2]",
    "area_km2": "Polygon area, EPSG:2048",
    "dwellings_wp2": "Residential dwellings inside polygon (hook; filled after WP2)",
    "dwellings_wp2_status": "Status of the WP2 dwellings join",
    "bp_source_id": "Current business plan source_id",
    "bp_url": "Current business plan URL",
    "is_service_sra": "False for the Claremont Boulevard bond levy",
    "pending_approval": "Establishment not yet approved by Council at last budget",
    "g3_candidate": "Residential, polygon, fy_exact onset, G in FY2011/12..2023/24",
    "g3_candidate_with_first_stage": "g3_candidate and fs_documented_within_onset_plus2",
    "sra_class_alt07": "sra_class, levy-share residential threshold 0.7 instead of 0.5 (sensitivity)",
    "g3_candidate_alt07": "g3_candidate recomputed with sra_class_alt07",
    "g3_candidate_alt07_with_first_stage": "g3_candidate_alt07 and fs_documented_within_onset_plus2",
}


def write_codebook(on: pd.DataFrame) -> None:
    rows = []
    for c in on.columns:
        s = on[c]
        num = pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)
        rows.append(dict(
            variable=c, description=DESCR.get(c, ""), dtype=str(s.dtype),
            n_nonmissing=int(s.notna().sum()),
            mean=round(float(s.mean()), 4) if num and s.notna().any() else None,
            sd=round(float(s.std()), 4) if num and s.notna().sum() > 1 else None,
            min=s.min() if num and s.notna().any() else None,
            max=s.max() if num and s.notna().any() else None,
            n_true=int(s.sum()) if pd.api.types.is_bool_dtype(s) else None,
        ))
    pd.DataFrame(rows).to_csv(CLEAN / "codebook_sra_onsets.csv", index=False)


if __name__ == "__main__":
    main()
