"""Phase 1b: reproduce the DLBCL-Morph paper's Cox baseline (target C-index 0.635).

Faithful reimplementation of Stanford's notebooks/survival_regression.ipynb
(master branch, downloaded 2026-08-23). Deliberately replicates the original's
legacy methodology — in-sample fitting, dataset-wide QuantileTransformer,
bootstrap optimism correction — because this is a reproduction, not our model.
Our own models (Phase 3+) use fold-safe preprocessing instead.

Original targets (GEOMETRIC): optimism 0.152, corrected C-index 0.635,
adjusted 95% CI (0.574, 0.691). CLINICAL: 0.674 (0.602, 0.737).
ALL: 0.700 (0.651, 0.744). Small deviations (~±0.01) are expected from
library-version differences.

Kaggle usage:
    python reproduce_baseline.py \
        --data-dir /kaggle/input/dlbcl-morph-tables \
        --output-dir /kaggle/working/phase_01b_reproduction
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter

GEOMETRIC_TARGETS = {"optimism": 0.152, "corrected_c_index": 0.635, "ci": (0.574, 0.691)}

NEW_CLINICAL_COLS = [
    "MYC IHC", "BCL2 IHC", "BCL6 IHC", "CD10 IHC", "MUM1 IHC",
    "HANS", "BCL6 FISH", "MYC FISH", "BCL2 FISH", "Age", "ECOG PS", "LDH",
    "EN", "Stage", "IPI Score", "IPI Risk Group (4 Class)", "RIPI Risk Group",
]

GEO_COLS = [
    "rotate_angle_mean", "rotate_angle_std", "shortAxis_mean",
    "shortAxis_std", "longAxis_mean", "longAxis_std", "ellip_perimt_mean",
    "ellip_perimt_std", "ellip_area_mean", "ellip_area_std",
    "hull_area_mean", "hull_area_std", "minDiameter_mean",
    "minDiameter_std", "maxDiameter_mean", "maxDiameter_std",
    "minAngle_mean", "minAngle_std", "maxAngle_mean", "maxAngle_std",
    "esf_mean", "esf_std", "csf_mean", "csf_std", "sf1_mean", "sf1_std",
    "sf2_mean", "sf2_std", "elogation_mean", "elogation_std",
    "convexity_mean", "convexity_std", "rectCenter_x_mean",
    "rectCenter_x_std", "rectCenter_y_mean", "rectCenter_y_std",
    "rect_width_mean", "rect_width_std", "rect_height_mean",
    "rect_height_std", "ellip_centroid_x_mean", "ellip_centroid_x_std",
    "ellip_centroid_y_mean", "ellip_centroid_y_std", "OS", "FUS",
]

PENALIZERS = {"GEOMETRIC": 0.0, "CLINICAL": 0.0, "ALL": 0.00005}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True,
                        help="Directory containing cell_shapes.csv and clinical_data_cleaned.csv")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--features", default="ALL_MODES",
                        help="GEOMETRIC | CLINICAL | ALL | ALL_MODES (run all three)")
    parser.add_argument("--num-bootstraps", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42,
                        help="The original notebook hardcodes 42; change only to probe stability")
    return parser.parse_args()


def load_and_aggregate(data_dir: Path) -> pd.DataFrame:
    """Original cells 6-9: load, mean-impute, merge, per-patient mean/std."""
    df_outcome = pd.read_csv(data_dir / "clinical_data_cleaned.csv")

    # Original uses df.fillna(df.mean()); numeric_only keeps pandas >=2 behaviour identical.
    df_outcome = df_outcome.fillna(df_outcome.mean(numeric_only=True))

    df_cells = pd.read_csv(data_dir / "cell_shapes.csv")
    print(f"patients before join: {df_cells['patient_id'].nunique()} "
          f"(cells rows: {len(df_cells):,})")

    df = df_cells.merge(
        df_outcome[["patient_id", "OS", "Follow-up Status"] + NEW_CLINICAL_COLS],
        left_on="patient_id", right_on="patient_id", how="inner", validate="m:1",
    )
    print(f"patients after join: {df['patient_id'].nunique()}")

    df = df.drop(["patch_id", "cell_number"], axis=1).astype(float)

    # String aggregators keep pandas >=2 behaviour identical to the original's np.mean/np.std.
    df_agg = df.groupby("patient_id").agg(["mean", "std"])
    df_agg.columns = df_agg.columns.map("_".join)
    drop = ["OS_std", "Follow-up Status_std"] + [c + "_std" for c in NEW_CLINICAL_COLS]
    df_agg = df_agg.drop(drop, axis=1)
    return df_agg.rename(columns={"OS_mean": "OS", "Follow-up Status_mean": "FUS"})


def select_frame(df_agg: pd.DataFrame, features: str) -> tuple[pd.DataFrame, float]:
    """Original cells 12-13: feature-set selection and penalizer choice."""
    if features == "ALL":
        return df_agg, PENALIZERS["ALL"]
    if features == "GEOMETRIC":
        return df_agg[GEO_COLS], PENALIZERS["GEOMETRIC"]
    if features == "CLINICAL":
        return df_agg.drop(set(GEO_COLS) - {"OS", "FUS"}, axis=1), PENALIZERS["CLINICAL"]
    raise ValueError(f"unknown feature set: {features}")


def quantile_transform(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Original cells 14-15. NOTE: fitted on the full dataset including OS/FUS —
    legacy leakage replicated intentionally for reproduction fidelity."""
    from sklearn.preprocessing import QuantileTransformer

    qt = QuantileTransformer(n_quantiles=10, random_state=seed)
    qt.fit(df)
    return pd.DataFrame.from_records(qt.transform(df), columns=df.columns)


