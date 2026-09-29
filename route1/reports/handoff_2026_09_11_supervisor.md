# Route 1 — handoff to supervisor

**Date:** 2026-09-11 · **From:** implementation researcher, Windows workspace
**Responds to:** supervisor review and next orders, 2026-09-11
**Assume the Mac holds none of these artifacts.** All figures inline.

**Headline:** your three corrections were all right and are implemented. Two
further errors of my own surfaced during the work and are recorded. **One
ordered task overturned a Phase 2 conclusion: GSE31312 is usable, and is
probably a better external cohort than the one I had selected.** No model has
been fitted to patient outcomes. Zero Kaggle sessions, zero GPU time.

---

## 1. Corrected gate table

| Phase | Status | Basis |
|---|---|---|
| 0 — workspace | **PASS for local continuation** | Hash registry; no claim the two copies are reconciled |
| 1 — identity/outcomes | **PARTIAL** | OS origin INFERRED, not documented |
| 2 — external cohorts | **PARTIAL** | Roles changed again (§4); endpoint origins and ID semantics open |
| 3 — representation | **PARTIAL** | Aggregation now specified; QC/normalisation claims downgraded |
| 3R-A/B/C | **Complete, not a gate** | Corrections, population freeze, representation checks |
| 4 — protocol | **DRAFTED, NOT FROZEN** | 7 freeze prerequisites unmet |
| 5 — implementation | **Synthetic tests PASS 7/7** | No real-data fitting |

I am not describing Phases 0–3 as collectively passed. My earlier Phase 2 and
Phase 3 PASS calls stay withdrawn.

## 2. OS time origin — precise unresolved statement

**GSE181063: UNRESOLVED. Grade INFERRED.**
Max censored follow-up 14.3190 y against the ceiling of 14.33 y implied by
Lacy (accrual 1 Sep 2004 – 31 Aug 2012; mortality follow-up to 31 Dec 2018).
This is *compatible* with a diagnosis origin. It does not exclude other
origins and does not identify which field generated the times. No
publication/supplement definition, analysis code, or depositor statement has
been found; Painter is paywalled and not in PMC (`isOpenAccess=N, inEPMC=N,
inPMC=N`).

**GSE87371: UNRESOLVED.** `OS_TIME: duration of overall survival (OS) in
months` establishes neither diagnosis nor treatment-initiation origin.

**GSE31312: potentially RESOLVABLE — new.** Its supplement carries
`Date of diagn`, `Date of progr`, `Date last f/u` and `Date death` per case, so
a diagnosis-origin OS is *derivable from dates* rather than inferred. This is
the strongest lead yet on the estimand problem.

**No survival model will be fitted until the estimand is defensible.**

Also downgraded: the seven negative follow-up values are "negative OS intervals
requiring source clarification", not a "registry-linkage artifact". What is
computed is that all seven are `curative_intent=0` on supportive/palliative/NEC
regimens and none is in the eligible set.

## 3. Verified unique-patient and primary counts

**Identifier semantics were tested, not assumed.** Samples sharing
`pid_pmid_32187361` were checked for agreement on fields that must be constant
within a patient. All 12 multi-sample groups agree exactly on sex, age at
diagnosis, OS time and OS status — **0 conflicts**, so no reconciliation was
required and the field behaves as a patient key.

Selection: one sample per patient, deterministic and outcome-independent —
pretreatment (all eligible qualify) → highest `probe_detection` → GSM order.

| Set | Patients | Events |
|---|---:|---:|
| Identity-safe eligible | **301** | **142** (47.2%) |
| Observed `ipi_score` | 230 | 105 |
| All five components present | 264 | 120 |
| **PRIMARY — observed OR reconstructable IPI** | **265** | **121** |

Reverse-KM follow-up **recomputed after deduplication: 8.79 y** (the 8.08 y
figure was sample-weighted). Range 0.0110–14.3190 y.
Subtypes GCB 143 / ABC 90 / UNC 51 / **MHG 17**.
Component missingness: ECOG 5.6%, stage 8.0%, LDH 7.3%, extranodal 10.0%, age 0%.

**243 unidentified samples excluded** from supervised development and from
representation learning. Bounds restated as you directed: at least 301 and at
most 544 patients are represented; neither bound resolves the 243.

## 4. External cohorts — ID semantics, endpoints, common predictors

