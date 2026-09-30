# Hidden overlap between public DLBCL expression cohorts, and how the literature uses it

**Date:** 2026-09-30 · **Author:** Kawser Sikder (LLM-assisted) · **Route 1, D-008 follow-on**
**Scripts:** `src/overlap_01_geo_identity.py`, `overlap_02_literature_roles.py`, `overlap_03_classification.py`
**Outputs:** `manifests/geo_identity_keys.csv`, `geo_overlap_pairs.csv`, `overlap_literature_classification.csv`
**Scope:** GEO sample *metadata* and published papers only. No expression value
and no outcome field was used in matching. Outcome-bearing characteristics are
filtered out before parsing.

---

## Headline

The signature-audit pilot suggested that some "independent" DLBCL validation
cohorts are not independent. That is now **verified from GEO's own records**,
and the literature has been checked for how it uses those cohorts:

1. **GSE53786 is 96% GSE10846.** 114 of its 119 samples are *the same GEO
   sample records*. One CEL file (e.g. GSM274896) is listed in GSE10846,
   GSE11318 and GSE53786.
2. **GSE11318's expression arm is 80% GSE10846.** 163 of its 203 expression
   samples are the same records.
3. **GSE4732 profiles about 180 GSE10846 patients on a different platform.**
   It shares 185 LLMPP case numbers with GSE10846, and 181 of those agree on
   every available age and sex field. GSE4732 is Lymphochip, GSE10846 is
   HG-U133 Plus 2.0.
4. **None of these series' GEO summaries mentions the overlap.** GSE53786 is
   titled as an FFPE NanoString study, yet its GEO samples are GSE10846's
   frozen-tissue Affymetrix arrays.
5. **Of 45 open-access papers that used one of these pairs as analysis
   cohorts, 30 (67%) trained on one member and "validated" on the other.**
   13 more counted overlapping series as separate replications, and 2 pooled
   them. **44 of 45 report no de-duplication.** The 45th mentions removing
   "duplicate entries" but still presents GSE10846 and GSE11318 as independent
   validation cohorts. 12 of the 30 cross-use papers appeared in 2025–2026.

## 1. Overlap evidence (GEO metadata)

Keys used:

- **K1:** the same GSM accession in two series.
- **K2:** the same LLMPP microarray-database ID (`mAdbID`).
- **K3:** the same submitter case number, corroborated on non-outcome
  demographics.

| Pair | n (a / b) | K1 same GSM | K2 same mAdbID | K3 same case no. | Grade |
|---|---|---:|---:|---:|---|
| GSE10846 × GSE53786 | 420 / 119 | **114** | 114 | 114 | **VERIFIED** (identical sample records) |
| GSE10846 × GSE11318 | 420 / 203 expr. | **163** | 163 | 165 | **VERIFIED** |
| GSE11318 × GSE53786 | 203 / 119 | 41 | 41 | 41 | **VERIFIED** |
| GSE10846 × GSE4732 | 420 / 303 | 0 | 0 | 185 | **PROBABLE**: 181/185 agree on all available sex/age; 3 are chance collisions (sex and age both differ); 1 has no demographics |
| GSE11318 × GSE4732 | 406 / 303 | 0 | 0 | 202 | not corroborated yet |

**Not testable from metadata:** GSE31312, GSE87371, GSE181063, GSE117556,
GSE32918, GSE69051, GSE23501, GSE19246, GSE12195, GSE34171, GSE22470 and
GSE4475 carry no shared IDs. Any overlap among them needs **expression-level**
duplicate detection. That applies especially to the HMDS Leeds DASL series
GSE181063 / GSE117556 / GSE69051 / GSE32918. The method has a precedent in
DLBCL: Mosquera Orgueira et al., *BMC Cancer* 2020
(doi:10.1186/s12885-020-07492-y) used Spearman correlation > 0.99 and found
**4 duplicates between GSE23501 and GSE10846**, which they removed.

## 2. How the literature uses the overlapping pairs

- **Search:** Europe PMC full text, 2026-09-30, for papers naming both members
  of each pair together with signature or risk-model terms. Results:
  - GSE10846 + GSE11318: 44
  - GSE10846 + GSE53786: 33
  - GSE10846 + GSE4732: 6
  - GSE11318 + GSE53786: 14
- **Papers read:** 60 unique open-access papers, of which 59 were parseable.
  Every sentence naming one of the four accessions was extracted and each
  paper classified by reading (`overlap_literature_classification.csv`).

