#!/usr/bin/env python3
# ============================================================
# 04_pilot_report.py
# Purpose: Compute every number in the P-B gazette pilot report from the
#          pipeline outputs and write quality_reports/pilot/P-B_gazette_pilot.md
#          (coverage, notice volume with exact Poisson CIs, stage/type mix,
#          JHB reference-number chronology, OCR share, s.4.7 / PSC-provider
#          availability, effort metrics for costing the 1999-2026 compile).
#          Descriptive only: nothing is merged with outcome data.
# Inputs:  data/cleaned/gazette/{gazette_inventory, listing_records,
#          extraction_log, sar_candidates, contents_sar_entries,
#          sar_notices_jhb_pilot}.parquet, validation_sample.csv
# Outputs: quality_reports/pilot/P-B_gazette_pilot.md
#          quality_reports/pilot/figures/P-B_jhb_ref_chronology.{pdf,png}
#          data/cleaned/gazette/pilot_metrics.json (all computed numbers)
# Usage:   py -3.12 04_pilot_report.py
# ============================================================

import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
import config  # noqa: E402
from common import setup_logging  # noqa: E402

logger = logging.getLogger("04_pilot_report")
FIG_DIR = config.REPORT_DIR / "figures"
METRICS = config.CLEAN_DIR / "pilot_metrics.json"
WINDOW_YEARS = {w: ((hi - lo).days + 1) / 365.25 for w, (lo, hi) in config.WINDOWS.items()}
METROS = ["JHB", "Tshwane", "Ekurhuleni", "other", "unknown"]


def poisson_ci(k: int, level: float = 0.95) -> tuple[float, float]:
    """Exact (Garwood) CI for a Poisson count."""
    a = 1 - level
    lo = 0.0 if k == 0 else stats.chi2.ppf(a / 2, 2 * k) / 2
    hi = stats.chi2.ppf(1 - a / 2, 2 * k + 2) / 2
    return lo, hi


