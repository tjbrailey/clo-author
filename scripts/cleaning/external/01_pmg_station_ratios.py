#!/usr/bin/env python3
# ============================================================
# 01_pmg_station_ratios.py
# Parse PMG written reply NW3216 (27 Nov 2018): residents per police officer
# for each Gauteng station, and match station names to the SAPS crime panel.
# Input:  data/raw/pmg_nw3216/nw3216_2018.html (saved from
#         https://pmg.org.za/committee-question/11688/)
# Output: data/cleaned/pmg_station_police_ratio_2018.csv
# Usage:  py -3.12 -I scripts/cleaning/external/01_pmg_station_ratios.py
# ============================================================
import html
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
raw = (ROOT / "data/raw/pmg_nw3216/nw3216_2018.html").read_text(encoding="utf-8", errors="replace")
raw = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
lines = [l.strip() for l in html.unescape(re.sub(r"<[^>]+>", "\n", raw)).split("\n") if l.strip()]

start = next(i for i, l in enumerate(lines) if l.startswith("Reply"))
end = next((i for i in range(start, len(lines)) if lines[i].startswith("(b)")), len(lines))

rows, cluster, prev = [], None, None
for l in lines[start:end]:
    m_cluster = re.match(r"^(.+?)\s*\((\d+)\)$", l)
    m_ratio = re.match(r"^1\s*:\s*([\d\s,]+)$", l)
    if m_cluster and not l.startswith("(a)"):
        cluster = re.sub(r"\s+", " ", re.sub(r"[^\w\s-]", " ", m_cluster.group(1))).strip()
    elif m_ratio and prev is not None:
        rows.append({"cluster": cluster, "station_reply": prev,
                     "residents_per_officer": int(re.sub(r"[\s,]", "", m_ratio.group(1)))})
        prev = None
    elif not re.match(r"^\d+$", l) and not l.startswith("(a)"):
        prev = l

df = pd.DataFrame(rows)
df["station"] = df.station_reply.str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
# reply spelling/OCR -> SAPS crime-panel name ("protea glen" left unmatched: the panel's
# "protea" station only appears from 2024, so equating them would be a guess)
CROSSWALK = {"attridgeville": "atteridgeville", "bekkergdal": "bekkersdal", "crystal park": "crystalpark",
             "heidelberg": "heidelberg (gp)", "johannesburg central": "jhb central", "kli town": "kliptown",
             "kwa-thema": "kwa thema", "lyttleton": "lyttelton", "mofatview": "moffatview",
             "na)edi": "naledi", "norkem park": "norkempark", "pulfontein": "putfontein",
             "reiger park": "reigerpark", "roodepood": "roodepoort", "soshanguue": "soshanguve"}
df["station"] = df.station.replace(CROSSWALK)

saps = pd.read_parquet(ROOT / "data/cleaned/saps_crime_ward.parquet", columns=["station"])
gp = set(saps.station.str.lower().str.strip())
df["in_saps_panel"] = df.station.isin(gp)
df["year"] = 2018
df["source"] = "PMG NW3216, reply 27 Nov 2018"

out = ROOT / "data/cleaned/pmg_station_police_ratio_2018.csv"
df.to_csv(out, index=False)
print(f"Stations parsed: {len(df)} in {df.cluster.nunique()} clusters; "
      f"matched to SAPS panel: {df.in_saps_panel.sum()}/{len(df)}")
print("Unmatched (reply spelling):", sorted(df.loc[~df.in_saps_panel, "station"]))
print("SAPS Gauteng stations not in reply:", sorted(gp - set(df.station)))
print(f"Saved: {out}")
