#!/usr/bin/env python3
# ============================================================
# scripts/cleaning/e3/02_parse_levy_tables.py
# Title:   Parse SRA additional-rate (levy) lines from City budget documents
# Author:  data-engineer (PSC Exposure project)
# Date:    2026-09-30
# Purpose: WP5 step 3. Onset priority 1 (memo s5.4) is "the first City FY with
#          an SRA additional-rate budget line". This script turns every budget
#          document that lists SRA levies into one row per SRA x FY x source:
#            - Budget tariff books FY2007/08 and FY2009/10 (Wayback), each with
#              a prior-year column (FY2006/07, FY2008/09);
#            - Budget Annexure 3 FY2014/15..FY2026/27, two-period tables
#              (prior approved + proposed) to FY2019/20 and single-period
#              tables with separate residential / non-residential rates after.
#          It also parses each annexure's footnote legend so the row-level
#          flags (*, **, #) become "new_approved", "new_pending", "renewal".
# Inputs:  data/raw/e3/text/*.txt, data/raw/e3/provenance.csv,
#          scripts/cleaning/e3/manual/sra_crosswalk.csv
# Outputs: data/cleaned/e3/intermediate/levy_lines.csv
#          data/cleaned/e3/intermediate/levy_unmatched_lines.csv (QA)
#          data/cleaned/e3/intermediate/levy_flag_legends.csv
# Usage:   py -3.12 scripts/cleaning/e3/02_parse_levy_tables.py
# ============================================================

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e3_config import INTERMEDIATE, MANUAL, PROVENANCE, RAW_TEXT  # noqa: E402

NUM = re.compile(r"^-?\d[\d,]*(?:\.\d+)?$")
TOKEN = re.compile(r"N/A|Delete|-?\d{1,3}(?:[, ]\d{3})+(?:\.\d+)?|-?\d+\.\d+|-?\d+")
SUBLINE = re.compile(r"^\s*-\s*(Residential|Non[- ]?Residential(?:\s*>\s*50%)?|Commercial)", re.I)
NOISE = re.compile(
    r"^(=== PAGE|City of Cape Town|Annexure|ANNEXURE|Page \||\d{4}/\d{2} Budget|Amended at|"
    r"CITY IMPROVEMENT|ADDITIONAL RATES|Approved|Budget|Special Rating Area\s|City Improvement"
    r"|R( R)*$|R$|\d{4}/\d{2}( \d{4}/\d{2})*$|Residential Non|Additional Rate|\d+$|Rate$)")


def isnum(tok: str) -> bool:
    return bool(NUM.match(tok.replace(" ", "")))


def to_float(tok: str) -> float | None:
    t = tok.replace(",", "").replace(" ", "")
    return float(t) if NUM.match(t) else None


def load_xwalk() -> list[tuple[str, re.Pattern]]:
    xw = pd.read_csv(MANUAL / "sra_crosswalk.csv")
    # longest patterns first so "Claremont Boulevard" beats "Claremont"
    rows = sorted(xw.itertuples(), key=lambda r: -len(r.levy_pattern))
    return [(r.sra_key, re.compile(r.levy_pattern, re.I)) for r in rows]


def match_sra(line: str, xw) -> str | None:
    for key, pat in xw:
        if pat.search(line):
            return key
    return None


def tokens(line: str) -> list[str]:
    # drop the name part: tokens are taken only after the last letter run that is
    # not N/A / Delete, so names containing digits are not an issue here
    return [t.replace(" ", "") if t not in ("N/A", "Delete") else t
            for t in TOKEN.findall(line)]


def legend(text: str) -> dict[str, str]:
    """Footnote legend: symbol -> meaning (new_approved/new_pending/renewal)."""
    out = {}
    for m in re.finditer(r"(?m)^\s*(\*\*|\*|#)\s*(.{10,200})$", text):
        sym, desc = m.group(1), m.group(2).lower()
        if "establish" in desc:
            out[sym] = "new_pending" if "subject to" in desc else "new_approved"
        elif re.search(r"further period|exten|new business plan|further term", desc):
            out[sym] = "renewal_pending" if "subject to" in desc else "renewal_approved"
    return out


