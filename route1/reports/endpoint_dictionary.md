# GSE181063 — endpoint and field dictionary

**Date:** 2026-09-10 · **Phase 1 task 2, 3, 5, 6, 7**

Source of every definition below is stated. Where a definition could not be
obtained, that is recorded as unresolved rather than inferred.

## Provenance

| Artifact | Value |
|---|---|
| Metadata dump | `data/raw/gse181063/GSE181063_gsm_brief.txt` |
| SHA-256 | `cafd3057122e7a887581d089a7d729c6382bfa57bbfd3369aeb2a4d336d00466` |
| Series full record | `route1/data/raw/GSE181063_series_full.txt` (SHA-256 `b5c20e81a34651648e35d07eece6f7bdcefaf69f9abf38d92774fa14c839c274`) |
| PubMed abstracts | `route1/data/raw/pubmed_abstracts_30408148_30523719_32187361.txt` (SHA-256 `cb602da4ee84702e2dcf0ac4ae231d53aa3779febf8743691fbbf9d173964b3d`) |
| Retrieved | 2026-09-10 |

**The series names its own citations.** `!Series_pubmed_id = 32187361` and
`= 30408148` — Lacy and Painter, both HMRN. Sha (30523719) is **not** linked to
this series, independently corroborating D-004.

---

## 1. Overall survival — RESOLVED

| Field | Meaning | Source |
|---|---|---|
| `os_followup_y` | Time from **date of diagnosis** to death or censoring, in **years** | Lacy (PMID 32187361) + empirical confirmation below |
| `os_status` | `1` = died, `0` = censored alive. Verified to contain only `{0, 1}` | Released values, asserted in code |

### Evidence, and why this is a confident link rather than an assumption

Lacy states the HMRN cohort comprised subjects "newly diagnosed with DLBCL
between **1 September 2004 and 31 August 2012**", and that "all patients were
followed up for mortality until **31 December 2018**."

If the time origin is date of diagnosis and the administrative cutoff is
2018-12-31, the **maximum attainable follow-up** is
2004-09-01 → 2018-12-31 = **14.33 years**.

Observed in the data:

| Quantity | Value |
|---|---|
| Max `os_followup_y`, censored patients | **14.3190 y** |
| Lacy-implied ceiling | **14.33 y** |
| Discrepancy | ≈ 0.01 y (≈ 5 days) |

The observed maximum sits just inside the implied administrative ceiling, which
is exactly what a diagnosis-origin/fixed-cutoff design produces (the earliest
patient was diagnosed ~5 days after the window opened). A different origin — for
example end of treatment, as the prior DLBCL-Morph study uses — would not
reproduce this ceiling. Maximum among *deaths* is lower (13.1526 y), as
expected.

**Consequence:** survival modelling is **not** blocked on endpoint semantics.

### Hard constraint

The completed DLBCL-Morph study measures OS from **end of treatment**. These are
different estimands and **must not be pooled or compared as though equivalent**.
Recorded in `route1/configs/project.yaml` as
`do_not_merge_with: dlbcl_morph_end_of_treatment_os`.

---

## 2. Negative and near-zero follow-up times — RESOLVED

`os_followup_y` has **no zero values** and **7 negative values**
(min −0.1342 y ≈ −49 days), i.e. death recorded before the diagnosis date. This
is a registry-linkage artifact, not a survival time.

All 7 share a coherent profile — every one is `curative_intent = 0` with a
supportive/palliative or NEC regimen, and every one is a death:

| GSM | `os_followup_y` | regimen | curative intent |
|---|---:|---|---:|
| GSM5482802 | −0.0246 | Supportive/palliativeonly | 0 |
| GSM5483546 | −0.0356 | NEC | 0 |
| GSM5483691 | −0.0548 | Supportive/Palliative/None | 0 |
| GSM5483908 | −0.0767 | Supportive/palliativeonly | 0 |
| GSM5484001 | −0.0055 | Supportive/palliativeonly | 0 |
| GSM5484054 | −0.1342 | Supportive/palliativeonly | 0 |
| GSM5484094 | −0.0027 | Supportive/Palliative/None | 0 |

**None of the 7 is in the eligible set.** They are removed by the prespecified
curative-intent and regimen filters, on treatment grounds, before any outcome
was examined. The explicit `os_time_positive` cascade step therefore drops **0**
additional samples — it is retained as an assertion, not a filter.

