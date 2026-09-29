# Phase 3A E-007 Full-Extraction Console Audit

**Run date:** 2026-08-28  
**Evidence available:** complete Kaggle console transcript and one displayed QC
overlay; full output bundle not yet copied locally.

## Automatic result

E-007 completed successfully with `gate=True`:

- exact input inventory verified before inference: 170 patients and 30,007
  H&E patches;
- patch inventory SHA-256 prefix `10d1e96e4b67...`, matching the frozen E-007
  config;
- E-001 checkpoint MD5
  `dea287c50949db8c6b7f6b7bfad87271`;
- 170 patient feature rows;
- 30,007 processed patches;
- 1,959,950 detected nuclear objects;
- 542 low-tissue patch-summary exclusions (1.81% of patches);
- 170 QC overlays, one per patient;
- 178 listed output files totalling 288,994,830 bytes (approximately 275.6
  MiB);
- logged inference span from the initial mode line to the last patient line:
  3,276 seconds (54.6 minutes).

The mean counts are 65.32 detected objects per patch and 11,529 detected
objects per patient. These are descriptive pipeline quantities, not biological
or prognostic estimates.

## Displayed-overlay assessment

The displayed first-patient overlay contains a substantial blank/background
region. Predicted probability and instance contours are concentrated in the
tissue-bearing region, with little response in the blank area. Most visible
nuclear profiles receive plausible contours. Mild merging/splitting and
boundary uncertainty remain expected from the E-004 to E-006 reviews.

This single overlay is computationally usable and is consistent with the
frozen tissue rule. It does not substitute for systematic review of all 170
overlays or independent pathology review.

## Interpretation

The automatic E-007 extraction gate passed and the full outcome-blind feature
cache may be preserved and audited locally. The result does **not** yet permit
joining clinical outcomes, selecting prognostic features, fitting survival
models, or claiming pathology validation.

## Required next checks

After the complete output folder is available locally:

1. generate and verify a SHA-256 artifact manifest;
2. confirm the exact 170 patient rows, 30,007 patch rows, 1,959,950 cell rows,
   542 low-tissue records, and 170 overlays from the saved files;
3. inspect `run_summary.json` and every promotion-gate field;
4. audit missingness, finite values, duplicate keys, per-patient patch counts,
   exclusion-log consistency, and feature distributions;
5. compare the ten E-006 patients against E-006 to confirm identical cell-level
   extraction and expected patient-summary values; and
6. prepare a structured 170-overlay review sheet, then obtain independent
   pathology review before any outcome analysis.
