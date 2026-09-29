# Phase 4 — Cell-of-origin from H&E: Statistical Analysis Protocol

**Protocol version:** 1.0 (DRAFT — unsigned)
**Written:** 2026-09-03
**Machine-readable twin:** `configs/phase_04_coo_analysis_protocol.yaml`
**Scope document:** `reports/phase_04_coo_study_scope.md`
**Status:** awaiting sign-off. **No feature–label relationship has been examined.**

---

## 0. Purpose and binding scope

This protocol fixes every analytical choice for the cell-of-origin study before
any model is fitted. Once signed it is hash-locked; later changes are amendments
recorded in §12 **before** the affected results are inspected.

It governs experiments **E-010** (internal ladder) and **E-011** (external
validation).

### 0.1 Label-blindness declaration

Label counts, class balance, and the encoding audit (§1.3) have been computed —
these are required to design the study. **No relationship between any image
feature and the COO label has been examined.** Blindness ends at split
generation (§5.3), which reads `patient_id` and `HANS` only.

### 0.2 Precondition

The Phase 3C survival preprint must be posted before E-010 begins. This study is
not a substitute for that result and must not delay it.

---

## 1. Data, cohorts, and label

### 1.1 Inputs

| Input | Path |
|---|---|
| Image features | `kaggle/.../output_e007_full_extraction/patient_features.csv` |
| H&E patches | `DLBCL-Morph/Patches/HE/<patient>/<patch>.png` (30,007) |
| Clinical / label | `data/raw/dlbcl_morph/clinical_data_cleaned.csv` |
| Released geometry | `data/raw/dlbcl_morph/cell_shapes.csv` |

### 1.2 Endpoint

**Cell of origin, binary: GCB vs non-GCB**, from the released `HANS` column.

### 1.3 Label encoding — established empirically

Verified 2026-09-03 by `src/analysis/verify_hans_encoding.py`:

> **`HANS = 1` → GCB.  `HANS = 0` → non-GCB.**
> Concordance with the reconstructed Hans decision tree: **172/174 (98.9%)**.

The audit also established the component scales, which the released data
dictionary describes incorrectly:

| Column | Actual scale | Positivity rule |
|---|---|---|
| CD10 IHC | **binary {0,1}** | `> 0` |
| BCL6 IHC | percent, 0–90 by 10 | **`>= 30%`** |
| MUM1 IHC | **binary {0,1}** | `> 0` |

A BCL6 cut-off sweep from 0% to 100% peaks exactly at 30%, the canonical Hans
threshold — independent confirmation that the released label follows the
published rule. Applying a 30% threshold to all three columns, as the data
dictionary implies, drops concordance to 74.7%; that reading is **prohibited**.

### 1.4 Label noise — stated before modelling

Two ceilings apply, and both are reported regardless of result:

1. **Internal (1.1%).** Patients 26804 and 26836 are CD10−/BCL6+/MUM1−, which the
   published rule calls GCB, but are labelled non-GCB. No cut-off resolves them
   without breaking others, so they are scorer judgement. They are **not
   corrected**; 26804 is in the image cohort and is dropped only in the D_COO
   sensitivity.
2. **Label-definition (~15–20%).** Hans IHC is a proxy for gene-expression COO,
   with commonly cited concordance of 80–85%. An AUROC of 0.85 against Hans
   labels is **not** an AUROC of 0.85 against true COO. Every reported figure is
   against Hans labels and must be described that way.

### 1.5 Cohorts (frozen)

163 of the 170 image-eligible patients carry a HANS label (95.9%).

| Cohort | n | GCB | non-GCB | Definition | Role |
|---|---:|---:|---:|---|---|
| **A_COO** | **163** | **70 (42.9%)** | **93 (57.1%)** | All labelled image-eligible | **Primary** |
| B_COO | 162 | 70 | 92 | − 26807 (QC FAIL panel) | Sensitivity |
| C_COO | 161 | 70 | 91 | − 26807, 13957 | Sensitivity |
| D_COO | 162 | 70 | 92 | − 26804 (Hans-discordant) | Sensitivity |

All excluded patients are non-GCB, so the minority class is **70 in every
cohort**. Cohort A carries all conclusions.

Recomputing HANS from components does not extend coverage: every patient with
all three stains already has a label. The released column is used as-is.

---

## 2. Representations

### 2.1 Handcrafted (reused, already frozen)

The E-007 partition from Phase 3B §2 is reused **unchanged**: F0 (9, excluded),
F1a shape (28), F1b stain (12), F2 packing (16). The F0 exclusion rationale
carries over — these measure sampling exposure, not biology.

### 2.2 Foundation-model embeddings

Patch embeddings from a **frozen, pretrained** encoder, aggregated by
attention-based multiple-instance learning (ABMIL).

| Choice | Value | Reason |
|---|---|---|
| Primary encoder | **H-optimus-0** (`bioptimus/H-optimus-0`) | Apache 2.0, ungated, giga-scale, runs on a T4 |
| Secondary encoder | **Phikon-v2** (`owkin/phikon-v2`) | Ungated, ViT-L, comfortable on a T4 |
| Aggregator | ABMIL | Appropriate for ~177 instances/patient |
| Prohibited | TransMIL, HIPT | Assume whole-slide spatial hierarchies TMA cores lack |