Minimum eligible follow-up is **+0.0110 y** (≈ 4 days), a genuine early death
that is **retained**. Per the plan, early deaths are not discarded.

15 samples cohort-wide have follow-up ≤ 0.01 y and all are deaths; 8 of those
are outside the eligible set for other reasons.

---

## 3. Follow-up duration — RESOLVED, method must be named

Three defensible-sounding statistics differ materially on the eligible set:

| Method | Value |
|---|---|
| Median of observed times, all patients | 6.24 y |
| Median of observed times, censored only | 7.63 y |
| **Reverse Kaplan–Meier (report this)** | **8.08 y** |

Range 0.0110 – 14.3190 y. Reverse Kaplan–Meier is the correct summary of
follow-up duration because the median of observed times is pulled down by
deaths. **An earlier internal report quoted 6.24 y; that figure is superseded.**

---

## 4. `qc_fail` — PARTIALLY RESOLVED

**The generating criteria are not documented** in the GEO series record, the
sample records, or any accessible publication. Painter (PMID 30408148), the
DASL/COO paper most likely to define it, is a *Br J Haematol* Letter that is not
open access and not in PMC (Europe PMC: `isOpenAccess = N`, `inEPMC = N`,
`inPMC = N`, no PMCID). It was therefore characterised empirically instead.

Distribution: `0` → 1,099 · `1` → 136 · `2` → 58 · `3` → 13 · `4` → 1 · `5` → 3.

**It behaves as a count of failed technical QC criteria:**

| `qc_fail` | n | mean `probe_detection` |
|---:|---:|---:|
| 0 | 1,099 | 0.6794 |
| 1 | 136 | 0.6291 |
| 2 | 58 | 0.5874 |
| 3 | 13 | 0.5817 |
| 5 | 3 | 0.4486 |

Monotone decreasing in signal detection (Spearman −0.251).

**It is not outcome-selective**, which is the property that matters for using it
as a filter: Spearman vs `os_status` = **0.028**; death rate 0.516 at
`qc_fail = 0` versus 0.515 at `1`. Filtering on `qc_fail == 0` therefore does
not select on survival.

**It is confounded with reagent lot** — MCS3 passes 32/52 (62%) versus MCS4
1,067/1,258 (85%). Phase 3 must treat reagent lot as a batch variable.

**Residual risk:** without the criteria list, it cannot be excluded that
`qc_fail` encodes something partly non-technical. The empirical evidence bounds
the consequence: whatever it encodes is monotone in array signal detection and
near-independent of outcome. `qc_fail == 0` is the strictest available choice and
no new outcome-driven threshold was introduced.

---

## 5. `CHOP-R` — UNRESOLVED

`firstline_regimen == "CHOP-R"` (828 samples cohort-wide) is a **regimen label**.
What it denotes in delivered terms — cycle count, dose intensity, documented
attenuation for older or frailer patients, intrathecal or radiotherapy
consolidation — is **not** recorded in any released field, and Painter is
paywalled.

**Consequence:** the study may state a treatment-matched *label*, not a uniform
delivered dose. Any claim of dose uniformity would be unsupported. This does not
block modelling; it bounds the wording, and it is a limitation for Phase 8.

Related released regimens kept out of the primary population and available as
prespecified secondary populations: `CHOP-R/Bortezomib` (34), `CHOP` (29).

---

## 6. Other fields used

| Field | Note |
|---|---|
| `case_diagnostic_subtype_icdo3` | ICD-O-3 subtype. **Use this, not `diagnostic_group`** — the latter's "DLBCL" value (1,149) still contains PMBL (45), T-cell/histiocyte-rich (31), plasmablastic (26) and primary CNS (5) |
| `sample_pre_active_treatment` | `Yes` / `No` / `Treatment data not available` — the third is treated as missing, not a category |
| `curative_intent` | `1` / `0` |
| `pred_combine` | GCB / ABC / UNC / MHG. Out-of-sample application of the MHG classifier — see D-004 |
| `probe_detection` | Proportion of probes detected; technical quality |
| `reagent` | MCS3 / MCS4 — batch variable |
| `microdissection` | TRUE for 36 samples; a tissue-handling difference to check in Phase 3 |
| Data processing | "Data were normalised using **Lumi** for R." The series supplementary file is nonetheless named `GSE181063_RawData.txt.gz` — **do not assume it is normalised, and do not log-transform twice** |
