# Phase 3R-A — source corrections and evidence grading

**Date:** 2026-09-11
**Responds to:** supervisor review of 2026-09-11
**Nature:** append-only correction. The original Phase 0–3 reports are preserved
unedited; this document records what was wrong, what the evidence actually
supports, and at what grade.

## Evidence grades used throughout

| Grade | Meaning |
|---|---|
| **DOCUMENTED** | Explicit statement in a primary source, quoted verbatim with location |
| **COMPUTED** | Direct computation on a retrieved artifact, reproducible from a named script |
| **INFERRED** | Analytical observation consistent with evidence but not stated by any source |
| **WITHDRAWN** | Previously asserted by me; retracted |

---

## 1. WITHDRAWN — the B4 mask is a no-op, not a 1.9% perturbation

**My claim (Phase 3):** the realistic platform mask perturbs 1.9% of program
genes (26 of 1,361), so B4 ≈ B3.

**Correct position:** under my own stated rules the mask removes **exactly
zero** eligible input genes. `representation.yaml` defines

- ranking universe `U` = development ∩ external measured genes
- primary mask `M` = development − external measured genes

so `U ∩ M = ∅` by construction. Once inputs are restricted to `U`, applying `M`
is a null operation.

**COMPUTED verification:**

```
|U| = 15,647    |M| = 5,171    |U ∩ M| = 0
masking M removes 0 of 15,647 universe genes
```

**My error:** I measured lost genes against `on_dev` (the development platform)
rather than against the model's actual input set (`U`). Wrong denominator. The
1.9% figure describes a quantity no model would ever see. The supervisor's
argument is stronger than mine and supersedes it: B4 was not a weak test, it
was not a test at all.

**Action:** B4 withdrawn from the ladder per supervisor decision 2.1 option (b).
It will **not** be run to manufacture a null. A synthetic assertion proving the
no-op is required in Phase 3R-C. Random dropout inside `U` is explicitly *not* a
repair — it would be a different perturbation with no claim to represent the
actual platform move.

---

## 2. WITHDRAWN — Sha 2015 did not train the BDC classifier on HMDS DASL data

**My claim (Phase 2):** "Sha 2015 developed the BDC classifier on HMDS Illumina
DASL v3 (41 BL, 206 DLBCL) and v4 (70 BL, 169 DLBCL) paraffin samples", making
overlap with GSE181063 "plausible and material".

**DOCUMENTED correction**, Sha 2015 (PMC4512160), Methods, "Data sets":

> "Five public data sets were downloaded from the Gene Expression Omnibus.
> GSE4732 was split into two subsets derived from different array platforms,
> here referred to as GSE4732_p1 and GSE4732_p2. **Classifier development
> employed GSE4732_p1 and GSE4475**, and the other data sets were used in
> testing transferability of classifiers."

And on the 28-gene list:

> "the 28 genes for which measurements are available in GSE4732_p1 and are part
> of the classifier used in GSE4475 … The 28 gene list matches the performance
> of the full list in both data sets … and was selected for future work."

GSE4732_p1 is Dave et al.; GSE4475 is Hummel et al. The HMDS DASL v3/v4 rows I
cited are entries in the paper's **Table 1 dataset summary** — they were used
for application and transferability evaluation, not as the supervised training
set.

**My error:** I inferred the training cohort from a table listing, and from
institutional provenance (Care/Barrans being the GSE181063 depositors). Same
failure mode as the PMID 30408148 error: inference from proximity instead of
reading the specific statement. This is the second attribution error of this
kind in this project.

**Revised position:** the supervised training set for BDC is
**GSE4732_p1 + GSE4475**, neither of which is HMRN. HMDS DASL material
contributed evaluation and normalisation work. That is a real development
exposure worth recording, but it is **not** equivalent to the DASL patients
being the classifier's training cohort, and I must not label it so.

---

## 3. WITHDRAWN — "inflated B1 makes B2−B1 conservative"

**My claim (Phases 2 and 3):** if B1's labels are partly in-sample, B1 is
optimistically strong, which makes the B2 > B1 contrast conservative.

