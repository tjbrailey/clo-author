#!/usr/bin/env python3
# ============================================================
# 03_loadshedding_exposure.py
# Scheduled load shedding around each QoL wave-7 interview (Gauteng, Aug 2023-Apr 2024).
# Chain: interview EA (2011 frame) -> SAL -> Census 2011 sub-place name -> load-shedding
# area(s) whose published suburb list contains that name -> the area's scheduled power cuts.
# Inputs:  data/raw/loadshedding/beyarkay_hf/data/*.parquet (Kane & eskom-calendar
#          contributors, Hugging Face, CC BY-NC-SA 4.0)
#          data/raw/units/statssa/ea_boundaries_2013/SA_nogaps_2013.dbf (EA -> SAL)
#          data/raw/census2011_profiles/geo-type.dta (SAL -> sub-place, municipality)
#          data/cleaned/qol_harmonized.parquet (wave 7 EA codes and interview dates)
# Output:  data/cleaned/loadshedding/national_stage_daily.csv
#          data/cleaned/loadshedding/area_hours_daily_gauteng.csv
#          data/cleaned/loadshedding/subplace_area_crosswalk_gauteng.csv
#          data/cleaned/loadshedding/qol7_ea_date_exposure.csv (merge on ea_code + interview_date)
# Usage:   py -3.12 -I scripts/cleaning/external/03_loadshedding_exposure.py
# ============================================================
import difflib
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio

ROOT = Path(__file__).resolve().parents[3]
LS = ROOT / "data/raw/loadshedding/beyarkay_hf/data"
OUT = ROOT / "data/cleaned/loadshedding"
OUT.mkdir(parents=True, exist_ok=True)
WIN = (pd.Timestamp("2023-07-01"), pd.Timestamp("2024-05-01"))  # wave 7 plus a lead-in for 7-day lags
EVENING = (18, 23)  # hours counted as evening darkness


def tz_naive(s):
    return s.dt.tz_convert("Africa/Johannesburg").dt.tz_localize(None)


def merge_intervals(df):
    # slots overlap by 30 min and split at stage changes; merge before summing durations
    out = []
    for area, g in df.sort_values(["area_name", "start"]).groupby("area_name", sort=False):
        s0, e0 = None, None
        for s, e in zip(g.start, g.end):
            if s0 is None:
                s0, e0 = s, e
            elif s <= e0:
                e0 = max(e0, e)
            else:
                out.append((area, s0, e0))
                s0, e0 = s, e
        if s0 is not None:
            out.append((area, s0, e0))
    return pd.DataFrame(out, columns=["area_name", "start", "end"])


def daily_hours(iv, key):
    # split intervals at midnight; total and evening hours per key-date
    rows = []
    for k, s, e in zip(iv[key], iv.start, iv.end):
        d = s.normalize()
        while d < e:
            a, b = max(s, d), min(e, d + pd.Timedelta(days=1))
            ev_a, ev_b = max(a, d + pd.Timedelta(hours=EVENING[0])), min(b, d + pd.Timedelta(hours=EVENING[1]))
            rows.append((k, d, (b - a).total_seconds() / 3600, max((ev_b - ev_a).total_seconds() / 3600, 0)))
            d += pd.Timedelta(days=1)
    return (pd.DataFrame(rows, columns=[key, "date", "hours", "evening_hours"])
            .groupby([key, "date"], as_index=False).sum())


# ---- national stage (all areas outside Cape Town) ----
st = pd.read_parquet(LS / "stage_timeline.parquet")
st = st[st.applies_to == "all_other_areas"].assign(start=lambda d: tz_naive(d.start), end=lambda d: tz_naive(d.end))
st["key"] = "national"
nat = daily_hours(st, "key").drop(columns="key")
st["stage_x_h"] = st.stage * (st.end - st.start).dt.total_seconds() / 3600
sh = st.assign(date=st.start.dt.normalize()).groupby("date").agg(max_stage=("stage", "max"), stage_hours=("stage_x_h", "sum"))
nat = nat.merge(sh, on="date", how="left")
days = pd.DataFrame({"date": pd.date_range("2022-07-01", "2025-05-31")})
nat = days.merge(nat, on="date", how="left").fillna({"hours": 0, "evening_hours": 0, "max_stage": 0, "stage_hours": 0})
nat.to_csv(OUT / "national_stage_daily.csv", index=False)

# ---- Gauteng areas and their daily scheduled hours without power ----
areas = pd.read_parquet(LS / "areas.parquet")
subs = pd.read_parquet(LS / "suburbs.parquet").merge(areas[["area_name", "provider"]], on="area_name")
MUNI_PROVIDER = {"city-of-johannesburg": "city-power", "city-of-tshwane": "city-of-tshwane",
                 "ekurhuleni": "gauteng-ekurhuleni", "emfuleni": "gauteng-emfuleni"}
