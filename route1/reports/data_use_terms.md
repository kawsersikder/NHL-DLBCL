# Phase 2 — data use terms and redistribution

**Date:** 2026-09-10 · **Status: PARTIAL — see §4**

This records what was and was not established. No licence text was inferred,
and no term below is asserted from general knowledge of how GEO "usually"
works.

## 1. What was retrieved

Only **sample metadata** (`targ=gsm&form=text&view=brief`) for GSE181063,
GSE31312, GSE10846 and GSE87371, plus open-access full texts from PMC and
PubMed abstracts via E-utilities. **No expression matrix has been downloaded
from any cohort.** `GSE181063_RawData.txt.gz` was deliberately not retrieved.

All downloads are immutable under `route1/data/raw/` with SHA-256 recorded.

## 2. What the records themselves state

The GEO series and sample records for all four accessions contain **no licence
field, no data-use restriction field, and no consent or access-tier
statement**. GSE181063 declares a BioProject relation (PRJNA750740) and a
supplementary file; none of the four is marked as controlled access.

Two ethics statements were captured incidentally from full texts:

- Sha 2015 (Leeds/HMDS): "This study is covered by standard NRES (National
  Research Ethics Service) ethics approval for Haematological Malignancy
  Diagnostic Service (HMDS; St James Hospital, Leeds) local cases and
  treatment was not modified as a consequence of the study. The re-analyses of
  data from the LY10 and RCHOP14/21 clinical trials are separately covered by
  each trial."

This confirms trial-derived subsets can carry **separate** governance from
registry cases — relevant because GSE87371 is trial-derived (LYSA).

## 3. Working constraints adopted

Pending formal verification, this study operates under the more restrictive
reading:

1. **Do not re-host source data.** Point at accessions with checksums, as the
   project already does for DLBCL-Morph via tracked `PROVENANCE.md`. The
   repository's existing `.gitignore` policy already implements this pattern.
2. **Attribution.** Any output must cite the accession *and* its associated
   publications — for GSE181063 that is Painter (PMID 30408148) and Lacy
   (PMID 32187361) as named in `Series_pubmed_id`.
3. **Derived artifacts.** Program scores, model weights and predictions are
   derived summaries, not redistributions of source expression. Publish those;
   do not publish reconstructed per-sample expression matrices.
4. **No linkage attempts.** Do not attempt to re-identify patients or to link
   the 243 unidentified GSE181063 samples to any external record.

## 4. NOT established — do not treat this file as a licence review

- No per-series terms of use were fetched from a licence page for any of the
  four accessions.
- NCBI/GEO's general submission and use policies were **not** retrieved or
  quoted; nothing here should be read as a statement of them.
- Redistribution permission for **derived model artifacts** trained on these
  data was not verified against any source's terms.
- GSE31312's clinical supplement (475 cases) was not obtained and its terms are
  unknown.
- LYSA trial governance for GSE87371 was not checked beyond the observation
  above that trial data may carry separate approval.

**Consequence:** this is sufficient to proceed with metadata-level auditing and
with development modelling on already-public expression data under the
constraints in §3. It is **not** sufficient to authorise publishing any
artifact that could constitute redistribution. That check must be completed
before Phase 8 release, and is listed as a Phase 8 dependency.
