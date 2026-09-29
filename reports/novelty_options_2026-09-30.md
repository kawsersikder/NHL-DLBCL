# Where the novelty is: options after Study 1

**Date:** 2026-09-30 · **Author:** Kawser Sikder (LLM-assisted)
**Status:** direction analysis only. No data opened, no outcome read, no model
fitted. Every external claim below was checked against the source on this date.
One PubMed query and two web searches are **not** a systematic search, so no
novelty claim here may go into a manuscript until the search is repeated
properly.

---

## 0. Bottom line

1. **More image models on DLBCL-Morph survival would not be novel.** This is now
   shown with DLBCL-specific numbers, not a pan-cancer average (§1.1).
2. **Route 1 as currently framed has a novelty problem.** "Do program scores add
   beyond IPI?" was asked for gene signatures in 2013, with a null-leaning
   answer (§1.2).
3. **The best available next study reuses all of Route 1 but asks a different
   question:** a pre-registered audit of the *published* DLBCL prognostic gene
   signatures against IPI and against random gene sets, on the endpoint-verified,
   identity-audited cohorts Route 1 has already built (§2). Its answer is useful
   whichever way it comes out, so its value doesn't depend on finding signal.
4. **Re-scoping is only legitimate now.** The Route 1 protocol is not frozen and
   no outcome has been read. Once outcomes are seen, changing the question
   becomes fishing.
5. **The only route to data nobody else has is a local cohort** (§4). It has the
   longest lead time, so the conversation should start now if at all.

---

## 1. What today's evidence rules out

### 1.1 Image-based survival on DLBCL-Morph is saturated

ImmunoBench's repository ships `dataset_csv/DLBCL_Morph_survival.csv` with
**170 patients and 58 events, identical to our cohort A**. Its public
leaderboard (`site-data.js`, task `Lymphoma-OS`) reports these concordances for
14 pathology foundation models:

| Best | Median of 14 | Worst |
|---:|---:|---:|
| 0.598 (Prov-GigaPath) | ~0.54 | 0.485 (CTransPath) |

On the same patients our IPI-component clinical model scores **0.706**, and our
best image family 0.589. Nine models in our own ladder, a random survival forest
and 14 foundation models all sit at or below 0.60. Adding a 25th model is not a
research question.

*Caveat:* the task-to-dataset mapping is inferred. DLBCL-Morph is the
benchmark's only lymphoma dataset with survival, and `Lymphoma-OS` is its only
lymphoma survival task. Splits differ and no intervals are published.

### 1.2 Route 1's current question has prior art

- **Hong, Kahl & Gray, *Blood* 2013** (PMID 23160463,
  doi:10.1182/blood-2012-08-450106) applied concordance-based incremental-value
  methods to **3 published gene signatures in 2 cohorts** (CHOP and R-CHOP). They
  concluded the signatures "are inferior to clinical factors and provide little
  added value in risk assessment." Gentles & Alizadeh replied in the same year
  (PMID 23580636).
- PubMed returns **677 records** for DLBCL × gene prognostic signature/risk
  model (query in §6). Most are single-cohort "novel N-gene signature" papers.

So "eight Hallmark programs beyond IPI" would be one more entry in a crowded
field, with an expected answer already on record. It could be rigorous, but
rigour alone is a thin novelty claim when the headline result is predictable.

### 1.3 COO-from-H&E is still open, but only with an external labelled cohort

ImmunoBench's `Lymphoma-Subtype` task (AUC up to 0.998) is **not** DLBCL
cell-of-origin. It comes from a private dataset, `Lymph-SUB` (320 patients;
H&E, CD3, CD5, CD79a, CD21, EBER, CD20), which is lymphoma *typing*. So
externally validated COO from H&E remains unpublished as far as checked. The
blocker hasn't moved: no public H&E cohort carries COO labels (O-077). An
internal-only COO result would repeat what exists.

---

## 2. Option A (recommended): a pre-registered audit of published DLBCL prognostic signatures

### Question

> Across the DLBCL prognostic gene-expression signatures published since 2013,
> how many add discrimination beyond IPI in independent, endpoint-verified
> cohorts, and how many beat size-matched random gene sets?

### Why this is a contribution rather than a 678th signature

- **The random-signature null has not been applied in lymphoma, as far as
  checked.** Venet, Dumont & Detours (*PLoS Comput Biol* 2011;7:e1002240,
  verified) showed that most *random* gene sets are significantly associated
  with breast-cancer outcome, which reframed that whole literature. PubMed:
  **0 records** for random signatures × lymphoma/DLBCL.
- **Hong 2013 is the closest prior audit.** It pre-dates the post-2015 signature
  flood, covered 3 signatures, and used no random-set control.
- **Route 1 has built exactly what that literature lacks.** Almost no signature
  paper verifies its endpoint's time origin, tests patient-vs-sample identity,
  or traces whether its "validation" cohort was used in development. Route 1
  has done all three: WP1's verified diagnosis-origin OS (475/475), the
  301-patient identity audit, and the Care 2013 / Sha 2015 lineage tracing.
- **Both answers are publishable and useful.** "Few signatures beat random gene
  sets once IPI is in the model" warns clinicians and reviewers. "Signature
  class X survives" tells the field where to look.

### Design sketch (for a dated protocol, not a commitment)