Both encoders are pre-specified now so that neither can be chosen after seeing
results. The primary estimand uses **H-optimus-0 only**.

**Embedding extraction runs once, outside the cross-validation loop. This is not
leakage:** the encoder is frozen, was pretrained on unrelated data, and never
sees a COO label. Only the ABMIL head is fitted inside training folds.

---

## 3. Model ladder

| ID | Model | Input | Role |
|---|---|---|---|
| **C0** | Clinical logistic | Age, ECOG PS, LDH, EN, Stage | **Negative control** |
| C1 | Handcrafted morphology | F1 ∪ F2 (56) | Cheap comparator; runs first |
| C2 | Released geometry | `cell_shapes.csv` mean+SD (44) | Literature comparator |
| **C3** | **H-optimus-0 + ABMIL** | frozen embeddings | **Primary image model** |
| C3b | Phikon-v2 + ABMIL | frozen embeddings | Secondary encoder |
| C4 | Fusion | C1 ∪ C3 risk score | Does handcrafted add to learned? |

**C0 is a falsification check, not a hypothesis.** COO should not be predictable
from systemic clinical variables. If C0 achieves AUROC ≥ 0.65, the design is
compromised — investigate before interpreting anything else.

**Execution order.** C0–C2 run first (no GPU). Seeing their results does **not**
license any change to C3, whose specification is frozen here.

### 3.1 Primary estimand

> **E1 — Out-of-fold AUROC of C3 on Cohort A_COO, tested against the null of
> 0.5.** Signal is declared present if the 95% patient-level bootstrap lower
> bound exceeds 0.5.

### 3.2 Key secondary estimand

> **E2 — AUROC of the locked C3 model on the external TCGA-DLBC cohort (§4).**

E2 is the study's contribution. E1 establishes only that the signal exists
in-domain; E2 tests whether it transfers, which no published work has done.

---

## 4. External validation (E-011)

### 4.1 Cohort and label

TCGA-DLBC: diagnostic H&E whole-slide images, open access from the GDC portal
(≈48 patients). COO is not distributed as a label and is **derived from RNA-seq**
using a published gene-expression classifier, specified in the amendment that
accompanies the E-011 run.

This creates a **label-definition mismatch**: training on Hans IHC, testing
against gene-expression COO. The mismatch is stated in every report of E2 and is
not a defect to hide — GEP is the reference standard, so E2 is arguably the
harder and more meaningful test.

### 4.2 Feasibility gate

E-011 proceeds only if **all** hold:

1. ≥ 40 patients with a usable diagnostic H&E slide **and** a derived COO label;
2. derived class balance no more extreme than 80/20; and
3. the derivation method is fixed and documented **before** any image is scored.

If the gate fails, that is reported as a finding — public external COO
validation data for DLBCL does not exist — and E2 is marked not evaluable.

### 4.3 Domain-shift handling

TCGA-DLBC is whole-slide; DLBCL-Morph is TMA cores. Pre-specified:

- tile at the same pixel patch size as DLBCL-Morph patches, matching
  microns-per-pixel where scanner metadata permits; record any mismatch;
- apply the frozen E-006 tissue rule (`tissue_fraction >= 0.50`);
- sample patches per patient to approximate the DLBCL-Morph median (~177),
  with the sampling seed fixed; and
- apply **no** stain normalisation in the primary analysis, with a
  normalisation variant as sensitivity S_ext.

### 4.4 Single-use rule

The external cohort is scored **once**, with the internal model fully locked. No
hyperparameter, threshold, or preprocessing choice may be revised after any
external number is seen. Any revision voids E2, which must then be reported as
exploratory.

### 4.5 Early-stopping rule

If **both** C1 and C3 have an internal AUROC upper bound below 0.65 on Cohort A,
E-011 is **optional**. Validating a model with no in-domain signal wastes weeks;
the internal null is reported instead.

---

## 5. Validation design

| Parameter | Value |
|---|---|
| Design | Repeated nested cross-validation |
| Outer folds / repeats | 5 × 10 (50 outer fits) |
| Inner folds | 5 (tuning only) |
| Stratification | **HANS label** (outer and inner) |
| Seed | `20260903` |
| Unit | patient |
| Split file | `data/manifests/coo_split_ids.csv` |

Splits are generated fresh; the Phase 3B survival splits are **not** reused —
different stratification variable, different cohort size. The generator reads
`patient_id` and `HANS` only, and aborts if the protocol hash has changed.

### 5.1 Power

Cohort A: 163 patients, minority class 70, ≈14 minority per held-out fold. At
AUROC 0.80 the approximate 95% CI half-width is **≈0.07**. This is adequate to
separate signal from chance and to detect gross external failure; it is **not**
adequate to estimate the ceiling precisely, or to resolve differences between
encoders of less than ~0.10.

External (n≈48): CI half-width ≈0.14. E2 can detect gross failure only. This is
stated in advance and is not a reason to over-read a favourable point estimate.

---

## 6. Fold-internal pipeline