def md_table(df: pd.DataFrame, floatfmt: str = "{:.1f}") -> str:
    cols = [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for v in r.values:
            if isinstance(v, float) and not np.isnan(v):
                cells.append(floatfmt.format(v))
            elif isinstance(v, float):
                cells.append("NA")
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def wednesdays(lo: date, hi: date) -> list[date]:
    d = lo + timedelta(days=(2 - lo.weekday()) % 7)
    out = []
    while d <= hi:
        out.append(d)
        d += timedelta(days=7)
    return out


# ---------------------------------------------------------------------------
def dated_numbers(inv: pd.DataFrame, listing: pd.DataFrame) -> pd.DataFrame:
    """(date, number) of every issue the inventory or either listing shows,
    in or out of window. Used to bound the expected issue-number range at a
    window edge (an issue numbered beyond the first number dated after the
    window is a mis-dated record, not a window issue)."""
    a = inv.loc[inv["issue_no"].notna() & ~inv["issue_no_suspect"].fillna(False).astype(bool),
                ["issue_date", "issue_no"]].rename(columns={"issue_date": "d", "issue_no": "n"})
    b = listing[["listing_date", "listing_issue_no"]].rename(
        columns={"listing_date": "d", "listing_issue_no": "n"})
    x = pd.concat([a, b], ignore_index=True)
    x["d"] = pd.to_datetime(x["d"], errors="coerce").dt.date
    x["n"] = pd.to_numeric(x["n"], errors="coerce")
    return x.dropna().astype({"n": int})


def runs(nums: list[int]) -> list[tuple[int, int]]:
    out = []
    for n in nums:
        if out and n == out[-1][1] + 1:
            out[-1] = (out[-1][0], n)
        else:
            out.append((n, n))
    return out


def coverage(inv: pd.DataFrame, listing: pd.DataFrame) -> tuple[str, dict]:
    ok = inv["fetch_status"].isin(["cached", "downloaded"])
    prim = inv[ok & inv["is_primary_copy"] & inv["window"].notna()].copy()
    prim["d"] = pd.to_datetime(prim["issue_date"]).dt.date
    m = {"files_downloaded": int(ok.sum()), "fetch_failures": int((~ok).sum()),
         "listing_rows": int(len(listing)), "not_gauteng": int(inv["not_gauteng"].sum()),
         "date_suspect": int(inv.loc[inv["window"].notna(), "date_suspect"].sum()),
         "issue_no_suspect": int(inv.loc[inv["window"].notna(), "issue_no_suspect"].sum()),
         "meta_conflicts": int(inv["meta_conflict"].notna().sum())}
    rows, gap_lines = [], []
    neigh = dated_numbers(inv, listing)
    for w, (lo, hi) in config.WINDOWS.items():
        g = prim[prim["window"] == w]
        wed = wednesdays(lo, hi)
        ords = sorted(g.loc[g["issue_type"] == "ordinary", "d"])
        # an ordinary issue within 2 days of a Wednesday covers it (public
        # holidays move publication to Tuesday/Thursday)
        missing_wed = [x for x in wed if not any(abs((o - x).days) <= 2 for o in ords)]
        src = g["source"].value_counts().to_dict()
        rows.append({"Window": w, "Issues (unique)": len(g),
                     "Ordinary": int((g["issue_type"] == "ordinary").sum()),
                     "Extraordinary": int((g["issue_type"] == "extraordinary").sum()),
                     "Liquor": int((g["issue_type"] == "liquor").sum()),
                     "Wednesdays": len(wed), "Wednesdays w/o ordinary": len(missing_wed),
                     "From OpenGazettes": src.get("opengazettes", 0),
                     "From GPW": src.get("gpw", 0),
                     "Pages": int(g["n_pages"].sum())})
        m[f"{w}_issues"] = len(g)
        m[f"{w}_missing_wednesdays"] = [x.isoformat() for x in missing_wed]
        # Issue-number gaps per calendar-year segment (review WP1-H2). A number
        # is "explained" if it was found in the window OR any source shows it
        # dated outside the window (same-day extraordinary issues are numbered
        # out of date order around 30 June / 1 July). Only numbers that are
        # neither found nor explained count as archive gaps. The expected range
        # is bounded by the archive at the window edges:
        #   upper: the highest in-window number. Numbers above the K-th smallest
        #          number dated after the window (K = 5, robust to one mis-dated
        #          listing row) may themselves be post-window, so they are
        #          reported separately as an upper bound on the gap count;
        #   lower: 1 if the year starts in the window, else 1 above the K-th
        #          largest number dated before the window;
        #   a window that ends with the year (31 Dec) has no later number in
        #   the series, so its tail cannot be checked.
        K = 5
        n_found_w = n_exp_w = 0
        for yr, gy in g.groupby(pd.to_datetime(g["issue_date"]).dt.year):
            nos = sorted(set(gy.loc[~gy["issue_no_suspect"], "issue_no"].astype(int)))
            ny = neigh[[d.year == yr for d in neigh["d"]]]
            before = sorted(ny.loc[[d < lo for d in ny["d"]], "n"].unique())
            after = sorted(ny.loc[[d > hi for d in ny["d"]], "n"].unique())
            outside = set(before) | set(after)
            if date(yr, 1, 1) >= lo:
                lo_n = 1
            else:
                lo_n = min(nos[0], before[-min(K, len(before))] + 1) if before else nos[0]
            tail_unverified = len(after) == 0
            hi_n = nos[-1]
            hi_safe = hi_n if tail_unverified else min(hi_n, after[min(K, len(after)) - 1] - 1)
            anomalous = [n for n in nos if n > hi_safe]
            nos_ok = list(nos)
            explained = [n for n in range(lo_n, hi_n + 1) if n not in set(nos_ok)
                         and n in outside]
            missing = [n for n in range(lo_n, hi_n + 1) if n not in set(nos_ok)
                       and n not in outside]
            missing_safe = [n for n in missing if n <= hi_safe]
            n_exp = hi_n - lo_n + 1
            n_found_w += len(nos_ok)
            n_exp_w += n_exp - len(explained)  # window issues only
            m[f"{w}_{yr}_numbers"] = {
                "range": [lo_n, hi_n], "found": len(nos_ok), "expected": n_exp,
                "dated_outside_window": explained,
                "missing": missing, "missing_runs": runs(missing),
                "missing_below_post_window_bound": missing_safe,
                "anomalous_numbers_beyond_range": anomalous,
                "tail_unverified": tail_unverified,
                "head_unverified": bool(date(yr, 1, 1) < lo and lo_n == nos[0])}
            rr = runs(missing)
            gap_lines.append(
                f"- {w} {yr}: expected numbers {lo_n}-{hi_n} ({n_exp}); {len(nos_ok)} found in "
                f"window, {len(explained)} dated just outside it, {len(missing)} not found in "
                f"either source ({100 * (n_exp - len(missing)) / n_exp:.1f}% accounted for"
                + (f"; {len(missing_safe)} of the {len(missing)} lie below the first post-window "
                   f"numbers, so {len(missing) - len(missing_safe)} may belong after the window"
                   if len(missing_safe) != len(missing) else "") + ")"
                + (f"; runs: {len(rr)}, longest {max(b_ - a_ + 1 for a_, b_ in rr)}; numbers "
                   f"{', '.join(map(str, missing[:40]))}{' ...' if len(missing) > 40 else ''}"
                   if missing else "")
                + (f"; {len(anomalous)} in-window record(s) are numbered above the first "
                   f"post-window numbers ({', '.join(map(str, anomalous))}): same-day "
                   f"extraordinary issues are numbered out of date order, and a few may be mis-dated"
                   if anomalous else "")
                + ("; the tail of the series cannot be checked (the window ends with the year)"
                   if tail_unverified else ""))
        m[f"{w}_number_coverage"] = n_found_w / n_exp_w if n_exp_w else None
        m[f"{w}_numbers_found"] = n_found_w
        m[f"{w}_numbers_expected"] = n_exp_w
    gap_lines.append(
        "- **Lower bound.** Numbers not found are archive gaps (neither OpenGazettes nor the GPW "
        "library holds them). Notices in those issues are not observed, so every volume in this "
        "report is a lower bound (by about 1% for W1 and 5% for W2 if the gaps hold notices at the average rate). "
        "Extraordinary issues dominate the gaps, and SAR notices also appear in extraordinary "
        "issues.")
    txt = md_table(pd.DataFrame(rows)) + "\n\n" + "\n".join(gap_lines)
    return txt, m


def volume(df: pd.DataFrame, cov_m: dict) -> tuple[str, dict]:
    d = df[df["is_sar_notice"]]
    rows, m = [], {}
    for w in config.WINDOWS:
        T = WINDOW_YEARS[w]
        for metro in ["All Gauteng"] + METROS:
            sub = d[d["window"] == w] if metro == "All Gauteng" else d[
                (d["window"] == w) & (d["municipality"] == metro)]
            k = len(sub)
            if metro != "All Gauteng" and k == 0:
                continue
            lo, hi = poisson_ci(k)
            cov = cov_m.get(f"{w}_number_coverage") or 1.0
            rows.append({"Window": w, "Municipality": metro, "Notices": k,
                         "Years": round(T, 2), "Per year": k / T,
                         "95% CI low": lo / T, "95% CI high": hi / T,
                         "Issue-number coverage": cov,
                         "Per year if gaps are like found issues": k / T / cov})
            m[f"{w}_{metro}"] = {"n": k, "per_year": k / T, "ci": [lo / T, hi / T]}
    # decisions = final approvals + extensions/renewals with a final step
    m["_note"] = ("Poisson CIs treat notices as independent draws; they are conditional on "
                  "the archive, cover only sampling noise, and ignore gaps, re-numbered "
                  "republications (dedup key is kind, number, year) and clustered "
                  "same-day notices.")
    return md_table(pd.DataFrame(rows), "{:.2f}"), m


def crosstab(df: pd.DataFrame, col: str) -> str:
    d = df[df["is_sar_notice"] | (df["stage"] == "other")]
    t = pd.crosstab([d["window"], d["municipality"]], d[col], margins=True,
                    margins_name="Total").reset_index()
    t.columns = [str(c) for c in t.columns]
    return md_table(t, "{:.0f}")


def ref_chronology(df: pd.DataFrame) -> tuple[str, dict]:
    j = df[df["is_jhb"] & df["is_sar_notice"]].copy()
    j["d"] = pd.to_datetime(j["first_issue_date"])
    has = j[j["ref_number"].notna()].sort_values("d")
    m = {"jhb_notices": len(j), "jhb_with_ref": len(has),
         "ref_source": has["ref_source"].value_counts().to_dict()}
    lines = [f"- JHB closure-decision notices: {len(j)}; with a parsed reference number: "
             f"{len(has)} ({100 * len(has) / max(1, len(j)):.0f}%). Source of the number: "
             + ", ".join(f"{k} {v}" for k, v in m["ref_source"].items()) + "."]
    if len(has) >= 5:
        rho, p = stats.spearmanr(has["d"].map(pd.Timestamp.toordinal), has["ref_number"])
        refs = has["ref_number"].astype(int).tolist()
        desc = sum(b < a for a, b in zip(refs, refs[1:]))
        m.update(spearman_rho=float(rho), spearman_p=float(p),
                 adjacent_decreases=int(desc), adjacent_pairs=len(refs) - 1)
        for w in config.WINDOWS:
            r = has.loc[has["window"] == w, "ref_number"].astype(int)
            if len(r):
                m[f"{w}_ref_range"] = [int(r.min()), int(r.median()), int(r.max())]
                lines.append(f"- {w}: refs min / median / max = {int(r.min())} / "
                             f"{int(r.median())} / {int(r.max())} (n = {len(r)}).")
        lines.append(f"- Spearman rank correlation of reference number with publication date: "
                     f"rho = {rho:.2f} (p = {p:.3f}). Consecutive notices (by date) where the "
                     f"number falls: {desc} of {len(refs) - 1} pairs.")
        dup = has.groupby("ref_number").filter(lambda g: len(g) > 1)
        m["refs_seen_twice"] = int(dup["ref_number"].nunique())
        if len(dup):
            ex = dup.sort_values(["ref_number", "d"]).groupby("ref_number").apply(
                lambda g: f"{int(g.name)}: " + " -> ".join(
                    f"{x.date()} {s}" for x, s in zip(g["d"], g["stage"])),
                include_groups=False)
            lines.append(f"- Reference numbers appearing on more than one notice: "
                         f"{len(ex)} (e.g. " + "; ".join(ex.head(8)) + ").")
        _plot_refs(has)
    return "\n".join(lines), m


def _plot_refs(has: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "serif", "font.size": 11})
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4))
    styles = {"intent": ("#0072B2", "o"), "final_approval": ("#D55E00", "s"),
              "renewal": ("#009E73", "^"), "extension": ("#CC79A7", "D"),
              "removal": ("#000000", "x"), "unknown": ("#999999", "v")}
    for stage, (col, mk) in styles.items():
        s = has[has["stage"] == stage]
        if len(s):
            ax.scatter(s["d"], s["ref_number"], c=col, marker=mk, s=28, label=stage.replace("_", " "),
                       alpha=0.85, edgecolors="none" if mk != "x" else None)
    ax.set_xlabel("Gazette publication date")
    ax.set_ylabel("JRA application reference number")
    ax.grid(axis="y", color="#dddddd", linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=6, frameon=False, fontsize=9)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIG_DIR / f"P-B_jhb_ref_chronology.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)
    has[["notice_id", "first_issue_date", "ref_number", "ref_source", "stage"]].to_csv(
        FIG_DIR / "P-B_jhb_ref_chronology_data.csv", index=False)


