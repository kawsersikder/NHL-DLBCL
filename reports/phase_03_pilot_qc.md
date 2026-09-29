# Phase 3A E-005 Pilot QC Review

**Run date:** 2026-08-28  
**Review date:** 2026-08-28  
**Canonical artifact:** `kaggle/phase_03_morphology_survival/output_e005_pilot/`  
**Configuration:** `configs/phase_03_feature_extraction.yaml`  
**Review scope:** computational integrity and visual plausibility; not a pathologist assessment

## Result

E-005 passed its implemented automatic gate and completed the frozen,
outcome-blind cohort: 10/10 patients, 1,894/1,894 patches, 113,833 detected
objects, 10 patient rows, and the known patient 17649 / patch 5053 exclusion.
The checkpoint MD5 was `dea287c50949db8c6b7f6b7bfad87271`. No clinical or
survival outcome table was loaded.

The run took 201.666 seconds at 9.392 patches/second. Its measured projection
for 30,007 patches is 0.888 hours on a Tesla T4. The 17 original output files
occupy 18,600,216 bytes; linear scaling gives approximately 294.7 MB for the
full cohort, including one overlay per patient at the current rate.

## Integrity audit

| Check | Result |
|---|---:|
| Patch rows | 1,894 |
| Patient rows | 10 |
| Duplicate patient/patch keys | 0 |
| Duplicate patient rows | 0 |
| Patient IDs consistent across patch/patient tables | Yes |
| Patch detected-cell sum equals run summary | Yes |
| Patient detected-cell sum equals run summary | Yes |
| Patch primary-cell sum equals patient primary-cell sum | Yes |
| Patient numeric feature finite fraction | 100% |
| Zero-variance patient numeric features | 0 |
| `cells.parquet` header/footer magic | Valid `PAR1` |
| Explicitly excluded patches | 1 (`17649/5053`) |

Eight patch-level spatial values are non-finite, all explained: four belong to
the explicitly excluded `17649/5053` patch, and four belong to `13965/29722`,
which has five border detections and zero primary nuclei. These values are
ignored by the patient aggregation and all 64 patient numeric columns remain
finite.

Patch predicted counts range from 5 to 103 (median 60); primary counts range
from 0 to 83 (median 46). No patch has zero detected objects, and no patch has
more than 50% predicted nuclear foreground. The patient feature table contains
real between-patient variation in every numeric column.

## Overlay review

All 10 generated panels were inspected. Five were rated `usable` and five
`usable_with_caution`; none showed catastrophic domain failure. Dense fields
have strong nuclear coverage. The caution cases show the expected limitations
already documented in Phase 2: occasional merged/split nuclei, elongated
stromal or edge structures, pale-nucleus misses, and border truncation. The
per-panel record is in `reports/phase_03_pilot_overlay_review.csv`.

This is an AI-assisted computational review, not an independent
haematopathologist assessment. Expert review remains required before treating
the recovered instances as pathology-validated measurements.

## Outcome-blind background finding

The pilot exposed a patch-level aggregation issue not covered by the automatic
gate. Nine patches have estimated tissue fraction below 0.25; all nine were
visually checked and are predominantly white glass with only a thin tissue
edge. At a 0.50 cutoff, 54/1,894 patches (2.85%, across eight patients) would be
ineligible for patch-level count and spatial summaries. Representative patches
immediately below and above 0.50 were inspected, and 0.50 separates
majority-background from majority-tissue fields reasonably under the current
fixed RGB heuristic.

The original DLBCL-Morph repository states that patches were extracted inside
pathologist ROIs, but edge patches can still contain substantial glass:
https://github.com/stanfordmlgroup/DLBCL-Morph. Published computational
pathology pipelines use task-specific tissue-coverage rules rather than one
universal threshold; examples include filtering patches with more than 65%
background/muscle and majority-tissue patch selection:
https://doi.org/10.1371/journal.pone.0268954 and
https://doi.org/10.1371/journal.pone.0282577.

## Promotion decision

Do not run the 170-patient extraction from the unchanged E-005 code. First run
a short outcome-blind E-006 validation with the following frozen candidate
rule:

1. `tissue_fraction >= 0.50` is required only for patch-level cell-count,
   nearest-neighbour, Delaunay, and foreground summaries;
2. valid non-border nuclei from partial-tissue patches remain eligible for
   patient-level per-cell morphology distributions;
3. every low-tissue patch is flagged and recorded rather than silently
   dropped;
4. the known `17649/5053` artifact remains excluded from both branches; and
5. E-006 must reproduce all patient rows, remain outcome-blind, and produce
   finite patient features before the full extraction.

This change is based only on image/QC information from the pre-specified pilot,
not survival outcomes. Full extraction should remain a separate experiment
with its own configuration and hashes.
