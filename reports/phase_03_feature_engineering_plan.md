# Phase 3A Plan — Outcome-Blind Morphology Feature Extraction

**Prepared:** 2026-08-28  
**Current readiness:** E-005 10-patient automatic gate passed; pilot QC/distribution review and artifact preservation pending  
**Configuration:** `configs/phase_03_feature_extraction.yaml`

## Why this is the next step

The Phase 2 automatic gate passed and preliminary DLBCL-Morph review found
19/20 usable overlays. The next scientific question is whether the frozen
all-nuclei instances can produce stable, interpretable patient-level features.
It is too early to fit survival models: doing so before artifact rules and the
feature schema are frozen would allow outcome-informed pipeline tuning.

## Frozen cohort inventory

`data/manifests/patient_manifest.csv` contains availability fields only and no
outcomes:

| Item | Count |
|---|---:|
| Clinical patients | 209 |
| H&E image-eligible patients | 170 |
| Clinical patients without released H&E patches | 39 |
| Released H&E patches | 30,007 |
| Released-cell patients | 170 |
| Released cells in `cell_shapes.csv` | 1,035,909 |

The 170 H&E-patch patients and 170 released-cell patients match exactly. No H&E
patient ID falls outside the clinical table. Patch counts range from 22 to 321
per eligible patient (mean 176.5).

## Stage 3A.1 — smoke-test the implemented extractor `[PASSED 2026-08-28]`

`kaggle/phase_03_morphology_survival/phase_03a_feature_extraction.py` is the
self-contained Kaggle script. It reuses the exact E-001 architecture and
frozen postprocessing. The smoke run was required to:

1. discover the extracted `HE/<patient_id>/<patch_id>.png` layout;
2. verify checkpoint MD5 before inference;
3. process one patch in smoke mode;
4. write one row per detected object to Parquet with patient, patch, local
   centroid, morphology, colour, border flag, and QC flags;
5. derive spatial features only within each patch;
6. aggregate to exactly one row per patient; and
7. record package versions, GPU, seed, elapsed time, input counts, exclusions,
   and hashes.

No clinical or outcome table may be loaded in this stage.

The Kaggle CUDA smoke run passed on patient 13964, patch 303. It verified the
checkpoint MD5, discovered the H&E input and working-directory YAML, detected
61 objects, wrote all required artifacts, produced an interpretable QC panel,
and returned `gate=True`. The smoke gate does not test the known patient 17649
failure because smoke mode intentionally processes only one patient and patch.

## Stage 3A.2 — 10-patient stress pilot `[AUTOMATIC GATE PASSED 2026-08-28]`

Run the pre-specified 10 patients in the YAML config. They deliberately cover
low contrast, dense tissue, partial tissue, debris, elongated structures, and
the known failed patch. Selection did not use outcomes.

Promotion to full extraction requires:

- all 10 patients and every discovered H&E patch complete;
- exactly 10 patient-feature rows;
- >=99% finite values among required features;
- patient 17649's linear artifact is flagged by patch/object QC;
- a recorded patches/second rate and projected full-cohort runtime/storage;
- no global cross-patch graph or physical-unit density claim; and
- inspection of feature distributions and at least 10 new overlay/QC panels.

The E-005 Kaggle CUDA run completed all 10 specified patients and all 1,894
discovered patches, yielding 113,833 detected objects, 10 patient feature rows,
10 overlays, and `gate=True`. The known patient 17649 / patch 5053 failure was
recognized by the automatic gate. The console timestamps indicate roughly
three minutes of execution. The preserved `run_summary.json` records 201.666
seconds, 9.392 patches/second, and a 0.888-hour projection for 30,007 patches.
All 10 overlays were computationally reviewed and were usable, with the known
mild merge/split, elongated-structure, and edge-field limitations; independent
pathology review remains pending.

Outcome-blind QC also found 54/1,894 patches below 50% estimated tissue and nine
near-empty patches below 25%. Before full extraction, E-006 must validate a
majority-tissue rule for patch-level count/spatial summaries only. Valid nuclei
from partial patches remain in per-cell morphology distributions, and all
low-tissue patches must be recorded rather than silently dropped. See
`reports/phase_03_pilot_qc.md`.

## Primary and sensitivity feature branches

The primary branch uses all accepted, non-border instances and does not add a
new post-hoc shape filter. A sensitivity branch may exclude extreme area or
elongation values, but its bounds must be derived from LyNSeC validation object
distributions without using DLBCL survival outcomes.

Because the released tables provide patch-local centroids, nearest-neighbour
and Delaunay features are computed within patch and then aggregated to patient
level. Cross-patch distances are invalid until a patch-to-ROI coordinate map is
verified. Cells/mm2 and Ripley's radii in micrometres are deferred until pixel
spacing is verified.

## Stage 3A.3 — full 170-patient extraction

Only after the pilot gate and independent overlay review:

1. run all 30,007 H&E patches once;
2. cache cells and patient features as versioned Parquet/CSV;
3. retain an exclusion log rather than silently dropping patches;
4. compare patient-level distributions with the released `cell_shapes.csv`
   branch; and
5. freeze the final 170-patient feature matrix and its hash.

## Stage 3B — patient-level survival baselines

After the feature matrix is frozen:

1. freeze repeated nested, event-stratified patient-level CV splits for the 170
   image-eligible patients (58 OS events);
2. evaluate clinical-only on the same 170-patient cohort for fair incremental
   comparison; retain the 209-patient clinical result as a secondary cohort;
3. fit released-geometric, recovered-morphology, and clinical+morphology
   elastic-net Cox models; use RSF as secondary;
4. fit imputation, scaling, feature selection, and hyperparameters inside each
   training fold only; and
5. report C-index, time-AUC, integrated Brier score, 1/2/3-year calibration,
   and 1,000 patient-level bootstrap confidence intervals.

E-006 subsequently completed the same 10 patients and 1,894 patches with the
same 113,833 objects, exactly 54 low-tissue flags, and strict `gate=True`.
This confirms that segmentation stayed fixed and the aggregation/QC rule
behaved as pre-specified. Local verification further confirmed byte-identical
cell Parquet and overlays, identical per-cell feature columns, 55 complete QC
records, and intended changes only to patch-summary statistics. The immediate
task is the separate provisional E-007 170-patient feature cache. It remains
outcome-blind; scientific promotion and survival modelling are conditional on
independent pathology review.

E-007 is now executable from
`kaggle/phase_03_morphology_survival/write_e007_config.py` followed by
`phase_03a_e007_full_extraction.py`. Before loading the model, it requires the
exact frozen image inventory: patient-list SHA-256
`cdb1b0aed4c70325e7202cb7d3ca80a7ef490c3eb19edb6904ba8ea796b5e50c`
and sorted `patient/patch.png` inventory SHA-256
`10d1e96e4b6789a12745dc274e61d99ee34b6f798097fc1b27e07d1c31548d97`.
These resolve to 170 patients and 30,007 patches in both the local source ZIP
and the outcome-blind patient manifest.
