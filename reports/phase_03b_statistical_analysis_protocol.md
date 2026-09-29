# Phase 3B — Statistical Analysis Protocol

**Protocol version:** 1.1 (§6.2 scope clarified 2026-09-01, before outcome access)
**Written:** 2026-08-30
**Written by:** Claude (Phase 3B protocol lock)
**Machine-readable twin:** `configs/phase_03b_analysis_protocol.yaml`
**Status:** sign-off recorded in §13. **No outcome column was read to produce this document.**

---

## 0. Purpose and binding scope

This protocol fixes every analytical choice for Phase 3C **before** overall
survival is joined to the frozen E-007 feature cache. Once signed, it is
hash-locked. Any later change is an *amendment*, must be dated and justified in
§12, and must be recorded before the affected results are inspected.

The protocol governs experiments **E-008** (outcome-blind entropy comparator)
and **E-009** (the survival model ladder).

### Outcome-blindness declaration

Everything produced up to and including this document is outcome-blind. Blindness
formally ends at **Step S2** (split generation, §5.3), which reads the OS event
indicator and nothing else. That single, pre-specified read is what §5.3
authorises — it authorises nothing further.

---

## 1. Data, cohorts, and endpoint

### 1.1 Inputs

| Input | Path | Frozen identity |
|---|---|---|
| Image features | `kaggle/phase_03_morphology_survival/output_e007_full_extraction/patient_features.csv` | E-007, 170 rows × 65 features |
| Patch QC | `.../output_e007_full_extraction/patch_qc.csv` | 30,007 rows |
| Clinical table | `data/raw/dlbcl_morph/clinical_data_cleaned.csv` | MD5 `9be9d237c49506db16d3c3b53825f827` |
| Released geometry | `data/raw/dlbcl_morph/cell_shapes.csv` | figshare, MD5 in `PROVENANCE.md` |
| Entropy features | `reports/phase_03b_entropy_features.csv` | produced by E-008, §4 |

### 1.2 Join rule

`patient_id` is cast to `str` in every table. All IDs are 5-digit numeric. The
join was verified outcome-blind on 2026-08-30:

- E-007 features ∩ clinical = **170**
- E-007 features ∩ `cell_shapes.csv` = **170**
- E-007 features \ clinical = **∅**; symmetric difference with geometry = **∅**

Any future run that does not reproduce 170/170/∅ **must abort**.

### 1.3 Endpoint

**Overall survival only.** `OS` is time in years from *end of treatment*;
`Follow-up Status` is the event indicator (1 = deceased). PFS is excluded — the
table has PFS times but no progression-status indicator, so it is not analysable
(Decision Log, 2026-08-23).

### 1.4 Cohorts (frozen pre-outcome, from E-007-AI-QC)

| Cohort | n | Definition | Role |
|---|---|---|---|
| **A** | **170** | All image-eligible patients | **Primary** |
| B | 169 | Excludes 26807 (failed representative field) | Pre-specified sensitivity |
| C | 168 | Excludes 26807 and 13957 (23.4% low-tissue patches) | Pre-specified sensitivity |

Cohort A carries **58 OS events**. All conclusions are drawn from Cohort A.
B and C exist to test robustness, not to be selected on the basis of a better
result. If A, B, and C disagree materially, that disagreement is reported as a
finding, not resolved by preference.

### 1.5 The 209-patient clinical model is not a comparator

A clinical-only model can be fitted on all 209 patients, but it is **descriptive
context only**. Every paired comparison in this protocol is restricted to the
identical Cohort A patients and identical outer splits. Comparing a 209-patient
model to a 170-patient model is prohibited.

---

## 2. Feature families (frozen partition)

The 65 E-007 feature columns are partitioned exhaustively and disjointly. This
partition is the highest-leakage-risk decision in the project and is fixed here,
before outcome access.

### F0 — QC / exposure (9 columns) — **excluded from all primary models**

```
patch_count_total, patch_count_primary, patch_count_low_tissue
cell_count_total, cell_count_primary
patch_tissue_fraction_{median, iqr, p10, p90}
```

**Rationale for exclusion.** These quantify *how much tissue was sampled and how
clean it was* — TMA core availability and slide background — not tumour biology.
`cell_count_total` is near-deterministic in `patch_count_total`. Admitting them
as predictors would let the model exploit a sampling artifact and would be
indefensible at review. They are retained for QC adjustment and §9.3 sensitivity.

### F1 — Nuclear morphology distributions (40 columns) → **M4a**

**F1a — shape (28):** `cell_X_{median, iqr, p10, p90}` for
`X ∈ {area_px, perimeter_px, eccentricity, solidity, circularity, major_axis_px, minor_axis_px}`

