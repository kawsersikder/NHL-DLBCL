# DLBCL Pathology Prognosis — Project Update

**Updated:** 3 September 2026
**Current stage:** Phase 3C complete — pre-registered null result; manuscript drafted; Phase 4B (cell-of-origin) scoped and protocol drafted
**Canonical status:** `PROJECT_STATUS.md`

---

## The headline

**The primary hypothesis was tested and rejected.**

Adding 56 outcome-blind H&E image features to a five-covariate clinical model did
not improve overall-survival prediction:

> **ΔC (M5 − M1) = −0.0231, 95% CI [−0.0499, +0.0008]**

The interval includes zero and the point estimate is negative. The clinical model
reached Harrell C = 0.706; the combined model 0.683. Every image-only model was
significantly worse than clinical covariates alone, and only the clinical and
combined models passed the pre-specified calibration gate.

This was a **single pre-specified test on a protocol signed before any outcome
column was read** (2026-09-01, lock hash `94c9a6ef…`). It is a result, not a
setback.

## What was actually established

| Model | Harrell C [95% CI] | Calibration |
|---|---|:--:|
| M1 clinical | **0.706 [0.623, 0.777]** | ✅ 0.82 |
| M5 clinical + image | **0.683 [0.600, 0.756]** | ✅ 0.94 |
| M4b packing only | 0.589 [0.505, 0.669] | ❌ |
| M4c image (primary) | 0.579 [0.497, 0.666] | ❌ |
| M2 released geometry | 0.521 [0.435, 0.605] | ❌ |
| M4a morphology only | 0.497 [0.421, 0.576] | ❌ |
| M3 global entropy | 0.456 [0.376, 0.539] | ❌ |

The null is robust across three cohorts (n=170/169/168), four feature views, two
learners, and five pre-specified variants. The full ladder, all seven
sensitivities, and every model that failed are published in
`reports/phase_03c_model_ladder_results.md`.

**One nuance, reported and not oversold:** M5 is better calibrated than M1 (0.94
vs 0.82) and has the best integrated Brier score in the ladder. The image
features are not pure noise — they slightly improve overall accuracy while
slightly degrading rank discrimination. This is not a rescue of the primary
result and must never be presented as one.

**One correction to our own finding:** M3's below-chance 0.456 is *not* robust.
It rises to 0.507 and 0.497 in cohorts B and C. Removing patient 26807 alone
moves entropy from below-chance to chance. The defensible claim is that global
entropy carries **no signal** in this cohort — not that it is anti-predictive.

## Independent corroboration

ImmunoBench — 14 pathology foundation models, 13,657 patients, 26,058
whole-slide images, including a DLBCL-Morph survival task — reports a **best
macro-averaged prognosis C-index of 0.545**, with the explicit statement that
neither foundation-model nor task-specific paradigms achieved robust performance
on prognosis endpoints.

Our handcrafted image model sits at 0.579, in the same range.

This reframes the result decisively. The finding is not *"our features were
weak."* It is *"H&E-derived features do not reach clinical-baseline prognostic
performance in DLBCL, whether handcrafted or learned by frontier models trained
on millions of slides."* The limitation is a property of the problem.

*(The repository was verified directly on 2026-09-03 after an automated research
agent incorrectly reported it did not exist. Verify citations by opening them.)*

## Two reproducibility findings

These emerged incidentally and are now co-equal contributions of the paper.

1. **A released checkpoint that does not function.** The published HoLy-Net H&E
   weights load with 798/798 tensors, zero missing and zero unexpected keys —
   complete architectural coverage — yet score **Dice 0.282** on their own
   source dataset. Threshold sweeps, channel-order inversion, and direct-versus-
   API forward passes were all excluded as explanations. Reported as a failure
   *in our hands*, not as evidence the original result is false.

2. **A published baseline that does not survive fold-safe refitting.** We first
   reproduced the original analysis faithfully (geometric 0.6358 vs published
   0.635; clinical 0.6738 vs 0.674 — agreement to three decimals). Refitting the
   same released features under nested CV, with all preprocessing inside
   training folds and **without** the dataset-wide `QuantileTransformer`, gives
   **C = 0.521**. Cohort size also differs (170 vs 209), so this is **not** a
   like-for-like refutation and must not be written as one — but the direction
   and magnitude are large and the mechanism is identifiable.

## Reproducibility of our own work

The complete ladder was re-fitted in a second environment (Python 3.13.9 /
numpy 2.3.5 / Windows versus Python 3.12.13 / numpy 2.0.2 / Linux). Across
9 models × 7 metrics, the **maximum absolute difference was 1.8 × 10⁻¹⁴**.

