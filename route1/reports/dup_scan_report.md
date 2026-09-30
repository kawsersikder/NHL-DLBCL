# Expression-level duplicate scan: report

**Date:** 2026-09-30 · **Plan:** `dup_scan_plan.md` (frozen, commit `3123d56`, before download)
**Decision:** D-009 (local compute) · **Scripts:** `src/dup_01_download.py`, `src/dup_02_scan.py`
**Inputs:** 15 GEO series matrices, SHA-256 in `manifests/dup_scan_inputs.csv`
**Outputs:**
- `manifests/dup_scan_candidates.csv`: all pre-specified calls, primary and secondary.
- `dup_scan_reported_duplicates.csv`: the reported tier (§3).
- `dup_scan_series_counts.csv` and `dup_scan_summary.json`: controls, quantiles, versions.

**Outcome-blind:** no `!Sample_characteristics` line was stored. Sex was
inferred from expression.

---

## Headline

1. **The Leeds (HMDS) DASL series share samples, and that includes our own
   development cohort.** **145 of GSE181063's 1,310 samples (11.1%)** have an
   expression duplicate in **GSE69051 (77)** or **GSE117556 / REMoDL-B (68)**.
   **79 of GSE69051's 250 samples (31.6%)** are duplicates.
   - All 147 pairs have r = 0.896–0.994, against a between-series 99.99th
     percentile of 0.733.
   - Sex agreement is 99%.
   - No series summary discloses the overlap.
2. **GSE23501 is mostly re-profiled material.** **41 of its 69 samples (59%)**
   have a duplicate elsewhere:
   - **37 in GSE19246**, a Roche/BCCA/NCI study of 59 matched frozen/FFPE
     tumours (r 0.67–0.83). That is consistent with the same tumours on
     different preparations.
   - **4 in GSE10846** (r 0.91–0.95).
3. **The method reproduces an independent published finding exactly.**
   Mosquera Orgueira et al. (*BMC Cancer* 2020) reported 4 duplicates between
   GSE23501 and GSE10846. The scan finds those 4, at r ≥ 0.9.
4. **GSE31312 and GSE87371 show no duplicates with any scanned series.**
   These are the audit's proposed evaluation cohorts. For GSE87371, one
   marginal r = 0.52 call falls below the reporting tier. This strengthens
   GSE31312's role as the primary evaluation cohort.

## 1. Inputs and features

| Run | Series (samples) | Features |
|---|---|---:|
| GPL570 | GSE10846 (420), GSE11318 (203), GSE53786 (119), GSE31312 (498), GSE87371 (223), GSE23501 (69), GSE19246 (177), GSE12195 (136), GSE34171 (91), GSE56315 (88) | 41,320 complete probes |
| GPL14951 | GSE181063 (1,310), GSE117556 (928), GSE69051 (250) | 29,372 |
| GPL96 × GPL570 (exploratory) | GSE57611 (148) vs the GPL570 set | 18,312 shared probes |
| GPL8432 × GPL14951 (exploratory) | GSE32918 (249) vs the GPL14951 set | 24,521 shared ILMN IDs |

## 2. Controls (pre-specified)

| Control | Result | Verdict |
|---|---|---|
| PC1: identical GSMs above threshold | **318 / 318** (min r 0.806 vs threshold 0.433) | PASS |
| PC2: published GSE23501 × GSE10846 duplicates | 5 primary calls; **4 at r ≥ 0.9**, the published 4. The 5th, r = 0.44, sits in the biological-similarity range | PASS |
| NC: GSE87371 × GSE10846 primary candidates | **0** (5 secondary, threshold-only, r 0.44–0.51) | PASS |
| Sex agreement, primary calls **between** series | **199 / 204 (97.5%)** | Supports specificity |
| Sex agreement, primary calls **within** a series | **50 / 75 (67%)**, close to chance | Within-series calls **not claimed** |

## 3. Reported duplicates (post-hoc reporting tier, stated as such)

The pre-specified primary rule (threshold AND mutual best match) is
**specific between series on GPL14951**, but on GPL570 it also admits pairs of
biologically similar samples at r ≈ 0.43–0.60, whose sex agreement is 73%.
The GPL570 distribution shows a gap between r = 0.60 and 0.67.

The **reported tier** therefore adds, post hoc: between series,
sex-concordant, and r ≥ 0.65. The full pre-specified output is published
alongside, so the tier can be checked.

