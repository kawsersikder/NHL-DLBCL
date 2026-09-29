# Phase 2 Recovery Plan — Nucleus Segmentation and QC

**Date:** 2026-08-28  
**Status:** E-004 automatic gate passed; preliminary computational visual gate passed; independent pathology review pending.  
**Immediate implementation:** `kaggle/phase_02_segmentation_qc/phase_02_unet_recovery_qc.py`

## Decision in one sentence

Do not spend more Kaggle runs tuning the released `he.tar` checkpoint. Use the
successful E-001 LyNSeC H&E U-Net as the DLBCL-specific recovery segmenter,
derive nucleus instances with watershed, and gate it on 50 recorded LyNSeC
validation tiles plus 20 patient-diverse DLBCL-Morph H&E overlays. If that gate
fails, use DLBCL-Morph's released per-nucleus masks and `cell_shapes.csv` as the
precomputed-cell branch rather than blocking the entire pathology project.

## What the failed HoLy-Net probe established

The checkpoint itself is intact: MD5 matches Zenodo, 798 tensors load from
`checkpoint.desc`, and the matching `HoVerNet(num_types=3, mode="fast")`
architecture has 100% key coverage with zero missing or unexpected keys.

The failure is functional, not a file-loading error:

| Diagnostic | Result |
|---|---:|
| LyNSeC tile | `0_l2.npy` |
| Pixel Dice at threshold 0.50 | 0.2819 |
| Best threshold-sweep Dice | 0.3029 at 0.10 |
| RGB direct vs TIAToolbox `infer_batch` | identical; maximum difference 0.00000000 |
| BGR Dice at threshold 0.50 | 0.2725 |
| Best BGR threshold-sweep Dice | 0.3048 at 0.10 |

The overlay contains large false-positive and false-negative regions. A simple
translation cannot explain the mismatch. Therefore channel order, threshold,
manual softmax extraction, and a fixed crop offset have been ruled out.

