"""Aggregate the released DLBCL-Morph cell geometry to patient level for M2.

M2 reproduces the published Stanford geometric baseline. The released
`cell_shapes.csv` holds one row per segmented cell (1.9M rows, ~357 MB); the
published model uses the patient-level mean and standard deviation of 22
descriptors, giving 44 columns.

This is pure geometry — no outcome column is read. The 22 descriptors and their
order are taken verbatim from `survival_regression_original.ipynb` so that M2 is
a faithful reproduction rather than our own reinterpretation.

Four of the descriptors are *positional* (`rectCenter_x`, `rectCenter_y`,
`ellip_centroid_x`, `ellip_centroid_y`). They encode where a cell sat in its
patch, not its shape. They are retained here for fidelity to the published
baseline; protocol §9.5 (sensitivity S5) refits M2 without them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd


EXPECTED_PATIENTS = 170

# Verbatim from the published notebook, in its original order.
GEOMETRY_DESCRIPTORS = [
    "rotate_angle", "shortAxis", "longAxis", "ellip_perimt", "ellip_area",
    "hull_area", "minDiameter", "maxDiameter", "minAngle", "maxAngle",
    "esf", "csf", "sf1", "sf2", "elogation", "convexity",
    "rectCenter_x", "rectCenter_y", "rect_width", "rect_height",
    "ellip_centroid_x", "ellip_centroid_y",
]

# Location in the patch, not shape. Ablated by sensitivity S5.
POSITIONAL_DESCRIPTORS = [
    "rectCenter_x", "rectCenter_y", "ellip_centroid_x", "ellip_centroid_y",
]


def sha256(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cell-shapes", type=Path, default=Path("data/raw/dlbcl_morph/cell_shapes.csv")
    )
    parser.add_argument(
        "--cohort",
        type=Path,
        default=Path(
            "kaggle/phase_03_morphology_survival/output_e007_full_extraction/patient_features.csv"
        ),
        help="Cohort A membership; only patient_id is read.",
    )
    parser.add_argument(
        "--out", type=Path, default=Path("reports/phase_03b_geometry_features.csv")
    )
    args = parser.parse_args()

    cohort = pd.read_csv(args.cohort, usecols=["patient_id"], dtype=str)
    patients = sorted(cohort["patient_id"].unique(), key=int)
    print(f"cohort A: {len(patients)} patients")

    print(f"reading {args.cell_shapes} ...")
    cells = pd.read_csv(
        args.cell_shapes,
        usecols=["patient_id", *GEOMETRY_DESCRIPTORS],
        dtype={"patient_id": str},
    )
    print(f"  {len(cells):,} cell rows, {cells['patient_id'].nunique()} patients")

    cells = cells[cells["patient_id"].isin(patients)]
    grouped = cells.groupby("patient_id")[GEOMETRY_DESCRIPTORS]

    # Interleave mean/std per descriptor to match the published column order.
    means = grouped.mean()
    stds = grouped.std()
    features = pd.DataFrame(index=means.index)
    for descriptor in GEOMETRY_DESCRIPTORS:
        features[f"{descriptor}_mean"] = means[descriptor]
        features[f"{descriptor}_std"] = stds[descriptor]

    features = features.reindex(patients).reset_index().rename(
        columns={"index": "patient_id"}
    )

    if len(features) != EXPECTED_PATIENTS:
        sys.exit(f"ABORT: {len(features)} rows, expected {EXPECTED_PATIENTS}")
    if features.isna().any().any():
        missing = features.columns[features.isna().any()].tolist()
        sys.exit(f"ABORT: missing values in {missing}")
    expected_columns = 1 + 2 * len(GEOMETRY_DESCRIPTORS)
    if features.shape[1] != expected_columns:
        sys.exit(f"ABORT: {features.shape[1]} columns, expected {expected_columns}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(args.out, index=False)

    summary = {
        "purpose": "M2 released-geometry baseline (protocol §3, model M2)",
        "source": str(args.cell_shapes),
        "source_sha256": sha256(args.cell_shapes),
        "cell_rows_in_cohort": int(len(cells)),
        "patients": int(len(features)),
        "descriptors": len(GEOMETRY_DESCRIPTORS),
        "feature_columns": features.shape[1] - 1,
        "positional_descriptors": POSITIONAL_DESCRIPTORS,
        "positional_columns_ablated_by_S5": [
            f"{d}_{stat}" for d in POSITIONAL_DESCRIPTORS for stat in ("mean", "std")
        ],
        "column_order_source": "survival_regression_original.ipynb geo_cols",
        "output_sha256": sha256(args.out),
    }
    summary_path = args.out.with_name(args.out.stem + "_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"\nwrote {args.out}  ({features.shape[1] - 1} feature columns)")
    print(f"wrote {summary_path}")
    print(f"  sha256 = {summary['output_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