An initial sensitivity run was destroyed by a filename collision — all cohort A
variants wrote to identical names and the last writer won. The bug is fixed and
the incident is recorded in the results report and the manuscript rather than
quietly omitted.

## Where the work stands

**Done:** protocol signed and hash-locked; E-008 entropy comparator frozen;
splits frozen; E-009 ladder complete including all sensitivities and the RSF
arm; figures; results report; medRxiv manuscript drafted in Markdown and LaTeX
(13 pages, builds clean).

**Immediate blockers — all administrative, none analytical:**

1. affiliation, institutional email, ORCID
2. public GitHub repository and a Zenodo deposit for the artifacts
3. **verify every reference by opening it** — refs [2], [4], [6] are flagged; a
   subagent produced a fabricated DOI during this project
4. supervisor read-through
5. confirm the ethics wording and complete the AI-tool disclosure

**Strongly recommended before submission:** the targeted 50-panel independent
haematopathology review. Its purpose has changed — for a null result it exists
to **rule out the obvious reviewer objection** that the finding reflects poor
segmentation. That is a much easier ask of a pathologist than endorsing a
biomarker.

## What will not happen

**No further learners will be added to the survival ladder.** Not TabPFN, not
LLM-based methods, not a different CNN library. The pre-specified S6 already
tested whether a different model class helps — RSF was worse on every model —
and ImmunoBench tested 14 foundation models at scale. The bottleneck is 58
events, not the function class.

Adding a tenth model after seeing nine fail would convert a pre-registered study
into a fishing expedition and destroy its single most valuable property. Any
such run requires a §12 amendment recorded *before* execution and must be
labelled post-hoc exploratory.

Phase 4 (survival MIL / foundation-model fusion) is **deprioritised** for the
same reason: it would spend the remaining GPU budget reproducing a known
negative result.

## Next study — Phase 4B, cell-of-origin from H&E

Not a continuation of the survival question. A different, better-conditioned one.

> Can cell-of-origin (GCB vs non-GCB, by the Hans algorithm) be predicted from
> routine H&E alone — and does that prediction hold in an independent cohort?

| | Survival study | COO study |
|---|---:|---:|
| Informative units | **58 events** | **163 labelled patients** |
| Class balance | 34% event rate | 70 / 93 (42.9% / 57.1%) |
| Censoring | yes | **none** |
| Events per variable | **0.8** | ~1.1, with far fewer features possible |

The survival study was underpowered by construction. This one is merely small.

**The gap is real:** internal COO-from-H&E results exist (best located ≈0.87
AUC, n=115, single centre, no external cohort). **No externally validated result
has been published.** That is the contribution.

**Framing:** resource-limited pathology. IHC panels are unavailable in many
hospitals, so COO subtyping is simply not performed. A model that triages which
cases most need the panel has genuine value there — an argument this project can
make credibly and most competing groups cannot.

**Already established:**

- `HANS = 1` → GCB, `HANS = 0` → non-GCB, at 172/174 (98.9%) concordance.
- The released **data dictionary is wrong**: it describes CD10 and MUM1 as
  "% positive" when both are binary {0,1}; only BCL6 is percent-scaled.
  Applying a 30% threshold to all three — as the dictionary implies — drops
  concordance to **74.7%**, silently inverting about a quarter of the labels.
  A BCL6 cut-off sweep peaks at exactly 30%, the canonical Hans threshold.
- Label-noise floors: 1.1% internal (two irreducible discordant patients) on top
  of the ~15–20% Hans-versus-GEP ceiling. Both are reported regardless of result.

**Protocol drafted and unsigned:** `reports/phase_04_coo_analysis_protocol.md`.
C0–C4 ladder with a clinical-only falsification check, E1/E2 estimands, an
external feasibility gate, a single-use rule on the external cohort, and an
early-stopping rule so a null in-domain result does not cost three weeks of
external validation.

**Precondition: the Phase 3C preprint is posted before E-010 begins.**

## Honest expectations

A second null is entirely possible. That decision — to publish either way —
should be made now, while the answer is still unknown.

This paper will not change how DLBCL is treated. No honest version of it would.
What it can do is add one carefully-done, fully-reproducible result to the
record, and leave behind a frozen protocol, a public artifact set, and two
documented reproducibility failures that will save the next researcher months.

## Next concrete action

Fill in the manuscript placeholders, verify the references, get a supervisor
read-through, and post to medRxiv. Then send the data-request and courtesy
emails with the preprint link attached — a citable artifact changes the reply
rate far more than any wording will.
