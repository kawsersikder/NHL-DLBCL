# Phase 0 — phase-end report

**Date:** 2026-09-10 · **Machine:** Windows workspace `F:\Research Projects\NHL-DLBCL`

---

## 1. Completed

| Work | Artifact |
|---|---|
| Read the authoritative workspace instructions (plan rule 1) | `.agents/AGENTS.md`, `.agents/skills/dlbcl-research/SKILL.md` |
| Created the isolated working area, source downloads separate from generated outputs | `route1/{src,reports,manifests,configs,kaggle,data/raw,data/metadata,artifacts,predictions,logs}` |
| Inventoried and hashed the analysis-relevant tree; summarised bulk trees without hashing | `route1/src/phase0_inventory.py` → `route1/manifests/source_registry.csv`, `route1/reports/workspace_inventory.md` |
| Recorded version-control state and cross-machine divergence | `route1/reports/workspace_inventory.md` |
| Registered three workspace conflicts with resolutions | `route1/reports/decision_log.md` (D-001 … D-003) |
| Corrected my own PMID attribution error and amended the handoff in place | `route1/reports/decision_log.md` (D-004); `reports/route_audit_2026_09_10_handoff.md` §4b |
| Project configuration, provisional values marked as such | `route1/configs/project.yaml` |

## 2. Verified

- **106 analysis-relevant files** hashed (SHA-256): 17 code, 48 data/manifest, 30 protocol/report, 5 config, 4 manuscript, 1 notebook, 1 other.
- **Bulk trees, summarised not hashed:** `DLBCLMorph` 390,129 files / 14.66 GB; `kaggle_upload_staging` 14 / 14.52 GB; `models` 2 / 0.45 GB; `kaggle` 343 / 0.46 GB; `cell_shapes.csv` 0.37 GB. Each carries its own tracked `PROVENANCE.md`.
- **Version control: branch `HEAD`, 0 commits across all refs, 0 tracked files, no remotes.** The `.gitignore` validated in O-072 was never committed against.
- **The Windows copy is the correct implementation copy**, confirmed locally rather than assumed: `src/analysis/` contains 13 scripts and `.agents/` is present — both reported absent on the Mac.
- **PMID attributions**, by direct retrieval (`route1/data/raw/pubmed_abstracts_30408148_30523719_32187361.txt`, SHA-256 `cb602da4ee84702e2dcf0ac4ae231d53aa3779febf8743691fbbf9d173964b3d`): 30408148 = Painter HMRN cell-of-origin; **30523719 = Sha MHG on REMoDL-B**; 32187361 = Lacy HMRN targeted sequencing. The supervisor's correction was right and my §4b claim was wrong.

## 3. Unresolved

| Item | Consequence |
|---|---|
| **No version history, two diverged copies.** Hashes make the current state auditable but cannot reconstruct which version produced any existing result — including the manuscript sources, where the Markdown draft and `main.tex` are known to disagree. | Does **not** affect Route 1's planned analysis: its inputs are freshly retrieved GEO artifacts with recorded hashes. Affects any future attempt to reconcile the two copies or re-derive the prior study. Raised 2026-09-10 and deferred by the researcher. |
| `reports/research_2026_09_10_sources/` absent here (exists on the Mac). | No effect — every count used by Route 1 was re-derived locally rather than imported. |
| Whether GSE181063 is Sha's MHG validation set. | If yes, `pred_combine` MHG labels are partly in-sample for the MHG classifier, compromising **B1 as a comparator**. Does not affect B0 or B2 program scores. Phase 2 task 4. |
| Whether the project's stated novelty position and target journal still apply now that the documented "Option C fallback" is active (D-003). | Research-direction question for the supervisor, not an implementation decision. |

## 4. Gate

**PASS.**

All four Phase 0 deliverables exist. The executing copy is explicit and verified locally rather than by report. Input provenance is recorded by hash. Three workspace conflicts are documented with resolutions and none of them can change the planned analysis: D-001 (commit step) is substituted by this manifest, D-002 (layout) is a location choice, D-003 (scope) is the activation of a documented fallback rather than an undocumented departure. No file was merged, renamed or overwritten across machine copies.

The one genuinely unresolved item — absent version history — is recorded as an open risk and is shown above not to bear on Route 1's inputs.

## 5. Next

**Phase 1 — resolve patient identity and endpoint semantics.** In order:

1. Re-parse GSE181063 metadata into `route1/data/metadata/gse181063_samples.csv` under the Phase 1 path, validating exact category spellings, missing-value conventions and numeric coercions rather than reusing the O-076 run.
2. **Resolve `os_followup_y` semantics** — time origin, units, death coding, censoring, follow-up cutoff — from Painter (30408148) and Lacy (32187361) and their supplements. Painter is a 4-page letter with no MEDLINE abstract, so the full text and supplement are required. **If the GEO field cannot be confidently linked to a published definition, survival modelling stays blocked** and only independent work continues.
3. Establish patient/specimen relationships and repeat biopsies. `pid_pmid_32187361` covers only 583 of 1,310 samples, so this cannot be settled from that field alone. This is the item that decides whether 556 is a patient count or only a sample count.
4. Verify what `qc_fail == 0` actually measures.
5. Resolve what `CHOP-R` denotes, including documented dose attenuation.

No permission is required for the above; it is authorised in-scope work.

## 6. Compute

| Field | Value |
|---|---|
| Kaggle sessions used | **0** |
| GPU used | none — no fitting has occurred |
| Session elapsed | n/a (local metadata and inventory work only) |
| Fits completed / remaining | 0 / all |
| Persistence verified | n/a — no checkpointed workload yet |
| Resume location | n/a |
| Local artifacts | `route1/` (see §1); source downloads immutable under `route1/data/raw/` |

No model of any kind has been fitted. No expression matrix has been downloaded.
