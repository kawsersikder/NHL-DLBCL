# Signature-audit feasibility pilot: report

**Date:** 2026-09-30 · **Decision:** D-008 · **Plan:** `signature_pilot_plan.md`
(committed `0ba9732` *before* retrieval)
**Scripts:** `src/sig_pilot_01_search.py`, `sig_pilot_02_fulltext.py`, `sig_pilot_03_extraction.py`
**Scope kept:** papers only. No expression matrix or outcome field was opened,
and no association was computed.

---

## Headline

**GO for protocol drafting, with four design changes the pilot forced (§4).**
The literature is large enough and extractable enough for a real audit:

- about 158 eligible signature papers in the frozen search;
- about 36 evaluable on the verified-endpoint cohort from open-access sources
  alone.

The pilot also shows why the audit is needed. **GSE10846 was touched by 9 of
the 14 signatures whose lineage could be traced**, and one paper states that a
second "independent" validation cohort was drawn from GSE10846's own patients.

## 1. Search and sample

| | Value |
|---|---|
| Hits, frozen query, 2013-01-01 to 2026-09-30 | **317** |
| PMID-list SHA-256 | `5353658d30484d48a6051eab9a475af8bbd9ab76fd5e5448ed95e611d5bbc32f` |
| Sample | 40, `random.Random(20260930)` over sorted PMIDs |
| Included (I1–I4) | **20 / 40 = 50%** (95% CI 35–65%) |

Exclusions: 16 × I3 (protein/IHC, single-gene, plasma, diagnostic or biology-only
signatures), 2 × I2, 1 × I4, 1 × I1. Decisions and reasons are in
`manifests/sig_pilot_screening.csv`.

## 2. Extractability (n = 20 included)

| | n | % (95% CI) |
|---|---:|---|
| Open-access full text (Europe PMC) | 12 | 60% (39–78) |
| **Complete gene list from open sources** | **12** | 60% (39–78) |
| Gene signatures with coefficients stated in text | **6** | 30% (15–52) |
| Lineage traceable for our four cohorts | 14 | 70% (48–85) |

- All 8 abstract-only records lacked either the gene list or the cohort names;
  one (PMID 42803950) listed its genes but not its cohorts.
- Two included records evaluate **established classifiers** (DHITsig;
  LymphGen-Sig with 294 genes). Their gene lists must come from the originating
  papers.

## 3. Lineage

### 3.1 Which of our cohorts each traceable signature touched (n = 14)

| Cohort | Touched by | Signatures (draw order) |
|---|---:|---|
| **GSE10846** | **9 / 14** | 9, 10, 15, 23, 24, 31, 33, 38, 39 |
| GSE31312 | 5 / 14 | 9, 10, 31, 38, 39 |
| GSE87371 | 3 / 14 | 10, 31, 40 |
| GSE181063 | 2 / 14 | 9, 40 |

- "Touched" covers training, gene screening, or reported validation.
- In three cases (9, 10, 31), one signature touches three of our four cohorts.

### 3.2 Eligible signature × cohort pairs

Counted for the 11 signatures that are both scoreable and traceable. #35 is
excluded as non-transferable: it is relapsed/refractory and uses NanoString
thresholds. #37 has unknown lineage.

| Rule | Pairs (of 44) | GSE181063 | **GSE31312** | GSE87371 | GSE10846 |
|---|---:|---:|---:|---:|---:|
| (a) Conservative: exclude any named cohort | **22** | 8 | **6** | 7 | 1 |
| (b) Training/screening only | 28 | 8 | 7 | 9 | 4 |

### 3.3 Accession-level lineage is not enough, which the pilot found in the sources

- **GSE53786 is drawn from GSE10846.** PMID 25940947 states the 68 Scott et al.
  cases were *"drawn from the Lenz et al. dataset"*. A signature trained on
  GSE10846 and "validated" on GSE53786 was validated on its own patients.
