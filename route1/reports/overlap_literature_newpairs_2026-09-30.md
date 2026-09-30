# Literature use of the scan-detected overlapping pairs, plus a cross-version finding

**Date:** 2026-09-30 · **Follows:** O-089 (identifier overlap + 59 papers), O-090 (expression scan)
**Scripts:** `src/overlap_04_literature_newpairs.py`, `src/overlap_05_classification_newpairs.py`
**Outputs:** `manifests/overlap_literature_classification_newpairs.csv`, `manifests/overlap_literature_summary.json`
**Scope:** published papers and GEO metadata. The §3 check also uses
expression plus a non-outcome demographic (age), and no outcome field.

---

## Headline

- **Across every overlapping pair found so far, 66 open-access papers used a
  pair as analysis cohorts. Only 1 removed the shared samples.** That paper
  was Mosquera Orgueira et al. 2020, the one that discovered them.
- 39 of the 66 cross-used a pair: trained on one member and validated on the
  other.
- **A post-hoc check found shared HMRN patients running across three series:**
  GSE32918 (DASL v3), GSE69051 and GSE181063. The pre-specified cross-version
  scan had missed them.

## 1. Classification of the two new pairs

These are Europe PMC hits naming both members of a pair together with
signature or risk-model terms. Rubric as O-089, plus **D** (cross-use *with*
reported de-duplication).

| Pair (shared samples) | Hits | OA read | C | R | M | D | N | U | Analysis users | De-duplicated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GSE181063 × GSE117556 (68; 5.2% / 7.3%) | 21 | 18 | 4 | 7 | 3 | 0 | 2 | 2 | **14** | **0** |
| GSE10846 × GSE23501 (4; 1.0% / 5.8%) | 33 | 30 | 9 | 6 | 2 | **1** | 12 | 0 | **18** | **1** |

Class key: C cross-use · R counted as separate replications · M merged · D
de-duplicated · N not analysis cohorts · U unclassifiable.

**Magnitude matters.** These pairs share 4–7% of samples. The O-089 pairs
share far more: GSE53786 is 96% GSE10846 and GSE11318 is 80%. Cross-use of a
low-overlap pair biases a validation only slightly, but it is the same lapse,
and it is just as uniformly unreported. **The headline bias finding stays with
the O-089 high-overlap pairs.** The new pairs show the practice is pervasive.

Examples:

- **Correct practice (D):** *"we used Spearman correlation to rule out
  duplicate samples. Indeed we detected 4 samples with almost perfect
  correlation (> 0.99) which we treated as duplicates"* (PMC7579992).
- **Cross-use (C):** a training pool including GSE117556 (723) and GSE181063
  (326), then validation on the *"remaining sample of GSE181063"* (484)
  (PMC10912034).
- **Merged (M):** *"all of DLBCL patients in GSE117556 and GSE181063 datasets
  were integrated into one dataset"* (PMC11640839).
- **Within-training duplication:** one signature (PMC12672785) trained on
  GSE19246 + GSE23501, which themselves share 37 samples.

## 2. Union across all overlapping pairs

| | Papers |
|---|---:|
| Distinct open-access papers read (O-089 + this report) | **84** |
| Used an overlapping pair as analysis cohorts | **66** |
| of which: cross-use (C) | 39 |
| counted overlapping series as separate replications (R) | 20 |
| merged without de-duplication (M) | 6 |
| **de-duplicated (D)** | **1** |

Each paper is counted once, at its most serious class across pairs.

**Limits:**
- Single reviewer.
- Open-access only: 6 non-OA hits in this round and about 17 in O-089 are
  unread.
- Only the pairs mapped so far are covered.

These counts are a **lower bound**.

## 3. Post-hoc finding: GSE32918 ↔ GSE69051 ↔ GSE181063

**Trigger.** PMC6704056 states that GSE32918 and GSE69051 *"had some common
samples"*. The O-090 cross-version scan (DASL v3 vs v4) had found none: its
maximum r was 0.724, against a threshold of 0.775. So this was checked
**after the fact, and is labelled as such**.

**Method:**
- Exact age to 2 decimals, a non-outcome demographic present in both series.
  Replicate arrays were excluded.
- A permutation null with GSE69051 ages jittered by ±3 years, 200 draws.
- Then the expression rank of each age-matched partner among all 250
  GSE69051 samples.

**Result:**

| | Value |
|---|---:|
| GSE32918 samples whose exact age appears in GSE69051 | **16** |
| Chance expectation (null mean / max over 200 draws) | 4.9 / 13 |
| Age-matched pairs that are also the **best (rank 1–2 of 250) expression match** | **12** |
| Remaining 4 age matches, expression rank | 185–241 (chance collisions) |
| Cross-version r of the 12 | 0.24–0.68 (bulk median 0.007, 99th pct 0.351) |

The 12 GSE69051 partners form **one consecutive block**, GSM1691332–GSM1691344,
titled `HMRN_<n>_v4_old`. These are older HMRN samples re-run on DASL v4.
**11 of that block are also expression duplicates of GSE181063 arrays**
(O-090; r 0.92–0.98). So the same HMRN patients appear across GSE32918 (v3),
GSE69051 (v4) and GSE181063.

**Grade: PROBABLE** (age key plus a rank-1 expression match; cross-version,
different arrays). This moves the lineage entry "GSE32918 ↔ GSE181063 overlap
PLAUSIBLE BUT UNVERIFIED" to **PROBABLE for about 11 patients**.

**It also confirms that the cross-version scan has false negatives.** The
threshold was set from the between-series distribution, and cross-version
re-profiling of the same patient only reaches r ≈ 0.24–0.68. Future
cross-version checks need a demographic key or a rank-based rule, not a global
r threshold.

**Reinterpreting PMC6704056's correction.** Its corrected counts (172 and 157)
match this project's non-replicate counts (172 and 159). Its correction was
probably mostly *within-series de-replication*, not removal of the cross-series
overlap. It is still counted as **N** for GSE10846 × GSE23501, where GSE23501 is
excluded.

## 4. Consequences

1. **The combined overlap map gains an edge:** GSE32918 ↔ GSE69051 ↔ GSE181063
   (about 11–12 probable patients). GSE32918 is **not** independent of
   GSE181063.
2. **The audit's lineage rule** must treat GSE32918, GSE69051, GSE117556 and
   GSE181063 as one overlapping family, with patient-level exclusion.
3. **The methods paper has a strong, simple message:** in public DLBCL cohorts,
   overlap is common, undisclosed and almost never removed. The one paper that
   checked found duplicates.