The [Zenodo v1 record](https://zenodo.org/records/8065174) contains the LyNSeC
arrays and two checkpoints (`he.tar`, `ihc.tar`) but no original inference code,
environment lockfile, or split manifest. The paper reports H&E F1 0.899, but
that metric and split are not directly comparable to this pixel-Dice smoke test;
the source-data overlay is nevertheless too poor to approve the checkpoint for
morphology extraction. See the [HoLy-Net paper record](https://pubmed.ncbi.nlm.nih.gov/38237235/).

## Why the project can continue without `he.tar`

Phase 2's scientific requirement is **usable nucleus instances on
DLBCL-Morph**, not mandatory use of one checkpoint.

Two existing project assets remove the checkpoint as a single point of failure:

1. E-001 already trained a DLBCL-specific H&E SmallUNet on LyNSeC. It reached
   tile-level validation Dice 0.8779 and produced visually credible binary masks.
   The locally archived `output_final/best_model.pt` has MD5
   `dea287c50949db8c6b7f6b7bfad87271`; the recovery script records the hash of
   the checkpoint actually discovered in Kaggle.
   Its limitation is explicit: LyNSeC does not provide patient identifiers, so
   this is an engineering model, not a patient-level validation result.
2. DLBCL-Morph already releases per-tumour-nucleus binary masks and
   `cell_shapes.csv`. Its original pipeline used general HoVer-Net to segment
   nuclei independently in non-overlapping 224x224 H&E patches and retained
   neoplastic nuclei. The official paper describes the masks, patch identifiers,
   and geometric features, and the repository provides the feature code:
   [DLBCL-Morph paper](https://arxiv.org/html/2009.08123v3),
   [official repository](https://github.com/stanfordmlgroup/DLBCL-Morph).

This permits a primary recovery branch and a precomputed-cell fallback without
changing the OS prognosis question.

## Recovery branch: E-001 U-Net plus watershed instances

The recovery script loads the exact E-001 checkpoint and validation manifest.
It converts the U-Net's binary probability mask into individual nuclei using a
distance transform and marker-controlled watershed. It then reports:

- semantic Dice;
- centroid-matched detection precision, recall, and F1;
- absolute nucleus-count error;
- panoptic quality (PQ), detection quality (DQ), and segmentation quality (SQ);
- LyNSeC ground-truth/prediction/error overlays; and
- DLBCL-Morph probability/instance overlays with a blank review sheet.

The binary model detects all nuclei. It does **not** provide a validated
tumour/non-tumour label. Its downstream feature branch must therefore remain
type-free: morphology distributions, total nuclear density, nearest-neighbour
statistics, Delaunay topology, and Ripley's K/L. Tumour/non-tumour mixing must
be omitted unless a separate classifier is later validated.

### Pre-specified engineering gate

The 50-tile LyNSeC pilot passes only when all three conditions hold:

| Measure | Required value |
|---|---:|
| Mean semantic Dice | >= 0.80 |
| Mean centroid detection F1 (12 px radius) | >= 0.70 |
| Median absolute count error | <= 20% |

The DLBCL-Morph visual gate passes only when at least 80% of the 20
patient-diverse patches are marked usable and no systematic severe failure mode
is present. A haematopathologist should review the final panels before full
feature extraction. Until then, the result is preliminary QC.

## Recorded outcome (E-004, 2026-08-28)

The 50-tile pilot passed all pre-specified automatic thresholds: mean semantic
Dice 0.8879, mean centroid detection F1 0.8923, and median absolute count error
9.69%. All 20 DLBCL-Morph overlays were produced from 20 unique patients.

A preliminary AI-assisted computational review marked 19/20 usable. This is
not a pathologist review. Patient 17649 / patch 5053 failed because a long
non-nuclear linear structure was fragmented into multiple predicted instances.
The aggregate count diagnostics also show mild systematic over-splitting:
48/50 LyNSeC tiles were over-counted, mean signed count error was +12.6%, and
11/50 exceeded 20% absolute count error.

The recovery model is therefore provisionally promoted to the outcome-blind
10-patient feature-extraction stress pilot described in
`reports/phase_03_feature_engineering_plan.md`. Full-cohort extraction remains
conditional on independent overlay review and frozen object-QC rules.

## Exact Kaggle sequence

1. Attach `dlbcl-kaggle-code` and `kawsersikder/dlbcl-morph-patches`. Confirm
   that an attached input contains E-001's `best_model.pt` and
   `tile_manifest.csv`; otherwise upload
   `phase_01_lynsec_he_nuclei_baseline/output_final/` as a small private Kaggle
   dataset and attach it.
2. Select a T4 GPU. Internet can remain off; this route does not download
   `he.tar` or install TIAToolbox.
3. Paste/run `phase_02_unet_recovery_qc.py` with `SMOKE_TEST = True`.
4. Confirm that it loads the E-001 checkpoint, identifies 64 manifest-recorded
   validation tiles, displays one LyNSeC overlay, and writes two DLBCL overlays.
5. If the smoke output is structurally correct, set `SMOKE_TEST = False` and
   use Save & Run All (Commit). This scores 50 LyNSeC validation tiles and
   creates 20 patient-diverse DLBCL-Morph overlays.
6. Download `run_summary.json`, `lynsec_metrics.csv`, both overlay directories,
   and `dlbcl_morph_review_sheet.csv`.
7. Complete the review sheet. Do not begin full inference until both the
   automatic gate and visual gate pass.

## If the recovery branch fails

Do not pivot immediately to transcriptomics. Use the DLBCL-Morph released-cell
branch first:

1. Treat `cell_shapes.csv` and the released `Cells/` masks as fixed upstream
   measurements from the original DLBCL-Morph pipeline.
2. Recompute patient-level morphology distributions with fold-safe downstream
   preprocessing.
3. Use `patch_id` plus per-cell centroids to derive within-patch density,
   nearest-neighbour, and graph features. Do not imply that a patch centroid is
   a whole-core coordinate unless a verified patch-to-ROI coordinate map is
   reconstructed.
4. Keep these tumour-nucleus features separate from the all-nuclei U-Net branch
   in tables and ablations.

This fallback is scientifically legitimate because the DLBCL-Morph authors
explicitly release the masks/features and demonstrate their prognosis signal.
It is less novel than a new DLBCL-specific segmenter, so the contribution must
come from rigorous spatial aggregation, fold-safe survival modelling, clinical
incremental value, and honest ablations.

## Optional comparator, not the next run

If a second model is needed after the recovery pilot, use a maintained,
version-pinned implementation rather than reconstructing `he.tar` again:

- TIAToolbox provides `hovernet_fast-pannuke` with a supported instance
  segmentation engine and standard output configuration:
  [official example](https://tia-toolbox.readthedocs.io/en/stable/_notebooks/jnb/08-nucleus-instance-segmentation.html).
- StarDist provides the official `2D_versatile_he` H&E instance model:
  [official repository and model list](https://github.com/stardist/stardist).

These are comparator/domain-gap baselines, not substitutes for LyNSeC or manual
DLBCL-Morph QC. Adding them before the recovery gate would increase dependency
risk without resolving the immediate decision.

## Phase boundary after recovery

Phase 2 is complete only after:

- the 50-tile automated gate is recorded;
- 20 DLBCL-Morph overlays are reviewed;
- the chosen cell source and feature semantics are frozen;
- the environment, checkpoint hash, postprocessing parameters, and exclusions
  are registered; and
- the patient/image manifest is reconciled for the morphology cohort.

Only then should Phase 3 extract features. All survival preprocessing,
selection, scaling, and model tuning must remain inside patient-level training
folds.