- **GSE11318 and GSE10846 are both LLMPP series.** Patient overlap is
  *possible* and **unverified**. It is treated as an exclusion conservatively
  (#20).
- **GSE117556 (REMoDL-B) and GSE181063 (HMRN)** share the HMDS Leeds lab and the
  GPL14951 platform. Patient overlap is **unverified** (#39).

## 4. Design changes forced by the pilot

1. **Lineage must be traced at the patient level, not by accession.** The
   registry needs an overlap table between accessions (GSE10846 ⊃ GSE53786;
   GSE11318 ? GSE10846; GSE117556 ? GSE181063) before eligibility is computed.
2. **GSE10846 is effectively unusable as an evaluation cohort.** Under the
   conservative rule it is eligible for 1 of 11 signatures. It should be dropped
   from the audit's evaluation set, consistent with its earlier demotion (O-080).
3. **GSE31312 becomes the primary evaluation cohort.** It has the only verified
   diagnosis-origin endpoint (WP1) and is eligible for about 55% of traceable
   signatures (6/11; 95% CI 28–79%). GSE181063 is eligible for 8/11 but stays
   blocked on its OS origin, which makes the depositor email more valuable, not
   less.
4. **A fixed scoring rule is required, and gene direction must be extracted.**
   Only 30% of signatures give usable coefficients, so the primary analysis
   cannot use published weights. The protocol must extract **each gene's
   published direction** (risk vs protective) and score a signed rank. This
   field was not in the pilot plan. It is the main extraction gap to close.
   Published weights become a sensitivity analysis where they exist.

## 5. Open protocol decisions the pilot surfaced (not resolved here)

- **Orientation of random gene sets.** Published signatures carry directions;
  random sets do not. Two options:
  - learn a single orientation parameter inside cross-fitting, for published
    and random sets alike;
  - give random sets random signs.
  The choice changes the null and must be fixed before any outcome is read.
- **Rule (a) vs (b).** Reported validation often shaped which signature was
  published, which favours (a). (b) keeps about 27% more pairs.
- **Access to paywalled texts.** 40% of included papers are not open-access. An
  OA-only audit is biased toward OA venues. Needs institutional access or
  author requests, or else the restriction reported as a limitation.
- **Median dichotomisation** is common in the sources (#9, 10, 39, 40). The
  audit should use continuous scores and say so.

## 6. Source-quality observations (retain; relevant to the audit's message)

- Gene-symbol typos: `PPARGCIA` for PPARGC1A (#23).
- Accession typos: `GSE80371` for GSE87371 (#31); `GSE10864` for GSE10846 (#39).
- An internal gene-list inconsistency: one sentence lists 8 of 9 genes (#33).

Each was reconciled against the paper's own formula or later text and is
recorded in `manifests/sig_pilot_extraction.csv`.

## 7. Extrapolation (indicative only)

- About **158** eligible signature papers in the frozen search (95% range
  111–206).
- With OA-only extraction (60%) and traceable lineage (70%), about **36** would
  be evaluable on GSE31312 under the conservative rule.
- That is enough for a distributional audit. It is **not** a precision claim;
  per-signature ΔC precision on GSE31312 still needs the WP4 simulation.

## 8. Deviations from the frozen plan

1. **Parser bug, fixed and re-run.** The first run read article IDs with
   `.//ArticleIdList`, which also matched the reference list, so DOIs and PMCIDs
   of cited papers overwrote the article's own. It was fixed to
   `./PubmedData/ArticleIdList` and re-run. **Hit count, PMID-list hash and
   sample order were identical** (verified); only the ID fields changed.
2. **"Gene direction"** was not a planned extraction field. It is added as a
   protocol requirement (§4.4), not back-filled here.

## 9. Limitations

- One reviewer (LLM), for both screening and extraction.
- 40 of 317 records sampled.
- 8 included records read from the abstract only.
- The lineage roles for #15 (DLBCL-1 = GSE10846) are INFERRED from sample size
  and text, not stated as an accession.

None of the pilot's numbers may be quoted as audit results.

## 10. Next steps

1. Supervisor and Kawser review of §4–§5.
2. Draft protocol v3 (the signature audit), resolving the §5 decisions before
   any outcome is read.
3. Build the patient-level accession overlap table (§4.1).
4. Send the GSE181063 depositor request (still unsent; needs Kawser's
   authorisation).