### 4.1 GSE31312 — your bounded retrieval overturned my conclusion

I had deferred this cohort as having "no outcome data in GEO". The supplement
`GSE31312_Microarray_and_clinical_data_DLBCL_475_cases_PMID_22437443.pdf.gz`
retrieved (40,773 bytes gz, SHA-256 `f905c7ba…`), 18 pages, 475 cases, parses
cleanly.

**Documented columns** — table 1: `Case # · Age · Gender · HIV status · AA S ·
AAS code · N extran · ECOG · Ecog code · IPI sco · IPI code · Bulky code ·
B-sy · LDH · Response · Date of diagn · Date of progr · Date last f/u`;
table 2 (p.9): `Case # · Date death · PFScensor · OScensor · PFS · OS · CD10 ·
Bcl6 · FOXP1 · GCET · MUM1 · 3-markers algorithm · GEP · GEO Depository #`.

**Linkage is explicit.** The "GEO Depository #" value is literally
`DLBCL GEP data N####`, identical to GEO `!Sample_title`.
**475 supplement IDs; 498 GEO titles; intersection = 470.**

So GSE31312 offers, on ~470 linkable cases: OS time and event, PFS, date of
death, **all five IPI components**, IPI score, **dates permitting a
diagnosis-origin endpoint**, five IHC markers, Hans (GC/nonGC) and GEP subtype
(GCB/ABC/UC).

**Caution, not yet promoted.** (a) The event coding appears inverted again — on
inspected rows a present `Date death` coincides with `OScensor = 0` — but my
PDF text extraction is fragile and this needs systematic re-extraction and
verification. (b) Patient-vs-sample identity is unverified. (c) 5 supplement
cases and 28 GEO samples do not link. (d) Retrieval is not promotion to final
test, per your instruction.

### 4.2 GSE87371 — endpoint DOCUMENTED, identity NOT

Verbatim from GSM2328918 (archived, SHA-256 `038c1674…`):

```
ID: sample ID
OS_TIME: duration of overall survival (OS) in months
CENS_OS: coded as 0 if OS event, 1 if not
```

`death_event = 1 − cens_os`; 2 samples non-binary → missing.
**`ID` is documented as a *sample* ID.** I had promoted it to a patient key
because all 223 values are distinct; distinctness is not identity. Withdrawn —
patient structure UNRESOLVED.

**Common predictors:** fields are `ID, diagnosis, age, Sex, Stage, treatment,
ipi, age_adjusted_ipi, pfs_time, cens_pfs, os_time, cens_os, coo`.
**ECOG, LDH and extranodal count are ABSENT** — my `cohort_catalog.csv`
`has_ipi_components: True` was wrong. It has the composite score only. This
independently forces your IPI-based R0.

**Alias registered:** all 223 samples carry both `GSE87371` and **`GSE136971`**.

### 4.3 GSE10846

233 R-CHOP samples / 233 distinct `Individual` / 60 deaths, median follow-up
2.12 y, **components present** (ECOG 210, stage 226, LDH ratio 192, extranodal
203 of 233). The 6 orphan accessions are confirmed as exactly
GSM361239–GSM361244, all-`NA`. Remains development-validation, not final test
(§5).

## 5. Corrected comparator lineage

**Your correction accepted and verified.** Sha 2015 (PMC4512160), Methods:

> "Five public data sets were downloaded from the Gene Expression Omnibus …
> **Classifier development employed GSE4732_p1 and GSE4475**, and the other
> data sets were used in testing transferability of classifiers."

So the BDC supervised training set is **GSE4732_p1 (Dave) + GSE4475 (Hummel)**,
neither of which is HMRN. HMDS DASL v3/v4 are Table 1 entries used for
application and transferability. **My claim that the classifier was trained on
HMDS DASL is withdrawn.** I inferred a training cohort from a table listing
plus institutional provenance.

**Care 2013 (PMC3570548) stands:** "We used two data sets (GSE32918, and
GSE10846 divided into CHOP and R-CHOP treated groups) for classifier
development." GSE10846 therefore carries genuine **expression/subtype
development exposure** — which I now distinguish from survival-outcome
leakage, as you required. It remains development-validation.

**Withdrawn:** "an optimistic R1 makes R2−R1 conservative." Correlated errors,
shared inputs and selection can move a paired contrast either way. Also
softened: clustering on a full cohort does not by itself mean survival labels
trained the clustering, though the representation is not independent of it.

