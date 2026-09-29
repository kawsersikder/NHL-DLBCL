# Phase 3C — survival model ladder results (E-009)

**Run date:** 2026-09-01
**Protocol:** Phase 3B v1.1, signed 2026-09-01 by Kawser Sikder, lock hash `94c9a6ef…`
**Cohort:** A (n=170, 58 OS events) unless stated
**Status:** complete — every model and every pre-specified sensitivity has been run

> **Scope.** These are **internal exploratory** results. They are not external
> validation, not clinical validation, and they do not support any pathology
> claim. Independent haematopathology review (R-003) is deliberately deferred
> and remains a pre-publication gate.

---

## 1. Headline

**The image features do not add prognostic value beyond the clinical model.**

> Primary estimand (§3.2): paired difference in out-of-fold Harrell C between
> **M5** (clinical + image) and **M1** (clinical alone), Cohort A.
>
> **ΔC = −0.0231, 95% CI [−0.0499, +0.0008]. The interval includes zero.**

The point estimate is negative: adding 56 image features to a 5-covariate
clinical model made discrimination slightly *worse*. At 46 training events
against up to 61 candidate features (EPV ≈ 0.8), this is the expected behaviour
of a model given more parameters than the data can support.

This is a pre-registered null result on a single pre-specified test. No
adjustment for multiplicity is applied to it, and none is needed.

## 2. The full ladder

Cohort A, penalised Cox, pooled out-of-fold predictions, 1,000-resample
patient-level paired bootstrap.

| Model | Role | k | kept | Harrell C [95% CI] | Uno C | IBS | Calib. slope | Calib. OK |
|---|---|---:|---:|---|---:|---:|---:|:--:|
| **M1** | **Clinical Cox** | 5 | 5 | **0.706 [0.623, 0.777]** | 0.738 | 0.091 | 0.82 | ✅ |
| **M5** | **Clinical + image** | 61 | 27 | **0.683 [0.600, 0.756]** | 0.709 | **0.088** | 0.94 | ✅ |
| M0a | IPI score | 1 | 1 | 0.637 [0.558, 0.706] | 0.701 | 0.094 | 0.46 | ❌ |
| M4b | Packing only | 16 | 8 | 0.589 [0.505, 0.669] | 0.591 | 0.099 | 0.38 | ❌ |
| M4c | Image (primary) | 56 | 22 | 0.579 [0.497, 0.666] | 0.574 | 0.095 | 0.65 | ❌ |
| M0b | R-IPI group | 1 | 1 | 0.573 [0.493, 0.645] | 0.613 | 0.098 | 0.41 | ❌ |
| M2 | Released geometry | 44 | 17 | 0.521 [0.435, 0.605] | 0.543 | 0.101 | 0.00 | ❌ |
| M4a | Morphology only | 40 | 14 | 0.497 [0.421, 0.576] | 0.533 | 0.101 | −0.07 | ❌ |
| M3 | Global entropy | 5 | 4 | 0.456 [0.376, 0.539] | 0.433 | 0.105 | −0.02 | ❌ |

`kept` is the median number of columns surviving fold-internal redundancy
pruning (§6.2). Note how aggressively it bites: M4a declares 40 features and
retains 14.

### Paired differences vs M1 (Holm-adjusted family, §8)

| Comparison | ΔC | 95% CI | Excludes zero |
|---|---:|---|:--:|
| **M5 − M1** | **−0.023** | [−0.050, +0.001] | **no** |
| M0a − M1 | −0.071 | [−0.137, −0.013] | yes |
| M4b − M1 | −0.119 | [−0.224, −0.002] | yes |
| M4c − M1 | −0.127 | [−0.239, −0.015] | yes |
| M0b − M1 | −0.135 | [−0.208, −0.069] | yes |
| M2 − M1 | −0.187 | [−0.297, −0.062] | yes |
| M4a − M1 | −0.209 | [−0.303, −0.110] | yes |
| M3 − M1 | −0.251 | [−0.363, −0.147] | yes |

**Every** image-based model is significantly worse than clinical covariates
alone. M5 is the only model whose difference from M1 is not distinguishable
from zero — and its point estimate is on the wrong side.

### Time-dependent AUC

