"""Determine the encoding of the HANS column in the DLBCL-Morph clinical table.

The released data dictionary states that ``HANS`` is the "cell of origin
prediction based on the Hans algorithm" but does NOT say whether 1 means GCB or
non-GCB. Getting this backwards would invert every conclusion of a
cell-of-origin study, so it is established empirically here.

Method: the Hans algorithm is a deterministic decision tree over CD10, BCL6, and
MUM1 immunohistochemistry (Hans et al., Blood 2004):

    CD10+                      -> GCB
    CD10-, BCL6-               -> non-GCB
    CD10-, BCL6+, MUM1-        -> GCB
    CD10-, BCL6+, MUM1+        -> non-GCB

The released table contains the three component stains, so the label can be
reconstructed and cross-tabulated against the HANS column. Whichever mapping
reproduces the column is the encoding.

The script first characterises each stain column, because the columns are not
all on the same scale, and the positivity rule depends on that.

Usage:
    python src/analysis/verify_hans_encoding.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CLINICAL = ROOT / "data/raw/dlbcl_morph/clinical_data_cleaned.csv"

STAINS = ["CD10 IHC", "BCL6 IHC", "MUM1 IHC"]
HANS_THRESHOLD_PCT = 30.0  # Hans et al. 2004 cut-off for percent-positive scoring


def characterise(df: pd.DataFrame) -> dict[str, str]:
    """Report each stain column's scale and infer whether it is binary or percent."""
    scales: dict[str, str] = {}
    print("=" * 72)
    print("STEP 1 — what scale is each stain column on?")
    print("=" * 72)
    for col in STAINS:
        s = df[col].dropna()
        uniq = np.sort(s.unique())
        is_binary = set(uniq).issubset({0.0, 1.0})
        scale = "binary" if is_binary else "percent"
        scales[col] = scale
        print(f"\n{col}")
        print(f"  n = {len(s)}, missing = {df[col].isna().sum()}")
        print(f"  min = {s.min():.4g}, max = {s.max():.4g}, "
              f"n_unique = {len(uniq)}")
        print(f"  inferred scale: {scale.upper()}")
        if len(uniq) <= 12:
            print(f"  values: {list(uniq)}")
        else:
            print(f"  first 8 values: {list(uniq[:8])}")
            frac_le_1 = float((s <= 1.0).mean())
            print(f"  fraction of values <= 1.0: {frac_le_1:.3f}")
    return scales


def positive(series: pd.Series, scale: str) -> pd.Series:
    """Positivity call for a stain, given its scale."""
    if scale == "binary":
        return series > 0
    return series >= HANS_THRESHOLD_PCT


def derive_hans(df: pd.DataFrame, scales: dict[str, str]) -> pd.Series:
    """Reconstruct the Hans call. True = GCB, False = non-GCB."""
    cd10 = positive(df["CD10 IHC"], scales["CD10 IHC"])
    bcl6 = positive(df["BCL6 IHC"], scales["BCL6 IHC"])
    mum1 = positive(df["MUM1 IHC"], scales["MUM1 IHC"])

    gcb = pd.Series(False, index=df.index)
    gcb[cd10] = True                                  # CD10+ -> GCB
    gcb[~cd10 & bcl6 & ~mum1] = True                  # CD10-, BCL6+, MUM1- -> GCB
    # all remaining branches are non-GCB
    return gcb


def evaluate(df: pd.DataFrame, scales: dict[str, str], label: str) -> dict:
    """Cross-tabulate the reconstruction against the released HANS column."""
    complete = df[STAINS + ["HANS"]].notna().all(axis=1)
    sub = df[complete].copy()
    sub["derived_gcb"] = derive_hans(sub, scales)

    print(f"\n{'=' * 72}")
    print(f"STEP 2 — cross-tabulation ({label})")
    print("=" * 72)
    print(f"patients with all three stains and a HANS value: {len(sub)}\n")

    ct = pd.crosstab(sub["derived_gcb"], sub["HANS"],
                     rownames=["derived GCB"], colnames=["HANS column"])
    print(ct.to_string())

    n = len(sub)
    agree_1_gcb = int(((sub.derived_gcb) & (sub.HANS == 1)).sum()
                      + ((~sub.derived_gcb) & (sub.HANS == 0)).sum())
    agree_0_gcb = int(((sub.derived_gcb) & (sub.HANS == 0)).sum()
                      + ((~sub.derived_gcb) & (sub.HANS == 1)).sum())

    print(f"\nHypothesis A — HANS 1 = GCB : {agree_1_gcb}/{n} "
          f"({100 * agree_1_gcb / n:.1f}%)")
    print(f"Hypothesis B — HANS 0 = GCB : {agree_0_gcb}/{n} "
          f"({100 * agree_0_gcb / n:.1f}%)")

    return {"n": n, "sub": sub, "A": agree_1_gcb, "B": agree_0_gcb,
            "scales": dict(scales), "label": label}


