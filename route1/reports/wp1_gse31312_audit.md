# WP1 — GSE31312 source-auditable extraction and reconciliation

**Date:** 2026-09-11
**Scripts:** `route1/src/wp1_gse31312_extract.py`, `wp1_gse31312_reconcile.py`
**Source:** `GSE31312_clinical_supplement.pdf` (from `…pdf.gz`, SHA-256 of gz
`f905c7ba4517df7dfc1d38f8cba91c3b89251487085194637a7bad6b62c34128`;
decompressed PDF SHA-256 `ac7599977a55e57a51889add5914ca4f76c971565dc37335ddd9af319beb8857`)

**Headline: this cohort has a VERIFIED diagnosis-origin endpoint.** Derived
diagnosis-to-endpoint durations reproduce the released OS field for **475/475
cases within 0.10 months, median absolute difference 0.0003 months (~13
minutes)**. That is the evidentiary standard the study has been blocked on for
GSE181063, and here it is met by derivation rather than inference.

---

## 1. Extraction (3A)

Two tables, joined **only** on `Case #`:
table 1 pages 0–8 (clinical), table 2 pages 9–17 (outcome).

| Check | table 1 | table 2 |
|---|---|---|
| Rows | 475 | 475 |
| Unique `case_id` | 475 | 475 |
| Duplicated | 0 | 0 |
| Missing from 1…475 | none | none |
| Rows/page | 55, 56×7, 28 | 55, 56×7, 28 |
| Status `ok` | 172 + 301 flagged | **475 (all ok)** |

**Join on `case_id`, `validate="one_to_one"`: 475 matched, 0 orphans either
side.** No row- or page-position joining was used anywhere.

### Independent engine comparison

My first attempt compared engines **line-by-line** and reported 1,886/2,163
differences. **That comparison was invalid** — PyMuPDF segments lines
differently (1,411 vs 475 lines), so it measured layout, not content. Redone as
a layout-independent token-multiset comparison per page:

> **21 differing tokens across all 18 pages, every one of them on pages 0 and 9
> — the two header rows.** The engines agree exactly on all 16 data pages.

Agreement is recorded as evidence, not proof; flagged rows were inspected
individually.

### Flagged rows, all resolved

- **2 `token_mismatch` (cases 210, 337).** Real data gap: the `Bulky code` cell
  is blank in the source, e.g. `… low, int-low 0 0 CR 6/2/2005 3/4/2009` where
  every other row reads `… low, int-low nop 1 1 CR …`. The anchored parse
  detected the shift rather than absorbing it. `bulky_code` set to missing; no
  value invented.
- **301→303 `dates_ambiguous`.** Resolved empirically — see §3.

Discrepancy table with page references: `gse31312_extraction_discrepancies.csv`.

## 2. Linkage and identity (3B)

The supplement's `GEO Depository #` is literally `DLBCL GEP data N####`,
identical in form to GEO `!Sample_title`.

| | Count |
|---|---:|
| Supplement IDs | 475 |
| GEO IDs | 498 |
| **Linked** | **470** |
| Supplement-only | 5 — `N0053, N0109, N0172, N0241, N0268` |
| GEO-only | 28 |

Uniqueness assertions **passed**: `geo_sample_id` and `gsm` are each unique
within the linked set. No fuzzy matching was used; the 5 and 28 unmatched
records are listed rather than absorbed.

**Still unresolved:** whether `Case #` denotes one patient, and whether repeat
biopsies/arrays exist. The supplement does not define it, and 475 sequential
case numbers are consistent with either reading. **Not promoted to a verified
patient key.**

## 3. Endpoint semantics and date reconciliation (3C)

### 3.1 `OScensor` direction — established by contingency, not by medians

| | `os_censor=0` | `os_censor=1` |
|---|---:|---:|
| No death date | 0 | 303 |
| **Death date present** | **172** | **0** |

A perfectly clean 2×2 with zero off-diagonal entries. **`os_censor = 0` means
died; `1` means censored** — matching the documented GSE87371 convention.
Note there are **no** deaths lacking a date, so the direction is not confounded
by that case. `death_event = 1 − os_censor`.

### 3.2 Date ambiguity resolved against the released fields

Tolerance was fixed **before** inspecting anything: ±0.10 months (~3 days),
set by source precision (durations quoted to 3 decimals, dates day-resolution).

| | Rows |
|---|---:|
| 2 dates (ambiguous) | 303 |
| 3 dates (unambiguous) | 172 |
| Fewer than 2 | 0 |
| **2-date rows whose 2nd date matches released OS** | **303 (all)** |
| 2-date rows matching neither OS nor PFS | **0** |

So the second date is the last-follow-up/death date in every ambiguous row.
This was determined by agreement with the released duration, not assumed.

### 3.3 Diagnosis-origin OS reproduces the released OS

| | Value |
|---|---:|
| Comparable rows | **475 / 475** |
| Agreeing within 0.10 months | **475 (100%)** |
| Median absolute difference | **0.0003 months** |
| Outside tolerance | **0** |
| Not comparable | **0** |

**This certifies both the extraction and the estimand:** the released OS in
GSE31312 is measured from **date of diagnosis**. The endpoint is derived and
verified, not inferred from a maximum-follow-up argument.

### 3.4 Integrity checks — all retained, none discarded

| Check | Count |
|---|---:|
| Negative derived OS | 0 |
| Same-day diagnosis and endpoint | 0 |
| **Last follow-up after recorded death** | **1** (flagged, retained) |
| Death date present but `os_censor=1` | 0 |

## 4. Counts on linked cases (pre-eligibility)

| | Cases | Deaths |
|---|---:|---:|
| Linked | **470** | **170** |
| With observed IPI score | **424** | **155** |

For comparison, the currently designated final test (GSE87371 R-CHOP21/14,
non-PMBL) is **103 cases / 36 events**.

**Indicative only, pending the rebuilt simulation (WP4):** event count drives
the paired-ΔC standard error roughly as 1/√events, so 155 events versus 36
suggests an SE roughly halved. That is a material improvement but is **not** a
precision claim — the supervisor's §6A calibration rebuild must supply the real
figure, and the earlier +0.011-when-targeting-+0.03 run is withdrawn.

## 5. Promotion status — NOT promoted

Per the §3D rule, GSE31312 is **not** promoted to primary external test. Passed:
extraction integrity, linkage uniqueness, OS semantics, endpoint derivation,
clinical baseline availability. **Outstanding:**

1. **`Case #` → patient** relationship undocumented; repeat biopsies not ruled out.
2. **Treatment/disease eligibility not verified from the source.** The
   consortium title mentions R-CHOP; individual regimens must be confirmed from
   the publication, not inferred, and exceptions checked.
3. **Cohort independence not established.** Care 2013 considered this accession.
   "No outcome-based tuning by this project" and "never used in developing any
   inherited component" are different claims and both need checking.
4. The 5 supplement-only and 28 GEO-only records need investigation rather than
   dismissal as technical failures.
5. One record has follow-up after death.

## 6. Artifacts

| File | Rows |
|---|---:|
| `manifests/gse31312_table1_clinical.csv` | 475 |
| `manifests/gse31312_table2_outcome.csv` | 475 |
| `manifests/gse31312_linkage.csv` | 503 |
| `manifests/gse31312_reconciled.csv` | 475 |
| `reports/gse31312_extraction_discrepancies.csv` | 303 |

No model fitted. No expression data touched. No external prediction/outcome
association inspected.