gp_providers = set(MUNI_PROVIDER.values())
subs["muni"] = np.where(subs.provider.isin(gp_providers),
                        subs.provider.map({v: k for k, v in MUNI_PROVIDER.items()}), subs.municipality)
gp_munis = {"city-of-johannesburg", "city-of-tshwane", "ekurhuleni", "emfuleni", "midvaal", "lesedi",
            "mogale-city", "randfontein", "westonaria", "merafong-city"}
subs = subs[subs.muni.isin(gp_munis) & (subs.provider.isin(gp_providers) | (subs.provider == "eskom"))]

o = pd.read_parquet(LS / "outages.parquet", columns=["area_name", "start", "end", "stage", "schedule_backfilled"])
o = o[o.area_name.isin(subs.area_name.unique())].assign(start=lambda d: tz_naive(d.start), end=lambda d: tz_naive(d.end))
o = o[(o.end > WIN[0]) & (o.start < WIN[1])]
o = o[(o.end - o.start) > pd.Timedelta(minutes=30)]  # calendars hid cuts <=30 min; municipalities rarely ran them
area_day = daily_hours(merge_intervals(o), "area_name")
grid = pd.MultiIndex.from_product([sorted(subs.area_name.unique()), pd.date_range(*WIN, inclusive="left")],
                                  names=["area_name", "date"]).to_frame(index=False)
area_day = grid.merge(area_day, on=["area_name", "date"], how="left").fillna({"hours": 0, "evening_hours": 0})
area_day.to_csv(OUT / "area_hours_daily_gauteng.csv", index=False)


