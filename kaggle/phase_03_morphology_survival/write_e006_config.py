"""Paste this whole file into the Kaggle cell immediately before E-006."""

import hashlib
from pathlib import Path


CONFIG_TEXT = """experiment_id: E-006
name: phase_03a_outcome_blind_tissue_qc_validation
seed: 20260828

scope:
  mode: qc_validation
  patient_count: 10
  expected_patch_count: 1894
  patient_ids:
    - "13964"
    - "13965"
    - "17648"
    - "17649"
    - "18835"
    - "19681"
    - "26793"
    - "26806"
    - "26817"
    - "26838"
  selection_uses_outcomes: false

checkpoint:
  name: e001_small_unet
  md5: dea287c50949db8c6b7f6b7bfad87271

postprocessing:
  probability_threshold: 0.50
  minimum_nucleus_area_px: 20
  watershed_min_distance_px: 5
  change_without_new_experiment: false

object_qc:
  border_touching: flag_and_exclude_from_primary_shape_summaries
  primary_branch: no_additional_shape_filter
  known_visual_failures:
    - patient_id: "17649"
      patch_id: "5053"
      action: exclude_from_primary_and_record
      reason: linear_non_nuclear_structure_fragmented_into_multiple_instances
  sensitivity_branch:
    enabled: true
    bounds_source: lynsec_validation_object_distributions_only
    purpose: test_effect_of_extreme_area_and_elongation_artifacts

patch_qc:
  tissue_pixel_definition: mean_rgb_below_threshold
  tissue_pixel_mean_rgb_max: 235.0
  minimum_tissue_fraction_for_patch_summaries: 0.50
  partial_tissue_cells_in_per_cell_morphology: true
  low_tissue_action: exclude_from_patch_level_summaries_and_record
  rule_source: outcome_blind_e005_pilot_visual_qc
  change_without_new_experiment: false

features:
  per_cell:
    - area_px
    - perimeter_px
    - eccentricity
    - solidity
    - circularity
    - major_axis_px
    - minor_axis_px
    - rgb_mean
  within_patch_spatial:
    - nucleus_count
    - foreground_fraction
    - nearest_neighbour_px
    - delaunay_edge_px
  patient_aggregation:
    - median
    - interquartile_range
    - p10
    - p90
    - patch_level_median
    - patch_level_interquartile_range
  tumour_non_tumour_features: false
  physical_unit_features: deferred_until_pixel_spacing_verified
  cross_patch_spatial_graphs: false

required_outputs:
  - run_summary.json
  - resolved_config.yaml
  - environment.json
  - patch_qc.csv
  - exclusion_log.csv
  - cells.parquet
  - patient_features.csv
  - feature_schema.json
  - qc_overlays/

promotion_gate:
  all_10_patients_complete: true
  expected_processed_patches: 1894
  no_outcome_columns_loaded: true
  patient_feature_rows: 10
  finite_feature_fraction_min: 0.99
  expected_low_tissue_patches: 54
  low_tissue_patches_recorded: true
  partial_tissue_cell_morphology_retained: true
  known_failure_patient_17649_flagged: true
  runtime_and_storage_projection_recorded: true
"""

EXPECTED_SHA256 = "1a66ed47d786bbe8ea3e3ec75cac2a212984fdd2cba14ef61ddf7f2bcfe2a5f6"
observed_sha256 = hashlib.sha256(CONFIG_TEXT.encode("utf-8")).hexdigest()
if observed_sha256 != EXPECTED_SHA256:
    raise RuntimeError(
        f"Embedded E-006 config hash mismatch: {observed_sha256} != {EXPECTED_SHA256}"
    )

config_path = Path("/kaggle/working/phase_03_feature_extraction_e006.yaml")
config_path.write_text(CONFIG_TEXT, encoding="utf-8")
print(f"E-006 config ready: {config_path}")
print(f"SHA256: {observed_sha256}")
print(f"Bytes: {config_path.stat().st_size:,}")