| Model | 1y* | 2y | 3y | 5y |
|---|---:|---:|---:|---:|
| M1 | — | 0.702 | 0.774 | 0.759 |
| M5 | — | 0.675 | 0.764 | 0.723 |
| M4c | — | 0.577 | 0.608 | 0.576 |
| M3 | — | 0.434 | 0.440 | 0.427 |

\* 1-year AUC was pre-specified as exploratory (too few events for stability)
and is not interpreted.

## 3. Calibration

Only **M1 and M5** satisfy the §7.3 criterion of a calibration slope inside
[0.7, 1.3]. Every image-only model is severely miscalibrated — M2, M3 and M4a
have slopes at or below zero, meaning their risk ordering carries essentially no
usable information about outcome magnitude.

This rule was fixed before any result was seen precisely so it could not be
relaxed afterwards. It disqualifies the image-only models on calibration grounds
independently of their discrimination.

**One genuine nuance:** M5 is *better* calibrated than M1 (slope 0.94 vs 0.82)
and has the best integrated Brier score in the ladder (0.088 vs 0.091). So the
image features are not pure noise — they contribute slightly to overall
predictive accuracy while slightly degrading rank discrimination. This is a real
observation and it is reported as such. It is **not** a rescue of the primary
result and must not be presented as one.

### 3.1 Calibration plots

`reports/phase_03c_figures/calibration_cohortA.png` — observed Kaplan–Meier
survival against mean predicted survival, by quintile of predicted risk, at 2,
3 and 5 years, for M1, M4c and M5.

M1 and M5 track the diagonal at 3 and 5 years. **M4c's 5-year panel is close to
horizontal**: predicted survival varies across quintiles while observed survival
does not. That is what an absence of discrimination looks like, and it is a more
direct picture of the finding than the C-index alone.

Note the axes are zoomed to roughly [0.4, 1.0]. With 58 events in 170 patients,
no patient group has predicted 5-year survival below ~0.55, so a full 0–1 axis
would compress every point into one corner.

### 3.2 Kaplan–Meier by held-out risk tertile

`reports/phase_03c_figures/kaplan_meier_tertiles_cohortA.png`

Tertile cut-points were derived **inside each training fold** and applied to
held-out patients (§7.5); each patient's group is the modal assignment across
the 10 repeats. No patient's own outcome informed its risk group, and no
cut-point was searched on the full cohort — the specific weakness identified in
the July 2026 entropy paper.

| Model | Log-rank p | Reading |
|---|---:|---|
| M1 | 1.3 × 10⁻⁷ | Clear three-way separation; high-risk tertile reaches ~0.58 at 5 years |
| M5 | 2.5 × 10⁻⁵ | Separates, but less cleanly than M1 |
| M4c | 0.096 | **Does not separate** |

The image-only model fails to stratify patients into distinguishable risk groups
at conventional significance. M5 separates, but its p-value is two orders of
magnitude weaker than M1's — consistent with the primary estimand, where adding
image features slightly degraded discrimination.

## 4. Sensitivity analyses (§9)

### S1 / S2 — QC-outlier cohorts

| Cohort | n | ΔC (M5 − M1) | 95% CI |
|---|---:|---:|---|
| A (primary) | 170 | −0.0231 | [−0.0499, +0.0008] |
| B (drops 26807) | 169 | −0.0106 | [−0.0465, +0.0233] |
| C (drops 26807, 13957) | 168 | −0.0019 | [−0.0288, +0.0277] |

The conclusion does not depend on the QC outliers. Removing them moves ΔC
*toward* zero, so the mildly negative estimate in Cohort A was partly driven by
them. All three intervals include zero.

**Important correction.** M3's below-chance performance in Cohort A (0.456) is
**not robust**: it rises to 0.507 in B and 0.497 in C. Removing patient 26807
alone — the cohort's lowest-entropy patient — moves entropy from below-chance to
chance. The defensible claim is that **global entropy carries no prognostic
signal in this cohort**, not that it is anti-predictive. Any stronger statement
would be an artifact of one QC-outlier patient.

### S3–S7 — model variants (Cohort A)

