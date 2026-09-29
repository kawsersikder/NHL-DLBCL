"""Cross-check every number in the manuscript tables against the frozen CSVs.

The manuscript's whole argument is methodological rigour, so a transcription
error in it would be uniquely damaging. This parses the LaTeX ladder and
paired-difference tables out of main.tex and compares each value to the source
result file, reporting any disagreement beyond display rounding.

Usage:
    python src/analysis/audit_manuscript_numbers.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TEX = ROOT / "reports/preprint/main.tex"
TABLES = ROOT / "reports/phase_03c_results_tables"

# Model id -> the leading cell text used in the manuscript ladder table.
LADDER_ROWS = {
    "M1": r"\textbf{M1}", "M5": r"\textbf{M5}", "M0a": "M0a", "M4b": "M4b",
    "M4c": "M4c", "M0b": "M0b", "M2": "M2", "M4a": "M4a", "M3": "M3",
}

NUM = r"[-−]?\d+\.\d+"


def numbers(text: str) -> list[float]:
    """Pull every decimal number out of a table row, normalising minus signs."""
    raw = re.findall(NUM, text)
    return [float(x.replace("−", "-")) for x in raw]


def find_row(tex: str, cell: str, min_numbers: int = 1) -> str | None:
    """Return the table row whose first cell is exactly ``cell``.

    Matched line-by-line rather than by regex: LaTeX rows contain backslash
    commands (``\\checkmark``, ``$\\times$``) that defeat naive row patterns.

    A model id such as ``M0a`` heads a row in BOTH the Methods ladder-definition
    table (integers only) and the Results table (the values we want), so
    candidates are filtered by how many decimals they carry and the richest is
    returned.
    """
    target = cell.strip()
    candidates = [
        line for line in tex.splitlines()
        if "&" in line and line.split("&", 1)[0].strip() == target
    ]
    candidates = [c for c in candidates if len(numbers(c)) >= min_numbers]
    if not candidates:
        return None
    return max(candidates, key=lambda c: len(numbers(c)))


def close(a: float, b: float, places: int) -> bool:
    return round(a, places) == round(b, places)


def main() -> int:
    tex = TEX.read_text(encoding="utf-8")
    lad = pd.read_csv(TABLES / "model_ladder_cohortA.csv").set_index("model")
    prd = pd.read_csv(TABLES / "paired_differences_cohortA.csv")

    problems: list[str] = []
    checked = 0

    # ---- main ladder table -------------------------------------------------
    print("=" * 74)
    print("LADDER TABLE  (Harrell C, CI, Uno C, IBS, calibration slope)")
    print("=" * 74)
    print(f"{'model':6} {'field':16} {'manuscript':>12} {'source':>12}  ok")

    for mid, cell in LADDER_ROWS.items():
        row = find_row(tex, cell, min_numbers=6)
        if row is None:
            problems.append(f"{mid}: ladder row not found in main.tex")
            continue
        vals = numbers(row)
        # Expect: C, ci_lo, ci_hi, uno, ibs, slope  (k and kept are integers)
        if len(vals) < 6:
            problems.append(f"{mid}: only {len(vals)} decimals parsed")
            continue
        c, lo, hi, uno, ibs, slope = vals[:6]
        src = lad.loc[mid]
        for name, got, want, places in [
            ("harrell_c", c, src.harrell_c_pooled, 3),
            ("ci_lower", lo, src.harrell_c_lower, 3),
            ("ci_upper", hi, src.harrell_c_upper, 3),
            ("uno_c", uno, src.uno_c, 3),
            ("integrated_brier", ibs, src.integrated_brier, 3),
            ("calib_slope", slope, src.calibration_slope, 2),
        ]:
            checked += 1
            good = close(got, want, places)
            if not good:
                problems.append(
                    f"{mid} {name}: manuscript {got} vs source {want:.6f}")
            print(f"{mid:6} {name:16} {got:>12.3f} {want:>12.6f}  "
                  f"{'ok' if good else 'MISMATCH'}")

    # ---- paired differences table -----------------------------------------
    print()
    print("=" * 74)
    print("PAIRED DIFFERENCES TABLE  (delta C and CI vs M1)")
    print("=" * 74)
    print(f"{'comparison':14} {'field':10} {'manuscript':>12} {'source':>12}  ok")

    tex_pairs = {
        "M5": r"\textbf{M5 $-$ M1}", "M0a": "M0a $-$ M1", "M4b": "M4b $-$ M1",
        "M4c": "M4c $-$ M1", "M0b": "M0b $-$ M1", "M2": "M2 $-$ M1",
        "M4a": "M4a $-$ M1", "M3": "M3 $-$ M1",
    }
    for mid, cell in tex_pairs.items():
        row = find_row(tex, cell)
        if row is None:
            problems.append(f"{mid}: paired row not found")
            continue
        vals = numbers(row)
        if len(vals) < 3:
            problems.append(f"{mid}: paired row parsed {len(vals)} numbers")
            continue
        d, lo, hi = vals[:3]
        row = prd[prd.comparison == f"{mid}_minus_M1"].iloc[0]
        for name, got, want in [("delta_c", d, row.delta_c_mean),
                                ("ci_lower", lo, row.delta_c_lower),
                                ("ci_upper", hi, row.delta_c_upper)]:
            checked += 1
            good = close(got, want, 3)
            if not good:
                problems.append(
                    f"{mid} {name}: manuscript {got} vs source {want:.6f}")
            print(f"{mid:14} {name:10} {got:>12.3f} {want:>12.6f}  "
                  f"{'ok' if good else 'MISMATCH'}")

    # ---- key inline claims -------------------------------------------------
    print()
    print("=" * 74)
    print("INLINE CLAIMS  (verified against source, for manual reading)")
    print("=" * 74)
    inline = {
        "primary estimand mean": (-0.0231, prd[prd.comparison == "M5_minus_M1"]
                                  .iloc[0].delta_c_mean, 4),
        "primary estimand lower": (-0.0499, prd[prd.comparison == "M5_minus_M1"]
                                   .iloc[0].delta_c_lower, 4),
        "primary estimand upper": (0.0008, prd[prd.comparison == "M5_minus_M1"]
                                   .iloc[0].delta_c_upper, 4),
    }
    for name, (claimed, source, places) in inline.items():
        checked += 1
        good = close(claimed, source, places)
        if not good:
            problems.append(f"{name}: manuscript {claimed} vs {source:.6f}")
        print(f"{name:26} {claimed:>10} {source:>14.6f}  "
              f"{'ok' if good else 'MISMATCH'}")

    # ---- cohort B/C values quoted in the sensitivity section ---------------
    for cohort, claimed in [("B", (-0.0106, -0.0465, 0.0233)),
                            ("C", (-0.0019, -0.0288, 0.0277))]:
        src = pd.read_csv(TABLES / f"paired_differences_cohort{cohort}.csv")
        row = src[src.comparison == "M5_minus_M1"].iloc[0]
        for name, got, want in [
            (f"cohort {cohort} dC", claimed[0], row.delta_c_mean),
            (f"cohort {cohort} lo", claimed[1], row.delta_c_lower),
            (f"cohort {cohort} hi", claimed[2], row.delta_c_upper),
        ]:
            checked += 1
            good = close(got, want, 4)
            if not good:
                problems.append(f"{name}: manuscript {got} vs {want:.6f}")
            print(f"{name:26} {got:>10} {want:>14.6f}  "
                  f"{'ok' if good else 'MISMATCH'}")

    print()
    print("=" * 74)
    print(f"checked {checked} values")
    if problems:
        print(f"PROBLEMS: {len(problems)}")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("RESULT: every checked value matches its source artifact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
