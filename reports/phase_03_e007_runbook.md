# Phase 3A E-007 Full-Extraction Runbook

## Purpose

Create a provisional, outcome-blind morphology feature cache for all 170
DLBCL-Morph patients with H&E patches. E-007 freezes the checkpoint,
postprocessing, object-QC, and tissue-QC decisions validated in E-006. It does
not read clinical variables or outcomes and is not authorization to begin
survival modelling.

## Kaggle setup

Attach:

1. `kawsersikder/dlbcl-morph-patches`;
2. `kawsersikder/dlbcl-e001-unet`.

Use a GPU notebook. Disable or remove the old E-005/E-006 execution cells so
Save & Run All cannot rerun them.

Run these tracked files as consecutive notebook cells:

1. `kaggle/phase_03_morphology_survival/write_e007_config.py`;
2. `kaggle/phase_03_morphology_survival/phase_03a_e007_full_extraction.py`.

Keep `SMOKE_TEST = False`. The first cell must report E-007 config SHA-256
`3fec807b1fd57f74d811b793cc62b47435c21ba6b55ccac022d8dce9d5db0cd6`.
The second must report `mode: FULL_EXTRACTION` and then verify 170 patients and
30,007 patches before processing.

## Frozen input and model gates

- Patient-list SHA-256:
  `cdb1b0aed4c70325e7202cb7d3ca80a7ef490c3eb19edb6904ba8ea796b5e50c`
- Sorted `patient/patch.png` inventory SHA-256:
  `10d1e96e4b6789a12745dc274e61d99ee34b6f798097fc1b27e07d1c31548d97`
- E-001 checkpoint MD5: `dea287c50949db8c6b7f6b7bfad87271`
- Probability threshold: 0.50
- Minimum nucleus area: 20 pixels
- Watershed minimum distance: 5 pixels
- Patch-summary tissue eligibility: tissue fraction at least 0.50 using mean
  RGB below 235 as the tissue-pixel rule

Do not alter these values inside E-007. Any methodological change requires a
new experiment ID.

## Required completion checks

The final banner must show:

- 170 patient rows;
- 30,007 processed patches;
- `gate=True`.

The JSON gate additionally requires matching input hashes, at least 99% finite
numeric patient features, the known patient 17649/patch 5053 artifact logged,
one or more patch-summary-eligible patches for every patient, every low-tissue
patch represented in the exclusion log, exact implementation of the frozen
eligibility rule, and valid primary cells from partial-tissue patches retained
in the cell morphology table.

## Preservation

Download the complete `/kaggle/working/phase_03a_e007_full_extraction` folder,
including `cells.parquet`, `patch_qc.csv`, `patient_features.csv`,
`exclusion_log.csv`, both config/schema/environment JSON/YAML records,
`run_summary.json`, and all 170 overlays. Preserve the Kaggle output ZIP until
the local checksum manifest is generated and verified.

Expected compute is approximately 0.91 T4 GPU-hours. Core tabular output was
projected at roughly 295 MB; overlays add further storage.

## Post-run boundary

After E-007, perform integrity checks, distribution review, and a structured
pathology overlay review. Do not join outcomes, select prognostic features, or
fit survival models until the independent pathology-review gate is documented.
