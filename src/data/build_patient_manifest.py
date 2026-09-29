"""Build the outcome-blind DLBCL-Morph patient/image inventory.

The manifest contains availability and count fields only.  It deliberately
does not copy survival outcomes or clinical predictors, so image eligibility
can be frozen without looking at the endpoint.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def read_patient_ids(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    patient_ids = [row["patient_id"].strip() for row in rows]
    if len(patient_ids) != len(set(patient_ids)):
        raise RuntimeError(f"Duplicate clinical patient IDs in {path}")
    return patient_ids


def count_pngs_by_patient(he_root: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for patient_directory in sorted(path for path in he_root.iterdir() if path.is_dir()):
        counts[patient_directory.name] = sum(
            1
            for path in patient_directory.iterdir()
            if path.is_file() and path.suffix.lower() == ".png"
        )
    return counts


def count_rows(path: Path, patient_field: str, predicate=None) -> Counter[str]:
    counts: Counter[str] = Counter()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if predicate is None or predicate(row):
                counts[row[patient_field].strip()] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinical", type=Path, required=True)
    parser.add_argument("--he-root", type=Path, required=True)
    parser.add_argument("--cell-shapes", type=Path, required=True)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    patient_ids = read_patient_ids(args.clinical)
    clinical_set = set(patient_ids)
    he_counts = count_pngs_by_patient(args.he_root)
    released_cell_counts = count_rows(args.cell_shapes, "patient_id")
    core_counts = count_rows(args.core, "patient_id")
    he_annotation_counts = count_rows(
        args.annotations,
        "patient_id",
        predicate=lambda row: row.get("stain", "").upper() == "HE",
    )

    fields = [
        "patient_id",
        "he_patch_count",
        "has_he_patches",
        "released_cell_count",
        "has_released_cells",
        "core_count",
        "he_annotation_count",
        "image_eligible",
        "eligibility_note",
    ]
    rows: list[dict[str, str | int]] = []
    for patient_id in sorted(patient_ids, key=int):
        he_patch_count = he_counts[patient_id]
        released_cell_count = released_cell_counts[patient_id]
        image_eligible = int(he_patch_count > 0)
        rows.append(
            {
                "patient_id": patient_id,
                "he_patch_count": he_patch_count,
                "has_he_patches": int(he_patch_count > 0),
                "released_cell_count": released_cell_count,
                "has_released_cells": int(released_cell_count > 0),
                "core_count": core_counts[patient_id],
                "he_annotation_count": he_annotation_counts[patient_id],
                "image_eligible": image_eligible,
                "eligibility_note": "HE patches available" if image_eligible else "No HE patches released",
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "clinical_patient_count": len(patient_ids),
        "image_eligible_patient_count": sum(int(row["image_eligible"]) for row in rows),
        "clinical_patients_without_he_patches": sum(
            int(not row["image_eligible"]) for row in rows
        ),
        "he_patch_count": sum(he_counts.values()),
        "he_patient_directories": len(he_counts),
        "released_cell_count": sum(released_cell_counts.values()),
        "released_cell_patients": len(released_cell_counts),
        "he_patients_not_in_clinical_table": sorted(set(he_counts) - clinical_set),
        "released_cell_patients_not_in_clinical_table": sorted(
            set(released_cell_counts) - clinical_set
        ),
        "manifest_contains_outcomes": False,
        "eligibility_rule": "patient has at least one released H&E patch",
    }
    args.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