def availability(df: pd.DataFrame) -> tuple[str, dict]:
    d = df[df["is_sar_notice"]]
    rows = []
    for metro in ["JHB", "Tshwane", "Ekurhuleni", "other"]:
        s = d[d["municipality"] == metro]
        if not len(s):
            continue
        rows.append({"Municipality": metro, "Notices": len(s),
                     "Ref no. %": 100 * s["ref_number"].notna().mean(),
                     "Suburb %": 100 * s["suburb"].notna().mean(),
                     "Streets %": 100 * (s["n_streets"] > 0).mean(),
                     "Applicant %": 100 * s["applicant"].notna().mean(),
                     "s.4.7 count %": 100 * s["affected_persons_n"].notna().mean(),
                     "PSC provider %": 100 * s["psc_provider"].notna().mean(),
                     "PSIRA mentioned %": 100 * s["psira_mentioned"].mean(),
                     "Validity %": 100 * s["validity_months"].notna().mean(),
                     "OCR used %": 100 * s["ocr_used"].mean(),
                     "Manual review %": 100 * s["needs_manual_review"].mean()})
    t = pd.DataFrame(rows)
    m = {"affected_n_found": int(d["affected_persons_n"].notna().sum()),
         "psc_found": int(d["psc_provider"].notna().sum()),
         "psc_values": d["psc_provider"].dropna().value_counts().to_dict(),
         "validity_months": d["validity_months"].value_counts().to_dict()}
    return md_table(t, "{:.0f}"), m


