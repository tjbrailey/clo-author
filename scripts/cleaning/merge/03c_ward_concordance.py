"""
Build a 2011-to-2016 ward boundary concordance using spatial overlay.

For Wave I QoL integration: ~286 of 572 Wave I ward codes match 2011 boundaries.
Of those, 237 already match 2016 directly. This concordance handles the ~49
that match 2011 but not 2016.

The remaining ~286 metro wards (prefixes 794=JHB, 793=TSH, 796=EKU) use
2006-era codes that don't appear in either 2011 or 2016 boundaries. Those
require the 2006/2009 ward shapefile from the Municipal Demarcation Board.

Input:
  data/raw/units/mdb/wards_2011/MDBWard2011.gdb
  data/raw/units/mdb/wards_2016/MDBWard2016.gdb
Output:
  data/cleaned/ward_concordance_2011_2016.parquet
"""
import geopandas as gpd
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa

print("=== Building 2011-to-2016 ward concordance ===\n")

# Load boundaries
wards_2011 = gpd.read_file("data/raw/units/mdb/wards_2011/MDBWard2011.gdb")
wards_2016 = gpd.read_file("data/raw/units/mdb/wards_2016/MDBWard2016.gdb")

# Align CRS
if wards_2011.crs != wards_2016.crs:
    wards_2011 = wards_2011.to_crs(wards_2016.crs)

# Filter to Gauteng
gauteng_prefixes_2011 = ("793", "794", "796", "742", "746", "748", "831", "640", "637", "420", "830")
gauteng_prefixes_2016 = ("797", "798", "799", "742", "746", "748", "831", "640", "637", "420", "830")

wards_2011["ward_2011"] = wards_2011["WardID"].astype(str)
wards_2016["ward_2016"] = wards_2016["WardID"].astype(str)

gp_2011 = wards_2011[wards_2011["ward_2011"].str[:3].isin(gauteng_prefixes_2011)].copy()
gp_2016 = wards_2016[wards_2016["ward_2016"].str[:3].isin(gauteng_prefixes_2016)].copy()

print(f"Gauteng 2011 wards: {len(gp_2011)}")
print(f"Gauteng 2016 wards: {len(gp_2016)}")

# Compute overlay
print("\nComputing intersection overlay...")
overlay = gpd.overlay(
    gp_2011[["ward_2011", "geometry"]],
    gp_2016[["ward_2016", "geometry"]],
    how="intersection"
)
overlay["piece_area"] = overlay.geometry.to_crs(epsg=32735).area

# Area weights: for each 2011 ward, what fraction goes to each 2016 ward
total_2011 = overlay.groupby("ward_2011")["piece_area"].sum().rename("total_area_2011")
overlay = overlay.merge(total_2011, on="ward_2011")
overlay["weight"] = overlay["piece_area"] / overlay["total_area_2011"]

concordance = overlay[["ward_2011", "ward_2016", "piece_area", "weight"]].copy()

print(f"Concordance rows: {len(concordance)}")
print(f"Unique 2011 wards: {concordance['ward_2011'].nunique()}")
print(f"Unique 2016 wards: {concordance['ward_2016'].nunique()}")

# Sanity check
w_sum = concordance.groupby("ward_2011")["weight"].sum()
print(f"Weight sum per 2011 ward: min={w_sum.min():.4f}, max={w_sum.max():.4f}")

# Check how many 2011 wards map 1:1 to 2016 wards
one_to_one = concordance.groupby("ward_2011").filter(lambda g: len(g) == 1)
print(f"\n1:1 mappings: {one_to_one['ward_2011'].nunique()} wards")
print(f"1:many mappings: {concordance['ward_2011'].nunique() - one_to_one['ward_2011'].nunique()} wards")

# Save
pq.write_table(pa.Table.from_pandas(concordance), "data/cleaned/ward_concordance_2011_2016.parquet")
print("\nSaved: data/cleaned/ward_concordance_2011_2016.parquet")

print("\n=== Done ===")