def run_mode(df_agg: pd.DataFrame, features: str, args: argparse.Namespace) -> dict:
    print("=" * 70)
    print(f"MODE: {features}")
    print("=" * 70)

    df, penalizer = select_frame(df_agg, features)
    df = quantile_transform(df, args.seed)

    events = int(df["FUS"].sum())
    print(f"patients={len(df)}  events={events}  features={len(df.columns) - 2}  penalizer={penalizer}")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # convergence warnings on p>>n are expected
        # Original cell 18: uncorrected in-sample C-index
        cph = CoxPHFitter(penalizer=penalizer)
        cph.fit(df, duration_col="OS", event_col="FUS")
        c_main = cph.score(df, scoring_method="concordance_index")
        print(f"uncorrected (in-sample) C-index: {c_main:.4f}")

        # Original cells 20-21: bootstrap optimism
        np.random.seed(args.seed)
        c_boot, c_orig = [], []
        for _ in range(args.num_bootstraps):
            idx = np.random.choice(np.arange(len(df)), size=len(df), replace=True)
            sample = df.iloc[idx]
            boot_cph = CoxPHFitter(penalizer=penalizer)
            boot_cph.fit(sample, duration_col="OS", event_col="FUS")
            c_boot.append(boot_cph.score(sample, scoring_method="concordance_index"))
            c_orig.append(boot_cph.score(df, scoring_method="concordance_index"))
        optimism = float(np.mean(np.array(c_boot) - np.array(c_orig)))
        c_corrected = c_main - optimism
        print(f"optimism: {optimism:.4f}   corrected C-index: {c_corrected:.4f}")

        # Original cells 24-25: percentile CI from scoring the fixed model
        np.random.seed(args.seed)
        cph_full = CoxPHFitter(penalizer=penalizer)
        cph_full.fit(df, duration_col="OS", event_col="FUS")
        c_indices = []
        for _ in range(args.num_bootstraps):
            idx = np.random.choice(np.arange(len(df)), size=len(df), replace=True)
            c_indices.append(cph_full.score(df.iloc[idx], scoring_method="concordance_index"))
        c_indices.sort()
        # Original hardcodes indices 24/974 for 1000 bootstraps (=2.5th/97.5th pct);
        # derive them from n so smaller --num-bootstraps smoke tests don't crash.
        lo_i = max(0, round(0.025 * args.num_bootstraps) - 1)
        hi_i = min(args.num_bootstraps - 1, round(0.975 * args.num_bootstraps) - 1)
        lo, hi = c_indices[lo_i], c_indices[hi_i]
        print(f"CI: ({lo:.3f}, {hi:.3f})   adjusted CI: ({lo - optimism:.3f}, {hi - optimism:.3f})")

    result = {
        "mode": features,
        "uncorrected_c_index": round(float(c_main), 4),
        "optimism": round(float(optimism), 4),
        "corrected_c_index": round(float(c_corrected), 4),
        "ci95": [round(float(lo), 4), round(float(hi), 4)],
        "adjusted_ci95": [round(float(lo - optimism), 4), round(float(hi - optimism), 4)],
        "patients": len(df),
        "events": events,
    }
    if features == "GEOMETRIC":
        delta = abs(result["corrected_c_index"] - GEOMETRIC_TARGETS["corrected_c_index"])
        result["paper_target"] = {
            "corrected_c_index": GEOMETRIC_TARGETS["corrected_c_index"],
            "ci": list(GEOMETRIC_TARGETS["ci"]),
            "abs_deviation": round(delta, 4),
            "within_tolerance_0.01": bool(delta <= 0.01),
        }
        print(f"deviation from published 0.635: {delta:.4f}")
    return result


def main() -> None:
    args = parse_args()
    modes = ["GEOMETRIC", "CLINICAL", "ALL"] if args.features == "ALL_MODES" else [args.features]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "run_config.json").write_text(json.dumps({
        "arguments": {k: str(v) for k, v in vars(args).items()},
        "modes": modes,
        "python_version": sys.version.split()[0],
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "machine": platform.machine(),
        "source_notebook": "stanfordmlgroup/DLBCL-Morph@master notebooks/survival_regression.ipynb",
        "note": ("Reproduction of legacy in-sample + optimism-correction methodology; "
                 "dataset-wide QuantileTransformer replicated intentionally. "
                 "Not the evaluation protocol for project models."),
    }, indent=2), encoding="utf-8")

    df_agg = load_and_aggregate(args.data_dir)

    results = []
    for mode in modes:
        try:
            results.append(run_mode(df_agg, mode, args))
        except Exception as exc:  # keep partial results crash-safe
            print(f"MODE {mode} FAILED: {exc}")
            results.append({"mode": mode, "status": "failed", "error": repr(exc)})
        (args.output_dir / "run_summary.json").write_text(json.dumps({
            "status": "training_in_progress" if any("error" not in r and i < len(modes) - 1
                                                    for i, r in enumerate(results)) else "complete",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "results": results,
        }, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print("SUMMARY (paper: GEOMETRIC 0.635 (0.574, 0.691) | CLINICAL 0.674 | ALL 0.700)")
    for r in results:
        if "error" in r:
            print(f"  {r['mode']:10s} FAILED: {r['error'][:80]}")
        else:
            print(f"  {r['mode']:10s} corrected C-index {r['corrected_c_index']:.3f} "
                  f"adj CI ({r['adjusted_ci95'][0]:.3f}, {r['adjusted_ci95'][1]:.3f})")


if __name__ == "__main__":
    main()