Fitted inside each training fold, applied unchanged to held-out data:
**impute → prune → scale → fit**.

- **Imputation:** median (continuous) / mode (categorical). Affects C0 only;
  E-007 features are 100% finite.
- **Redundancy pruning:** Spearman |ρ| > 0.90, deterministic tie-break by the
  frozen family order F0 → F1a → F1b → F2, then `feature_schema.json` column
  order. Applies to C0–C2 and C4; not to raw embeddings.
- **Scaling:** `StandardScaler`.
- **Class imbalance:** 57/43 is mild; **no resampling or class weighting** in the
  primary analysis. A `class_weight="balanced"` variant is sensitivity S4_COO.

### 6.1 Learners

**C0, C1, C2, C4 — penalised logistic regression** (elastic net):
`l1_ratio ∈ {0.1, 0.5, 0.9, 1.0}`; `C` over a 20-point log grid.

**C3, C3b — ABMIL**, fixed architecture, bounded grid:

| Hyperparameter | Grid |
|---|---|
| Attention hidden dim | {128, 256} |
| Dropout | {0.25, 0.5} |
| Learning rate | {1e-4, 1e-3} |
| Weight decay | 1e-4 (fixed) |
| Max epochs | 50, early stopping patience 10 on inner-fold AUROC |
| Loss | Binary cross-entropy |

Inner-fold selection criterion: mean AUROC. The grid is deliberately small; it
may not be expanded after seeing results.

---

## 7. Metrics

**Discrimination:** AUROC (primary), AUPRC, balanced accuracy at 0.5.

**Triage operating points** — the clinically motivated framing (scope §3):
sensitivity at 90% specificity, and specificity at 90% sensitivity. **Thresholds
are derived inside training folds only** and applied to held-out patients. No
full-cohort threshold search, at any stage.

**Calibration:** slope and intercept, plus calibration curves.

> **Rejection criterion.** A model with higher AUROC but a calibration slope
> outside **[0.7, 1.3]** does not supersede a well-calibrated competitor. Fixed
> now so it cannot be relaxed once the winner is known.

**Uncertainty:** 1,000 patient-level bootstrap resamples; percentile 95% CIs for
every metric and every paired difference.

---

## 8. Multiplicity

| Family | Members | Adjustment |
|---|---|---|
| **Primary** | E1 (C3 vs 0.5) | none — single pre-specified test |
| Key secondary | E2 (external) | none — single test, reported with its CI |
| Secondary ladder | C1, C2, C3b, C4 vs 0.5 | Holm within family |
| Negative control | C0 | not a hypothesis test |
| Sensitivities | §9 | descriptive, unadjusted |

**Every model fitted is reported, including those that fail.**

---

## 9. Sensitivity analyses

| ID | Analysis | Purpose |
|---|---|---|
| S1_COO | Cohort B (n=162) | Effect of the QC FAIL panel |
| S2_COO | Cohort C (n=161) | Effect of both QC outliers |
| S3_COO | Cohort D (n=162) | Effect of the Hans-discordant patient |
| S4_COO | `class_weight="balanced"` | Imbalance handling |
| S5_COO | C3 without F1b-equivalent colour cues (stain-normalised input) | Stain/batch confounding |
| S6_COO | C1 spread-only vs central-only | Reuses the Phase 3B feature views |
| S_ext | External with stain normalisation | Domain-shift mitigation |

---

## 10. Reporting

Deliverables: `reports/phase_04_coo_results.md`,
`reports/phase_04_coo_results_tables/`, calibration curves, ROC curves,
out-of-fold prediction dumps, per-fold hyperparameters, and for every fit the
seed, split hash, environment lockfile, and protocol hash.

**Language rules.**

- Report against **Hans IHC labels**, never as "cell of origin" without that
  qualifier.
- TCGA-DLBC is **domain generalisation**, never "external clinical validation."
- No claim that H&E replaces IHC. The motivated use is **triage where IHC is
  unavailable**.
- State both label-noise ceilings (§1.4) wherever an accuracy figure appears.

---

## 11. Integrity rules

1. Representations (§2) and the ladder (§3) do not change after label access.
2. The external cohort is scored once (§4.4).
3. The primary encoder is H-optimus-0. Reporting C3b instead because it scored
   higher is prohibited.
4. No threshold is optimised on a full cohort, internal or external.
5. The ABMIL grid may not be expanded post hoc.
6. Segmentation and feature extraction are **never** re-run against labels.
7. If a result looks strong, the response is §9 and E2 — not a faster write-up.

---

## 12. Amendment log

| Date | § | Change | Rationale | Made by | Before results seen? |
|---|---|---|---|---|---|
| — | — | none | — | — | — |

*The E-011 gene-expression COO derivation method (§4.1) will be added here as a
dated amendment before any TCGA image is scored.*

---

## 13. Sign-off

Signing freezes §§1–11 and authorises split generation, then E-010, then E-011.

| Role | Name | Date | Protocol SHA-256 |
|---|---|---|---|
| Researcher | | | |
| Supervisor (recommended) | | | |

**Unsigned. Do not generate splits or fit any model until this table is
completed.**