**F1b — stain intensity (12):** `cell_rgb_mean_{r,g,b}_{median, iqr, p10, p90}`

F1b is kept separable because stain intensity is confounded with staining batch
and scanner. §9.4 ablates it.

### F2 — Local packing and architecture (16 columns) → **M4b**

`patch_Y_{median, iqr, p10, p90}` for
`Y ∈ {primary_cell_count, nuclear_foreground_fraction, nearest_neighbour_median_px, delaunay_edge_median_px}`

`patch_tissue_fraction_*` is deliberately **not** here — it is F0.

### Cross-cutting views (subsets, not additional families)

| View | Columns | Tests |
|---|---|---|
| **Central tendency** | the 14 `*_median` columns of F1 ∪ F2 | "means are enough" null |
| **Spread / heterogeneity** | the 42 `*_{iqr,p10,p90}` columns of F1 ∪ F2 | Hypotheses 1 and 3 |
| **Patch-to-patch heterogeneity** | the 12 `patch_*_{iqr,p10,p90}` columns | Hypothesis 3 |

**Count check:** 9 + 40 + 16 = 65 ✓ (+ `patient_id` = 66 columns in file).

---

## 3. Model ladder

Every model uses identical Cohort A patients and identical outer splits (§5).

| ID | Model | Feature set | k | Role |
|---|---|---|---|---|
| M0a | IPI score | `IPI Score` | 1 | Clinical standard |
| M0b | R-IPI group | `RIPI Risk Group` | 1 | Clinical standard |
| M1 | **Clinical Cox** | `Age, ECOG PS, LDH, EN, Stage` | 5 | **Primary clinical baseline** |
| M2 | Released geometry | `cell_shapes.csv` mean+SD | 44 | Reproduced literature baseline |
| M3 | Global entropy | E-008 entropy features | 5 | Comparator to Carreras 2026 |
| M4a | Morphology only | F1 | 40 | Pleomorphism ablation |
| M4b | Packing only | F2 | 16 | Architecture ablation |
| M4c | **Primary image model** | F1 ∪ F2 | 56 | — |
| M5 | **Primary incremental** | M1 ∪ M4c | 61 | — |
| M6 | Frozen encoder / MIL | TBD | — | Optional Phase 4 benchmark |

### 3.1 Notes on individual models

- **M1** uses the *raw* IPI components rather than the collapsed score, per the
  locked ladder. IHC/FISH markers are **not** in M1 — they belong to Phase 3D.
- **M2** reproduces the Stanford `GEO_COLS` set verbatim (22 descriptors ×
  mean/SD). That set includes four *positional* descriptors
  (`rectCenter_x`, `rectCenter_y`, `ellip_centroid_x`, `ellip_centroid_y`; 8
  columns) which encode location in the patch, not shape. They are retained for
  fidelity to the published baseline, and §9.5 runs M2 without them.
  **Unlike E-002, M2 here is fitted fold-safely** — the legacy in-sample fit and
  dataset-wide `QuantileTransformer` are not reused.
- **M3** is fitted as a continuous covariate. **No cut-point is searched**, at
  any stage, on any cohort.

### 3.2 Primary estimand

> The paired difference in out-of-fold discrimination between **M5** and **M1**
> on Cohort A.

One primary test. No minimum improvement is assumed; a well-powered null result
is a reportable outcome.

---

## 4. E-008 — outcome-blind entropy comparator

Run and freeze **before** §5.3.

- **Input:** all 30,007 H&E patches, `DLBCL-Morph/Patches/HE/<patient>/<patch>.png`.
- **Per patch:** convert RGB → grayscale (ITU-R 601-2 luma), quantise to 256
  levels, compute Shannon entropy in bits over the intensity histogram of the
  whole patch. No tissue masking — this deliberately reproduces the "global
  grayscale entropy" comparator rather than improving on it.
- **Eligibility:** the frozen E-006 tissue rule. Patches with
  `tissue_fraction < 0.50` are excluded from patient aggregation and recorded.
