"""Audit a downloaded Phase 3A E-007 feature-extraction bundle.

This validator is outcome-blind. It checks artifact integrity, table relations,
the frozen E-007 QC rules, and exact reproducibility for the ten E-006 patients.
It deliberately does not join clinical or survival data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as parquet
import yaml
from PIL import Image


EXPECTED_PATIENTS = 170
EXPECTED_PATCHES = 30_007
EXPECTED_CELLS = 1_959_950
EXPECTED_LOW_TISSUE = 542
EXPECTED_ELIGIBLE_PATCHES = 29_464
EXPECTED_EXCLUSION_ROWS = 543
EXPECTED_OVERLAYS = 170
EXPECTED_CHECKPOINT_MD5 = "dea287c50949db8c6b7f6b7bfad87271"
EXPECTED_PATIENT_SHA256 = (
    "cdb1b0aed4c70325e7202cb7d3ca80a7ef490c3eb19edb6904ba8ea796b5e50c"
)
EXPECTED_PATCH_SHA256 = (
    "10d1e96e4b6789a12745dc274e61d99ee34b6f798097fc1b27e07d1c31548d97"
)
LOW_TISSUE_ACTION = "exclude_from_patch_level_summaries_and_record"
KNOWN_FAILURE = ("17649", "5053")
OVERLAY_PATTERN = re.compile(
    r"^patient_(?P<patient>\d+)_patch_(?P<patch>\d+)_feature_qc\.png$"
)


def compact_list_sha256(values: list[str]) -> str:
    payload = json.dumps(values, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def canonical_order(frame: pd.DataFrame, include_cell: bool = False) -> pd.DataFrame:
    ordered = frame.assign(
        __patient=frame["patient_id"].astype(int),
        __patch=frame["patch_id"].astype(int),
    )
    keys = ["__patient", "__patch"]
    if include_cell:
        keys.append("cell_id")
    return ordered.sort_values(keys).drop(columns=["__patient", "__patch"]).reset_index(
        drop=True
    )


def exact_frame_equal(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    if list(left.columns) != list(right.columns) or left.shape != right.shape:
        return False
    for column in left.columns:
        left_values = left[column].to_numpy()
        right_values = right[column].to_numpy()
        if pd.api.types.is_numeric_dtype(left[column]):
            if not np.array_equal(left_values, right_values, equal_nan=True):
                return False
        elif not np.array_equal(left_values.astype(str), right_values.astype(str)):
            return False
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--e007", type=Path, required=True)
    parser.add_argument("--e006", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--review-csv", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    e007 = args.e007.resolve()
    e006 = args.e006.resolve()
    checks: list[dict[str, object]] = []
    metrics: dict[str, object] = {}

    def check(name: str, passed: bool, detail: object) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    required_core = {
        "cells.parquet",
        "environment.json",
        "exclusion_log.csv",
        "feature_schema.json",
        "patch_qc.csv",
        "patient_features.csv",
        "resolved_config.yaml",
        "run_summary.json",
    }
    observed_core = {path.name for path in e007.iterdir() if path.is_file()}
    check("required_core_files", required_core == observed_core, sorted(observed_core))

    all_files = sorted(path for path in e007.rglob("*") if path.is_file())
    overlays = sorted((e007 / "qc_overlays").glob("*.png"))
    metrics["artifact_file_count"] = len(all_files)
    metrics["artifact_total_bytes"] = sum(path.stat().st_size for path in all_files)
    metrics["overlay_count"] = len(overlays)
    check("artifact_file_count", len(all_files) == 178, len(all_files))
    check("overlay_count", len(overlays) == EXPECTED_OVERLAYS, len(overlays))

    summary = json.loads((e007 / "run_summary.json").read_text(encoding="utf-8"))
    schema = json.loads((e007 / "feature_schema.json").read_text(encoding="utf-8"))
    resolved_config = yaml.safe_load(
        (e007 / "resolved_config.yaml").read_text(encoding="utf-8")
    )
    tracked_config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    check("resolved_config_matches_tracked", resolved_config == tracked_config, True)
    check("summary_gate_pass", summary["promotion_gate"]["pass"] is True, True)
    check("selection_is_outcome_blind", summary["selection_uses_outcomes"] is False, True)
    check("outcome_join_blocked", summary["outcome_join_permitted"] is False, True)
    check(
        "checkpoint_md5",
        summary["checkpoint_md5"] == EXPECTED_CHECKPOINT_MD5,
        summary["checkpoint_md5"],
    )
    check("summary_schema_match", summary["scientific_scope"] == schema, True)

    manifest = pd.read_csv(args.manifest, dtype={"patient_id": str})
    eligible_manifest = manifest.loc[manifest["image_eligible"] == 1].copy()
    expected_patients = sorted(eligible_manifest["patient_id"].tolist(), key=int)
    check("manifest_patient_count", len(expected_patients) == EXPECTED_PATIENTS, len(expected_patients))

    patients = pd.read_csv(e007 / "patient_features.csv", dtype={"patient_id": str})
    patches = pd.read_csv(
        e007 / "patch_qc.csv", dtype={"patient_id": str, "patch_id": str}
    )
    exclusions = pd.read_csv(
        e007 / "exclusion_log.csv", dtype={"patient_id": str, "patch_id": str}
    )
    parquet_file = parquet.ParquetFile(e007 / "cells.parquet")
    parquet_rows = parquet_file.metadata.num_rows
    parquet_columns = parquet_file.schema_arrow.names
    metrics["parquet_rows"] = parquet_rows
    metrics["parquet_columns"] = parquet_columns
    check("parquet_row_count", parquet_rows == EXPECTED_CELLS, parquet_rows)

    cells = parquet_file.read().to_pandas()
    cells["patient_id"] = cells["patient_id"].astype(str)
    cells["patch_id"] = cells["patch_id"].astype(str)
    check("loaded_cell_row_count", len(cells) == EXPECTED_CELLS, len(cells))
    check("patient_feature_rows", len(patients) == EXPECTED_PATIENTS, len(patients))
    check("patch_rows", len(patches) == EXPECTED_PATCHES, len(patches))
    check("exclusion_rows", len(exclusions) == EXPECTED_EXCLUSION_ROWS, len(exclusions))

    observed_patients = sorted(patients["patient_id"].tolist(), key=int)
    check("patient_ids_match_manifest", observed_patients == expected_patients, True)
    check(
        "patient_ids_match_summary",
        observed_patients == sorted(summary["patients"], key=int),
        True,
    )
    check("unique_patient_rows", not patients["patient_id"].duplicated().any(), True)
    check(
        "unique_patch_keys",
        not patches.duplicated(["patient_id", "patch_id"]).any(),
        True,
    )
    check(
        "unique_cell_keys",
        not cells.duplicated(["patient_id", "patch_id", "cell_id"]).any(),
        True,
    )

    patch_inventory = [
        f"{row.patient_id}/{row.patch_id}.png"
        for row in canonical_order(patches).itertuples(index=False)
    ]
    patient_hash = compact_list_sha256(observed_patients)
    patch_hash = compact_list_sha256(patch_inventory)
    check("patient_inventory_hash", patient_hash == EXPECTED_PATIENT_SHA256, patient_hash)
    check("patch_inventory_hash", patch_hash == EXPECTED_PATCH_SHA256, patch_hash)

    manifest_counts = eligible_manifest.set_index("patient_id")["he_patch_count"].astype(int)
    observed_patch_counts = patches.groupby("patient_id").size()
    check(
        "per_patient_patch_counts_match_manifest",
        observed_patch_counts.sort_index().equals(manifest_counts.sort_index()),
        True,
    )

    patient_numeric = patients.select_dtypes(include=[np.number])
    check(
        "patient_features_all_finite",
        bool(np.isfinite(patient_numeric.to_numpy(dtype=float)).all()),
        float(np.isfinite(patient_numeric.to_numpy(dtype=float)).mean()),
    )
    forbidden_tokens = ("survival", "outcome", "death", "event", "overall_survival")
    all_columns = [column.lower() for column in patients.columns]
    outcome_like = [
        column for column in all_columns if any(token in column for token in forbidden_tokens)
    ]
    check("no_outcome_like_patient_columns", not outcome_like, outcome_like)

    patch_keys = pd.MultiIndex.from_frame(patches[["patient_id", "patch_id"]])
    cell_keys = pd.MultiIndex.from_frame(cells[["patient_id", "patch_id"]])
    check("all_cells_reference_known_patch", bool(cell_keys.isin(patch_keys).all()), True)

    predicted = cells.groupby(["patient_id", "patch_id"]).size().reindex(patch_keys, fill_value=0)
    primary_mask = (cells["border_touching"] == 0) & (
        cells["patch_excluded_from_primary"] == 0
    )
    primary = (
        cells.loc[primary_mask]
        .groupby(["patient_id", "patch_id"])
        .size()
        .reindex(patch_keys, fill_value=0)
    )
    border = (
        cells.loc[cells["border_touching"] == 1]
        .groupby(["patient_id", "patch_id"])
        .size()
        .reindex(patch_keys, fill_value=0)
    )
    check(
        "patch_predicted_counts_match_cells",
        np.array_equal(predicted.to_numpy(), patches["predicted_cell_count"].to_numpy()),
        True,
    )
    check(
        "patch_primary_counts_match_cells",
        np.array_equal(primary.to_numpy(), patches["primary_cell_count"].to_numpy()),
        True,
    )
    check(
        "patch_border_counts_match_cells",
        np.array_equal(border.to_numpy(), patches["border_cell_count"].to_numpy()),
        True,
    )

    observed_low = patches["tissue_fraction"] < 0.50
    observed_eligible = (patches["excluded_from_primary"] == 0) & ~observed_low
    check(
        "low_tissue_rule_exact",
        np.array_equal(observed_low.astype(int), patches["low_tissue_for_patch_summaries"]),
        int(observed_low.sum()),
    )
    check(
        "eligibility_rule_exact",
        np.array_equal(
            observed_eligible.astype(int), patches["eligible_for_patch_summaries"]
        ),
        int(observed_eligible.sum()),
    )
    check("low_tissue_count", int(observed_low.sum()) == EXPECTED_LOW_TISSUE, int(observed_low.sum()))
    check(
        "eligible_patch_count",
        int(observed_eligible.sum()) == EXPECTED_ELIGIBLE_PATCHES,
        int(observed_eligible.sum()),
    )

    low_patch_keys = set(
        map(tuple, patches.loc[observed_low, ["patient_id", "patch_id"]].to_numpy())
    )
    low_exclusions = exclusions.loc[exclusions["action"] == LOW_TISSUE_ACTION]
    low_exclusion_keys = set(
        map(tuple, low_exclusions[["patient_id", "patch_id"]].to_numpy())
    )
    check(
        "low_tissue_exclusion_log_exact",
        low_patch_keys == low_exclusion_keys and len(low_exclusions) == EXPECTED_LOW_TISSUE,
        len(low_exclusions),
    )
    check(
        "exclusion_actions_unique_per_patch",
        not exclusions.duplicated(["patient_id", "patch_id", "action"]).any(),
        True,
    )
    known_rows = exclusions.loc[
        (exclusions["patient_id"] == KNOWN_FAILURE[0])
        & (exclusions["patch_id"] == KNOWN_FAILURE[1])
    ]
    check("known_failure_logged_once", len(known_rows) == 1, len(known_rows))
    known_cell_mask = (cells["patient_id"] == KNOWN_FAILURE[0]) & (
        cells["patch_id"] == KNOWN_FAILURE[1]
    )
    check(
        "known_failure_cell_flags",
        bool((cells.loc[known_cell_mask, "patch_excluded_from_primary"] == 1).all())
        and bool((cells.loc[~known_cell_mask, "patch_excluded_from_primary"] == 0).all()),
        int(known_cell_mask.sum()),
    )
    partial_primary = int(
        (
            cell_keys.isin(pd.MultiIndex.from_tuples(sorted(low_patch_keys)))
            & (cells["border_touching"].to_numpy() == 0)
            & (cells["patch_excluded_from_primary"].to_numpy() == 0)
        ).sum()
    )
    check(
        "partial_tissue_primary_cells_retained",
        partial_primary == summary["promotion_gate"]["partial_tissue_primary_cells_retained"],
        partial_primary,
    )

    patch_group = patches.groupby("patient_id")
    cell_group = cells.groupby("patient_id")
    primary_cell_group = cells.loc[primary_mask].groupby("patient_id").size()
    aggregate_expected = pd.DataFrame(
        {
            "patch_count_total": patch_group.size(),
            "patch_count_primary": patch_group["eligible_for_patch_summaries"].sum(),
            "patch_count_low_tissue": patch_group["low_tissue_for_patch_summaries"].sum(),
            "cell_count_total": cell_group.size(),
            "cell_count_primary": primary_cell_group,
        }
    ).reindex(patients["patient_id"])
    aggregate_observed = patients.set_index("patient_id")[aggregate_expected.columns]
    check(
        "patient_count_aggregates_match_source_tables",
        np.array_equal(
            aggregate_expected.to_numpy(dtype=np.int64),
            aggregate_observed.to_numpy(dtype=np.int64),
        ),
        True,
    )

    cell_numeric = cells.select_dtypes(include=[np.number])
    check(
        "cell_numeric_values_finite",
        bool(np.isfinite(cell_numeric.to_numpy(dtype=float)).all()),
        True,
    )
    range_checks = {
        "area_positive": bool((cells["area_px"] > 0).all()),
        "axes_nonnegative": bool(
            ((cells["major_axis_px"] >= 0) & (cells["minor_axis_px"] >= 0)).all()
        ),
        "major_axis_ge_minor": bool(
            (cells["major_axis_px"] + 1e-12 >= cells["minor_axis_px"]).all()
        ),
        "eccentricity_0_1": bool(cells["eccentricity"].between(0, 1).all()),
        "solidity_0_1": bool(cells["solidity"].between(0, 1).all()),
        "rgb_0_255": bool(
            cells[["rgb_mean_r", "rgb_mean_g", "rgb_mean_b"]]
            .ge(0)
            .all()
            .all()
            and cells[["rgb_mean_r", "rgb_mean_g", "rgb_mean_b"]]
            .le(255)
            .all()
            .all()
        ),
        "binary_flags": bool(
            cells["border_touching"].isin([0, 1]).all()
            and cells["patch_excluded_from_primary"].isin([0, 1]).all()
        ),
    }
    check("cell_feature_ranges", all(range_checks.values()), range_checks)

    patch_missing = {
        column: int(patches[column].isna().sum())
        for column in patches.columns
        if patches[column].isna().any()
    }
    metrics["patch_missing_values"] = patch_missing
    check(
        "all_patients_have_eligible_patch",
        bool((patch_group["eligible_for_patch_summaries"].sum() > 0).all()),
        True,
    )

    overlay_records: list[dict[str, object]] = []
    invalid_overlays: list[str] = []
    for overlay in overlays:
        match = OVERLAY_PATTERN.match(overlay.name)
        if match is None:
            invalid_overlays.append(overlay.name)
            continue
        try:
            with Image.open(overlay) as image:
                image.verify()
        except Exception as error:  # pragma: no cover - audit failure path
            invalid_overlays.append(f"{overlay.name}: {error}")
            continue
        overlay_records.append(
            {
                "patient_id": match.group("patient"),
                "patch_id": match.group("patch"),
                "overlay_file": overlay.name,
                "computational_review": "",
                "pathology_review": "",
                "reviewer": "",
                "notes": "",
            }
        )
    overlay_patients = sorted({str(row["patient_id"]) for row in overlay_records}, key=int)
    check("all_overlay_pngs_valid", not invalid_overlays, invalid_overlays)
    check("one_overlay_per_patient", overlay_patients == expected_patients, len(overlay_patients))
    args.review_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(overlay_records).sort_values(
        "patient_id", key=lambda series: series.astype(int)
    ).to_csv(args.review_csv, index=False)

    e006_summary = json.loads((e006 / "run_summary.json").read_text(encoding="utf-8"))
    pilot_patients = [str(value) for value in e006_summary["patients"]]
    e006_cells = parquet.read_table(e006 / "cells.parquet").to_pandas()
    e006_cells[["patient_id", "patch_id"]] = e006_cells[["patient_id", "patch_id"]].astype(str)
    e007_pilot_cells = cells.loc[cells["patient_id"].isin(pilot_patients)].copy()
    check(
        "e006_cell_rows_exact_in_e007",
        exact_frame_equal(
            canonical_order(e006_cells, include_cell=True),
            canonical_order(e007_pilot_cells, include_cell=True),
        ),
        {"e006": len(e006_cells), "e007_subset": len(e007_pilot_cells)},
    )

    e006_patches = pd.read_csv(
        e006 / "patch_qc.csv", dtype={"patient_id": str, "patch_id": str}
    )
    e007_pilot_patches = patches.loc[patches["patient_id"].isin(pilot_patients)].copy()
    check(
        "e006_patch_rows_exact_in_e007",
        exact_frame_equal(
            canonical_order(e006_patches), canonical_order(e007_pilot_patches)
        ),
        {"e006": len(e006_patches), "e007_subset": len(e007_pilot_patches)},
    )

    e006_patients = pd.read_csv(e006 / "patient_features.csv", dtype={"patient_id": str})
    e007_pilot_patients = patients.loc[patients["patient_id"].isin(pilot_patients)].copy()
    check(
        "e006_patient_features_exact_in_e007",
        exact_frame_equal(
            e006_patients.sort_values("patient_id", key=lambda series: series.astype(int)).reset_index(drop=True),
            e007_pilot_patients.sort_values("patient_id", key=lambda series: series.astype(int)).reset_index(drop=True),
        ),
        True,
    )

    e006_overlay_by_patient = {}
    for path in (e006 / "qc_overlays").glob("*.png"):
        match = OVERLAY_PATTERN.match(path.name)
        if match:
            e006_overlay_by_patient[match.group("patient")] = path
    e007_overlay_by_patient = {
        OVERLAY_PATTERN.match(path.name).group("patient"): path
        for path in overlays
        if OVERLAY_PATTERN.match(path.name)
    }
    shared_overlay_hashes = {
        patient_id: sha256(e006_overlay_by_patient[patient_id])
        == sha256(e007_overlay_by_patient[patient_id])
        for patient_id in pilot_patients
    }
    check(
        "e006_overlays_byte_identical_in_e007",
        len(shared_overlay_hashes) == len(pilot_patients)
        and all(shared_overlay_hashes.values()),
        shared_overlay_hashes,
    )

    feature_only = patients.select_dtypes(include=[np.number]).drop(
        columns=[
            "patch_count_total",
            "patch_count_primary",
            "patch_count_low_tissue",
            "cell_count_total",
            "cell_count_primary",
        ],
        errors="ignore",
    )
    correlation = feature_only.corr(method="spearman").abs()
    upper = correlation.where(np.triu(np.ones(correlation.shape), k=1).astype(bool))
    highly_correlated = [
        {"feature_a": row, "feature_b": column, "abs_spearman": float(value)}
        for row, values in upper.iterrows()
        for column, value in values.items()
        if pd.notna(value) and value >= 0.95
    ]
    metrics["feature_column_count_excluding_id"] = int(patient_numeric.shape[1])
    metrics["high_correlation_pair_count_abs_spearman_ge_0_95"] = len(highly_correlated)
    metrics["high_correlation_pairs_abs_spearman_ge_0_95"] = highly_correlated
    metrics["patient_count_ranges"] = {
        column: {
            "min": int(patients[column].min()),
            "median": float(patients[column].median()),
            "max": int(patients[column].max()),
        }
        for column in [
            "patch_count_total",
            "patch_count_primary",
            "patch_count_low_tissue",
            "cell_count_total",
            "cell_count_primary",
        ]
    }

    failed = [item for item in checks if not item["pass"]]
    result = {
        "status": "pass" if not failed else "fail",
        "source": str(e007),
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "checks": checks,
        "metrics": metrics,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ["status", "checks_passed", "checks_total"]}, indent=2))
    if failed:
        for item in failed:
            print(f"FAILED: {item['name']}: {item['detail']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
