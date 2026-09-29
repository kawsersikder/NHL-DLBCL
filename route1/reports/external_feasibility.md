# Phase 2 — external cohort feasibility and comparator provenance

**Date:** 2026-09-10
**Manifests:** `cohort_catalog.csv`, `cohort_lineage.csv`, `comparator_provenance.csv`
**Downloads:** `route1/data/raw/GSE{31312,10846,87371}_gsm_brief.txt`, `pmc_sha2015_PMC4512160.xml`, `pmc_care2013_PMC3570548.xml` — SHA-256 in the Phase 2 report

---

## 1. Candidate cohort audit

| | GSE31312 | GSE10846 | GSE87371 |
|---|---|---|---|
| Deposited | 498 | 420 | 223 |
| Platform | GPL570 | GPL570 | GPL570 |
| Patient key | **none** | `Individual` (414) | `ID` (223) |
| OS time / event in GEO | **no / no** | yes / yes | yes / yes |
| IPI components | **no** | yes (some missing) | yes (`ipi` 0 missing) |
| Time units | — | **years** | **months** |
| Treatment-matched N | — | 233 (R-CHOP-Like) | 103 (R-CHOP21/14, non-PMBL) |
| Events in matched set | — | **60** | **36** |
| Usable from GEO alone | **NO** | yes | yes |

### GSE31312 — not usable from GEO

Its sample records contain exactly two fields: `immunohistochemistry subgroup`
and `gene expression profiling subgroup`. **There is no survival, treatment,
or clinical variable in GEO.** The 475-case clinical supplement referenced in
the assessment lives with the publication, not the deposit. Using this cohort
requires obtaining and joining that supplement, which is unverified work of
unknown licence status. **Excluded from the current role assignment**; it
remains a later option.

### GSE10846 — usable, and the 6 orphans are resolved

`Chemotherapy` splits 233 R-CHOP-Like / 181 CHOP-Like / 6 `NA`. **The 6 NA
samples are exactly GSM361239–GSM361244** — the accessions the assessment
flagged as unexplained. They carry `NA` for every clinical field and have no
outcome data, so 420 deposited = 414 annotated + 6 unusable. Asserted in code.

No real patient duplication: 414 annotated samples map to 414 distinct
`Individual` values, and the R-CHOP subset is 233 samples / 233 patients.

R-CHOP subset: **60 deaths**, median follow-up **2.12 y** (max 10.29) — short.
IPI components present at 210/233 ECOG, 226/233 stage, 192/233 LDH ratio,
203/233 extranodal sites, with age and sex complete.

### GSE87371 — usable, best-annotated, and carries an inverted event indicator