- **Patient aggregation:** `mean` (matches Carreras et al. exactly) plus
  `median, iqr, p10, p90` (matches this project's distribution-aware style) → 5
  features.
- **Output:** `reports/phase_03b_entropy_features.csv` (170 rows) plus a
  SHA-256 manifest and a run summary. Gate: 170 rows, 100% finite, patch counts
  reconcile exactly with `patch_qc.csv`.

The `mean` column is M3's primary covariate; the other four are a pre-specified
secondary elaboration reported alongside it.

---

## 5. Validation design

### 5.1 Structure

Repeated **nested** patient-level cross-validation.

| Parameter | Value |
|---|---|
| Outer folds | 5 |
| Outer repeats | 10 (→ 50 outer fits per model) |
| Inner folds | 5 (hyperparameter tuning only) |
| Stratification | OS event indicator, outer and inner |
| Seed | `20260830` |
| Unit | patient (no patch ever crosses a split) |

No locked hold-out test set: ~12 events in a 20% split is too unstable
(risk R-001, resolved 2026-08-23). This is an **internal** estimate and must
never be described as external or clinical validation.

### 5.2 Power reality — stated up front

Cohort A has 58 events. An outer training fold carries ≈46 events against up to
61 candidate features in M5 → **events per variable ≈ 0.8**. This is far below
the conventional 10 EPV heuristic and is precisely why:

- penalised Cox is the primary learner, not unpenalised Cox;
- fold-internal redundancy pruning is mandatory (§6.2);
- calibration is a rejection criterion, not a footnote (§7.3); and
- the analysis is powered to detect a *large* increment, not a subtle one.

This limitation is reported in the manuscript regardless of the result.

### 5.3 Split generation (Step S2 — blindness ends here)

`src/analysis/build_split_ids.py` reads **only** `patient_id` and
`Follow-up Status`, and writes `data/manifests/split_ids.csv` with columns:

```
patient_id, repeat, outer_fold
```

Stratification on the event indicator is pre-specified here (per the 2026-08-30
decision) because unstratified folds would swing fold event counts badly at
n=58. The generator is deterministic given the seed; its output is hashed and
frozen, and **every** model in §3 consumes this one file.

---

## 6. Fold-internal pipeline

Everything below is fitted **inside each outer training fold** and applied
unchanged to the held-out fold. Nothing is fitted on pooled data.

### 6.1 Imputation

Median for continuous, mode for categorical, computed on the training fold.
Affects only M1 (`LDH` 4 missing, `EN` 2 missing across 209; fewer in Cohort A).
E-007 features are 100% finite and require no imputation.

### 6.2 Redundancy pruning

E-007 contains 39 highly correlated feature pairs (O-046). Within each training
fold, compute Spearman |ρ|; for any cluster with |ρ| > 0.90, retain the single
column appearing **first in the frozen family order of §2** (F0 → F1a → F1b →
F2, then the column order of `feature_schema.json`). This tie-break is
deterministic and pre-specified, so it cannot be tuned.

**Scope (clarified 2026-09-01, before outcome access).** This rule applies to
**every model in the ladder**, not only to those built from E-007 features. The
§2 family order does not cover the entropy family, so the frozen tie-break order
for M3 is its §4 declaration order:

```
entropy_mean → entropy_median → entropy_iqr → entropy_p10 → entropy_p90
```

The E-008 diagnostics (`reports/phase_03b_e008_entropy.md` §5) measured
`entropy_mean` vs `entropy_median` at ρ = +0.968, above threshold, so
`entropy_median` is pruned in favour of `entropy_mean`; `p10` and `p90` survive
at ρ < 0.90. M3 therefore carries 4 effective covariates. Applying the rule
uniformly avoids handing M3 a collinearity handicap that M4c does not carry,
which would make the paired comparison uneven.

This was settled while the outcome was still unread, and is deterministic.

### 6.3 Scaling

`StandardScaler` fitted on the training fold. Not `QuantileTransformer` — the
E-002 use of a dataset-wide quantile transform was a *deliberate reproduction of
a legacy quirk* and is not carried into our own models.

### 6.4 Learners

**Primary — penalised Cox** (`sksurv.linear_model.CoxnetSurvivalAnalysis`):

| Hyperparameter | Grid |
|---|---|
| `l1_ratio` | {0.1, 0.5, 0.9, 1.0} |
| `alpha` | 20-point log path, auto-derived per fold |

**Secondary — Random Survival Forest** (`sksurv.ensemble.RandomSurvivalForest`),
a fixed nonlinear ablation, **not** a route to unconstrained searching:

| Hyperparameter | Grid |
|---|---|
| `n_estimators` | 500 (fixed) |
| `min_samples_leaf` | {5, 10, 20} |
| `max_features` | {"sqrt", 0.33} |

Inner-fold selection criterion: mean Harrell C-index across inner folds.

> **Kaggle dependency:** `scikit-survival` must be explicitly installed and
> version-pinned in the E-009 notebook, and the pinned version recorded in
> `environment.json`. It is not in the default Kaggle image.

---

## 7. Metrics

### 7.1 Discrimination

- **Harrell C-index** — primary, for comparability with the published 0.635 / 0.674 / 0.700.
- **Uno C-index** — censoring-robust confirmation, truncated at 5 years.
- **Time-dependent cumulative/dynamic AUC** at 2, 3, 5 years (primary) and
  1 year (exploratory — too few events for a stable estimate).

### 7.2 Calibration and overall accuracy

- **Integrated Brier score** over [0.25, 5.0] years.
- **Calibration slope and intercept** at each horizon, with calibration plots.

### 7.3 Calibration as a rejection criterion

A model with higher discrimination but a calibration slope outside [0.7, 1.3]
does **not** supersede a well-calibrated competitor. This rule is fixed now so
it cannot be relaxed after seeing which model wins.

### 7.4 Uncertainty

1,000 **patient-level paired** bootstrap resamples of the pooled out-of-fold
predictions; 95% percentile intervals for every metric and every paired
difference. Because pairs are resampled jointly, the ΔC interval respects the
correlation between models.

### 7.5 Kaplan–Meier presentation

Risk tertiles, with cut-points derived **inside training folds only** and
applied to held-out patients. No full-cohort threshold search — this is the
exact methodological weakness identified in the July 2026 entropy paper.

---

## 8. Multiplicity

| Family | Members | Adjustment |
|---|---|---|
| **Primary** | M5 vs M1 | none — single pre-specified test |
| Secondary ladder | M4a/M4b/M4c/M3/M2/M0 vs M1 | Holm within family |
| Cohort sensitivity | B, C | descriptive, unadjusted |
| Ablations (§9) | as listed | descriptive, unadjusted |
| Phase 3D markers | HANS/CD10/BCL6/MUM1/MYC/BCL2/FISH | BH-FDR, labelled exploratory |

The complete table of every model fitted — including any that fail — is
published. Reporting only the best C-index is explicitly listed in the novelty
landscape as an invalidating practice.

---

## 9. Pre-specified sensitivity analyses

| ID | Analysis | Purpose |
|---|---|---|
| S1 | Cohort B (n=169) | Effect of the one FAIL panel |
| S2 | Cohort C (n=168) | Effect of both QC outliers |
| S3 | M5 + F0 as adjustment covariates | Does sampling exposure explain any gain? |
| S4 | M4c without F1b (stain) | Stain/batch confounding |
| S5 | M2 without the 8 positional columns | Location is not shape |
| S6 | RSF in place of penalised Cox | Nonlinearity |
| S7 | Spread-only vs central-only feature views | Hypotheses 1 and 3 |

---

## 10. Reporting

Deliverables for E-009:

- `reports/phase_03c_model_ladder_results.md` — full ladder, all metrics, all CIs
- `reports/phase_03c_results_tables/` — machine-readable per-model metrics
- Calibration plots, KM curves, out-of-fold prediction dumps
- Seeds, split hash, environment lockfile, config hash for every fit

Language rules, carried from the novelty landscape:

- "nuclear pleomorphism", "cellular packing", "within-patch spatial organization"
- **never** tumour–immune mixing, immune phenotype, or spatial-omics surrogate
- **never** external or clinical validation
- results stay **internal/exploratory** until the independent expert audit
  (`reports/phase_03_e007_expert_priority_subset.csv`) is recorded

---

## 11. Stopping and integrity rules

1. Feature families (§2) and the ladder (§3) do not change after outcome access.
2. Segmentation is **never** retuned against outcomes. Expert disagreement
   activates a frozen sensitivity branch — never a re-extraction.
3. No cut-point is optimised on the full cohort, for entropy or risk.
4. If the join does not reproduce 170/170/∅, abort and investigate.
5. If a result looks strong, the response is §9 and the expert audit — not a
   faster path to writing.

---

## 12. Amendment log

| Date | §  | Change | Rationale | Made by | Before results seen? |
|---|---|---|---|---|---|
| — | — | none | — | — | — |

---

## 13. Sign-off

Signing freezes §§1–11 and authorises E-008, then Step S2, then E-009.

| Role | Name | Date | Protocol SHA-256 |
|---|---|---|---|
| Researcher | Kawser Sikder | 2026-09-01 | 94c9a6ef3a3a75ef2dfde58b7fa8e64ace8d664d5938313921d3a178465c2221 |
| Reviewer (optional) | | | |

**Signed 2026-09-01.** §§1–11 are frozen. Any subsequent change is an amendment,
must be recorded in §12 before the affected results are inspected, and will
change the lock hash — causing `src/analysis/build_split_ids.py` to abort until
the amendment is re-signed.

Entered by an LLM on 2026-09-01 at the explicit instruction of Kawser Sikder.