def effort(inv: pd.DataFrame, log: pd.DataFrame, df: pd.DataFrame, cands: pd.DataFrame,
           contents: pd.DataFrame) -> tuple[str, dict]:
    dl = inv["download_seconds"].dropna()
    per_issue = log["seconds_total"]
    m = {"issues_processed": len(log), "pages": int(log["n_pages"].sum()),
         "pages_ocr": int(log["n_ocr_pages"].sum()),
         "pages_rotated": int(log.get("n_rotated", pd.Series([0])).sum()),
         "share_pages_ocr": float(log["n_ocr_pages"].sum() / log["n_pages"].sum()),
         "issues_with_ocr": int((log["n_ocr_pages"] > 0).sum()),
         "download_s_mean": float(dl.mean()) if len(dl) else None,
         "download_s_total": float(dl.sum()) if len(dl) else None,
         "cpu_s_per_issue_mean": float(per_issue.mean()),
         "cpu_s_per_issue_p90": float(per_issue.quantile(0.9)),
         "cpu_s_total": float(per_issue.sum()),
         "ocr_s_total": float(log["seconds_ocr"].sum()),
         "notices": len(df), "notices_manual": int(df["needs_manual_review"].sum()),
         "notices_ocr": int(df["ocr_used"].sum()),
         "candidates_total": len(cands),
         "contents_entries": len(contents),
         "contents_found": int(contents["found_in_body"].sum()) if len(contents) else 0}
    issues_per_year = np.mean([m_ / WINDOW_YEARS[w] for w, m_ in (
        (w, (inv["window"] == w).sum()) for w in config.WINDOWS)])
    m["issues_per_year"] = float(issues_per_year)
    years = 2026 - 1999 + 1
    n_issues_full = issues_per_year * years
    m["full_compile_issues_est"] = float(n_issues_full)
    m["full_compile_download_h"] = float(n_issues_full * (m["download_s_mean"] or 4) / 3600)
    m["full_compile_cpu_h_6workers"] = float(n_issues_full * m["cpu_s_per_issue_mean"] / 3600 / 6)
    notices_per_year = np.mean([(df["window"] == w).sum() / WINDOW_YEARS[w]
                                for w in config.WINDOWS])
    m["notices_per_year"] = float(notices_per_year)
    m["full_compile_notices_est"] = float(notices_per_year * years)
    lines = [
        f"- Issues processed: {len(log)} ({m['pages']:,} pages). Pages OCR'd: {m['pages_ocr']:,} "
        f"({100 * m['share_pages_ocr']:.1f}%), in {m['issues_with_ocr']} issues; landscape "
        f"(rotated-text) pages read from the unsorted text layer: {m['pages_rotated']}.",
        f"- Download: {m['download_s_mean']:.1f} s per file on average at the 2 s/request "
        f"limit ({m['download_s_total'] / 3600:.2f} h for {len(dl)} files)." if len(dl) else
        "- Download time: not recorded (all files were already cached).",
        f"- Extraction + OCR (6 local processes): {m['cpu_s_per_issue_mean']:.1f} s per issue on "
        f"average (p90 {m['cpu_s_per_issue_p90']:.1f} s); OCR is {100 * m['ocr_s_total'] / max(1, m['cpu_s_total']):.0f}% "
        f"of it. Parsing (03) takes seconds.",
        f"- Notices needing manual reading (any of: stage, municipality or reference missing, "
        f"restriction type unknown, or detected only via the contents page): "
        f"{m['notices_manual']} of {len(df)} ({100 * m['notices_manual'] / max(1, len(df)):.0f}%); "
        f"notices whose text came (partly) from OCR: {m['notices_ocr']} "
        f"({100 * m['notices_ocr'] / max(1, len(df)):.0f}%).",
    ]
    lines.append(
        "- **Extrapolation caveat.** The 1999-2026 effort figures scale two sampled windows "
        "(2017-18 and Jul 2021-Jun 2022) linearly to 28 years. Issue counts, notice volume "
        "and OCR share vary over time (older gazettes are more often scanned; extraordinary "
        "issue volume spiked in 2022), so treat them as order-of-magnitude.")
    return "\n".join(lines), m


