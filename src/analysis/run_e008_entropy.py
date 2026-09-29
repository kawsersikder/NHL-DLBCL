"""E-008 — outcome-blind global grayscale entropy comparator.

Implements Phase 3B protocol section 4 verbatim. For every H&E patch in the
frozen E-007 cache this computes Shannon entropy of the whole-patch grayscale
intensity histogram, with no tissue masking, and aggregates it to the patient.
The point is to reproduce the published "global entropy" comparator faithfully
rather than to improve on it, so that M3 is a fair opponent and not a strawman.

This script is outcome-blind. It never opens the clinical table.

Eligibility is taken from the frozen `patch_qc.csv` rather than recomputed, so
that patient patch counts reconcile with E-007 by construction. Entropy is
computed and recorded for all patches, including ineligible ones, so that later
sensitivity work needs no re-run.

Runs unchanged locally and on Kaggle; on Kaggle the inputs are auto-discovered
under /kaggle/input and outputs land in /kaggle/working. No GPU is used, so run
the notebook on a CPU accelerator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image


EXPECTED_PATIENTS = 170
EXPECTED_PATCHES = 30_007
EXPECTED_ELIGIBLE_PATCHES = 29_464
GRAY_LEVELS = 256

ON_KAGGLE = Path("/kaggle/working").exists()
KAGGLE_INPUT = Path("/kaggle/input")

# The five patient-level covariates of M3. `entropy_mean` is the primary
# covariate (it matches the published comparator exactly); the other four are
# the pre-specified secondary elaboration. QC counts are deliberately prefixed
# so they cannot be swept into a model by a careless column glob.
FEATURE_COLUMNS = [
    "entropy_mean",
    "entropy_median",
    "entropy_iqr",
    "entropy_p10",
    "entropy_p90",
]


def breadth_first_directories(root: Path, max_depth: int = 7):
    """Walk Kaggle input mounts breadth-first, preferring the known dataset slugs."""
    current = [root]
    for _ in range(max_depth + 1):
        current.sort(
            key=lambda path: (
                "dlbcl-phase3b-inputs" not in str(path).lower(),
                "dlbcl-morph-patches" not in str(path).lower(),
                str(path),
            )
        )
        yield from current
        next_level: list[Path] = []
        for directory in current:
            try:
                next_level.extend(path for path in directory.iterdir() if path.is_dir())
            except OSError:
                continue
        if not next_level:
            return
        current = next_level


def find_he_directory() -> Path:
    for directory in breadth_first_directories(KAGGLE_INPUT):
        candidate = directory / "HE"
        if not candidate.is_dir():
            continue
        patient = next((path for path in candidate.iterdir() if path.is_dir()), None)
        if patient is not None and next(patient.glob("*.png"), None) is not None:
            return candidate
    raise FileNotFoundError(
        "HE/<patient_id>/<patch_id>.png tree not found; "
        "attach kawsersikder/dlbcl-morph-patches"
    )


def find_patch_qc() -> Path:
    for directory in breadth_first_directories(KAGGLE_INPUT):
        candidate = directory / "patch_qc.csv"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "patch_qc.csv not found; attach kawsersikder/dlbcl-phase3b-inputs"
    )


def sha256(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def patch_entropy(path: Path) -> tuple[float, str]:
    """Shannon entropy in bits of the 256-level grayscale histogram.

    Grayscale conversion is PIL's `convert("L")`, which is ITU-R 601-2 luma
    (L = 299/1000 R + 587/1000 G + 114/1000 B) as the protocol specifies.
    """
    with Image.open(path) as image:
        mode = image.mode
        if mode != "RGB":
            image = image.convert("RGB")
        counts = np.asarray(image.convert("L").histogram(), dtype=np.float64)

    total = counts.sum()
    if total <= 0:
        return float("nan"), mode
    probabilities = counts[counts > 0] / total
    return float(-np.sum(probabilities * np.log2(probabilities))), mode


def aggregate(values: np.ndarray) -> dict[str, float]:
    p10, p25, p75, p90 = np.percentile(values, [10, 25, 75, 90])
    return {
        "entropy_mean": float(values.mean()),
        "entropy_median": float(np.median(values)),
        "entropy_iqr": float(p75 - p25),
        "entropy_p10": float(p10),
        "entropy_p90": float(p90),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--patches-root",
        type=Path,
        default=None,
        help="Directory of per-patient H&E patch folders. Auto-discovered on Kaggle.",
    )
    parser.add_argument(
        "--patch-qc",
        type=Path,
        default=None,
        help="Frozen E-007 patch QC table; the sole eligibility authority.",
    )
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument(
        "--smoke",
        type=int,
        default=0,
        help="Process only the first N patients and skip gates (development only).",
    )
    args = parser.parse_args()

    if ON_KAGGLE:
        args.patches_root = args.patches_root or find_he_directory()
        args.patch_qc = args.patch_qc or find_patch_qc()
        args.out_dir = args.out_dir or Path("/kaggle/working/phase_03b_e008_entropy")
    else:
        args.patches_root = args.patches_root or Path("DLBCLMorph/Patches/HE")
        args.patch_qc = args.patch_qc or Path(
            "kaggle/phase_03_morphology_survival/output_e007_full_extraction/patch_qc.csv"
        )
        args.out_dir = args.out_dir or Path("reports")
    print(f"patches_root: {args.patches_root}")
    print(f"patch_qc:     {args.patch_qc}")
    print(f"out_dir:      {args.out_dir}")

    qc = pd.read_csv(args.patch_qc, dtype={"patient_id": str, "patch_id": str})
    print(f"patch_qc: {len(qc):,} rows, {qc['patient_id'].nunique()} patients")

    if not args.smoke:
        if len(qc) != EXPECTED_PATCHES:
            sys.exit(f"ABORT: patch_qc has {len(qc)} rows, expected {EXPECTED_PATCHES}")
        if qc["patient_id"].nunique() != EXPECTED_PATIENTS:
            sys.exit("ABORT: patch_qc patient count does not match E-007")

    qc = qc.sort_values(
        by=["patient_id", "patch_id"],
        key=lambda column: column.astype(int),
    ).reset_index(drop=True)

    if args.smoke:
        keep = sorted(qc["patient_id"].unique(), key=int)[: args.smoke]
        qc = qc[qc["patient_id"].isin(keep)].reset_index(drop=True)
        print(f"SMOKE MODE: {len(qc):,} patches from {len(keep)} patients")

    # Verify the cache and the disk agree before computing anything.
    on_disk = {
        (directory.name, png.stem)
        for directory in sorted(args.patches_root.iterdir())
        if directory.is_dir()
        for png in directory.glob("*.png")
    }
    expected = set(zip(qc["patient_id"], qc["patch_id"]))
    missing = expected - on_disk
    if missing:
        sys.exit(f"ABORT: {len(missing)} patch_qc rows have no PNG, e.g. {sorted(missing)[:3]}")
    if not args.smoke:
        extra = on_disk - expected
        if extra:
            sys.exit(f"ABORT: {len(extra)} PNGs are absent from patch_qc, e.g. {sorted(extra)[:3]}")

    entropies = np.empty(len(qc), dtype=np.float64)
    modes: Counter[str] = Counter()
    for position, (patient, patch) in enumerate(zip(qc["patient_id"], qc["patch_id"])):
        entropies[position], mode = patch_entropy(
            args.patches_root / patient / f"{patch}.png"
        )
        modes[mode] += 1
        if (position + 1) % 5000 == 0:
            print(f"  {position + 1:,}/{len(qc):,} patches")

    if not np.isfinite(entropies).all():
        sys.exit(f"ABORT: {int((~np.isfinite(entropies)).sum())} patches produced non-finite entropy")

    patch_level = qc[
        ["patient_id", "patch_id", "tissue_fraction", "eligible_for_patch_summaries"]
    ].copy()
    patch_level["patch_entropy_bits"] = entropies

    eligible = patch_level[patch_level["eligible_for_patch_summaries"] == 1]
    print(f"eligible patches: {len(eligible):,} of {len(patch_level):,}")

    rows = []
    for patient, group in eligible.groupby("patient_id", sort=False):
        row = {"patient_id": patient}
        row.update(aggregate(group["patch_entropy_bits"].to_numpy()))
        row["qc_patch_count_eligible"] = int(len(group))
        row["qc_patch_count_total"] = int((patch_level["patient_id"] == patient).sum())
        rows.append(row)
    features = pd.DataFrame(rows).sort_values(
        "patient_id", key=lambda column: column.astype(int)
    ).reset_index(drop=True)

    # Gates (protocol section 4).
    if not args.smoke:
        if len(features) != EXPECTED_PATIENTS:
            sys.exit(f"ABORT: {len(features)} patient rows, expected {EXPECTED_PATIENTS}")
        if len(eligible) != EXPECTED_ELIGIBLE_PATCHES:
            sys.exit(
                f"ABORT: {len(eligible)} eligible patches, expected {EXPECTED_ELIGIBLE_PATCHES}"
            )
        if not np.isfinite(features[FEATURE_COLUMNS].to_numpy()).all():
            sys.exit("ABORT: non-finite value in the patient feature table")
        reconciliation = features.set_index("patient_id")["qc_patch_count_eligible"]
        reference = eligible.groupby("patient_id").size()
        if not reconciliation.equals(reference.reindex(reconciliation.index)):
            sys.exit("ABORT: patient patch counts do not reconcile with patch_qc")
        print("gates: PASS")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    features_path = args.out_dir / "phase_03b_entropy_features.csv"
    patch_path = args.out_dir / "phase_03b_entropy_patch_level.csv"
    features.to_csv(features_path, index=False)
    patch_level.to_csv(patch_path, index=False)

    summary = {
        "experiment": "E-008",
        "protocol_section": "4",
        "outcome_blind": True,
        "grayscale": "PIL convert('L') = ITU-R 601-2 luma",
        "gray_levels": GRAY_LEVELS,
        "tissue_masking": "none (deliberate — reproduces the published comparator)",
        "eligibility_source": str(args.patch_qc),
        "patches_total": int(len(patch_level)),
        "patches_eligible": int(len(eligible)),
        "patients": int(len(features)),
        "image_modes": dict(modes),
        "smoke_mode": bool(args.smoke),
        "on_kaggle": ON_KAGGLE,
        "patches_root": str(args.patches_root),
        "feature_columns": FEATURE_COLUMNS,
        "primary_covariate": "entropy_mean",
        "patch_entropy_bits": {
            "min": float(entropies.min()),
            "max": float(entropies.max()),
            "mean": float(entropies.mean()),
        },
        "sha256": {
            features_path.name: sha256(features_path),
            patch_path.name: sha256(patch_path),
        },
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "pillow": Image.__version__,
        },
    }
    summary_path = args.out_dir / "phase_03b_entropy_run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"\nwrote {features_path}")
    print(f"wrote {patch_path}")
    print(f"wrote {summary_path}")
    print(f"  sha256(features) = {summary['sha256'][features_path.name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
