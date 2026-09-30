# Expression-level duplicate scan: plan (frozen before download)

**Date:** 2026-09-30 · **Decision:** D-009 (run locally) · **Follows:** O-089
**Status: FROZEN at the time of writing.** It was written before any expression
matrix was downloaded. Deviations are reported as deviations.

## Purpose

Detect the same biological sample appearing under different GEO accessions,
within or across public DLBCL series. The metadata scan (O-089) cannot see this
where series share no identifiers. The scan is **outcome-blind**:

- only the expression table and sample IDs are parsed;
- every `!Sample_characteristics` line, the ones carrying follow-up and status,
  is skipped;
- the one non-outcome demographic used, sex, is inferred **from the expression
  data itself**.

## Inputs (GEO series matrices, downloaded with SHA-256 recorded)

| Platform | Series |
|---|---|
| GPL570 (HG-U133 Plus 2.0) | GSE10846, GSE11318 (GPL570 part), GSE53786, GSE31312, GSE87371, GSE23501, GSE19246, GSE12195, GSE34171 (GPL570 part), GSE56315, GSE57611 |
| GPL14951 (WG-DASL HT v4) | GSE181063, GSE117556, GSE69051 |
| GPL8432 (WG-DASL v3), exploratory cross-version | GSE32918 vs the GPL14951 set, by gene symbol |

Samples on another platform inside a listed series are dropped. Any series
whose matrix turns out to be on a platform other than the one listed is
reported and analysed with its true platform.

## Method (fixed)

1. **Features.**
   - Within a platform: probes with no missing value in every included series.
   - Cross-version: gene symbol (median over single-symbol probes), restricted
     to genes present in both.
2. **Transform,** designed to remove processing and batch differences but keep
   sample identity:
   - (a) within-sample rank over features, scaled to [0, 1];
   - (b) centre each feature within its series (subtract the series mean);
   - (c) z-score each sample's residual profile.
3. **Similarity:** Pearson correlation of residual profiles for all sample
   pairs. This is the correlation-after-batch-centering approach of the
   doppelgänger literature (Waldron et al., *JNCI* 2016).
4. **Call rule (primary, fixed now).** A pair of distinct GSM accessions is a
   **duplicate candidate** if both hold:
   - (i) `r ≥ median + 10 × MAD` of all *between-series* correlations on that
     platform;
   - (ii) each sample is the other's best match outside its own GSM.
   Pairs meeting (i) without (ii) are listed as secondary.
5. **Identical accessions.** The same GSM in two series is removed from
   detection counts. It is used as a **positive control** for the metric: its
   residual correlation must clear the threshold.

## Controls (fixed now, reported whatever they show)

- **Positive control 1:** identical GSMs shared by GSE10846 / GSE11318 /
  GSE53786 (163 + 114 + 41 records) must all be flagged.
- **Positive control 2:** Mosquera Orgueira et al. 2020 report **4 duplicates
  between GSE23501 and GSE10846**. The scan should find at least 4 in that
  pair.
- **Negative control:** GSE87371 (LYSA, France) × GSE10846 (LLMPP, US) are
  different networks and countries, so 0 candidates are expected. Any flags
  there count against the method.
- **Corroboration by expression-inferred sex.** Sex is called per sample from
  XIST vs chrY genes (RPS4Y1, DDX3Y, KDM5D, EIF1AY), by 2-means on
  (XIST − mean chrY) within each series. True duplicates must agree on
  inferred sex. Agreement among candidates is reported against the ~50%
  expected for random pairs.

## What is reported

- The per-pair candidate list: GSMs, series, r, robust z, mutual-best flag,
  sex agreement.
- A series × series count matrix.
- Control results.
- The correlation distribution, as quantiles.

No survival, treatment or response field is read. No association of any kind
is computed.
