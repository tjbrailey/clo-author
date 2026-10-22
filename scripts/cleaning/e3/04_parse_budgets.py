#!/usr/bin/env python3
# ============================================================
# scripts/cleaning/e3/04_parse_budgets.py
# Title:   SRA expenditure budgets by category -> security (first-stage) share
# Author:  data-engineer (PSC Exposure project)
# Date:    2026-09-30
# Purpose: WP5 step 5. Memo s5.3: the first stage is levy-funded security
#          spend. The City Open Data Portal publishes each SRA's approved
#          budget by expense category for FY2015/16, FY2016/17 (ODS) and
#          FY2021/22-2023/24 (XLSX). This script reads all of them into one
#          long table and computes the security share of total expenditure.
#          Security = "Security Services" / "Public Safety Services" (the
#          label changed between vintages) plus "Law Enforcement Officers"
#          (City LEOs contracted by the SRA), kept as separate columns too.
# Inputs:  data/raw/e3/docs/odp_budget_*.{zip,xlsx}, manual/sra_crosswalk.csv
# Outputs: data/cleaned/e3/intermediate/budget_lines.csv (long)
#          data/cleaned/e3/sra_security_budget.parquet (sra_key x fy)
# Usage:   py -3.12 scripts/cleaning/e3/04_parse_budgets.py
# ============================================================

from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e3_config import CLEAN, INTERMEDIATE, MANUAL, RAW_DOCS, fy_start  # noqa: E402

SECURITY = re.compile(r"^(security services|public safety services)$", re.I)
LEO = re.compile(r"law enforcement", re.I)


def xwalk():
    xw = pd.read_csv(MANUAL / "sra_crosswalk.csv")
    return xw


def key_for(name: str, xw: pd.DataFrame, col: str) -> str | None:
    name = str(name).strip()
    hits = [r.sra_key for r in xw.itertuples()
            if re.search(getattr(r, col), name, re.I)]
    # prefer the longest pattern (e.g. "Claremont Road" over "Claremont")
    hits = sorted(hits, key=lambda k: -len(xw.set_index("sra_key").at[k, col]))
    return hits[0] if hits else None


def read_member(zpath: Path) -> tuple[bytes, str]:
    with zipfile.ZipFile(zpath) as z:
        name = [n for n in z.namelist() if re.search(r"\.(xlsx|ods)$", n)][0]
        return z.read(name), name


def parse_xlsx(data: bytes, source_id: str, xw) -> list[dict]:
    """One sheet per SRA; header row 1 has FY labels in columns 1,3,5."""
    rows = []
    book = pd.read_excel(io.BytesIO(data), sheet_name=None, header=None)
    for sheet, df in book.items():
        if sheet.strip().lower() == "blank":
            continue
        key = key_for(sheet, xw, "odp_sheet_pattern")
        if key is None:
            raise ValueError(f"{source_id}: unmapped sheet {sheet!r}")
        fy_cols = {c: str(df.iat[1, c]) for c in range(1, df.shape[1])
                   if re.match(r"^\d{4}/\d{2}$", str(df.iat[1, c]).strip())}
        in_exp = False
        for i in range(3, df.shape[0]):
            label = str(df.iat[i, 0]).strip()
            if label.lower().startswith("income"):
                break
            in_exp = True
            for c, fy in fy_cols.items():
                v = pd.to_numeric(df.iat[i, c], errors="coerce")
                if pd.notna(v):
                    rows.append(dict(sra_key=key, fy=fy_start(fy), category_raw=label,
                                     amount=float(v), source_id=source_id, sheet=sheet))
        assert in_exp
    return rows


def parse_ods(data: bytes, source_id: str, xw) -> list[dict]:
    """Single sheet of stacked blocks: [n, name, 'YYYY/YY'] then category rows."""
    df = pd.read_excel(io.BytesIO(data), header=None, engine="odf", dtype=object)
    rows, key, fy = [], None, None
    for i in range(df.shape[0]):
        c0, c1, c2 = df.iat[i, 0], df.iat[i, 1], df.iat[i, 2]
        if pd.notna(c0) and re.match(r"^\d{4}/\d{2}$", str(c2).strip()):
            key = key_for(c1, xw, "levy_pattern")
            if key is None:
                raise ValueError(f"{source_id}: unmapped block {c1!r}")
            fy = fy_start(str(c2).strip())
            continue
        if key is None or pd.isna(c1):
            continue
        label = str(c1).strip()
        if label.lower() in ("income", "expenditure") or label.lower().startswith(
                ("revenue", "utilisation", "total income", "(surplus")):
            continue
        v = pd.to_numeric(c2, errors="coerce")
        if pd.notna(v) and v >= 0:
            rows.append(dict(sra_key=key, fy=fy, category_raw=label, amount=float(v),
                             source_id=source_id, sheet=""))
    return rows


def main() -> None:
    xw = xwalk()
    rows = []
    for p in sorted(RAW_DOCS.glob("odp_budget_*")):
        if p.name.endswith(".json"):
            continue
        sid = p.stem
        if p.suffix == ".zip":
            data, member = read_member(p)
        else:
            data, member = p.read_bytes(), p.name
        if member.endswith(".ods"):
            rows += parse_ods(data, sid, xw)
        else:
            rows += parse_xlsx(data, sid, xw)
    df = pd.DataFrame(rows)
    # income rows in the ODS vintages sit after "Income"; drop anything after
    # "Total Expenditure" by keeping only expenditure-type labels
    df = df[~df.category_raw.str.contains(r"^total income|revenue|additional rates|"
                                          r"accumulat|sponsorship", case=False)]
    # the same FY can appear in several vintages (2021-23 zip, 2021-24 xlsx,
    # 2023-24 zip); keep the most recent publication for each SRA x FY
    rank = {"odp_budget_2021_24_xlsx": 3, "odp_budget_2023_24_zip": 2,
            "odp_budget_2021_23_zip": 1}
    df["vintage_rank"] = df.source_id.map(rank).fillna(0)
    best = df.groupby(["sra_key", "fy"]).vintage_rank.transform("max")
    df = df[df.vintage_rank == best].drop(columns="vintage_rank")
    df["is_total"] = df.category_raw.str.match(r"(?i)^total expenditure")
    df["is_security"] = df.category_raw.str.match(SECURITY)
    df["is_leo"] = df.category_raw.str.contains(LEO)
    INTERMEDIATE.mkdir(parents=True, exist_ok=True)
    df.to_csv(INTERMEDIATE / "budget_lines.csv", index=False)

    keys = ["sra_key", "fy", "source_id"]
    df["amt_total"] = df.amount.where(df.is_total, 0.0)
    df["amt_security"] = df.amount.where(df.is_security, 0.0)
    df["amt_leo"] = df.amount.where(df.is_leo, 0.0)
    out = (df.groupby(keys)[["amt_total", "amt_security", "amt_leo"]].sum().reset_index()
           .rename(columns={"amt_total": "total_expenditure",
                            "amt_security": "security_services",
                            "amt_leo": "law_enforcement_officers"}))
    out = out[out.total_expenditure > 0].copy()
    out["security_total"] = out.security_services + out.law_enforcement_officers
    out["security_share"] = out.security_total / out.total_expenditure
    out.to_parquet(CLEAN / "sra_security_budget.parquet", index=False)
    print(out.groupby("fy").agg(n=("sra_key", "nunique"),
                                mean_share=("security_share", "mean"),
                                n_zero=("security_total", lambda s: int((s == 0).sum()))))


if __name__ == "__main__":
    main()