# ---------------------------------------------------------------------------
def parse_tariff_book(text: str, fy_prior: int, fy_cur: int, sid: str, xw) -> list[dict]:
    """Budget tariff books: '<name>[ - Cat] cent-in-the-rand [prior] y <cur>'."""
    rows = []
    start = text.find("CID/MID RATES LEVIES")
    for line in text[start:].splitlines():
        if "cent-in-the-rand" not in line:
            continue
        name = line.split("cent-in-the-rand")[0].strip()
        key = match_sra(name, xw)
        if key is None:
            continue
        cat = "all"
        m = re.search(r"-\s*(Commercial|Residential|Relief Main Road|Boulevard)\s*$", name, re.I)
        if m and m.group(1).lower() in ("commercial", "residential"):
            cat = "non_residential" if m.group(1).lower() == "commercial" else "residential"
        rest = line.split("cent-in-the-rand", 1)[1]
        left, _, right = rest.partition(" y ")
        lt = [t for t in tokens(left) if isnum(t)]
        rt = [t for t in tokens(right) if isnum(t)]
        for fy, toks, role in ((fy_prior, lt, "prior"), (fy_cur, rt, "current")):
            rows.append(dict(sra_key=key, fy=fy, source_id=sid, column_role=role,
                             category=cat, present=bool(toks), budget=None,
                             rate=to_float(toks[-1]) if toks else None,
                             flag_raw="", flag_meaning="", raw=line.strip()[:160]))
    return rows


def table_lines(text: str) -> list[str]:
    lines = text.splitlines()
    # table begins after the first header row made only of "R" tokens
    begin = next((i for i, ln in enumerate(lines) if re.fullmatch(r"\s*R(\s+R)*\s*", ln)), None)
    if begin is None:
        return []
    out = []
    for ln in lines[begin + 1:]:
        # stop at the note or at the footnote legend ("*Subject to ...", "# On ...")
        if re.match(r"^\s*Note\s*:", ln) or re.match(
                r"^\s*(\*\*|\*|#)\s*(Subject|On |Council)", ln):
            break
        out.append(ln)
    return out


