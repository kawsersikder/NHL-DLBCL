# Route 1 — decision log

Append-only. Newest first. Every entry is dated **before** any run it affects.
This log is local to the Route 1 study; project-level entries also go to the
`PROJECT_STATUS.md` Decision Log per `.agents/AGENTS.md`.

---

## 2026-09-30 — D-007 · First git commit; D-001 partly closed

Kawser asked for the first commit. It is made on the Windows copy, on branch
`master` (the repository's only branch). Route 1 raw downloads
(`route1/data/raw/`) and the five GSE31312 row-level extracts carrying per-case
calendar dates are excluded by `.gitignore`. They are regenerable from hashed
sources by the committed WP1 scripts.

**What this closes in D-001:** the Windows copy now has a history, so future
changes to the protocol, manifests and manuscript sources are attributable.
**What it does not close:** the Mac copy is still diverged, and this commit
does not reconstruct which copy produced any result before today.

---

## 2026-09-11 — D-006 · Two further corrections of my own claims, both from inference-by-proximity

**(a) The B4 mask was a no-op, not a small perturbation.** I reported it as
perturbing 1.9% of program genes. Under my own stated rules the ranking
universe is `U = dev ∩ ext` and the mask is `M = dev − ext`, so `U ∩ M = ∅` by
construction. Verified: `|U|=15,647`, `|M|=5,171`, `|U ∩ M| = 0`. I had measured
loss against the development platform instead of against the model's actual
input set. B4 withdrawn per supervisor 2.1(b); it will **not** be run to
produce a null.

**(b) Sha 2015 did not train the BDC classifier on HMDS DASL data.** The paper
states: "Classifier development employed GSE4732_p1 and GSE4475, and the other
data sets were used in testing transferability of classifiers." The HMDS DASL
v3/v4 entries I cited are rows in its Table 1 dataset summary. I inferred a
training cohort from a table listing plus institutional provenance.

**Why both happened:** the same failure as D-004 — inferring from proximity
rather than reading the specific sentence. Three instances now (PMID
attribution, BDC training set, mask denominator). The countermeasure that
worked each time was being made to quote the exact source passage; that is now
the standard for every provenance claim in this study, recorded as evidence
grades in `phase3R_source_corrections.md`.

Also withdrawn: the claim that an inflated B1 necessarily makes B2−B1
conservative. Correlated errors and shared representations can move a paired
contrast either way.

Related: [[dlbcl-project-state]]

---

## 2026-09-10 — D-005 · Phase 2 and Phase 3 PASS calls withdrawn

Both are restated as **PARTIAL** per supervisor review. Phase 2: endpoint
origins, patient-ID semantics, shared-predictor availability and data terms
remain open. Phase 3: gene aggregation undefined, the masking contradiction
above, coverage accounting, and overstated QC/normalisation claims. Phases 0–3
are **not** to be described as collectively passed.

---

## 2026-09-10 — D-004 · Correction: `in_pmid_30408148` does NOT mark MHG-discovery membership

**Corrects an error I introduced**, not an error in the source data.

In `reports/route_audit_2026_09_10_handoff.md` §4b I claimed that 496 of the 556
eligible samples carry `in_pmid_30408148 = TRUE` and that this made them
"the cohort in which the molecular high-grade signature was itself discovered."
The count is right; the attribution is wrong. Verified by direct retrieval
(NCBI E-utilities, `route1/data/raw/pubmed_abstracts_30408148_30523719_32187361.txt`,
SHA-256 `cb602da4ee84702e2dcf0ac4ae231d53aa3779febf8743691fbbf9d173964b3d`):

| PMID | Paper | Cohort |
|---|---|---|
| 30408148 | Painter et al., *Br J Haematol* 2019;185(4):781-784 — "Cell-of-origin in DLBCL: findings from the UK's population-based Haematological Malignancy Research Network" | HMRN, population-based |
| **30523719** | **Sha et al., *J Clin Oncol* 2019;37(3):202-212 — "Molecular High-Grade B-Cell Lymphoma"** | **928 patients from the trial adding bortezomib to R-CHOP (REMoDL-B)** |
| 32187361 | Lacy et al., *Blood* 2020;135(20):1759-1771 — HMRN targeted sequencing, n=928, 14 centres, ~4M catchment | HMRN, population-based |

So the flag marks membership in a **cell-of-origin report on the same
population-based cohort**, and MHG was defined on a **different, trial-based**
cohort. My §4b framing overstated the problem.

**Cause:** I took the PMID→paper mapping from memory instead of opening the
record — the exact failure this project already has a standing rule against
after the ImmunoBench incident. The rule is not "verify citations you doubt";
it is verify citations, including the ones that feel obvious.

**What survives the correction, as an open question for Phase 2:** Sha's
abstract states "Findings were validated in an independent data set." If that
validation set is HMRN / GSE181063, then the `pred_combine` MHG labels shipped
with this cohort are partly **in-sample for the MHG classifier**. That would
compromise **B1 as a comparator** — it would not contaminate B0 or the program
scores in B2. Requires the Sha supplement and sample lineage; do not assert
either way until traced. Note also that Sha (REMoDL-B) and Lacy (HMRN) both
report n=928; these are coincident totals for *different* cohorts and must not
be conflated.

**Action:** §4b of the handoff report has been corrected in place with a visible
correction notice rather than a silent edit.

---

## 2026-09-10 — D-003 · Workspace conflict: project scope excludes GEO transcriptomics

`.agents/skills/dlbcl-research/SKILL.md` §3 lists "GEO transcriptomic cohorts"
under **"Out of scope (phase 1)"**, qualified as "Option C fallback only".
`.agents/AGENTS.md` line 79 states the project "is H&E morphology + clinical
survival prediction."

Route 1 is a GEO transcriptomic study. It is therefore **not** an extension of
the documented project scope — it is the activation of the documented Option C
fallback.

**Resolution:** proceed, on three grounds: the supervisor plan explicitly
directs a new study rather than an amendment; the workspace anticipated this
branch rather than prohibiting it; and the H&E route's own external-validation
options were audited and found unusable (O-071 for survival, O-075/O-077 for
COO). Recorded because a future reader comparing this study against AGENTS.md
would otherwise find an undocumented scope departure.

**Not resolved by this entry:** whether the project's stated primary novelty
position and target journal still apply. That is a research-direction question
for the supervisor, not an implementation decision.

---

## 2026-09-10 — D-002 · Workspace conflict: directory layout

`.agents/AGENTS.md` prescribes `src/`, `configs/`, `reports/`,
`data/manifests/`. The supervisor plan requires an isolated `route1/` working
area with its own subtree.

**Resolution:** honour the supervisor plan's isolation, and mirror AGENTS.md
conventions *inside* `route1/` — `snake_case` filenames, YAML configs,
immutable source downloads separated from generated outputs, and registration
of every artifact in the `PROJECT_STATUS.md` Output Registry with an `O-NNN`
ID. Isolation is the stronger requirement here because Route 1 must not be
able to overwrite or be confused with the signed Phase 3B/3C artifacts.

---

## 2026-09-10 — D-001 · Workspace conflict: commit step cannot be followed

`.agents/AGENTS.md` "When Starting a New Task" step 6 says "Commit with a
descriptive message." Phase 0 of the supervisor plan says do not initialise a
public repository or push anything.

**Verified state:** branch `HEAD`, **0 commits across all refs, 0 tracked
files, no remotes configured**. A `.gitignore` exists and was validated by
dry-run in O-072 but was never committed against.

**Resolution:** the AGENTS.md step is unfollowable without initialising
history, which this phase forbids. Substitute a local provenance manifest —
`route1/manifests/source_registry.csv`, 106 analysis-relevant files with
SHA-256 — and record bulk trees at directory level (30.5 GB across
`DLBCLMorph`, `kaggle_upload_staging`, `models`, `kaggle`, `cell_shapes.csv`).

**Open risk, not resolved:** with no commits and two diverged copies
(Windows/Mac), there is no mechanism to establish which version produced any
existing result, including the manuscript sources where the Markdown draft and
`main.tex` are known to disagree. Hashes make the *current* state auditable;
they do not reconstruct history. This was raised with the researcher on
2026-09-10 and deferred by his decision in favour of the research work.