| ID | Variant | Harrell C [95% CI] | Reference | Reading |
|---|---|---|---|---|
| S3 | M5 + F0 exposure covariates | 0.685 [0.598, 0.760] | M5 0.683 | Sampling exposure explains nothing; the F0 exclusion was sound |
| S4 | M4c without stain (F1b) | 0.554 [0.478, 0.636] | M4c 0.579 | Stain carried part of M4c's weak signal — a caution, since stain confounds with batch/scanner |
| S5 | M2 without positional columns | 0.531 [0.443, 0.612] | M2 0.521 | The 8 positional columns were not doing the work; M2's collapse needs another explanation |
| S7 | Central tendency only | 0.510 [0.430, 0.587] | — | Medians alone are uninformative |
| S7 | Spread / heterogeneity only | 0.554 [0.466, 0.641] | — | Spread > central, but the CI includes 0.5 |

**On S7.** Spread-only (0.554) outperforms central-only (0.510), which is
directionally consistent with the project's heterogeneity hypothesis and is the
only result in the ladder pointing that way. But the spread interval includes
0.5 and the gap is well within noise at this sample size. This is
**hypothesis-generating, not evidence**, and presenting it as support for the
distribution-tail thesis would be exactly the over-reading this protocol exists
to prevent.

## 5. A reproducibility finding

**M2, the reproduced published geometric baseline, achieves C = 0.521
[0.435, 0.605] — barely above chance.** The published figure for the comparable
model is ≈0.674.

Our implementation differs from the original in two ways documented in protocol
§3.1 before any result was seen:

1. **Fold-safe fitting.** Nested CV with all preprocessing inside training
   folds, versus the original in-sample fit.
2. **No dataset-wide `QuantileTransformer`.** The original applied a quantile
   transform fitted across the entire dataset, which leaks test-fold
   distributional information into training.

Cohort size also differs (170 image-eligible vs 209), so this is **not a
like-for-like refutation** and should not be written as one. But the direction
and magnitude are large, the mechanism is identifiable, and S5 rules out the
positional columns as the explanation.

Combined with E-003 — a released, published segmentation checkpoint that loads
with 798/798 tensors and still produces Dice 0.28 on its own source data — this
project now carries two independent, well-evidenced reproducibility findings in
the DLBCL computational-pathology literature.

## 6. Interpretation

1. **Clinical covariates remain the strongest predictor.** M1 at 0.706 exceeds
   the published clinical figures (0.635 / 0.674 / 0.700) and is well
   calibrated.
2. **Nuclear morphology distributions carry no detectable prognostic signal
   here.** M4a sits at chance (0.497).
3. **Local packing is the only image family above noise** (M4b, 0.589) — yet
   still significantly worse than clinical alone and badly miscalibrated.
4. **Global entropy carries no signal** (see the §4 correction).
5. **The null is robust** across three cohorts, four feature views, two
   learners, and five pre-specified variants.

### Why this is a contribution

The comparison literature contains a two-year-mortality CNN and an entropy paper
with a same-cohort optimised cut-point and no validation cohort. Against that,
a pre-registered, properly censored, calibration-checked, nested-CV null with a
frozen protocol and a published complete model table says something true that
has not been said clearly. A well-powered null is a result.

### What this does not show

This does not show that H&E morphology is uninformative in DLBCL. It shows that
*these* features, extracted *this* way, at *this* sample size, do not improve on
IPI components for OS in *this* cohort. With 58 events the analysis was powered
to detect a large increment, not a subtle one — as stated in §5.2 before any
outcome was read.

## 7. S6 — nonlinear learner

Random Survival Forest, 500 trees, tuned over `min_samples_leaf` ∈ {5, 10, 20}
and `max_features` ∈ {sqrt, 0.33}. Run on Kaggle; see §7.1.

| Model | Coxnet C | RSF C [95% CI] | RSF calib. | ΔC vs M1 |
|---|---:|---|---:|---|
| M1 | 0.706 | 0.676 [0.595, 0.744] | 0.66 ❌ | −0.031 [−0.066, +0.004] |
| M4c | 0.579 | 0.554 [0.468, 0.636] | 0.25 ❌ | −0.152 [−0.257, −0.044] |
| M5 | 0.683 | 0.646 [0.559, 0.726] | 0.70 ✅ | −0.062 [−0.138, +0.009] |

