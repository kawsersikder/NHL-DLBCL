# Phase 2 Segmentation and QC Result

**Run date:** 2026-08-28  
**Experiment:** E-004  
**Status:** automatic gate passed; preliminary computational visual gate passed; independent pathology review pending  
**Canonical artifact:** `kaggle/phase_02_segmentation_qc/output_final/`

## Outcome

The E-001 LyNSeC H&E SmallUNet plus fixed watershed postprocessing is accepted
for an **outcome-blind feature-extraction pilot**. It is not yet approved for
unreviewed full-cohort feature extraction or for clinical claims.

The model produces type-free all-nuclei instances. It does not provide a
validated tumour/non-tumour phenotype, so tumour/non-tumour mixing features
remain out of scope.

## Provenance

| Item | Value |
|---|---|
| Checkpoint | E-001 `best_model.pt` |
| Checkpoint MD5 | `dea287c50949db8c6b7f6b7bfad87271` |
| Probability threshold | 0.50 |
| Minimum nucleus area | 20 px |
| Watershed minimum distance | 5 px |
| Centroid match radius | 12 px |
| LyNSeC split | 50 tiles from E-001's recorded 64-tile validation split |
| DLBCL review sample | 20 patches from 20 unique patients; seed 20260828 |

## Automatic gate

| Metric | Observed | Pre-specified gate | Result |
|---|---:|---:|---|
| Mean semantic Dice | **0.8879** | >=0.80 | Pass |
| Mean centroid detection F1 | **0.8923** | >=0.70 | Pass |
| Median absolute count error | **9.69%** | <=20% | Pass |

The aggregate gate passes. A secondary diagnostic shows a systematic positive
count bias: 48/50 tiles were over-counted, mean signed count error was +12.6%,
and 11/50 tiles exceeded 20% absolute count error. The dominant interpretation
is mild watershed over-splitting. This must be retained as a limitation and
tested with a pre-specified object-QC sensitivity branch; it is not a reason to
retune the completed validation gate post hoc.

## DLBCL-Morph visual review

All 20 requested overlays were produced. A preliminary AI-assisted
computational review marked **19/20 (95%) usable**, exceeding the planned 80%
visual threshold. The review is recorded in
`reports/phase_02_preliminary_overlay_review.csv` and must not be represented as
a pathologist assessment.

The one preliminary failure was patient 17649 / patch 5053: a long
non-nuclear linear structure was segmented and fragmented into multiple
instances. Common non-severe findings across usable patches were mild
over-splitting, occasional low-contrast misses, partial-tissue fields, and a
small number of elongated stromal/artefactual false positives. There was no
widespread blank-background detection or catastrophic cross-domain failure.

## Decision and remaining gate

The recovery branch is sufficiently credible to proceed to a 10-patient,
outcome-blind feature-extraction stress pilot. Before full 170-patient
extraction:

1. obtain an independent haematopathology review of the 20 panels;
2. freeze patch/object exclusion and border-object rules;
3. verify pixel spacing before reporting cells/mm2 or Ripley's radii in micrometres;
4. keep spatial features within patch coordinates unless a verified
   patch-to-ROI coordinate transform is available; and
5. preserve a sensitivity comparison against the released
   `cell_shapes.csv` branch.

## Preserved files

The canonical output contains 73 files (74,102,690 bytes):

- `run_summary.json`;
- `lynsec_metrics.csv` and 50 LyNSeC overlays;
- the untouched blank `dlbcl_morph_review_sheet.csv`; and
- 20 DLBCL-Morph overlays.

The original blank review sheet is preserved so a human/pathologist can score
it independently. The preliminary computational review is stored separately.