def sweep_bcl6_threshold(df: pd.DataFrame, scales: dict[str, str],
                         winner: str) -> None:
    """Find the BCL6 positivity cut-off that best reproduces the HANS column.

    BCL6 is the only percent-scaled component, so it is the only place where an
    operational threshold choice can differ from the canonical 30%. Recovering
    the exact cut-off the original scorers used turns a near-perfect
    reconstruction into an exact one.
    """
    print(f"\n{'=' * 72}")
    print("STEP 3 — which BCL6 cut-off reproduces the released label?")
    print("=" * 72)

    complete = df[STAINS + ["HANS"]].notna().all(axis=1)
    sub = df[complete].copy()
    cd10 = positive(sub["CD10 IHC"], scales["CD10 IHC"])
    mum1 = positive(sub["MUM1 IHC"], scales["MUM1 IHC"])
    n = len(sub)

    print(f"\n{'BCL6 positive if >=':>22}  {'concordance':>12}  {'':>8}")
    best_thr, best_agree = None, -1
    for thr in [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        bcl6 = sub["BCL6 IHC"] >= thr
        gcb = pd.Series(False, index=sub.index)
        gcb[cd10] = True
        gcb[~cd10 & bcl6 & ~mum1] = True
        hans_gcb = (sub.HANS == 1) if winner == "A" else (sub.HANS == 0)
        agree = int((gcb == hans_gcb).sum())
        flag = "  <-- exact" if agree == n else ""
        print(f"{thr:>19}%  {agree:>7}/{n} {100 * agree / n:>6.1f}%{flag}")
        if agree > best_agree:
            best_thr, best_agree = thr, agree

    print(f"\nbest cut-off: BCL6 >= {best_thr}%  "
          f"({best_agree}/{n}, {100 * best_agree / n:.1f}%)")
    if best_agree == n:
        print("The released HANS column is reproduced EXACTLY. The label is a\n"
              "deterministic function of the three stain columns, so it can be\n"
              "recomputed for any patient whose components are present.")
    else:
        print("No cut-off reproduces the column exactly; residual discordance\n"
              "must be treated as label noise and reported.")


def main() -> int:
    df = pd.read_csv(CLINICAL, dtype={"patient_id": str})
    scales = characterise(df)

    results = [evaluate(df, scales, "inferred scales")]

    # If any column was inferred percent, also test the all-percent and
    # all-binary readings, so the conclusion does not rest on one inference.
    for forced in ("percent", "binary"):
        alt = {c: forced for c in STAINS}
        if alt != scales:
            results.append(evaluate(df, alt, f"all columns forced {forced}"))

    best = max(results, key=lambda r: max(r["A"], r["B"]))
    n, a, b = best["n"], best["A"], best["B"]
    winner = "A" if a >= b else "B"
    agree = max(a, b)
    meaning = "GCB" if winner == "A" else "non-GCB"

    print(f"\n{'=' * 72}")
    print("VERDICT")
    print("=" * 72)
    print(f"best reading      : {best['label']}")
    print(f"scales used       : {best['scales']}")
    print(f"concordance       : {agree}/{n} ({100 * agree / n:.1f}%)")
    print(f"\n  >>> HANS = 1 means {meaning}")
    print(f"  >>> HANS = 0 means {'non-GCB' if winner == 'A' else 'GCB'}")

    sub = best["sub"]
    if winner == "A":
        disc = sub[((sub.derived_gcb) & (sub.HANS == 0))
                   | ((~sub.derived_gcb) & (sub.HANS == 1))]
    else:
        disc = sub[((sub.derived_gcb) & (sub.HANS == 1))
                   | ((~sub.derived_gcb) & (sub.HANS == 0))]

    print(f"\ndiscordant cases  : {len(disc)}")
    if len(disc):
        print("\nThese need manual inspection before the label is trusted:")
        cols = ["patient_id"] + STAINS + ["HANS", "derived_gcb"]
        print(disc[cols].head(25).to_string(index=False))

    sweep_bcl6_threshold(df, best["scales"], winner)

    if agree / n < 0.95:
        print("\n*** WARNING: concordance below 95%. Do NOT proceed until the "
              "scale/threshold assumptions above are resolved. ***")
        return 1

    print("\nConcordance is high enough to treat the encoding as established.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
