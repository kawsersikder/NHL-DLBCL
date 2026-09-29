# Signature-audit feasibility pilot: plan (frozen before retrieval)

**Date:** 2026-09-30 · **Decision:** D-008 · **Status: FROZEN at the time of writing.**
This plan was written before any search result was retrieved. Any deviation is
recorded in the pilot report as a deviation, never as a silent edit.

## Purpose

Estimate, from a random sample of the literature, whether a full audit is
feasible. The pilot answers four questions:

1. What fraction of search hits are eligible signature papers?
2. What fraction publish a complete, extractable gene list? What fraction also
   publish coefficients?
3. Which GEO cohorts did each signature touch in development or reported
   validation? In particular: GSE181063, GSE31312, GSE87371, GSE10846.
4. How many signature × cohort pairs survive the lineage exclusion?

**The pilot reads papers only.** It opens no expression matrix and no outcome
field, and it computes no association of any kind.

## Search (frozen)

- **Database:** PubMed via NCBI E-utilities.
- **Query:**
  ```
  ("diffuse large B-cell lymphoma"[tiab] OR DLBCL[tiab]) AND (signature[tiab]
  OR "risk score"[tiab] OR "risk model"[tiab] OR "prognostic model"[tiab]) AND
  (gene[tiab] OR genes[tiab] OR expression[tiab]) AND (prognos*[tiab] OR
  survival[tiab])
  ```
- **Publication date:** 2013/01/01 – 2026/09/30. Chosen to post-date Hong,
  Kahl & Gray 2013, the prior audit of three signatures.
- **Recorded:** the retrieval timestamp, hit count and the full PMID list, with
  its SHA-256.

## Sample (frozen)

- **Rule:** sort the PMIDs numerically, then draw
  `random.Random(20260930).sample(pmids, 40)`.
- **N = 40.** At an expected inclusion rate of about 50–60%, this gives roughly
  20–24 signatures, enough to estimate lineage overlap to about ±15 percentage
  points.
- **No replacement draws.** An excluded record is not replaced, because the
  inclusion rate is itself a pilot estimate.

## Screening (title and abstract)

Include only if all four criteria hold:

| # | Criterion |
|---|---|
| I1 | Original research: not a review, meta-analysis, letter, comment or erratum |
| I2 | DLBCL patient samples (not only other lymphoma types, not only cell lines) |
| I3 | Proposes or evaluates a **multi-gene expression-based** prognostic signature or score |
| I4 | Time-to-event endpoint (OS, PFS or EFS) |

- **Recorded but not excluded at this stage:**
  - lncRNA or miRNA signatures (platform assayability is uncertain);
  - signatures from single-cell or spatial data;
  - signatures that combine genes with clinical variables.
- **Single reviewer (LLM).** The pilot is for feasibility only. The real
  registry needs a human second reviewer, with disagreements reported.

## Extraction (included records)

From the full text where open-access (Europe PMC), otherwise from the abstract.
Each field is recorded with a **verbatim quote and its location**:

- **genes:** the complete list, and whether it is complete as stated;
- **coefficients:** published, yes or no;
- **n_genes;**
- **molecule type:** mRNA, lncRNA, miRNA or mixed;
- **training / discovery cohorts:** accession IDs;
- **validation cohorts:** accession IDs;
- **endpoint.**

## Lineage rules, both measured in the pilot

- **(a) Conservative:** exclude every cohort the paper names in any role.
  Reported "validation" cohorts often shaped which signature was reported.
- **(b) Training-only:** exclude only discovery or training cohorts.

The protocol chooses between them. The pilot reports both.

## Outputs

- `route1/src/sig_pilot_01_search.py`
- `route1/manifests/sig_pilot_pubmed_hits.csv`
- `route1/manifests/sig_pilot_sample.csv`
- `route1/manifests/sig_pilot_screening.csv`
- `route1/manifests/sig_pilot_extraction.csv`
- `route1/reports/signature_pilot_report.md`
- Raw retrievals go to `route1/data/raw/signature_pilot/`, which git ignores.
