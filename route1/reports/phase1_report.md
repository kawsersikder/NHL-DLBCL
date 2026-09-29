# Phase 1 — phase-end report

**Date:** 2026-09-10 · **Machine:** Windows workspace · **Phase:** resolve patient identity and endpoint semantics

---

## 1. Completed

| Task | Work | Artifact |
|---|---|---|
| 1 | Re-parsed all 1,310 sample records with assertions on spellings, missing-value conventions and numeric coercion; cascade re-derived independently of O-076 | `route1/src/phase1_identity_endpoint.py` → `route1/data/metadata/gse181063_samples.csv`, `route1/manifests/eligibility_cascade.csv` |
| 2 | Resolved `os_followup_y` semantics against Lacy and confirmed empirically | `route1/reports/endpoint_dictionary.md` §1 |
| 3 | Characterised `qc_fail` empirically after establishing its documentation is inaccessible | `endpoint_dictionary.md` §4 |
| 4 | Established sample↔patient relationships, quantified repeat samples, eliminated all alternative identifier candidates | `route1/manifests/patient_specimen_map.csv`, `route1/reports/identity_and_eligibility_audit.md` |
| 5 | Attempted to resolve `CHOP-R` delivered-dose semantics | `endpoint_dictionary.md` §5 — unresolved, source paywalled |
| 6 | Investigated all negative and near-zero follow-up records | `endpoint_dictionary.md` §2 |
| 7 | Computed follow-up by three named methods | `endpoint_dictionary.md` §3 |

Downloads recorded with SHA-256 under `route1/data/raw/` (series full record, PubMed abstracts, two PMC XML attempts).

## 2. Verified

- **OS time origin is date of diagnosis; administrative cutoff 31 Dec 2018.** Lacy gives diagnosis window 1 Sep 2004 – 31 Aug 2012 and follow-up "until 31 December 2018", implying a 14.33 y ceiling. Observed max censored follow-up is **14.3190 y** — agreement to ≈5 days. A different origin would not reproduce that ceiling.
- **`Series_pubmed_id` = 32187361 and 30408148 only.** Sha (30523719) is not linked to this series — independent corroboration of D-004.
- **Sha's MHG validation set is EGAS00001002606** ("the core set of 624 patients … by RNA sequencing"), not HMRN. Sha further states MHG "was not trained or determined in any way from the REMoDL-B trial data". **The B1 in-sample concern I raised in Phase 0 is resolved and negative.**
- **556 is a sample count.** 313 eligible samples carry a patient ID → 301 patients (12 duplicates); **243 have no identifier**. Cohort-wide 583 → 534 patients (42 patients ×2, 2 ×3, 1 ×4). Verified ceiling on unique eligible patients: **544**.
- **All alternative identifiers eliminated:** `Sample_title` is the array index `DASLV4_<n>` (asserted), `Sample_supplementary_file` is `"NONE"` for all 1,310, single series ID, and the HMRN/LymphGen annotation block covers exactly the same 583 samples.
- **7 negative follow-up times exist** (min −0.1342 y), all `curative_intent = 0` on supportive/palliative/NEC regimens, all deaths — **none in the eligible set**. Eligible minimum is +0.0110 y and is retained.
- **Follow-up: 8.08 y by reverse Kaplan–Meier** (median of observed times 6.24 y; censored-only 7.63 y). The 6.24 y figure quoted in my earlier handoff is superseded.
- **`qc_fail` is monotone in `probe_detection`** (Spearman −0.251) and **near-independent of outcome** (Spearman 0.028; death rate 0.516 vs 0.515 at levels 0 and 1), so filtering on it does not select on survival. It is confounded with reagent lot (MCS3 62% pass vs MCS4 85%).
- Cascade reproduces the supplied counts exactly at every step.

## 3. Unresolved

| Item | Consequence |
|---|---|
| **Identity of 243 eligible samples (44%).** No identifier in any released field. | **Blocks a clean patient-grouped split over the full 556.** Forces a Phase 4 choice: (a) 301-patient identified subcohort with provable grouping but a DNA-suitability selection, (b) all 556 accepting an unquantified rule-4 violation, or (c) obtain the mapping from the depositors. Recommended framing: (a) primary + (b) prespecified sensitivity, declared before fitting. |
| **`qc_fail` generating criteria undocumented.** Painter is not open access, not in PMC. | Bounded, not eliminated: whatever it encodes is monotone in signal detection and near-independent of outcome. `qc_fail == 0` is the strictest available choice; no new outcome-driven threshold was introduced. |
| **`CHOP-R` delivered dose / attenuation undocumented.** | The study may claim a treatment-matched *label*, not uniform delivered dose. Bounds Phase 8 wording; does not block modelling. |
| **Prior indolent lymphoma / transformation / concurrent FL not recorded.** | ICD-O-3 alone cannot establish *de novo* status. The population must be described as "DLBCL-NOS by ICD-O-3 with curative-intent first-line CHOP-R", **not** as *de novo* DLBCL. |
| Event count for the 301-patient subcohort not yet computed. | Deliberate — it is a Phase 4 population decision and computing it now invites choosing the population by its numbers. |

## 4. Gate

**PARTIAL.**

The pass condition is "eligible unique patients, OS semantics and inclusion rules are defensible." Two of three are met:

- **OS semantics — defensible.** Resolved and empirically confirmed to ~5 days against the published follow-up frame. Survival modelling is **not** blocked.
- **Inclusion rules — defensible.** Cascade re-derived with assertions, exact released spellings, documented missing-value conventions, outcome-independent throughout, and the one QC filter shown not to select on survival.
- **Eligible unique patients — NOT established.** 556 is a sample count with a verified ceiling of 544 and no resolvable floor, because 243 samples carry no identifier.

Not BLOCKED: the endpoint is sound and a defensible identity-safe subcohort (301 patients) exists, so Phase 2 and 3 can proceed in full. Not PASS: the primary population cannot be finalised until the Phase 4 decision above is taken with its trade-off stated.

## 5. Next

**Phase 2 — audit external cohorts and comparator provenance.** All of it is independent of the unresolved identity item, so no work is stalled:

1. Same audit for GSE31312 (498), GSE10846 (420 deposited / 414 design — identify GSM361239–GSM361244), GSE87371 (223, includes PMBL).
2. Cohort lineage table. **Priority:** GSE181063 is HMRN (Leeds/York); Sha's MHG classifier was trained on "an earlier data set" using "all those with BL and DLBCL in our local database for the normalization background" — a Leeds database. Whether that earlier set overlaps HMRN patients is now the live comparator-provenance question, replacing the one D-004 closed. Requires Sha ref 18.
3. Comparator provenance for `pred_combine`, `lymphgen_class`, `modified_hmrn_class`, recording discovery / classifier-training / validation / reanalysis roles separately.
4. Licences and redistribution terms.
5. Propose cohort roles on metadata only, keeping at least one cohort untouched as final test.

## 6. Compute

| Field | Value |
|---|---|
| Kaggle sessions used | **0** |
| GPU used | none — no fitting has occurred |
| Session elapsed | n/a (local metadata work only) |
| Fits completed / remaining | 0 / all |
| Persistence verified | n/a |
| Resume location | n/a |
| Downloads this phase | 3 (series full record, PubMed abstracts, 2 PMC XML), all SHA-256 recorded under `route1/data/raw/` |

No model fitted. No expression matrix downloaded. `GSE181063_RawData.txt.gz` deliberately **not** retrieved — that is Phase 3 work under a declared schema/QC policy.
