# Phase 3A E-007 Full-Extraction Validation

**Experiment:** E-007  
**Run date:** 2026-08-28  
**Canonical artifact:**
`kaggle/phase_03_morphology_survival/output_e007_full_extraction/`  
**Audit result:** **PASS — 48/48 integrity and reproducibility checks**  
**Scientific status:** provisional outcome-blind cache; independent pathology
review remains mandatory before outcome joining or survival modelling.

## Run result

E-007 processed the exact frozen image inventory and passed its complete
automatic gate:

| Quantity | Result |
|---|---:|
| Image-eligible patients | 170 / 170 |
| H&E patches | 30,007 / 30,007 |
| Detected cell objects | 1,959,950 |
| Patient feature rows | 170 |
| Low-tissue patch-summary exclusions | 542 (1.81%) |
| Patch-summary-eligible patches | 29,464 |
| Exclusion-log rows | 543 |
| Primary cells retained from partial-tissue patches | 14,060 |
| QC overlays | 170 / 170 |
| Kaggle elapsed time | 3,353.3 s (55.9 min) |
| Saved files before local manifest | 178 |
| Saved size before local manifest | 288,994,830 bytes (275.6 MiB) |

The checkpoint MD5 is
`dea287c50949db8c6b7f6b7bfad87271`. The patient and patch inventory hashes are
respectively
`cdb1b0aed4c70325e7202cb7d3ca80a7ef490c3eb19edb6904ba8ea796b5e50c`
and
`10d1e96e4b6789a12745dc274e61d99ee34b6f798097fc1b27e07d1c31548d97`.
Both match the frozen config and the local outcome-blind manifest.

## Local integrity audit

The reproducible validator `src/validation/audit_e007_output.py` passed all 48
checks. Confirmed properties include:

- the saved resolved YAML is semantically identical to the tracked E-007 YAML;
- all promotion-gate entries are true, the run reads no outcomes, and
  `outcome_join_permitted` remains false;
- exactly 170 unique patient rows, 30,007 unique patient/patch rows, and
  1,959,950 unique patient/patch/cell rows are present;
- per-patient patch counts exactly match `patient_manifest.csv`;
- every cell references a known patch;
- patch predicted, primary, and border counts exactly reconcile to the Parquet
  cell table;
- all patient numeric features are finite and no outcome-like columns exist;
- every cell numeric value is finite; area, axes, eccentricity, solidity, RGB,
  and binary flags satisfy their implementation ranges;
- the 0.50 tissue threshold and patch-summary eligibility rule are implemented
  exactly;
- all 542 low-tissue patches have matching exclusion records;
- patient 17649 / patch 5053 is logged exactly once and all its cells are
  excluded from primary morphology;
- all 170 patients retain at least one patch eligible for patch-level summaries;
- all 170 overlay PNG files open successfully and map one-to-one to patients;
  and
- aggregate patient counts exactly reconcile to patch and cell source tables.

The 11 missing Delaunay values and six missing nearest-neighbour values in
`patch_qc.csv` are expected, not data corruption. Ten affected patches have
fewer than three primary cells; the eleventh is the pre-specified excluded
artifact patch 17649/5053. All 170 patient-level feature rows remain finite.
Blank `qc_flag` cells on 29,464 eligible patches mean “no flag.”

## E-006 reproducibility lock

For the ten E-006 patients, E-007 reproduced:

- all 113,833 per-cell rows exactly across every column;
- all 1,894 patch-QC rows exactly;
- all ten patient feature rows exactly; and
- all ten QC overlays byte-for-byte.

This is strong evidence that moving from E-006 to the full cohort introduced no
checkpoint, postprocessing, aggregation, or serialization drift.

## Cohort-level observations

Patient patch counts range from 22 to 321 (median 185). Total detected cell
counts range from 937 to 23,384 (median 11,384.5). Low-tissue counts range from
zero to 31 per patient (median one). Patient 13957 has the highest low-tissue
fraction, 18/77 patches (23.4%), and should receive targeted review.