def main():
    setup_logging("04_pilot_report")
    inv = pd.read_parquet(config.INVENTORY)
    listing = pd.read_parquet(config.LISTING_RECORDS)
    log = pd.read_parquet(config.EXTRACTION_LOG)
    cands = pd.read_parquet(config.SAR_CANDIDATES)
    contents = pd.read_parquet(config.CONTENTS_ENTRIES)
    df = pd.read_parquet(config.SAR_NOTICES)
    val = pd.read_csv(config.VALIDATION_SAMPLE)

    cov_txt, cov_m = coverage(inv, listing)
    vol_txt, vol_m = volume(df, cov_m)
    ref_txt, ref_m = ref_chronology(df)
    av_txt, av_m = availability(df)
    eff_txt, eff_m = effort(inv, log, df, cands, contents)
    d_sar = df[df["is_sar_notice"]]
    qual = {"flag_multi_notice": int(d_sar["flag_multi_notice"].sum()),
            "dup_suspect": int(d_sar["dup_suspect"].sum()),
            "removal_phrase_anywhere": int(d_sar["removal_phrase_anywhere"].sum()),
            "stage_counts": d_sar["stage"].value_counts().to_dict(),
            "procedural_by_stage": pd.crosstab(d_sar["stage"], d_sar["procedural_stage"])
            .to_dict()}
    metrics = {"quality": qual, "coverage": cov_m, "volume": vol_m, "refs": ref_m, "availability": av_m,
               "effort": eff_m,
               "stage_counts": df.groupby(["window", "municipality", "stage"]).size()
               .rename("n").reset_index().to_dict("records"),
               "validation_strata": val["sample_stratum"].value_counts().to_dict(),
               "validation_roles": val["sample_role"].value_counts().to_dict()}
    METRICS.write_text(json.dumps(metrics, indent=1, default=str), encoding="utf-8")

    tables = {
        "coverage": cov_txt, "volume": vol_txt, "stage": crosstab(df, "stage"),
        "procedural": crosstab(df, "procedural_stage"),
        "type": crosstab(df, "restriction_type"), "refs": ref_txt,
        "availability": av_txt, "effort": eff_txt,
        "n_val": str(len(val)), "n_val_precision": str(int((val["sample_role"] == "precision").sum())),
        "n_val_recall": str(int((val["sample_role"] == "recall").sum())),
        "val_strata": "; ".join(f"{k} {v}" for k, v in
                                val["sample_stratum"].value_counts().items()),
        "n_multi": str(qual["flag_multi_notice"]), "n_dup": str(qual["dup_suspect"]),
        "n_removal_any": str(qual["removal_phrase_anywhere"]),
    }
    tmpl = (Path(__file__).parent / "report_template.md").read_text(encoding="utf-8")
    report = tmpl
    for k, v in tables.items():
        report = report.replace("{{" + k + "}}", v)
    assert "{{" not in report, "unfilled template field"
    config.PILOT_REPORT.write_text(report, encoding="utf-8")
    logger.info("Wrote %s and %s", config.PILOT_REPORT.relative_to(config.REPO_ROOT),
                METRICS.relative_to(config.REPO_ROOT))


if __name__ == "__main__":
    main()