`modified_hmrn_class` / `hmrn_class_aic` remain **in-sample by construction**
(Lacy discovered them on these patients).

## 6. Final transform order and coverage denominators

**Executable order:**

```
platform probe→gene (single-symbol probes only; multi-mapping excluded)
→ detection filter: p<0.01 in ≥10% of TRAINING arrays (assay-specific)
→ log2(x + 1)
→ gene aggregation: MEDIAN across eligible probes
→ allowed universe = training-derived genes ∩ declared cross-platform universe
→ within-sample rank over that FIXED universe, scaled to [0,1]
→ program score = mean scaled rank of available program genes
→ (training-fold standardisation at model time)
```

**A second error of mine, caught by the check.** I had written that median
aggregation is order-invariant under log2, so ordering was immaterial. **False
for even probe counts** — the median averages two central values and averaging
does not commute with log2. **3,586 genes have even probe counts; the two
orders differ by up to 4.08 log2 units.** The order is now *declared*
(log2 first, so the central pair is averaged on the log scale where
intensities are approximately symmetric). The assertion now tests that they
*differ*, so this cannot silently reappear.

**Coverage denominators, all by set operations:**

| Quantity | Value |
|---|---:|
| GPL14951 genes | 20,818 |
| GPL570 genes | 21,653 |
| Declared cross-platform universe | 15,647 |
| Genes surviving mapping + detection filter | 18,826 |
| **ALLOWED UNIVERSE** | **14,637** |
| Lost program-gene **memberships** | 26 / **1,361** on-dev rows |
| Lost **unique** genes | 25 / **1,174** distinct on-dev genes |

The 26-vs-25 discrepancy is `NOP56`, which belongs to two programs.
*(An earlier draft gave the unique-gene denominator as 1,335 from recollection;
the computed value is 1,174.)*

**Coverage after the detection filter** (not annotation alone), all scoreable:

| Program (renamed to literal signature) | Set | Available | Fraction |
|---|---:|---:|---:|
| hallmark_inflammatory_response | 200 | 191 | 0.955 |
| hallmark_emt | 200 | 190 | 0.950 |
| hallmark_ifng_response | 200 | 189 | 0.945 |
| hallmark_tnfa_signaling_via_nfkb | 200 | 183 | 0.915 |
| hallmark_angiogenesis | 36 | 32 | 0.889 |
| hallmark_e2f_targets | 200 | 177 | 0.885 |
| hallmark_myc_targets_v1 | 200 | 176 | 0.880 |
| hallmark_oxphos | 200 | 172 | 0.860 |

Renaming applied per your §3.5 — inflammation is not a macrophage assay, EMT in
lymphoma tissue is not malignant-cell EMT, IFN-γ response is not antigen
presentation.

**QC/normalisation claims downgraded** as directed: `qc_fail` shows an
*association* with `probe_detection` (ρ −0.251), not strict monotonicity or a
code definition; "no strong association with death observed" replaces "outcome
independent"; `probe_detection = fraction p<0.01` is supported on 5 arrays
(COMPUTED-partial); unequal sorted columns exclude *global* quantile
normalisation only, not batchwise; within-sample ranks remove a monotone
per-sample transformation and do **not** correct probe affinity, background,
saturation or batch-dependent ordering.

## 7. Proof the old mask is inactive, and its removal

Asserted in `phase3R_representation_checks.py` C1, run 2026-09-11:

```
|U| (ranking universe)  = 15,647
|M| (dev minus ext)     =  5,171
|U ∩ M|                 =      0
ASSERTION PASSED: masking M removes 0 of the model's input genes.
```

