# Phase 4 — Cell-of-origin from H&E: study scope

**Written:** 2026-09-03
**Status:** scoping document — not a protocol, not pre-registered
**Precondition:** the Phase 3C survival null is written up and posted before this begins

> **Scope discipline.** The numbers below are label counts and image inventory
> only. No relationship between any feature and the COO label has been examined.
> A signed protocol must precede any modelling, exactly as in Phase 3B.

---

## 1. The question

> Can cell-of-origin (germinal-centre B-cell vs non-GCB, by the Hans algorithm)
> be predicted from routine H&E alone in DLBCL — and does that prediction hold
> in an independent cohort?

The second clause is the contribution. Internal COO-from-H&E results have been
reported (best located: AUC ≈ 0.87, n=115, single centre, 3-fold CV, no external
cohort). **No externally validated result has been published.** That is the gap.

---

## 2. Why this is a better-powered problem than the survival study

This is the decisive argument for the pivot, and it is not a small difference.

| | Phase 3C (survival) | Phase 4 (COO) |
|---|---:|---:|
| Informative units | **58 events** | **163 labelled patients** |
| Label completeness | — | 95.9% (7 missing of 170) |
| Class balance | 34% event rate | **57.1% / 42.9%** |
| Censoring | Yes — complicates everything | **None** |
| Minority class per 5-fold test split | ~11–12 events | **~14** |
| Events per variable, 61 features | **0.8** | ~1.1, and features can be far fewer |

Verified label availability among the 170 image-eligible patients:

| Column | Present | Missing |
|---|---:|---:|
| HANS | 163 | 7 (4.1%) |
| CD10 IHC | 163 | 7 (4.1%) |
| BCL6 IHC | 166 | 4 (2.4%) |
| MUM1 IHC | 163 | 7 (4.1%) |

HANS distribution: **93 (57.1%) vs 70 (42.9%)**. All three Hans component stains
are present for 158 patients, and all 158 also carry a HANS label — so the
algorithm's inputs can be audited against its output.

Approximate precision at n=163 with a 70/93 split: an AUC of 0.80 carries a 95%
CI of roughly **±0.07**. That is enough to distinguish real signal from chance,
and enough to detect gross failure on external validation — but not enough to
estimate the ceiling precisely. Compute this properly in the protocol.

**Interpretation:** the survival study was underpowered by construction. This one
is merely small. That is a meaningful difference.

---

## 3. Why it matters — and the framing that is uniquely yours

Predicting IHC from H&E has limited value where IHC is routine and cheap. Stated
that way, the clinical case is weak, and a reviewer will say so.

The honest and much stronger framing is **resource-limited pathology**.
Immunohistochemistry panels are not universally available; in many hospitals
across South Asia, Africa, and Latin America, COO subtyping is simply not
performed because the stains, antibodies, or trained staff are unavailable. A
model that triages COO from an H&E slide alone — flagging which cases most need
the panel — has genuine value in exactly those settings.

You are positioned to make that argument credibly. Most authors in this
literature are not. Make it explicitly, in the introduction, and make the
evaluation reflect it: report sensitivity at a high-specificity operating point
suitable for triage, not just a headline AUC.

---

## 4. Label definition and its ceiling

The label is the **Hans algorithm** classification, itself derived from CD10,
BCL6, and MUM1 immunohistochemistry.

Two things must be stated plainly in any write-up:

1. **Verify the encoding.** The released data dictionary does not state whether
   `HANS = 1` means GCB or non-GCB. Confirm against the CD10/BCL6/MUM1 columns
   and the published Hans decision rule before writing a line of modelling code.
   Getting this backwards would invert every conclusion.
2. **Hans IHC is a proxy, not ground truth.** Gene-expression profiling is the
   reference standard for COO; Hans IHC concordance with GEP is commonly cited
   around 80–85%. Label noise therefore bounds achievable accuracy. An AUC of
   0.85 against Hans labels is *not* an AUC of 0.85 against true COO. Say so.

---

## 5. Model ladder

Same discipline as Phase 3B: frozen before outcome access, identical splits for
every model, all preprocessing inside training folds.

| ID | Model | Features | Cost | Role |
|---|---|---|---|---|
| C0 | Clinical only | Age, ECOG, LDH, EN, Stage | trivial | **Negative control** — COO should *not* be predictable from clinical variables. If C0 beats chance, something is wrong with the design. |
| C1 | **E-007 handcrafted morphology** | F1 ∪ F2 (56) | **zero new compute** | Already extracted. Decisive cheap first look. |
| C2 | Released geometry | `cell_shapes.csv` mean+SD (44) | trivial | Literature comparator, and reuses your Phase 3C code path |
| C3 | Foundation model + attention-MIL | frozen embeddings | ~30 min T4 | The modern approach; where the headroom plausibly is |
| C4 | C1 ∪ C3 | fusion | small | Does handcrafted add to learned? |

