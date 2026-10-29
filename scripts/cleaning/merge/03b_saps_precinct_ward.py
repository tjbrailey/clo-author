"""
Build precinct→ward area-weighted crosswalk using SAPS 2016 precinct boundaries
and MDB 2016 ward boundaries, then produce ward-year and ward-wave SAPS crime
panels with full Gauteng ward coverage.

Input:
  data/raw/units/saps/boundaries_2016/Police_bounds.shp
  data/raw/units/mdb/wards_2016/MDBWard2016.gdb
  data/cleaned/saps_crime_ward.parquet  (station-level panel from 03_saps_crime.R)

Output:
  data/cleaned/precinct_ward_crosswalk.parquet
  data/cleaned/saps_crime_ward_year_full.parquet
  data/cleaned/saps_crime_ward_wave_full.parquet
"""
import geopandas as gpd
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
import numpy as np

print("=== Building precinct-to-ward crosswalk ===\n")

# ------ 1. Load boundaries ------
precincts = gpd.read_file("data/raw/units/saps/boundaries_2016/Police_bounds.shp")
precincts["station_lower"] = precincts["COMPNT_NM"].str.lower().str.strip()

wards = gpd.read_file("data/raw/units/mdb/wards_2016/MDBWard2016.gdb")
if wards.crs != precincts.crs:
    wards = wards.to_crs(precincts.crs)

# Filter to Gauteng
gauteng_prefixes = ("797", "798", "799", "742", "746", "748", "793", "794", "796", "831")
wards["ward_code"] = wards["WardID"].astype(str)
gauteng_wards = wards[wards["ward_code"].str[:3].isin(gauteng_prefixes)].copy()
print(f"Gauteng wards: {len(gauteng_wards)}")

# Gauteng precincts
gauteng_union = gauteng_wards.union_all()
gp_precincts = precincts[precincts.intersects(gauteng_union)].copy()
print(f"Gauteng precincts: {len(gp_precincts)}")

# ------ 2. Overlay ------
print("\nComputing intersection overlay...")
overlay = gpd.overlay(
    gp_precincts[["COMPNT_NM", "station_lower", "geometry"]],
    gauteng_wards[["ward_code", "geometry"]],
    how="intersection"
)
overlay["piece_area"] = overlay.geometry.to_crs(epsg=32735).area  # m²
print(f"Overlay pieces: {len(overlay)}")

# For each precinct, compute total area and each piece's share
precinct_area = overlay.groupby("station_lower")["piece_area"].sum().rename("precinct_total_area")
overlay = overlay.merge(precinct_area, on="station_lower")
overlay["weight"] = overlay["piece_area"] / overlay["precinct_total_area"]

crosswalk = overlay[["station_lower", "COMPNT_NM", "ward_code", "piece_area", "weight"]].copy()
print(f"\nCrosswalk rows: {len(crosswalk)} (precinct×ward pieces)")
print(f"Unique precincts: {crosswalk['station_lower'].nunique()}")
print(f"Unique wards: {crosswalk['ward_code'].nunique()}")

# Sanity: weights per precinct should sum to ~1
w_sum = crosswalk.groupby("station_lower")["weight"].sum()
print(f"Weight sum per precinct: min={w_sum.min():.4f}, max={w_sum.max():.4f}, mean={w_sum.mean():.4f}")

pq.write_table(
    pa.Table.from_pandas(crosswalk.drop(columns="COMPNT_NM")),
    "data/cleaned/precinct_ward_crosswalk.parquet"
)
print("Saved: data/cleaned/precinct_ward_crosswalk.parquet")

# ------ 3. Load SAPS crime station panel ------
crime = pq.read_table("data/cleaned/saps_crime_ward.parquet").to_pandas()
crime["station_lower"] = crime["station"].str.lower().str.strip()

