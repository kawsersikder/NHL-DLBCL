# Phase 3A E-006 Tissue-QC Validation

**Run date:** 2026-08-28  
**Canonical artifact:** `kaggle/phase_03_morphology_survival/output_e006_tissue_qc_validation/`  
**Tracked config SHA-256:** `1a66ed47d786bbe8ea3e3ec75cac2a212984fdd2cba14ef61ddf7f2bcfe2a5f6`  
**Review scope:** outcome-blind engineering and computational QC; independent pathology review pending

## Strict gate result

E-006 passed every pre-specified check:

| Check | Result |
|---|---:|
| Patients | 10 / 10 |
| Patches | 1,894 / 1,894 |
| Detected objects | 113,833 |
| Patient numeric finite fraction | 100% |
| Low-tissue patches | 54 / 54 expected |
| Patch-summary-eligible patches | 1,839 |
| Low-tissue log records | 54 |
| Known artifact exclusions | 1 (`17649/5053`) |
| Partial-tissue primary cells retained for morphology | 1,402 |
| Duplicate patient/patch keys | 0 |
| Promotion gate | PASS |

The run took 207.167 seconds at 9.142 patches/second. Its measured projection
for all 30,007 H&E patches is 0.912 Tesla-T4 hours.

The uploaded YAML is byte-identical to the tracked E-006 config. The
`resolved_config.yaml` hash differs because `yaml.safe_dump` normalised quotes
and numeric formatting; it is the runtime serialization of the same loaded
configuration.

## E-005 versus E-006

The E-006 `cells.parquet` and all 10 overlays are byte-identical to E-005. All
42 patient-level per-cell morphology columns are also exactly identical. The
shared patch-level inference/QC columns are unchanged.

All 20 patch-summary statistics changed in at least one patient, as expected
when majority-background patches are removed from those summaries. The largest
changes occur in patient 13965, which contains 29 of the 54 low-tissue patches:
its tissue-fraction IQR decreases from 0.1043 to 0.0468, tissue-fraction p10
increases from 0.5043 to 0.7451, nuclear-foreground p10 increases by 24%, and
primary-cell-count p10 increases from 33.5 to 40.0. These are directionally
consistent with removing mostly-glass edge tiles.

Patch eligibility by patient is:

| Patient | Total | Patch-summary eligible | Low tissue |
|---|---:|---:|---:|
| 13964 | 79 | 73 | 6 |
| 13965 | 286 | 257 | 29 |
| 17648 | 214 | 207 | 7 |
| 17649 | 193 | 187 | 5 |
| 18835 | 308 | 307 | 1 |
| 19681 | 219 | 215 | 4 |
| 26793 | 63 | 62 | 1 |
| 26806 | 175 | 175 | 0 |
| 26817 | 194 | 193 | 1 |
| 26838 | 163 | 163 | 0 |

## Decision

Freeze the E-006 rule for subsequent extraction:

- the E-001 checkpoint and watershed segmentation remain unchanged;
- `tissue_fraction >= 0.50` is required only for patch-level count/spatial
  summaries;
- valid non-border cells in partial-tissue patches remain eligible for
  per-cell morphology;
- every low-tissue patch and known visual failure is explicitly recorded; and
- physical-unit and cross-patch spatial claims remain disabled.

The full 170-patient extraction may be computed and cached as an explicitly
provisional, outcome-blind engineering artifact because the pipeline is frozen
and no survival data are read. Do not fit or interpret survival models from the
recovered features until independent pathology review is completed or the
absence of such review is formally accepted and reported as a limitation.