**C1 is the key property of this plan.** You already hold the features. The first
informative result costs an afternoon of CPU, not a GPU budget. If C1 lands near
0.50, that is itself a fast, cheap, publishable finding and you stop early.

For C3, given no institutional email is needed: **Phikon-v2** (ungated,
`owkin/phikon-v2`) and **H-optimus-0** (Apache 2.0, `bioptimus/H-optimus-0`) are
downloadable immediately. Both run on a T4; 30,007 patches is roughly 10–30
minutes of inference. Do not wait on gated models to start.

At ~177 patches per patient (TMA cores, not whole slides), use **attention-MIL
(ABMIL)**. Avoid TransMIL and HIPT — they assume whole-slide spatial hierarchies
that TMA cores do not have.

---

## 6. External validation — the hard part

This is where the study succeeds or fails as a contribution.

**Option A — TCGA-DLBC (free, immediate).** 48 patients, H&E whole-slide images,
open access. COO is not distributed as a label, but the cohort has RNA-seq, so
COO can be derived by a published gene-expression classifier — which is the
*reference standard*, arguably better than the Hans labels you train on.

Caveats, all real: n=48 gives an AUC CI of roughly ±0.14 — adequate only to
detect gross failure, not to estimate performance. TMA-trained → whole-slide
tested is a genuine domain shift. And training on Hans-IHC while testing against
GEP-derived COO introduces a label-definition mismatch you must state, not bury.

**Option B — email for a real external cohort.** The Gupta et al. TMC dataset
(115 patients, 62 ABC / 53 GCB, Tata Memorial Centre, India) is the closest match
and the most relevant comparator, since it is the internal-AUC-0.87 result you
would be testing. An Indian centre may also be more receptive to the
resource-limited framing. Not publicly available; requires contact.

**Do both.** A applies regardless; B is upside.

---

## 7. Realistic timeline

| Phase | Work | Duration |
|---|---|---|
| 0 | Post the Phase 3C preprint first | — |
| 1 | Verify HANS encoding; write and sign the protocol | 1 week |
| 2 | C0–C2 on existing features | 2–3 days |
| 3 | C3/C4 — embeddings + ABMIL on Kaggle | 1–2 weeks |
| 4 | TCGA-DLBC: download, tile, derive COO, evaluate | 2–3 weeks |
| 5 | Write-up | 2 weeks |

**Total ≈ 6–8 weeks.** Step 4 is the schedule risk; deriving COO from TCGA
RNA-seq is more fiddly than it sounds.

---

## 8. Honest risks

- **A second null is entirely possible.** If COO-from-H&E fails to replicate
  externally, you have two consecutive negative papers. That is scientifically
  valuable and professionally harder. Decide now that you will publish it either
  way — that decision is much easier to make before you know the answer.
- **Label noise caps performance.** Hans-vs-GEP disagreement is baked in.
- **Domain shift is severe.** TMA cores → whole slides, different scanners,
  different stain protocols. This is precisely what has not been tested before,
  which is why it is worth testing — but expect a drop.
- **n=48 external is weak.** Frame as domain generalisation, never validation.
- **Clinical utility must be argued, not assumed.** Without the resource-limited
  framing, a reviewer will ask why anyone would predict a cheap stain.

---

## 9. What carries over unchanged

Nearly all of it — this is the strongest practical argument for the pivot:

- the pre-registration and hash-locking workflow
- `build_split_ids.py` (stratify on COO label instead of event indicator)
- fold-internal pipeline, redundancy pruning, deterministic tie-breaks
- paired bootstrap comparison machinery
- calibration-as-rejection-criterion discipline
- the E-007 feature cache, unchanged and already frozen
- the artifact/manifest/SHA-256 conventions

Metrics change from censored-survival to classification: AUROC, AUPRC (the
minority class is 43%, so AUPRC matters less than in a rare-event setting),
sensitivity at fixed specificity for the triage use case, and calibration of
predicted probabilities.

---

## 10. Recommendation

Run **C1 first**, under a signed protocol, before spending anything on GPUs. It
costs an afternoon and it tells you whether there is any morphological signal in
features you already trust.

If C1 shows nothing and C3 shows nothing, you will have demonstrated — twice,
rigorously, with pre-registration — that routine H&E in DLBCL carries far less
extractable information than the field currently assumes. Two disciplined nulls
from one researcher is a more coherent scientific story than it first appears.

If C1 or C3 shows real signal that survives external testing, you have the first
externally validated COO-from-H&E result, with a public-health framing that few
competing groups can make honestly.

Both outcomes are worth the eight weeks. That is the test of a well-chosen
question.
