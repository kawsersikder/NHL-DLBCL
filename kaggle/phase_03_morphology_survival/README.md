# Phase 3 — Morphology Features and Survival Baselines

## Current state

Phase 2 passed its automatic gate and a preliminary computational overlay
review. Independent pathology review remains pending. The image inventory is
frozen at 170 eligible patients and 30,007 H&E patches.

The Phase 3A one-patch Kaggle CUDA smoke test passed on 2026-08-28 (patient
13964, patch 303; 61 detected cells; all required outputs; `gate=True`).

The fixed E-005 pilot also passed its automatic gate on 2026-08-28: 10
patients, 1,894 patches, 113,833 detected objects, 10 patient-level rows, and 10
overlays. Preserve the complete Kaggle output and review all overlays and
feature distributions before preparing the 170-patient run.

Local outcome-blind review found 54 majority-background patches below 50%
estimated tissue. E-006 then reproduced the cell table and overlays exactly,
applied the patch-summary rule as intended, and passed every strict gate. That
rule is now frozen for E-007.

## E-006 tissue-QC validation `[AUTOMATIC GATE PASSED]`

Use these two files:

1. `kaggle/phase_03_morphology_survival/write_e006_config.py`;
2. `kaggle/phase_03_morphology_survival/phase_03a_e006_tissue_qc_validation.py`.

Paste/run `write_e006_config.py` as the first Kaggle cell. It writes and
SHA-256-verifies the exact tracked YAML at
`/kaggle/working/phase_03_feature_extraction_e006.yaml`. Then paste/run the
complete E-006 validation file as the second cell. It is already set to
`SMOKE_TEST = False` and should take approximately the same three to four
minutes as E-005.

The expected final line is:

```text
PHASE 3A E006 QC_VALIDATION COMPLETE | patients=10 | patches=1894 | cells=113833 | low_tissue=54 | gate=True
```

The strict gate also expects 1,839 patch-summary-eligible patches, 55 exclusion
log rows (54 low-tissue records plus the known artifact), and valid
partial-tissue nuclei retained for per-cell morphology. Do not alter the 0.50
tissue threshold, patient IDs, checkpoint, or segmentation postprocessing.

The Kaggle run passed on 2026-08-28 with 10 patients, 1,894 patches, 113,833
objects, 54 low-tissue flags, and `gate=True`. Preserve the complete output
folder locally before preparing the separate full-cohort experiment.

## E-007 full extraction `[TECHNICAL PASS — FROZEN]`

E-007 completed on 2026-08-28: 170 patients, 30,007 patches, 1,959,950
objects, 542 low-tissue flags, 170 overlays, and `gate=True`. The complete
artifact is preserved in `output_e007_full_extraction/`; its 178-entry SHA-256
manifest and all 48 local integrity/reproducibility checks pass. Do not rerun
or modify the extraction. Independent pathology review remains the active gate
before any outcome join or survival modelling.

Use these two files in a fresh Kaggle notebook or with the old E-005/E-006
execution cells disabled:

1. `kaggle/phase_03_morphology_survival/write_e007_config.py`;
2. `kaggle/phase_03_morphology_survival/phase_03a_e007_full_extraction.py`.

Paste/run the config writer first. It creates and verifies
`/kaggle/working/phase_03_feature_extraction_e007.yaml`. Paste/run the complete
E-007 extraction file second with `SMOKE_TEST = False`, then use **Save Version
→ Save & Run All**. The run is projected at about 0.91 T4 GPU-hours and roughly
295 MB of core tabular output, plus 170 QC overlays.

Before inference, E-007 requires the exact frozen inventory: 170 image-eligible
patients and 30,007 PNG patches. It checks SHA-256 hashes of the numerically
sorted patient and `patient/patch.png` lists and stops on any mismatch. It also
reuses the exact E-001 checkpoint, segmentation settings, known-artifact rule,
and E-006 tissue rule.

The expected final line begins:

```text
PHASE 3A E007 FULL_EXTRACTION COMPLETE | patients=170 | patches=30007 |
```

and must end with `gate=True`. Download the complete
`phase_03a_e007_full_extraction` output folder or the Kaggle output ZIP; do not
copy only `patient_features.csv`.

## Kaggle inputs and YAML

Attach these two inputs:

1. `kawsersikder/dlbcl-morph-patches`;
2. `kawsersikder/dlbcl-e001-unet`.

The first notebook cell writes the exact YAML into `/kaggle/working`, so an
updated `dlbcl-kaggle-codee` input is not required for this run. The E-007
script is already pointed to that path. Its first three messages should show
`mode: FULL_EXTRACTION`, the expected checkpoint MD5, and the verified
170-patient/30,007-patch inventory.

E-007 is explicitly a provisional, outcome-blind cache. Do not attach clinical
outcomes to it yet. Independent pathology review remains required before
survival modelling or biomarker interpretation. Later survival inputs must use
one row per patient, with preprocessing and model selection entirely inside
patient-level training folds.

The complete methods and promotion gate are in
`reports/phase_03_feature_engineering_plan.md` and the E-006 audit is in
`reports/phase_03_e006_validation.md`.