def parse_annex3(text: str, fy: int, sid: str, xw, unmatched: list) -> list[dict]:
    two_period = fy <= 2019   # single-period (budget, res rate, non-res rate) from FY2020/21
    leg = legend(text)
    blocks: list[dict] = []
    cur = None
    for raw in table_lines(text):
        ln = raw.strip()
        if not ln or NOISE.match(ln):
            continue
        flags = re.findall(r"\*\*|\*|#", ln)
        clean = re.sub(r"^[*#\s]+", "", ln)
        key = match_sra(clean, xw)
        if key is not None:
            cur = dict(sra_key=key, lines=[clean], flags=flags)
            blocks.append(cur)
            continue
        if cur is None:
            continue
        if flags:
            cur["flags"] += flags
        cur["lines"].append(clean)
        if (re.match(r"^[A-Z][a-z]", clean) and not SUBLINE.match(clean)
                and not re.match(r"^(Total|Beam|Property Owners|> ?50)", clean)
                and TOKEN.search(clean)):
            unmatched.append(dict(source_id=sid, fy=fy, line=clean))
    rows = []
    for b in blocks:
        body = [x for x in b["lines"] if not re.match(r"^Total\b", x)]
        cats: dict[str, dict] = {}
        first_toks = tokens(body[0])
        long_lines = []
        for x in body:
            m = SUBLINE.match(x)
            cat = "all"
            if m:
                c = m.group(1).lower()
                cat = "residential" if c == "residential" else "non_residential"
                if ">" in c:
                    cat = "non_residential_gt50"
            t = tokens(x)
            if len(t) >= 4:
                long_lines.append(t)
            if t:
                cats.setdefault(cat, dict(toks=[]))["toks"].append(t)
        meaning = "|".join(sorted({leg.get(f, f"unknown:{f}") for f in b["flags"]}))
        if two_period:
            if long_lines:
                prior_present = any(isnum(t[0]) for t in long_lines) or (
                    len(first_toks) == 2 and isnum(first_toks[0]))
                cur_present = any(isnum(t[2]) for t in long_lines) or any(
                    len(tokens(x)) in (2, 3) and isnum(tokens(x)[0]) for x in body[1:])
            else:
                prior_present = None      # layout ambiguous (e.g. split rows)
                cur_present = True
            for cat, d in cats.items():
                t4 = [t for t in d["toks"] if len(t) >= 4]
                pb = to_float(t4[0][0]) if t4 else None
                cb = to_float(t4[0][2]) if t4 else None
                pr = to_float(t4[0][1]) if t4 else None
                cr = to_float(t4[0][3]) if t4 else None
                for role, fy_, pres, bud, rate in (("prior", fy - 1, prior_present, pb, pr),
                                                   ("current", fy, cur_present, cb, cr)):
                    rows.append(dict(sra_key=b["sra_key"], fy=fy_, source_id=sid,
                                     column_role=role, category=cat, present=pres,
                                     budget=bud, rate=rate,
                                     flag_raw="".join(b["flags"]) if role == "current" else "",
                                     flag_meaning=meaning if role == "current" else "",
                                     raw=" / ".join(b["lines"])[:300]))
        else:
            # names can wrap ("Oakwood / Hughenden /" + numbers + "Meadows"):
            # use the first line of the block that carries tokens
            t = next((tokens(x) for x in body if tokens(x)), [])
            budget = to_float(t[0]) if t and isnum(t[0]) else None
            res = t[1] if len(t) > 1 else ""
            nonres = t[2] if len(t) > 2 else ""
            if len(t) == 1 and b["sra_key"] == "glosderry":
                res = t[0]
            for cat, tok in (("residential", res), ("non_residential", nonres)):
                rows.append(dict(sra_key=b["sra_key"], fy=fy, source_id=sid,
                                 column_role="current", category=cat,
                                 present=bool(tok) and isnum(tok),
                                 budget=budget, rate=to_float(tok) if tok else None,
                                 flag_raw="".join(b["flags"]), flag_meaning=meaning,
                                 raw=" / ".join(b["lines"])[:300]))
    return rows


def main() -> None:
    INTERMEDIATE.mkdir(parents=True, exist_ok=True)
    xw = load_xwalk()
    prov = pd.read_csv(PROVENANCE)
    rows, unmatched, legends = [], [], []
    tb = {"wb_tariff_rates_cids_fy2007": (2006, 2007), "wb_tariff_rates_cids_fy2009": (2008, 2009)}
    for sid, (fp, fc) in tb.items():
        rows += parse_tariff_book((RAW_TEXT / f"{sid}.txt").read_text(encoding="utf-8"),
                                  fp, fc, sid, xw)
    for r in prov[prov.category == "annex3_additional_rates"].itertuples():
        text = (RAW_TEXT / f"{r.source_id}.txt").read_text(encoding="utf-8")
        if int(r.fy) == 2017:     # policy precedes the table in this PDF
            text = text[text.find("ADDITIONAL RATES 2017/2018"):]
        rows += parse_annex3(text, int(r.fy), r.source_id, xw, unmatched)
        for sym, m in legend(text).items():
            legends.append(dict(source_id=r.source_id, fy=int(r.fy), symbol=sym, meaning=m))
    df = pd.DataFrame(rows)
    df.to_csv(INTERMEDIATE / "levy_lines.csv", index=False, quoting=csv.QUOTE_NONNUMERIC)
    pd.DataFrame(unmatched, columns=["source_id", "fy", "line"]).to_csv(
        INTERMEDIATE / "levy_unmatched_lines.csv", index=False)
    pd.DataFrame(legends).to_csv(INTERMEDIATE / "levy_flag_legends.csv", index=False)
    per_fy = df[df.present == True].groupby("fy").sra_key.nunique()  # noqa: E712
    print("SRAs with a levy line, by City FY start year:")
    print(per_fy.to_string())
    print(f"rows {len(df)}; unmatched candidate lines {len(unmatched)}")


if __name__ == "__main__":
    main()
