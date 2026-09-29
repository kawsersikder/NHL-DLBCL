# Phase 2 — phase-end report

**Date:** 2026-09-10 · **Phase:** audit external cohorts and comparator provenance

---

## 1. Completed

| Task | Work | Artifact |
|---|---|---|
| 1 | Sample-level audit of GSE31312, GSE10846, GSE87371 — fields, patient keys, treatment, outcomes, units, matched N and events | `route1/src/phase2_cohort_audit.py` → `route1/manifests/cohort_catalog.csv` |
| 2 | Cohort lineage table across 7 cohorts/accessions including two not used, recorded so future use cannot be mistaken for independent | `route1/manifests/cohort_lineage.csv` |
| 3 | Comparator provenance with discovery / training / validation / reanalysis roles recorded separately | `route1/manifests/comparator_provenance.csv` |
| 4 | Traced actual sample lineage behind `pred_combine` via Sha 2019 refs 17 and 18 | `route1/reports/external_feasibility.md` §2 |
| 5 | Data use and redistribution constraints | `route1/reports/data_use_terms.md` |
| 6 | Cohort roles proposed on metadata only | `external_feasibility.md` §3 |

Downloads (SHA-256): `GSE31312_gsm_brief.txt` `43efca2d…`, `GSE10846_gsm_brief.txt` `1eacfb10…`, `GSE87371_gsm_brief.txt` `78ada970…`, `pmc_sha2015_PMC4512160.xml` `9b419355…`, `pmc_care2013_PMC3570548.xml` `8b30f4c4…`.

## 2. Verified

- **GSE31312 carries no outcome, treatment or clinical data in GEO** — only `immunohistochemistry subgroup` and `gene expression profiling subgroup`. Unusable without the separate publication supplement.
- **GSE10846's 6 unexplained accessions are exactly GSM361239–GSM361244**, `NA` on every clinical field. 420 deposited = 414 annotated + 6 unusable. Asserted in code. This closes the assessment's open item.
- **GSE10846** R-CHOP-Like subset: 233 samples / 233 distinct patients / **60 deaths**, median follow-up 2.12 y. IPI components present (ECOG 210, stage 226, LDH 192, extranodal 203 of 233; age and sex complete). No real patient duplication cohort-wide.
- **GSE87371 inverts the event indicator: `cens_os = 1` is censored/alive, `0` is died.** Established empirically — `cens_os = 0` median OS 14.8 months versus 40.0 for `cens_os = 1`. Guarded by an assertion in the audit script.
- **GSE87371** is treatment-heterogeneous (R-CHOP21 76, R-ACVBP+Conso 73, R-CHOP14 33, ACVBP 17, R-Mini-CHOP21 13, R-ACVBP+ASCT 11) and contains **20 PMBL**. Treatment-matched, PMBL-excluded subset: **103 patients / 36 events**, `ipi` complete. Times in **months** where the other cohorts use **years**.
- **The D-004 question is closed.** Sha 2019 validated MHG on `EGAS00001002606` (Reddy, 624 patients), not HMRN, and states MHG "was not trained or determined in any way from the REMoDL-B trial data."
- **A better-evidenced replacement question is open.** Sha 2019 ref 18 → Sha 2015 (PMC4512160) developed the BDC/MHG classifier on **HMDS Illumina DASL v3 and v4** paraffin samples; GSE181063 *is* HMDS DASL v4 material (`DASLV4_<n>`). Sha 2019 ref 17 → Care 2013 (PMC3570548) states: "We used two data sets (**GSE32918**, and **GSE10846** …) for classifier development", GSE32918 being an in-house HMDS population-based R-CHOP cohort. **Care and Barrans are the named contributors of GSE181063.**
- **Therefore GSE10846 is disqualified as the untouched final test** for any COO-informed comparator — a documented development role, not a suspicion.
- **`modified_hmrn_class` / `hmrn_class_aic` are in-sample by construction** — Lacy discovered those subtypes on these same 928 HMRN patients.