There are 65 numeric columns excluding the patient identifier, including five
count/QC columns. Outcome-blind Spearman analysis found 39 feature pairs with
absolute correlation at least 0.95. Most reflect expected redundancy among
area, perimeter, axes, RGB summaries, and patch density/spatial summaries.
Future modelling must therefore use regularisation and fold-internal
preprocessing/redundancy handling; these correlations are not justification for
outcome-informed feature selection on the full cohort.

## Preliminary representative-overlay review

Eight outcome-blind overlays were selected from distribution extremes. This is
a computational assessment, not a pathology opinion.

| Patient / patch | Selection reason | Preliminary assessment |
|---|---|---|
| 13952 / 60 | Highest absolute low-tissue count | Usable dense field; mild merge/split errors |
| 26807 / 1771 | Lowest cell yield and foreground | **Priority review:** fibrous/elongated field with fragmentation and possible non-nuclear structure capture |
| 26797 / 130 | Highest detected-cell count | Usable dense field; mild merge/split errors |
| 13976 / 31 | Lowest median cell area | Usable with caution in a mixed elongated field |
| 19691 / 104 | Highest median cell area | Large nuclear profiles broadly captured |
| 26822 / 273 | Highest median nuclear foreground | Usable dense field; expected mild boundary errors |
| 19700 / 335 | Highest tissue-fraction p10 | Usable dense tissue field |
| 17649 / 82 | Known-failure patient | Displayed patch usable; it is not excluded patch 5053 |

The structured sheet `reports/phase_03_e007_overlay_review.csv` contains all 170
patients and keeps pathology-review fields blank.

## Artifact preservation

The canonical directory contains 179 files and 289,015,310 bytes after adding
`artifact_manifest.sha256`. Its 178 manifest entries verify successfully.

Core SHA-256 values:

| File | SHA-256 |
|---|---|
| `cells.parquet` | `F5BB5A01D79D2675C02812F0BDBC5C888A27AF898B7943EC0DFFA5EFBBB127B0` |
| `patch_qc.csv` | `C71D7FE0B411F54D07EDD42110C21A37D7317DB0C072DEF75A361010FA6467EF` |
| `patient_features.csv` | `1CFADED8D172CE454FF4014B0E9F277EF5AA167790713930919C258D1124FCF1` |
| `exclusion_log.csv` | `89E54D20B6946CF508E9FA057944981816AE5F2E4DA9A923519D4E9F9B1DC96A` |
| `run_summary.json` | `55B31AA9458F591DACA5FC233FDB69532FE7801722DCC9AB44FDB2816D7BC7AC` |
| `resolved_config.yaml` | `6966F38CB7947DEFED15239B14E0B5BE1595806E609BF4281F087DCAB73B89EF` |
| `feature_schema.json` | `F94E8848D5B12AA04EF2319D9002EC0E88AB367C87CB030AC13F3A7869C8764E` |

## Decision

**Accept E-007 as the frozen, technically verified Phase 3A full-cohort feature
cache.** Do not rerun extraction or modify these artifacts.

The next gate is structured overlay review with special attention to patients
13957 and 26807, the known 17649/5053 artifact, and segmentation behaviour in
elongated/fibrous fields. Outcome joining, prognostic feature selection, and
survival modelling remain blocked until independent pathology review is
documented.

## 2026-08-28 gate addendum

The subsequent outcome-blind AI-assisted review has now inspected all 170
representative panels and is documented in `reports/phase_03_e007_ai_qc.md`.
It found 130 PASS, 39 CAUTION, and one failed representative field (patient
26807/patch 1771). The primary n=170, fail-only n=169, and strict-QC n=168
cohorts were frozen before individual outcome access.

This later decision supersedes only the final sentence above: after the Phase
3B statistical protocol and grayscale-entropy comparator are locked, internal
exploratory survival modelling may proceed. Independent expert review remains
mandatory before pathology/clinical interpretation, manuscript promotion, or
submission. AI-assisted QC must not be described as pathology validation.