| Pair | Pairs | r range | Interpretation |
|---|---:|---|---|
| GSE181063 × GSE69051 | 77 | 0.918–0.994 | same arrays or RNA deposited twice (same lab) |
| GSE181063 × GSE117556 | 68 | 0.897–0.990 | HMRN patients who also appear in the REMoDL-B series |
| GSE117556 × GSE69051 | 2 | 0.896–0.900 | same |
| GSE19246 × GSE23501 | 37 | 0.673–0.830 | same tumours, different preparation (probable) |
| GSE10846 × GSE23501 | 2 (+2 via GSE53786's identical copies) | 0.910–0.948 | reproduces Mosquera Orgueira 2020 |

**Not claimed:**
- 75 within-series primary calls (sex agreement near chance). They include
  GSE56315's sorted B-cell subsets from shared donors.
- 15 between-series primary calls at r 0.44–0.60.

**No evidence at this sensitivity:**
- GSE57611 (GPL96) vs GPL570: maximum between-series r is 0.547.
- GSE32918 (DASL v3) vs GPL14951: maximum r is 0.724.

*The cross-version sensitivity is unvalidated* (no positive control exists),
so "none found" is not "none present".

## 4. Consequences

### For Route 1

- **Our GSE181063 identity-safe population (301):** 10 patients have a
  duplicate in GSE69051.
- **Among the 243 excluded unidentified samples:** 15 have duplicates
  (13 in GSE117556, 2 in GSE69051).
- **Any audit pairing of GSE181063 with GSE117556 or GSE69051 must exclude the
  duplicated patients.** The map allows patient-level exclusion instead of
  dropping whole cohorts.
- Whether the REMoDL-B duplicates carry trial identifiers that could help
  resolve the 243 unidentified samples is an open question. Answering it would
  need GSE117556 characteristics, which contain outcomes, so it needs its own
  decision.

### For the literature

These are counts only, not yet classified. Papers naming a pair together with
signature or risk-model terms (Europe PMC, 2026-09-30):

| Pair | Papers |
|---|---:|
| GSE181063 + GSE117556 | **21** |
| GSE10846 + GSE23501 | **33** |
| GSE181063 + GSE69051 | 2 |
| GSE117556 + GSE69051 | 2 |
| GSE19246 + GSE23501 | 2 |

One pilot signature (#40, PMID 41549103) trained on GSE181063 and validated on
GSE117556. **Up to 68 duplicated samples** could sit on both sides. The exact
number depends on its R-CHOP subsets.

### Combined overlap map (identifier + expression)

| Series | Shared with | Samples | Evidence |
|---|---|---:|---|
| GSE53786 | GSE10846 | 114 / 119 | identical GSM |
| GSE11318 | GSE10846 | 163 / 203 | identical GSM |
| GSE4732 | GSE10846 | ~181 / 303 | case no. + age/sex (other platform) |
| GSE69051 | GSE181063, GSE117556 | 79 / 250 | expression |
| GSE181063 | GSE69051, GSE117556 | 145 / 1,310 | expression |
| GSE117556 | GSE181063, GSE69051 | 70 / 928 | expression |
| GSE23501 | GSE19246, GSE10846 | 41 / 69 | expression |
| GSE19246 | GSE23501 | 37 / 177 | expression |

## 5. Deviations and corrections

- **D1:** DASL has no XIST probe, so sex was called from chrY genes.
- **D2:** The cross-version run matched on ILMN IDs, with its threshold taken
  from GSE32918 pairs only.
- **D3:** GSE57611 is GPL96 and was analysed as an exploratory cross-platform
  run.
- **Implementation correction.** The first control summary counted secondary
  (threshold-only) pairs toward the negative control. The plan defines a
  candidate as the primary call, so the code was corrected to the plan and
  re-run. Candidate lists were unchanged.
- **Post-hoc reporting tier** (§3), with the full pre-specified output
  retained.

## 6. Limitations

- Mutual-best matching is one-to-one, so a sample copied into three or more
  series can be under-counted. No three-way groups were seen on GPL14951.
- Duplicates re-profiled from **different specimens of the same patient**
  (e.g. relapse biopsies) would show lower r and may be missed.
- **Not scanned:** RNA-seq cohorts (NCICCR, TCGA), GPL96 cohorts other than
  GSE57611 (GSE4475, GSE22470), and NanoString data.
- The counts are a **lower bound** on overlap in the public DLBCL cohorts.
- **Cross-version false negatives confirmed (addendum, 2026-09-30).** A post-hoc
  check (`overlap_literature_newpairs_2026-09-30.md` §3) found about 12 probable
  GSE32918 ↔ GSE69051 shared patients. They were identified by exact age plus a
  rank-1 expression match, at cross-version r 0.24–0.68, below this run's 0.775
  threshold. The GPL8432 × GPL14951 "no evidence" result above is therefore
  superseded.

## 7. Next steps

1. Classify the 21 GSE181063 + GSE117556 papers and the 33 GSE10846 + GSE23501
   papers with the O-089 rubric.
2. Write protocol v3: this map becomes Stage 1, with patient-level exclusion.
3. Release the combined overlap map (CSV and code) as a citable resource.
4. Extend the scan to RNA-seq cohorts, if the audit uses them.