| Element | Proposal |
|---|---|
| Signature registry | Systematic PubMed search with a frozen query and date. Each signature's gene list (and coefficients, where published) is extracted **with a verbatim source quote and page**, the project's standing rule since D-004/D-006 |
| Lineage matrix | For every signature, record which GEO cohorts it was trained or tuned on. **A signature is never evaluated on a cohort that touched its development.** This will remove many signature × cohort pairs; that exclusion is itself a finding |
| Arms | R0 = IPI (as in protocol v2). R0 + each published signature. R0 + size-matched random gene sets (e.g. 1,000 draws per signature size, from the same allowed universe). R0 + the 8 Hallmark programs (keeps Route 1's current question as one arm) |
| Scoring | Signatures without published coefficients are scored by one fixed rule (mean within-sample rank of available genes, the Route 1 transform), declared before any outcome is read |
| Primary estimand | Fraction of signatures whose paired ΔC over R0 exceeds the 95th percentile of the size-matched random-set distribution, in each eligible cohort |
| Cohorts | GSE31312 (verified endpoint, all IPI components, 424/155 with IPI). GSE181063 if its OS origin is resolved. GSE87371 (IPI score only). GSE10846 with lineage exclusions |
| Multiplicity | The signature distribution is the result. No per-signature significance claims |

### Costs and risks

- **Extraction labour is the main cost.** Tens of papers, each quoted
  verbatim. This is error-prone work, and this project has made
  attribution errors before (D-004, D-006), so each entry needs a source quote.
- **Many signatures are probably trained on these same GEO cohorts** (GSE10846
  especially). That is an expectation, not yet a verified fact. If most pairs
  are excluded, the audit shrinks. A lineage pass on roughly 20 signatures
  should come before committing.
- **Gene-symbol drift and platform coverage** will drop some genes. The Route 1
  coverage machinery already measures this.
- **The GSE181063 OS-origin blocker still applies** to that cohort. GSE31312
  alone may carry the primary analysis.

---

## 3. Option B (cheap, alongside): make Study 1 a benchmark, not just a null

Release the frozen splits (`ff22e982…`), the IPI baseline, and the fold-safe
evaluation harness with the preprint. State the result the community can use:
**on DLBCL-Morph OS, the number to beat is the clinical model at 0.706, not
chance.** With the ImmunoBench comparison now in the Discussion, this is a
sentence and a Zenodo deposit, not a new paper.

---

## 4. Option C (longest lead time, highest real-world value): a South Asian cohort

Every cohort in this project was deposited by US, UK or French groups:
DLBCL-Morph (Stanford), GSE181063 (University of York), GSE31312 (Roche
Molecular Systems, USA), GSE87371 (Centre Henri Becquerel, France) and GSE10846
(NCI, USA), per their GEO contact fields. The manuscript already cites
population-specific prognostic models (Chen 2016).

A Bangladeshi DLBCL cohort, even clinical-only with outcomes, would let this
project externally validate IPI/R-IPI/NCCN-IPI in a population absent from all
of its data. If H&E slides exist, it would also give Study 1 the external
cohort it lacks.

This needs a haematology partner, ethics approval and a data agreement, which
means months. It is a question to raise with the supervisor now, not a task to
start. Do **not** claim that no South Asian DLBCL data exists anywhere; that
needs its own search.

---

## 5. Not recommended

- New learners or feature sets for the Study 1 ladder (protocol §12, D-2026-09-03).
- Phase 4B without an external COO-labelled cohort.
- A new "novel N-gene signature". That is what the 677 records already are.
- Re-scoping Route 1 **after** any outcome is read.

## 6. Order of work

1. **Post Study 1.** What remains is author details, ORCID and Zenodo; the
   references were verified today.
2. **Decide on Option A before the Route 1 protocol freezes.** If yes, a
   lineage pass on about 20 signatures first, then a dated protocol. The
   GSE181063 depositor email is needed either way.
3. **Raise Option C** with the supervisor and any Dhaka haematology contact.

---

## Sources (all opened 2026-09-30)

- ImmunoBench README and task file: https://github.com/yanfang-research/ImmunoBench
  (`dataset_csv/DLBCL_Morph_survival.csv`, `train_scripts/survival_DLBCL_Morph.sh`)
- ImmunoBench leaderboard data: https://yanfang-research.github.io/ImmunoBench-Web/site-data.js
- Carreras et al., *Cancers* 2026;18(14):2279, doi:10.3390/cancers18142279, full text PMC13406279
- Hong, Kahl & Gray, *Blood* 2013, doi:10.1182/blood-2012-08-450106 (abstract via Europe PMC)
- Gentles & Alizadeh, *Blood* 2013, doi:10.1182/blood-2013-01-477521 (record only)
- Venet, Dumont & Detours, *PLoS Comput Biol* 2011;7(10):e1002240, doi:10.1371/journal.pcbi.1002240 (Crossref)
- LyNSeC deposit: https://zenodo.org/records/8065174 (API record)
- HoVer-Net architecture: https://github.com/vqdang/hover_net `models/hovernet/net_desc.py`
- PubMed queries (E-utilities, 2026-09-30):
  `(DLBCL OR "diffuse large B-cell lymphoma") AND (prognostic signature OR prognostic model OR risk score) AND (gene OR genes OR lncRNA)` → 677;
  `("random signature" OR "random signatures" OR "random gene sets" OR "random gene signatures") AND (lymphoma OR DLBCL)` → 0