**Correct position:** deleted. Correlated errors between B1 and B2 (which shares
B1's inputs), shared representations and selection effects can move a paired
contrast in **either** direction. The claimed directionality was asserted, never
demonstrated. No directional reassurance should appear in the protocol.

Also softened: clustering performed on a full cohort does not by itself mean
survival labels trained the clustering. The resulting representation is
nonetheless not independent of that cohort. Both statements now appear in that
form.

---

## 4. CORRECTED — GSE87371 does not carry the five IPI components

**My claim (Phase 2):** `cohort_catalog.csv` records
`has_ipi_components: True` for GSE87371.

**COMPUTED correction.** The complete characteristic set for GSM2328918 is:

```
ID, diagnosis, age, Sex, Stage, treatment, ipi, age_adjusted_ipi,
pfs_time, cens_pfs, os_time, cens_os, coo
```

Present: age, stage, composite `ipi`, `age_adjusted_ipi`.
**Absent: ECOG performance status, LDH, number of extranodal sites.**

So a five-component clinical model **cannot** be applied unchanged to this
cohort. This independently supports supervisor decision 2.4: the primary
transportable baseline must be **IPI-based (R0)**, not component-based.

For contrast, GSE10846 *does* carry components — ECOG 210/233, stage 226/233,
LDH ratio 192/233, extranodal 203/233, with age and sex complete — so the two
external cohorts are **not** interchangeable for R0's feature set.

---

## 5. REGISTERED — GSE87371 and GSE136971 are the same samples

**COMPUTED:** all 223 samples carry both `!Sample_series_id = GSE87371` and
`!Sample_series_id = GSE136971`.

**Action:** recorded in `cohort_lineage.csv` as an alias. GSE136971 must never
be treated as a second independent cohort.

---

## 6. UPGRADED to DOCUMENTED — GSE87371 endpoint coding

My Phase 2 conclusion was reached empirically (median OS 14.8 vs 40.0 months).
It is correct, and now has a direct source. **DOCUMENTED**, GSM2328918
`!Sample_description` block, verbatim:

```
ID: sample ID
AGE: age at diagnosis
PFS_TIME: duration of progression free survival (PFS) in months
CENS_PFS: coded as 0 if PFS event, 1 if not
OS_TIME: duration of overall survival (OS) in months
CENS_OS: coded as 0 if OS event, 1 if not
```

**Conversion rule:** `death_event = 1 − cens_os` for valid binary entries;
non-binary/unknown remain missing (2 samples). Archived at
`route1/data/raw/GSM2328918_full.txt`,
SHA-256 `038c1674bfd044f6aeb9dd2695d0d25eb3321eaf75ec7714decc76292d7deba2`.

**Also DOCUMENTED and consequential:** `ID` is described as **"sample ID"**, not
a patient ID. My Phase 2 catalog listed it as the patient key on the grounds
that all 223 values are distinct. Distinctness is not identity. GSE87371's
patient structure is now **UNRESOLVED**, and must receive the same discipline
applied to GSE181063.

**Also:** "duration of overall survival" establishes neither diagnosis nor
treatment-initiation origin. External time origin is **UNRESOLVED**.

---

## 7. DOWNGRADED — OS time origin in GSE181063 is supported, not established

**My claim (Phase 1):** "RESOLVED … the time origin is date of diagnosis …
survival modelling is not blocked."

**Correct position:** the observed maximum censored follow-up of **14.3190 y**
against Lacy's implied ceiling of **14.33 y** (diagnosis window 1 Sep 2004 –
31 Aug 2012, mortality follow-up to 31 Dec 2018) is **compatible** with a
diagnosis origin. It does not exclude other origins, and it does not
demonstrate which field generated the recorded times.

**Restated as:** *supported inference; direct field definition pending.*
Grade **INFERRED**, not DOCUMENTED.

Still required: an explicit publication/supplement definition, analysis-code
construction, or depositor statement linking `os_followup_y` to time zero.
Per supervisor §3.1, **survival models are not to be fitted until the estimand
is defensible.**

---

## 8. DOWNGRADED — the seven negative follow-up values

**My claim:** "a registry-linkage artifact … death recorded before the
diagnosis date."

**Correct position:** that is a hypothesis, not an observation. Supported
statement: **seven records have negative OS intervals (min −0.1342 y) requiring
source clarification.** What is genuinely COMPUTED is that all seven are
`curative_intent = 0` on supportive/palliative/NEC regimens, all are deaths, and
**none is in the eligible set** — they are removed by prespecified treatment
filters, not by any outcome-driven rule. Early *positive* deaths (minimum
+0.0110 y) remain retained under the frozen eligibility rules.

---

## 9. DOWNGRADED — QC and normalisation claims