# Fix unmatched stations (4 stations not in precinct shapefile)
# Try fuzzy matching for the 4 unmatched
crime_stations = set(crime["station_lower"].unique())
precinct_names = set(crosswalk["station_lower"].unique())
unmatched = crime_stations - precinct_names
print(f"\nUnmatched stations: {unmatched}")

# Manual fixes for known name differences
name_fixes = {
    "cosmo city": "cosmocity",
    "doornkop": "doornkop saps",
}
# Check if any fuzzy matches exist
for um in unmatched:
    candidates = [p for p in precinct_names if um in p or p in um]
    if candidates:
        print(f"  {um} -> candidates: {candidates}")

# Apply fixes if they exist in precinct names
for old, new in name_fixes.items():
    if new in precinct_names:
        crime.loc[crime["station_lower"] == old, "station_lower"] = new

# Crime columns
crime_cols = [c for c in crime.columns if c.startswith("total_")]

# ------ 4. Area-weighted ward-year panel ------
print("\nBuilding area-weighted ward-year panel...")

# Merge crime with crosswalk
crime_xw = crime.merge(crosswalk[["station_lower", "ward_code", "weight"]],
                        on="station_lower", how="inner",
                        suffixes=("_old", ""))

# Weight crime counts
for col in crime_cols:
    crime_xw[col + "_w"] = crime_xw[col] * crime_xw["weight"]

# Aggregate to ward-year
wcols_w = [c + "_w" for c in crime_cols]
ward_year = (crime_xw
    .groupby(["ward_code", "cal_year"])[wcols_w]
    .sum()
    .reset_index()
    .rename(columns={c + "_w": c for c in crime_cols})
)

# Round to integers (weighted counts)
for col in crime_cols:
    ward_year[col] = ward_year[col].round(0).astype(int)

# Add station count
station_counts = (crime_xw
    .groupby(["ward_code", "cal_year"])["station_lower"]
    .nunique()
    .reset_index()
    .rename(columns={"station_lower": "n_precincts"})
)
ward_year = ward_year.merge(station_counts, on=["ward_code", "cal_year"])

print(f"Ward-year panel: {len(ward_year):,} rows, {ward_year['ward_code'].nunique()} wards, {ward_year['cal_year'].nunique()} years")

pq.write_table(pa.Table.from_pandas(ward_year), "data/cleaned/saps_crime_ward_year_full.parquet")
print("Saved: data/cleaned/saps_crime_ward_year_full.parquet")

# ------ 5. Wave-aligned panel ------
print("\nBuilding wave-aligned panel...")

wave_map = [
    ("I",   2009, 2009),
    ("II",  2011, 2011),
    ("III", 2013, 2014),
    ("IV",  2015, 2016),
    ("V",   2017, 2018),
    ("6",   2020, 2021),
    ("7",   2023, 2024),
]

wave_dfs = []
for wave, start, end in wave_map:
    wslice = ward_year[(ward_year["cal_year"] >= start) & (ward_year["cal_year"] <= end)]
    wagg = (wslice
        .groupby("ward_code")[crime_cols]
        .mean()
        .reset_index()
    )
    wagg["wave"] = wave
    wagg["n_fy_covered"] = wslice.groupby("ward_code")["cal_year"].nunique().values
    wave_dfs.append(wagg)

ward_wave = pd.concat(wave_dfs, ignore_index=True)
ward_wave = ward_wave[["wave", "ward_code", "n_fy_covered"] + crime_cols]

print(f"Ward-wave panel: {len(ward_wave):,} rows, {ward_wave['ward_code'].nunique()} wards, {ward_wave['wave'].nunique()} waves")
print(f"\nWave coverage:")
for wave, start, end in wave_map:
    n = len(ward_wave[ward_wave["wave"] == wave])
    print(f"  {wave}: {n} wards")

pq.write_table(pa.Table.from_pandas(ward_wave), "data/cleaned/saps_crime_ward_wave_full.parquet")
print("Saved: data/cleaned/saps_crime_ward_wave_full.parquet")

print("\n=== Done ===")