# ---- name matching: Census 2011 sub-place -> load-shedding area(s) ----
def norm(s):
    s = str(s).lower().replace("_", " ").replace("-", " ")
    s = re.sub(r"\bext(ention|n)?\b\.?", "extension", s)
    s = re.sub(r"\bsp\b|\(.*?\)|[^a-z0-9, ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def expand(name):
    # "chantelle extension 1,13,14" -> chantelle extension 1 / 13 / 14 ; eskom "spruit view ext 1 a" -> drop a/b split
    n = re.sub(r"\s+[ab]$", "", norm(name))
    m = re.match(r"^(.*?extension)\s+([\d ,]+)$", n)
    if m:
        return [f"{m.group(1)} {x.strip()}" for x in m.group(2).split(",") if x.strip()]
    return [n.replace(",", " ").strip()]


def base(n):
    return re.sub(r"\s+extension\s+\d+$", "", n).strip()


ls_names = (subs.assign(name=subs.suburb.map(expand)).explode("name")[["muni", "name", "area_name"]]
            .dropna().drop_duplicates())
ls_names["base"] = ls_names.name.map(base)

geo = pd.read_stata(ROOT / "data/raw/census2011_profiles/geo-type.dta",
                    columns=["sal_code", "sp_code", "sp_name", "mp_name", "mn_name", "pr_name"])
geo = geo[geo.pr_name == "Gauteng"].copy()
CENSUS_MUNI = {"City of Johannesburg": "city-of-johannesburg", "City of Tshwane": "city-of-tshwane",
               "Ekurhuleni": "ekurhuleni", "Emfuleni": "emfuleni", "Midvaal": "midvaal", "Lesedi": "lesedi",
               "Mogale City": "mogale-city", "Randfontein": "randfontein", "Westonaria": "westonaria",
               "Merafong City": "merafong-city"}
unmapped = set(geo.mn_name) - set(CENSUS_MUNI)
assert not unmapped, f"Census municipalities without a mapping: {unmapped}"
geo["muni"] = geo.mn_name.map(CENSUS_MUNI)
sp = geo.drop_duplicates("sp_code")[["sp_code", "sp_name", "mp_name", "muni"]].copy()
sp["n"] = sp.sp_name.map(norm)
sp["mp"] = sp.mp_name.map(lambda s: re.sub(r"\bnu\b", "", norm(s)).strip())
# a main place with many sub-places (Tembisa 65, Pretoria 170) spans several blocks: no main-place fallback
MAX_SP_PER_MP = 10
sp.loc[sp.groupby("mp_name").sp_code.transform("size") > MAX_SP_PER_MP, "mp"] = ""


def match(n, cand, tag):
    # tiers: exact name, base name (extension dropped), fuzzy name, fuzzy base; returns (hits, label)
    for col, key in (("name", n), ("base", base(n))):
        hit = cand[cand[col] == key]
        if len(hit):
            return hit, f"{tag}_{'exact' if col == 'name' else 'base'}"
    for col, key in (("name", n), ("base", base(n))):
        close = difflib.get_close_matches(key, cand[col].unique().tolist(), n=1, cutoff=0.88)
        if close:
            return cand[cand[col] == close[0]], f"{tag}_fuzzy"
    return cand.iloc[0:0], None


rows = []
for r in sp.itertuples():
    cand = ls_names[ls_names.muni == r.muni]
    hit, how = match(r.n, cand, "subplace") if r.n else (cand.iloc[0:0], None)
    if how is None and r.mp:
        # coarser: whole main place (e.g. Tembisa) when the sub-place itself is not listed
        hit, how = match(r.mp, cand, "mainplace")
    for a in (hit.area_name.unique() if how else []):
        rows.append((r.sp_code, r.sp_name, r.muni, a, how))
xw = pd.DataFrame(rows, columns=["sp_code", "sp_name", "muni", "area_name", "match"])
xw["weight"] = 1 / xw.groupby("sp_code").area_name.transform("nunique")
xw.to_csv(OUT / "subplace_area_crosswalk_gauteng.csv", index=False)

# ---- QoL wave 7: EA-date exposure ----
ea = pyogrio.read_dataframe(ROOT / "data/raw/units/statssa/ea_boundaries_2013/SA_nogaps_2013.shp",
                            read_geometry=False, columns=["EA_CODE", "SAL_CODE"])
ea = ea.astype("int64").rename(columns={"EA_CODE": "ea", "SAL_CODE": "sal_code"})
q = pd.read_parquet(ROOT / "data/cleaned/qol_harmonized.parquet", columns=["wave", "ea_code", "ward_code", "interview_date"])
q = q[q.wave == "7"].dropna(subset=["ea_code", "interview_date"]).copy()
q["ea"] = pd.to_numeric(q.ea_code, errors="coerce").astype("Int64")
q["date"] = pd.to_datetime(q.interview_date).dt.normalize()
# keyed on EA + date only (a few 2011 EAs straddle 2021 wards); take ward from QoL when merging
ed = q.groupby(["ea_code", "ea", "date"]).size().rename("n_resp").reset_index()
ed = ed.merge(ea, on="ea", how="left").merge(geo[["sal_code", "sp_code"]].astype({"sal_code": "int64"}),
                                             on="sal_code", how="left")

lag = area_day.sort_values(["area_name", "date"]).copy()
for c in ["hours", "evening_hours"]:
    lag[f"{c}_prev7"] = lag.groupby("area_name")[c].transform(lambda s: s.shift(1).rolling(7).sum())
ex = (xw[["sp_code", "area_name", "weight"]].merge(lag, on="area_name")
      .assign(**{c: lambda d, c=c: d[c] * d.weight for c in ["hours", "evening_hours", "hours_prev7", "evening_hours_prev7"]})
      .groupby(["sp_code", "date"], as_index=False)[["hours", "evening_hours", "hours_prev7", "evening_hours_prev7"]].sum())
ex = ex.rename(columns=lambda c: c if c in ("sp_code", "date") else f"area_{c}")
ed = ed.merge(ex, on=["sp_code", "date"], how="left")
natl = nat.sort_values("date").assign(nat_hours_prev7=lambda d: d.hours.shift(1).rolling(7).sum())
ed = ed.merge(natl.rename(columns={"hours": "nat_hours", "evening_hours": "nat_evening_hours",
                                   "max_stage": "nat_max_stage", "stage_hours": "nat_stage_hours"}),
              on="date", how="left")
ed["n_areas"] = ed.sp_code.map(xw.groupby("sp_code").area_name.nunique()).fillna(0).astype(int)
ed["match"] = ed.sp_code.map(xw.groupby("sp_code").match.first())
ed = ed.rename(columns={"date": "interview_date"}).drop(columns="ea")
assert not ed.duplicated(["ea_code", "interview_date"]).any()
ed.to_csv(OUT / "qol7_ea_date_exposure.csv", index=False)

# ---- diagnostics ----
r = ed.n_resp.sum()
print(f"Wave-7 respondents: {r}; EA in 2011 frame: {ed.loc[ed.sal_code.notna(), 'n_resp'].sum() / r:.1%}; "
      f"matched to a load-shedding area: {ed.loc[ed.n_areas > 0, 'n_resp'].sum() / r:.1%}")
print("Match type (respondent share):", (ed.groupby("match").n_resp.sum() / r).round(3).to_dict())
print("Areas per matched sub-place:", ed.loc[ed.n_areas > 0].groupby("n_areas").n_resp.sum().to_dict())
print(f"Sub-places matched: {xw.sp_code.nunique()}/{len(sp)}; crosswalk rows: {len(xw)}")
print(f"Saved to {OUT.relative_to(ROOT)}")