| My claim | Corrected position |
|---|---|
| `qc_fail` is "monotone in `probe_detection`" | Spearman −0.251 with ordered group means (0.679/0.629/0.587/0.582/0.449) shows an **association**, not strict monotonicity and not a code definition. **UNRESOLVED:** what each level of `qc_fail` encodes. |
| Filtering on `qc_fail` "does not select on outcome" | Overstated. Similar death fractions and ρ=0.028 do not establish outcome independence, which concerns how the rule was created and applied; censoring and patient characteristics also matter. Restated as: **no strong association with death was observed in these data**. Per supervisor, no further QC/outcome correlation testing will be run. |
| `probe_detection` = fraction with detection p<0.01 | **Supported on 5 arrays to 6 d.p.** Grade COMPUTED-partial. To be validated across the available matrix in 3R-C. It explains `probe_detection`; it does **not** explain all levels of `qc_fail`. |
| "Not quantile-normalised" | Unequal sorted columns exclude *global* quantile normalisation across these samples. They do **not** exclude batchwise or other prior processing. Restated as: **observed values are not on a common quantile scale; processing provenance beyond "Lumi" remains unresolved.** |
| Within-sample ranks handle the platform difference | Overstated. Ranks remove a common monotone per-sample transformation. They do **not** correct probe affinity, background, saturation, batch-dependent ordering, or all platform effects. Also noted: log2 before pure ranking does not change rank order, though it can affect any preceding multi-probe aggregation. |

---

## 10. RECONCILED — 26 versus 25

**COMPUTED:** 26 lost program-gene **memberships** correspond to 25 **unique**
genes. `NOP56` belongs to two programs and is counted twice. Both figures are
reported with explicit denominators, verified by set operations in
`phase3R_representation_checks.py` (C2): **26 memberships out of 1,361
program-gene rows on the development platform; 25 unique genes out of 1,174
distinct on-development program genes.**

*(Correction to this document, 2026-09-11: an earlier draft of this section
gave the unique-gene denominator as 1,335. That figure was not computed — it
was written from recollection. The computed value is 1,174.)*

---

## 11. CORRECTED — patient bounds statement

**My claim:** "no resolvable floor."

**Correct position:** if the 301 identifiers denote distinct true patients, the
eligible records represent **at least 301 and at most 544** patients. Neither
bound resolves the 243 unidentified samples. The identifier semantics
themselves still require verification before 301 is treated as a patient count.

---

## 12. Program naming — to be applied in 3R-C

Feature names will be changed to the literal measured signatures:

| Old | New |
|---|---|
| `inflammatory_macrophage` | `hallmark_inflammatory_response` |
| `stromal_ecm` | `hallmark_emt` |
| `interferon_antigen_presentation` | `hallmark_ifng_response` |
| `proliferation_e2f` | `hallmark_e2f_targets` |
| `proliferation_myc` | `hallmark_myc_targets_v1` |
| `nfkb_signalling` | `hallmark_tnfa_signaling_via_nfkb` |
| `angiogenesis` | `hallmark_angiogenesis` |
| `oxidative_phosphorylation` | `hallmark_oxphos` |

Inflammation is not a macrophage-specific assay; EMT in lymphoma tissue does not
establish malignant-cell EMT; IFN-γ response is not a direct measurement of
antigen presentation. Interpretation requires evidence beyond a name.

Per supervisor §3.5, the current sets are **retained as provisional measured
programs**. The ≥10-gene rule will not be used to reject a set on principle, and
no set will be added or dropped to manufacture a masking effect.

---

## 13. Gate table, corrected

| Phase | My earlier claim | Supervisor status (adopted) |
|---|---|---|
| 0 — workspace | PASS | **PASS for local continuation.** No claim that the copies are reconciled. |
| 1 — identity/outcomes | PARTIAL | **PARTIAL.** OS origin is INFERRED, not resolved. |
| 2 — external cohorts | PASS | **PARTIAL.** Endpoint origins, patient IDs, shared predictors, subtype provenance and data terms all still open. |
| 3 — representation | PASS | **PARTIAL.** Aggregation undefined, mask contradiction, coverage accounting, overstated QC/normalisation claims. |

**I will not describe Phases 0–3 as collectively passed.** My Phase 2 and Phase 3
PASS calls are withdrawn in favour of PARTIAL.

---

## 14. Outstanding source retrievals

| Item | Status |
|---|---|
| GSE31312 clinical supplement `GSE31312_Microarray_and_clinical_data_DLBCL_475_cases_PMID_22437443.pdf.gz` | **Not yet retrieved** — bounded attempt required before calling the cohort clinically unavailable |
| `os_followup_y` time-origin definition | Not found; Painter paywalled (Europe PMC `isOpenAccess=N, inEPMC=N, inPMC=N`) |
| `qc_fail` code definitions | Not found |
| `pred_combine` classifier + version | Not found |
| GEO / MSigDB data-use terms for Kaggle upload | **Not checked** — required before uploading any input, even privately |
| GSE87371 `ID` → patient relationship | Unresolved |