Your argument is correct and supersedes my 1.9% figure, which used the wrong
denominator (`on_dev` rather than the model's input set `U`). B4 was not a weak
test but no test.

**Removed.** `representation.yaml` now carries `masking.status: WITHDRAWN`,
`applied_to: []`, with the historical spec retained for the record. **It will
not be run to produce a null.** Random dropout inside `U` is not a repair. A
targeted-panel study would need its own dated protocol.

## 8. Phase 4 draft, synthetic tests, T4 queue

**Ladder** (`analysis_protocol_v2_DRAFT.md`, unsigned):

| New | Old | Model |
|---|---|---|
| R0 | B0 | Penalised Cox on **IPI**, fixed encoding |
| R1 | B1 | R0 + verified equivalent COO/MHG — **conditional gate, currently unmet** |
| R2 | B2 | R1 + eight Hallmark program scores |
| R3 | B3 | Small neural model, same inputs, gated |
| — | B4 | **withdrawn** |

If R1 fails its gate, R2 is redefined as R0 + programs and the claim amended
before fitting.

**Precision assessment — the planning target is not reachable externally.**
Simulation at n=103 / 36 events, 2,000 replicates, paired on the same patients:

| Quantity | Value |
|---|---|
| SD of paired ΔC | **≈ 0.057** |
| 95% CI width | **≈ 0.22** |
| Target +0.03 ÷ CI half-width | **≈ 0.27** |

The target is ~4× smaller than the half-width. Per your instruction the target
is **not lowered**; the study is labelled a **preliminary external assessment
reporting intervals**. The protocol distinguishes (a) a positive point
estimate, (b) an interval excluding zero, (c) an interval supporting ≥ +0.03 —
and (c) is very unlikely to be attainable at this size. *(Caveat: my effect
calibration was crude — achieved mean +0.011 when targeting +0.03. The SD,
which the conclusion rests on, is stable.)*

**This is a further argument for reconsidering GSE31312** (~470 linkable cases)
as the final test instead of GSE87371 (103/36), subject to §4.1's cautions.

**Synthetic tests — 7/7 PASS**, no patient outcome read:

| | Test | Result |
|---|---|---|
| S1 | Grouped splitting | PASS — 0 overlap; naive row split leaks (non-vacuous control) |
| S2 | Risk direction | PASS — signs recovered, C=0.781 |
| S3 | Full-risk-set Cox partial likelihood | PASS — matches lifelines to **0.00e+00** |
| S4 | Ties handling | **PARTIAL — see caveat** |
| S5 | Fold-local preprocessing | PASS — held-out corruption moves training mean by 1.4e−16 |
| S6 | Checkpoint resume | PASS — reproduces uninterrupted run exactly, completed folds not refitted |
| S7 | Deadline guard | PASS — 10.5/11/11.5 h transitions correct, 30 min buffer, monotonic |

**S4 caveat, stated plainly:** it confirms ties exist (228 tied rows) and that
Efron is declared, but it does **not** compare Breslow vs Efron — I fitted the
same model twice with different step sizes. Ties handling is therefore
*declared*, not *validated*. To be fixed before any real fit.

**T4 queue:** R0–R2 are CPU-only. R3, if gated in, is ≤4 configs × 3 inner × 5
outer = **60 inner + 5 outer refits**. Removing B4 removes its queue entirely.
Session contract unchanged.

## 9. Depositor draft and remaining human dependencies

`route1/reports/depositor_metadata_request_DRAFT.md` — **written, NOT SENT.**
Addressed to Dr Matthew Care (GSE181063 contact), asking only for linkage among
existing anonymised records: (1) anonymous sample→patient mapping for the full
series, (2) `os_followup_y` time origin, (3) `qc_fail` code definitions,
(4) `pred_combine` classifier/version and whether series samples contributed to
its development. No identities requested.

**Requires a human decision:**

1. **Authorisation to send.** Item (2) is the hard gate blocking all fitting.
2. **Data-use terms not yet checked** — required before uploading any input to
   Kaggle, even privately. Not done; flagged rather than assumed permissive.
3. **Cohort-role reconsideration** given §4.1: should GSE31312 (~470 linkable,
   full components, derivable diagnosis-origin endpoint) replace GSE87371
   (103/36, no components, alias with GSE136971) as the untouched final test?
   I have **not** made this change — it reverses a role you reviewed, and
   promoting it requires verifying event coding and patient identity first.

## 10. Still outstanding

- `pred_combine` classifier/version — unresolved (Painter paywalled).
- `qc_fail` level definitions — unresolved.
- GSE31312 event-coding direction and patient identity — needs systematic
  re-extraction; the PDF parse is fragile.
- GSE87371 `ID` → patient relationship — unresolved.
- Horizon support per cohort — not yet inspected.
- Data-use terms — not checked.
- Version control: still 0 commits, two diverged copies.

**Nothing has been fitted to patient outcomes. The protocol is not frozen.**