| Class | n | Meaning |
|---|---:|---|
| **C** cross-use | **30** | trained or screened on one member, validated on the other (or a pooled overlapping set split into train/test) |
| **R** replication counting | 13 | overlapping series reported as separate independent validations |
| **M** merged | 2 | pooled without reported de-duplication |
| N not analysis cohorts | 13 | reviews, dataset lists, unrelated use |
| U unclassified | 1 | non-English text |

**Denominator: 45 papers that used an overlapping pair as analysis cohorts.**
C = 67%. C + R + M = 45/45, of which 44 report no de-duplication.

Representative quotes:

- *"GSE10846 was served as the training cohort, whereas GSE11318 and GSE87371
  datasets were designated as the validation cohorts."* (PMC11966244)
- *"To prevent overfitting and data leakage … feature selection … was
  restricted to the training set (GSE10846)"*, followed by external validation
  on GSE11318 (PMC13372773).
- GSE53786 described as *"this independent subset of DLBCL patients"*
  (PMC4864813).

**Limits of the literature count:**

- Single reviewer.
- Open-access papers only; about 17 non-OA papers with these pairs are
  unread.
- Only four overlapping pairs were checked. Pairs that need expression-level
  detection (§1) are not yet counted.

The count is therefore a **lower bound** on overlap misuse in this literature.

## 3. Related finding: the GSE181063 survival origin

HMRN's cohort profile (*Int J Epidemiol* 2018, PMC6005016) states that
*"Patients enter the cohort when they are first diagnosed"*. It adds that all
patients are flagged nationally for death, with deaths notified monthly. HMRN's
2015 *Br J Cancer* survival analysis (PMC4453686) reports deaths *"within 5
years of diagnosis"*.

That upgrades the evidence for a diagnosis-origin OS in GSE181063 from
INFERRED (maximum follow-up compatibility) to **COHORT CONVENTION DOCUMENTED,
FIELD-LEVEL UNCONFIRMED**. The depositor request remains the clean resolution.
The profile also documents near-complete death ascertainment, which strengthens
the endpoint's quality.

## 4. Prior art

- Waldron, Riester, Ramos, Parmigiani. "The Doppelgänger Effect: Hidden
  Duplicates in Databases of Transcriptome Profiles." *JNCI* 2016;108(11),
  doi:10.1093/jnci/djw146 (Crossref-verified). This is the general method and
  argument, shown in ovarian cancer.
- "Doppelgänger spotting in biomedical gene expression data", *iScience* 2022
  (PMID 35992056).
- DLBCL-specific: one paper de-duplicated one pair, the Mosquera Orgueira 2020
  paper above.
- **Not found: a systematic overlap map of public DLBCL cohorts, or a
  measurement of how often published DLBCL signatures are validated on
  overlapping data.** This comes from three Europe PMC queries and needs a
  proper search before any novelty claim.

## 5. What this changes

1. **This is the empirical core of the audit paper, and it comes first.** The
   question "do published signatures add beyond IPI?" can only be answered
   once the field's validation evidence has been de-duplicated. The overlap
   map is also a standalone community resource: a table any author can check
   before choosing a validation cohort.
2. **The audit's lineage rule is now concrete.** Exclusion is by patient, via
   the overlap map, not by accession. A signature trained on GSE10846 is
   ineligible on GSE11318, GSE53786 and (probably) GSE4732.
3. **One effect estimate should be pre-specified.** For signatures whose
   published "validation" used an overlapping series, compare discrimination
   on that series against a truly independent, endpoint-verified cohort
   (GSE31312). That measures how much the overlap inflated reported
   validation. **It reads outcomes, so it goes into protocol v3 before it is
   run. It must not be run ad hoc.**

## 6. Proposed next steps

1. **Expression-level duplicate scan.** This is outcome-blind: within-platform
   sample correlation across all public DLBCL cohorts with survival (GPL570;
   GPL14951; GPL8432 vs GPL14951 cross-version). It needs series-matrix
   downloads, a few GB. The compute is light enough to run locally, but the
   project's Kaggle-only rule means it's Kawser's call.
2. **Second reviewer (Kawser)** on the 59-paper classification.
3. **Protocol v3,** with the overlap map as Stage 1, the inflation estimate as
   a pre-specified secondary, and the signature audit as primary.
4. **Early release option:** publish the overlap map (CSV and code) on
   GitHub/Zenodo as a citable resource, ahead of the audit.