**`cens_os = 1` means CENSORED/ALIVE and `cens_os = 0` means DIED** — the
inverse of `os_status` in GSE181063. Established empirically: the `cens_os = 0`
group has median OS **14.8 months** versus **40.0** for `cens_os = 1`, and
deaths are observed earlier than censoring. 53 deaths / 168 censored / 2
unknown cohort-wide (24% mortality, consistent with a trial cohort at ~40
months' median follow-up).

This is the same class of trap as the HANS encoding this project already hit:
reading it by convention would invert every conclusion. The audit script
asserts the relationship so a later edit cannot silently flip it.
**Confirmation against the LYSA publication is still outstanding** — the
inference is strong but empirical.

Treatment is heterogeneous and mostly *not* R-CHOP: R-CHOP21 76,
R-ACVBP+Conso 73, R-CHOP14 33, ACVBP 17, R-Mini-CHOP21 13, R-ACVBP+ASCT 11.
ACVBP is a French regimen, not R-CHOP. `coo` includes **20 PMBL**, confirming
the assessment's warning to apply DLBCL scope explicitly.

Treatment-matched, PMBL-excluded subset: **103 patients, 36 events**.
Times are in **months**; GSE181063 and GSE10846 are in **years**.

---

## 2. Comparator provenance — the significant Phase 2 finding

Task 4 asked me to trace actual sample lineage rather than assert
contamination. Doing so closed the question D-004 raised and **opened a
different, better-evidenced one**.

**Closed.** Sha 2019 validated MHG on `EGAS00001002606` ("the core set of 624
patients … by RNA sequencing" — Reddy et al.), *not* HMRN, and states MHG "was
not trained or determined in any way from the REMoDL-B trial data".

**Opened.** Tracing Sha 2019's reference 18 leads to the classifier's actual
origin, and it points back at Leeds:

| Comparator | Where the classifier was built | Overlap risk with GSE181063 |
|---|---|---|
| **MHG** | Sha **2015** (*Genome Med*, PMC4512160) developed the BDC classifier on **HMDS Illumina DASL v3 (41 BL, 206 DLBCL) and v4 (70 BL, 169 DLBCL)** paraffin samples | **Plausible and material.** GSE181063 is HMDS DASL v4 material — its sample titles are literally `DASLV4_<n>` |
| **COO** | Care **2013** (*PLoS One*, PMC3570548): "We used two data sets (**GSE32918**, and **GSE10846** …) for classifier development", where GSE32918 is "a data set in-house … from a population-based cohort treated with R-CHOP" at HMDS Leeds | **Plausible.** Same institution and specimen service as GSE181063, earlier DASL version |

**Care and Barrans, the authors of both classifier papers, are the named
contributors of GSE181063.** So `pred_combine` was very likely produced by
Leeds-internal classifiers whose development sets may include patients now in
this cohort. I could not verify this either way: the attribution of
`pred_combine` to a specific method is not stated in the GEO record, and
Painter — the series' own COO citation — is paywalled and not in PMC.

### Two consequences

**(a) GSE10846 cannot be the untouched final test for any COO-informed
comparator.** It was used to *develop* the Care COO classifier. This is a
direct, documented conflict, not a suspicion.

**(b) B1 may be optimistically strong on GSE181063.** If the COO/MHG labels
come from classifiers trained partly on these patients, B1's apparent
performance is inflated. The direction matters: an inflated B1 makes the
incremental test **B2 > B1 conservative** — harder to pass, not easier. So this
does not invalidate the primary contrast, but it **does** mean B1's absolute
performance must not be reported as an independent estimate of what COO/MHG
achieves.

**(c) `modified_hmrn_class` and `hmrn_class_aic` are in-sample by
construction** — Lacy discovered those subtypes on these very patients
(n = 928 HMRN). They are not an out-of-sample comparator here and can only
support a matched genotyped-subset description.

---

## 3. Proposed cohort roles — metadata only, no outcomes inspected

| Role | Cohort | Basis |
|---|---|---|
| Development (provisional) | **GSE181063** | 556 samples / 250 events; Phase 1 identity caveat stands |
| Development-validation | **GSE10846 R-CHOP** (233 / 60) | Usable endpoints and IPI components, but disqualified as final test by the Care 2013 development role |
| **Untouched final test** | **GSE87371 R-CHOP21/14, non-PMBL** (103 / 36) | Independent network (LYSA, France), distinct from HMRN and LLMPP, no classifier-development role traced |
| Deferred | GSE31312 | No outcome data in GEO |
| Not used | GSE32918, REMoDL-B, EGAS00001002606 | Recorded in lineage so future use cannot be mistaken for independent |

**The final test is small: 103 patients, 36 events.** That is a real precision
limit and must be stated before fitting, not discovered afterwards. It is
adequate to detect gross failure and to estimate a paired difference with wide
intervals; it is not adequate to certify a small increment. Phase 4 must set
the minimum meaningful improvement against *this* precision.

GSE10846's short median follow-up (2.12 y) further limits which evaluation
horizons it can support — Phase 4 must prespecify horizon handling per cohort.

---

## 4. Unresolved

1. **Attribution of `pred_combine`** to a named classifier and version — blocked by Painter's paywall.
2. **Whether Sha 2015's BDC training samples or Care 2013's GSE32918 overlap GSE181063 patients** — requires those papers' sample lists; the deciding evidence for B1's in-sample status.
3. **GSE87371 `cens_os` coding** — established empirically, not yet confirmed against the LYSA publication.
4. **GSE31312 clinical supplement** — not obtained; licence unknown.
5. **Recruitment years for GSE10846, GSE87371, GSE31312** — not established, so no calendar-overlap check against HMRN's 2004–2012 window has been done.
