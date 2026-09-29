# GSE181063 — patient identity and eligibility audit

**Date:** 2026-09-10 · **Phase 1 tasks 1, 3, 4**
**Artifacts:** `route1/data/metadata/gse181063_samples.csv`,
`route1/manifests/patient_specimen_map.csv`,
`route1/manifests/eligibility_cascade.csv`

---

## 1. Headline: 556 is a SAMPLE count, not a patient count

The supervisor plan's warning — "a unique GEO accession is not proof of a unique
patient" — is not hypothetical here. It is measurable, and it is the binding
constraint on Phase 4.

| | Samples | Events | With patient ID | → unique patients | **No patient ID** |
|---|---:|---:|---:|---:|---:|
| Deposited | 1,310 | 683 | 583 | 534 | 727 |
| DLBCL-NOS (ICD-O-3) | 1,042 | 584 | 528 | 487 | 514 |
| `qc_fail == 0` | 885 | 490 | 467 | 434 | 418 |
| Pre-treatment biopsy | 783 | 429 | 427 | 413 | 356 |
| Curative intent | 645 | 298 | 357 | 344 | 288 |
| First-line CHOP-R | 556 | 250 | 313 | 301 | 243 |
| OS present | 556 | 250 | 313 | 301 | 243 |
| OS time > 0 | **556** | **250** | **313** | **301** | **243** |

The last two steps drop nothing: all 1,310 samples carry OS fields, and all 7
negative-time records were already excluded on treatment grounds
(see `endpoint_dictionary.md` §2).

## 2. Repeat samples are real and quantified

Cohort-wide, the 583 samples carrying `pid_pmid_32187361` map to **534 distinct
patients** — **49 extra samples**:

| Samples per patient | Patients |
|---:|---:|
| 1 | 489 |
| 2 | 42 |
| 3 | 2 |
| 4 | 1 |

**Within the eligible set:** 313 samples carry an identifier and resolve to
**301 patients** — 12 extra samples from 12 patients.

## 3. No other identifier exists in the release

Every plausible alternative key was checked and eliminated:

| Candidate | Verdict |
|---|---|
| `Sample_title` | Array index `DASLV4_<n>`. All 1,310 unique, matches the pattern exactly — asserted in code. **Not a patient key.** |
| `Sample_supplementary_file` | Literally `"NONE"` for all 1,310 samples |
| `Sample_series_id` | `GSE181063` for all — no sub-series structure |
| `pid_pmid_32187361` | The only patient identifier. Present for 583 of 1,310 |
| `modified_hmrn_class`, `lymphgen_class`, `hmrn_class_aic` | Present for exactly the same 583 samples — they are the Lacy annotation block, not independent keys |

So the identity of the **243 eligible samples without an identifier cannot be
resolved from this data source.**

## 4. Bounds on unique eligible patients

- **Verified ceiling: 544.** 556 samples minus the 12 confirmed duplicate
  samples.
- **Floor: unknown.** Any of the 243 unidentified samples could be a repeat of
  each other or of an identified patient.

**Indicative only, not a result:** duplication among *identified* eligible
samples runs at 12/313 = 3.8%. Applying that rate to the 243 unidentified would
suggest roughly 9 further duplicate samples, i.e. ~535 unique patients. This is
an extrapolation, and the unidentified subset is **not** a random sample — the
identifier comes from Lacy's targeted-sequencing cohort, where only 928 of 2,358
subjects "had suitable diagnostic material for genetic analysis", so identified
samples are selected on DNA suitability. The rate could differ. **Do not report
535 as a patient count.**

## 5. Consequence for Phase 4 — a genuine trade-off, not a formality

Plan rule 4 requires patient-grouped splits and states that multiple samples
from one patient must never cross a split boundary. Three options, none free:

**(a) Identified subcohort — 301 patients, deduplicated.**
Splits are provably patient-grouped. Cost: discards 44% of eligible samples,
and the retained set is selected on DNA suitability (Lacy's sequencing subset),
which is a tissue-quality selection that must be described, not assumed benign.
Event count falls from 250 to whatever the 301 carry — to be computed in
Phase 4 before any fitting.

**(b) All 556 samples, treating each as a patient.**
Retains power. Cost: violates rule 4 for an unquantified number of patients.
The leak is bounded (≈3.8% of the unidentified set, indicatively ~9 samples) but
not zero and not verifiable. A reviewer can ask, and the honest answer would be
"we could not establish it."

**(c) Obtain the sample→patient mapping from the depositors.**
Contact address is released (`matthew.care@york.ac.uk`, University of York).
**Not actioned:** plan rule 10 prohibits sending email without authorization.
Flagged for the supervisor as the only route that resolves this properly.

A defensible fourth position: run **(a) as the primary** analysis and **(b) as a
prespecified sensitivity**, declaring both before fitting. That is a Phase 4
decision and is deliberately not made here.

## 6. De novo DLBCL-NOS scope — PARTIALLY RESOLVED

`case_diagnostic_subtype_icdo3 == "Diffuse large B-cell lymphoma, NOS"` correctly
excludes the distinct entities that `diagnostic_group == "DLBCL"` would retain
(PMBL 45, T-cell/histiocyte-rich 31, plasmablastic 26, primary CNS 5, plus
Burkitt, Hodgkin and plasmacytoma cases).

**Unresolved:** the plan asks explicitly about **prior indolent lymphoma /
transformation and concurrent follicular lymphoma**. No released field records
prior or concurrent disease. ICD-O-3 subtype alone does **not** establish *de
novo* status, exactly as the plan cautions. Transformed DLBCL has different
biology and prognosis, so its possible presence is a real limitation on the
"de novo DLBCL-NOS" framing.

**Consequence:** the population should be described as *DLBCL-NOS by ICD-O-3 with
curative-intent first-line CHOP-R*, **not** as *de novo* DLBCL, unless the
depositors can confirm transformation status.

## 7. Cascade validation (task 1)

Re-derived independently of the earlier O-076 run, with assertions rather than
silent coercion. The parse asserts: 1,310 samples; unique GSMs; single platform
GPL14951; `Sample_title` matches `DASLV4_<n>`; the exact released spellings
`"Diffuse large B-cell lymphoma, NOS"`, `"CHOP-R"`, `"Yes"` all present;
`os_status` ∈ {0,1}. **One assertion fired on first run** and caught an ordering
bug of mine (a numeric check placed before type coercion) rather than letting a
wrong number through.

Missing-value conventions applied before numeric coercion:
`""`, `NA`, `na`, `N/A`, `unknown`, `Unknown`,
`"Treatment data not available"` → NaN. No non-numeric residue was reported
during coercion of any numeric field, so the release is internally clean on
those columns.

Counts reproduce the supplied cascade exactly at every step (1,042 / 885 / 783 /
645 / 556 samples; 584 / 490 / 429 / 298 / 250 events).
