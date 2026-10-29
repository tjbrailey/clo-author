#!/usr/bin/env python3
# ============================================================
# 02_wcpp_station_personnel.py
# Parse Western Cape Provincial Parliament question 9 (11 Mar 2022, Hon R Allen,
# reply Hon A Marais): police officers, vehicles and new vehicles for each of the
# 151 WC stations on five dates (30 Apr 2018-2021, 28 Feb 2022), plus the 2021
# residents-per-officer ratio. Station names are matched to the SAPS crime panel
# and to Redpath & Nagia-Luddy (2015) Table 1 (c. 2013 personnel).
# Input:  data/raw/wcpp_q9_2022/wcpp_node11830.html (saved from
#         https://www.wcpp.gov.za/node/11830)
# Output: data/cleaned/wcpp_station_personnel_2018_2022.csv (station x date, long)
#         data/cleaned/wcpp_station_ratio_2021.csv
# Usage:  py -3.12 -I scripts/cleaning/external/02_wcpp_station_personnel.py
# ============================================================
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
tables = pd.read_html(ROOT / "data/raw/wcpp_q9_2022/wcpp_node11830.html")

DATES = ["2018-04-30", "2019-04-30", "2020-04-30", "2021-04-30", "2022-02-28"]
# Tables appear in reply order: (a)(i) officers, (a)(ii)(a) vehicles,
# (a)(ii)(b) new vehicles, (b) 2021 ratio (two stations per row)
GROUPS = {"officers": [0, 1, 2, 3], "vehicles": [4, 5, 6, 7], "new_vehicles": [8, 9, 10]}


def norm(s):
    return re.sub(r"\s+", " ", str(s).replace("’", "'")).strip().lower()


def to_int(v):
    # "-" = no figure (Samora Machel 2018); ". 54" = stray full stop (Table Bay Harbour 2019)
    s = re.sub(r"[^\d]", "", str(v))
    return int(s) if s else pd.NA


def stack(idx, name):
    out = []
    for i in idx:
        t = tables[i].copy()
        t.columns = ["station_reply"] + DATES
        out.append(t)
    t = pd.concat(out, ignore_index=True)
    t["station_reply"] = t.station_reply.astype(str).str.strip()
    t = t[t.station_reply != "Stations"]  # header row, repeated mid-table in places
    long = t.melt(id_vars="station_reply", var_name="date", value_name=name)
    long[name] = long[name].map(to_int).astype("Int64")
    dups = long[long.duplicated(["station_reply", "date"], keep=False)]
    if len(dups):
        # reply repeats some rows verbatim; refuse to drop if the copies disagree
        assert not long.duplicated(["station_reply", "date"]).sum() - long.duplicated().sum(), \
            f"{name}: duplicated stations with conflicting values"
        print(f"{name}: identical duplicate rows dropped:", sorted(dups.station_reply.unique()))
        long = long.drop_duplicates()
    return long


panel = stack(GROUPS["officers"], "officers")
for name in ["vehicles", "new_vehicles"]:
    panel = panel.merge(stack(GROUPS[name], name), on=["station_reply", "date"], how="outer")

ratio = []
for i in [11, 12, 13]:
    t = tables[i].iloc[1:]
    for a, b in [(1, 2), (4, 5)]:
        ratio.append(t.iloc[:, [a, b]].set_axis(["station_reply", "residents_per_officer_2021"], axis=1))
ratio = pd.concat(ratio, ignore_index=True).dropna(subset=["station_reply"])
ratio["station_reply"] = ratio.station_reply.astype(str).str.strip()
ratio["residents_per_officer_2021"] = pd.to_numeric(ratio.residents_per_officer_2021).astype("Int64")

# reply spelling -> SAPS crime-panel name (Redpath 2015 uses the same spellings as SAPS)
CROSSWALK = {"diep river": "dieprivier", "doringbaai": "doring bay", "elandsbaai": "elands bay",
             "gansbaai": "gans bay", "groot drakenstein": "groot-drakenstein",
             "heidelberg": "heidelberg(c)", "lingelethu west": "lingelethu-west",
             "saldanha bay": "saldanha", "van rhynsdorp": "vanrhynsdorp",
             "heidelberg[c]": "heidelberg(c)", "ravensrnead": "ravensmead"}  # last two: ratio table only
for df in (panel, ratio):
    df["station"] = df.station_reply.map(norm).replace(CROSSWALK)

saps = pd.read_csv(ROOT / "data/raw/saps_crime/sapacr-2005-2026-v1.5.csv", usecols=["station", "dc_mn"])
WC_DC = {"city of cape town", "west coast", "cape winelands", "overberg", "garden route", "central karoo"}
wc = set(saps.loc[saps.dc_mn.isin(WC_DC), "station"].map(norm))
redpath = pd.read_csv(ROOT / "data/raw/redpath_nagia-luddy_2015/redpath_nagia-luddy_2015_table1.csv")
rp = set(redpath.place.map(norm))

for df in (panel, ratio):
    df["in_saps_panel"] = df.station.isin(wc)
    df["in_redpath_2013"] = df.station.isin(rp)
    df["source"] = "WCPP Q9, 11 Mar 2022 (Allen/Marais)"

stations = panel.drop_duplicates("station")
print(f"Officer panel: {panel.station.nunique()} stations x {panel.date.nunique()} dates; "
      f"ratio table: {len(ratio)} stations")
print(f"Matched to SAPS WC panel: {stations.in_saps_panel.sum()}/{len(stations)}; "
      f"to Redpath 2013: {stations.in_redpath_2013.sum()}/{len(stations)}")
print("Unmatched to SAPS:", sorted(stations.loc[~stations.in_saps_panel, "station"]))
print("Unmatched to Redpath:", sorted(stations.loc[~stations.in_redpath_2013, "station"]))
print("SAPS WC stations not in reply:", sorted(wc - set(panel.station)))
print("Missing values:", panel[["officers", "vehicles", "new_vehicles"]].isna().sum().to_dict())
tot = panel.groupby("date").officers.sum()
print("Province officer totals by date:", tot.to_dict())

panel.sort_values(["station", "date"]).to_csv(ROOT / "data/cleaned/wcpp_station_personnel_2018_2022.csv", index=False)
ratio.sort_values("station").to_csv(ROOT / "data/cleaned/wcpp_station_ratio_2021.csv", index=False)
print("Saved: data/cleaned/wcpp_station_personnel_2018_2022.csv, data/cleaned/wcpp_station_ratio_2021.csv")