RSF is worse than penalised Cox on **every** model, and RSF-M1 additionally
fails the §7.3 calibration criterion that Coxnet-M1 passes. This is the expected
direction at 46 training events — a forest needs more data than this to beat a
well-regularised linear model.

**Nonlinearity does not rescue the result.** The image features remain
uninformative under a learner explicitly chosen to capture interactions and
non-monotone effects that penalised Cox cannot.

### 7.1 Cross-environment reproduction

S6 was run on Kaggle after two local attempts failed — first a joblib/loky
process-pool deadlock on Windows, then a silent process death at 47/50 folds.
The Kaggle notebook re-fits the **entire** ladder, not only the RSF models, so it
doubles as an independent reproduction check.

| | Local | Kaggle |
|---|---|---|
| Python | 3.13.9 | 3.12.13 |
| numpy | 2.3.5 | 2.0.2 |
| OS | Windows 10 | Linux container |
| scikit-learn / scikit-survival | 1.9.0 / 0.28.0 | 1.9.0 / 0.28.0 |

Across 9 models × 7 metrics (Harrell C, Uno C, IBS, calibration slope, and AUC
at 2/3/5 years), the **maximum absolute difference was 1.8 × 10⁻¹⁴** — floating
point noise. Every reported value is identical to well beyond the precision at
which it is quoted.

That is a stronger reproducibility claim than same-machine determinism: the
analysis reproduces across operating systems, Python versions, and numpy
versions. Chain of custody also verified on Kaggle
(`protocol_unchanged_since_splits: true`).

> **Artifact history, recorded for honesty.** The first S6 run completed locally
> but its outputs were destroyed by a filename collision — all Cohort A variants
> initially wrote to identical names and the last writer won, leaving a file
> that looked like the primary result but contained the RSF variant. The bug is
> fixed; each variant now carries its own suffix. The values in this table come
> from the Kaggle run and match the destroyed run exactly.

## 8. Artifacts

| File | Contents |
|---|---|
| `model_ladder_cohortA.csv` | 9 primary models, all metrics |
| `model_ladder_cohortA_sens.csv` | + S3/S4/S5/S7 |
| `model_ladder_cohortB.csv` | S1, n=169 |
| `model_ladder_cohortC.csv` | S2, n=168 |
| `model_ladder_cohortA_rsf.csv` | S6, run on Kaggle |
| `paired_differences_*.csv` | bootstrap ΔC vs M1 |
| `oof_predictions_*.csv` | pooled out-of-fold risk per patient |
| `hyperparameters_*.csv` | per-fold chosen α, l1_ratio, features kept |
| `pooled_survival_*.npz` | out-of-fold S(t) on the 50-point grid, per model |
| `run_summary_*.json` | hashes, seeds, environment, chain of custody |
| `phase_03c_figures/calibration_cohortA.png` | calibration, 3 models × 3 horizons |
| `phase_03c_figures/kaplan_meier_tertiles_cohortA.png` | OS by held-out risk tertile |

Figures are regenerated from the frozen out-of-fold predictions by
`src/analysis/make_phase3c_figures.py`; nothing is refitted.

Every run records `protocol_unchanged_since_splits: true`, confirming the
protocol has not moved since the folds were frozen.

**Environment:** Python 3.13.9, numpy 2.3.5, pandas 2.3.3, scikit-learn 1.9.0,
scikit-survival 0.28.0. Seed 20260830 throughout. Re-running the primary
analysis reproduced all values to four decimal places.

## 9. Limitations

- 58 events; EPV ≈ 0.8 for M5. Powered for a large increment only.
- Internal nested CV, not external validation. No held-out test set — ~12 events
  in a 20% split is too unstable (R-001).
- Segmentation is an all-nucleus binary branch with patch-local pixel
  coordinates. No tumour/non-tumour phenotyping, no physical units, no
  cross-patch spatial structure.
- Features are provisional pending independent pathology review (R-003).
- TMA cores, not whole slides — a small, possibly unrepresentative tissue
  sample per patient.
- OS only. PFS is not analysable: the table has PFS times but no progression
  indicator.