## 3. Unresolved

| Item | Consequence |
|---|---|
| **Attribution of `pred_combine`** to a named classifier/version. Painter is paywalled and not in PMC. | B1's provenance cannot be stated precisely. |
| **Whether Sha 2015's BDC training samples or Care 2013's GSE32918 overlap GSE181063 patients.** | Decides whether **B1 is partly in-sample**. Direction is known and favourable: an inflated B1 makes the **B2 > B1** contrast *conservative*, so the primary test is not invalidated. But B1's absolute performance must not be reported as an independent estimate of COO/MHG. |
| **GSE87371 `cens_os` coding** confirmed empirically, not against the LYSA publication. | Strong inference, assertion-guarded. Must be confirmed before external evaluation — an inversion would flip every conclusion. |
| **Final test is small: 103 patients / 36 events.** | Adequate to detect gross failure and estimate a paired difference with wide intervals; **not** adequate to certify a small increment. Phase 4 must set the minimum meaningful improvement against this precision. |
| **GSE10846 median follow-up 2.12 y.** | Constrains which evaluation horizons it can support; Phase 4 must prespecify per-cohort horizon handling. |
| **Licence review incomplete** (`data_use_terms.md` §4). | Sufficient to proceed with development modelling on public data under stated constraints; **not** sufficient to authorise any Phase 8 artifact release. |
| Recruitment years not established for GSE10846/87371/31312. | No calendar-overlap check against HMRN's 2004–2012 window has been done. |

## 4. Gate

**PASS.**

The pass condition is "at least one credible independent external cohort has usable endpoints and the clinical fields required for the primary comparison."

**GSE87371 meets it:** usable OS time and event (coding resolved and assertion-guarded), `ipi` complete with age, sex, stage and treatment, and no traced role in developing any comparator used here — a different country and network from both HMRN and LLMPP. It is small, and that limit is now stated in advance rather than discovered later.

The condition is met without substituting an internal random split, and at least one cohort remains genuinely untouched.

**Two roles changed as a result of this phase**, which is the substantive output: GSE10846 moves from candidate final test to **development-validation** because of the Care 2013 development role, and GSE31312 is **deferred** because GEO holds no outcome data for it.

## 5. Next

**Phase 3 — characterise expression platforms and freeze biological inputs.**

1. Inspect **GPL14951** (Illumina WG-DASL HT v4) and **GPL570** (Affymetrix HG-U133 Plus 2.0) annotations; record versions, identifiers, ambiguous and multi-mapping probes, and candidate gene overlap. This is the first measurement of the platform-robustness premise, currently unquantified.
2. Acquire development expression under the §3 constraints of `data_use_terms.md`. **Note the trap already found:** GSE181063's `data_processing` says "normalised using Lumi for R" while its supplementary file is named `GSE181063_RawData.txt.gz` — establish which is which before any transformation, and never log twice.
3. Deterministic, outcome-independent probe-to-gene rule, applied identically across cohorts.
4. Propose 6–8 biological programs with gene-set source and version, scoring formula, direction, minimum coverage and missing-gene handling.
5. Specify the ranking reference universe — within-sample ranks shift when the measured gene universe changes.
6. Define coverage perturbations from the actual GPL14951↔GPL570 difference rather than a random mask.

Also carried into Phase 3/4: **reagent lot (MCS3/MCS4)** is a batch variable in the development cohort, and **36 samples are microdissected** — both are tissue/technical differences to handle explicitly.

## 6. Compute

| Field | Value |
|---|---|
| Kaggle sessions used | **0** |
| GPU used | none — no fitting has occurred |
| Fits completed / remaining | 0 / all |
| Persistence verified | n/a |
| Downloads this phase | 5, all SHA-256 recorded under `route1/data/raw/` |

No model fitted. No expression matrix downloaded from any cohort.
