"""Package the small Phase 3B analysis inputs as ONE Kaggle dataset.

Produces a private Kaggle dataset:

    kawsersikder/dlbcl-phase3b-inputs         (slug: dlbcl-phase3b-inputs)

These are the tables E-008 and E-009 need that are not already on Kaggle. The
clinical tables and released geometry are in `dlbcl-morph-tables`, and the
patches are in `dlbcl-morph-patches`; neither is duplicated here.

The dataset is versioned, because it is built in two passes:

    # before E-008 — patch QC and the frozen feature cache
    python make_and_upload_phase3b_inputs.py --upload

    # after E-008 and Step S2 — adds entropy features and the split manifest
    python make_and_upload_phase3b_inputs.py --upload --version "add E-008 + splits"

Files that do not exist yet are skipped with a note, so the first pass works
before entropy features or splits have been produced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT / "kaggle_upload_staging" / "phase3b_inputs"
META = STAGING / "dataset-metadata.json"
SLUG = "kawsersikder/dlbcl-phase3b-inputs"
TITLE = "dlbcl-phase3b-inputs"

E007 = "kaggle/phase_03_morphology_survival/output_e007_full_extraction"

# (source path relative to repo root, required for the first upload)
SOURCES = [
    ("src/analysis/run_e008_entropy.py", True),
    ("src/analysis/run_e009_ladder.py", False),
    (f"{E007}/patch_qc.csv", True),
    (f"{E007}/patient_features.csv", True),
    ("reports/phase_03b_entropy_features.csv", False),
    ("reports/phase_03b_geometry_features.csv", False),
    ("data/manifests/split_ids.csv", False),
    ("data/manifests/split_ids_summary.json", False),
    # E-009 recomputes the protocol lock hash as a chain-of-custody check, so
    # both protocol files must travel with the data.
    ("reports/phase_03b_statistical_analysis_protocol.md", False),
    ("configs/phase_03b_analysis_protocol.yaml", False),
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
        "--upload", action="store_true", help="run the kaggle CLI after staging"
    )
    parser.add_argument(
        "--version",
        type=str,
        default=None,
        help="version note; uploads a new version instead of creating the dataset",
    )
    args = parser.parse_args()

    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)

    manifest = {}
    for relative, required in SOURCES:
        source = ROOT / relative
        if not source.is_file():
            if required:
                sys.exit(f"ABORT: required input missing: {relative}")
            print(f"  skip (not yet produced): {relative}")
            continue
        shutil.copy2(source, STAGING / source.name)
        manifest[source.name] = {
            "source": relative,
            "bytes": source.stat().st_size,
            "sha256": sha256(source),
        }
        print(f"  staged {source.name}  ({source.stat().st_size:,} bytes)")

    (STAGING / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    META.write_text(
        json.dumps(
            {"title": TITLE, "id": SLUG, "licenses": [{"name": "unknown"}]}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nstaged {len(manifest)} files in {STAGING}")

    if not args.upload:
        print("dry run. re-run with --upload to push to Kaggle.")
        return 0

    if args.version:
        command = [
            sys.executable, "-m", "kaggle", "datasets", "version",
            "-p", str(STAGING), "-m", args.version, "--dir-mode", "zip",
        ]
    else:
        command = [
            sys.executable, "-m", "kaggle", "datasets", "create",
            "-p", str(STAGING), "--dir-mode", "zip",
        ]
    print(f"\n$ {' '.join(command)}")
    return subprocess.run(command).returncode


if __name__ == "__main__":
    raise SystemExit(main())
