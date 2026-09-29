# E-007 outcome-blind AI-assisted overlay QC

**Review date:** 2026-08-28  
**Scope:** one frozen representative overlay for each of 170 DLBCL-Morph H&E-eligible patients  
**Outcome access:** none  
**Reviewer:** LLM-assisted computational review; **not** a pathologist or haematopathologist

## Result

All 170 E-007 representative overlays were inspected using the H&E panel,
nucleus-probability panel, and predicted-instance contours. The review produced:

| AI-QC label | Patients | Meaning |
|---|---:|---|
| PASS | 130 | Technically usable representative panel; contours broadly follow visible nuclei and no dominant artifact is evident. |
| CAUTION | 39 | Usable for continued computational work, but the representative panel contains a material technical concern such as fibrous/elongated capture, sparse or partial tissue, low contrast, or merge/split ambiguity. |
| FAIL | 1 | The representative panel is not acceptable evidence of tumour-nuclear morphology. This does **not** by itself delete the patient. |

The per-patient record is
`reports/phase_03_e007_ai_overlay_review.csv`. The untouched 170-row sheet for
future independent review remains `reports/phase_03_e007_overlay_review.csv`.

The most frequent caution modes were fibrous capture (25 patients), elongated
objects (13), sparse tissue (13), and partial tissue (9). These counts overlap
because one panel can have more than one concern.

## Priority findings

### Patient 26807 — failed representative field

Patch 1771 is dominated by fibrous/spindle tissue and elongated fragmented
predictions. The panel is not a convincing tumour-nuclear field. Independent
outcome-blind quantitative QC supports treating this patient as the principal
technical sensitivity case:

- 35 available patches, at the 1.8th percentile of patient patch counts;
- median 27 predicted objects per patch, at the 0.6th percentile;
- median nuclear-foreground fraction 0.09, at the 0.6th percentile; and
- zero patches tripped the existing low-tissue rule because all tissue
  fractions remained at or above 0.50.

This exposes a limitation of the E-006 tissue rule: it detects background-poor
patches, not fields that contain tissue but little tumour-like nuclear content.
The E-007 cache stays frozen; no segmentation or threshold is retuned.

### Patient 13957 — caution for partial tissue

The representative panel is technically usable but contains a large
non-tissue area. Patient 13957 has 18/77 low-tissue patches (23.4%), the largest
fraction in the cohort; the next-highest patient is about 12%. This is a clear
outcome-blind QC outlier and is retained in the primary cohort but excluded in
the strict QC sensitivity cohort.

### Patient 17649 — known artifact remains excluded

The displayed E-007 representative patch 82 is usable. The already known
linear-artifact patch 5053 was pre-specified and excluded during extraction.
Every downstream table must verify that this exclusion remains in force.

## Frozen analysis sets

These sets were defined without individual survival outcomes and must not be
changed after outcome inspection:

1. **Primary cohort (n=170):** use every E-007 patient with the frozen
   patch-level rules. AI-QC labels are not used as outcome-driven exclusions.
2. **Failed-field sensitivity (n=169):** repeat the entire model ladder without
   patient 26807.
3. **Strict-QC sensitivity (n=168):** repeat the entire model ladder without
   patients 26807 and 13957. The criteria are median nuclear-foreground
   fraction below 0.15 plus a failed representative overlay for 26807, and
   patient low-tissue-patch fraction above 0.20 for 13957.

All clinical and image models must be re-fit on the same patients within each
sensitivity set so paired performance comparisons remain valid. The primary
result remains the 170-patient analysis; sensitivity sets test whether the
incremental result depends on obvious QC outliers.

## Practical expert-review plan

An independent expert should still review the work before scientific promotion
or manuscript claims, but the initial request can be reduced from all 170
panels to a targeted 50-panel audit:

- all 39 AI-CAUTION representative panels;
- the one AI-FAIL panel (26807/1771);
- the known excluded artifact (17649/5053); and
- nine deterministic, outcome-blind AI-PASS controls.

The ready-to-fill sheet is
`reports/phase_03_e007_expert_priority_subset.csv`. A full 170-panel review can
be requested later if the collaborator or journal requires it. Expert labels
must be recorded separately and must never be back-filled with AI judgments.

## Revised gate

The complete AI-assisted QC is sufficient for software validation, protocol
development, comparator implementation, and **explicitly exploratory/internal**
survival modelling after the statistical protocol is frozen. It is not
independent pathology validation and cannot support claims that the recovered
objects are tumour nuclei, that the features are clinically valid biomarkers,
or that the model is ready for clinical use.

Therefore:

- independent expert review no longer blocks internal exploratory modelling;
- protocol lock and the outcome-blind entropy comparator are the immediate
  gates before outcome joining;
- expert review remains mandatory before promoting results into pathology or
  clinical conclusions, drafting the final manuscript claim, or submission;
  and
- any material expert disagreement triggers the pre-specified sensitivity
  analyses, not post-hoc threshold tuning.

## Reproducibility artifacts

- `src/validation/build_e007_contact_sheets.ps1` creates the 22 all-patient
  contact sheets in `reports/phase_03_e007_ai_contact_sheets/`.
- `src/validation/write_e007_ai_overlay_review.ps1` deterministically writes
  the 170-row AI-QC table and 50-row expert-priority subset.
- `reports/phase_03_e007_ai_overlay_review.csv` is the auditable AI-QC result.
- `reports/phase_03_e007_expert_priority_subset.csv` is blank in all expert
  fields and ready for later independent review.

## Limitation

Only one representative panel per patient was visually inspected. A PASS label
does not certify every patch, and a CAUTION or FAIL label does not prove that
the entire patient cache is unusable. These labels are computational QC and
sensitivity-planning evidence, not diagnostic ground truth.
