# Phase 3 — phase-end report

**Date:** 2026-09-10 · **Phase:** characterise expression platforms and freeze biological inputs

---

## 1. Completed

| Task | Work | Artifact |
|---|---|---|
| 1 | Both platform annotations downloaded and parsed; versions, identifiers, blank/multi-mapping probes and gene overlap recorded | `manifests/platform_summary.csv`, `manifests/gene_mapping.csv` |
| 2 | Development expression acquired (metadata-declared terms, §3 of `data_use_terms.md`). **External expression deliberately NOT downloaded.** | `data/raw/GSE181063_RawData.txt.gz` |
| 3 | Raw/normalised/logged state determined empirically | `reports/platform_coverage.md` §4 |
| 4 | Deterministic outcome-independent probe→gene rule, identical across platforms | `configs/representation.yaml` |
| 5 | Eight biological programs proposed from published definitions | `manifests/program_gene_sets.csv` |
| 6 | Per-program source, version, formula, direction, minimum coverage, missing-gene handling | `configs/representation.yaml` |
| 7 | Ranking reference universe specified | `configs/representation.yaml` |
| 8 | Coverage perturbations defined from actual platform designs, plus random-mask sensitivity | `configs/representation.yaml` |

Downloads (SHA-256): GPL14951 `372432a3…` (62.1 MB), GPL570 `9ef4cf16…` (85.6 MB), GSE181063_RawData `a76e6993…` (134.4 MB), 8 MSigDB JSONs each hashed.

## 2. Verified

- **GPL14951:** 29,377 probes → **20,818 genes**; 0 blank, 0 multi-mapping. Annotation dated 2017-12-22.
- **GPL570:** 54,675 probes → **21,653 genes**; **8,893 blank symbols**, **2,796 multi-mapping excluded**. Annotation dated 2020-12-14.
- **Cross-platform overlap: 15,647 shared genes = 75.2% of the development platform** (lower bound — no alias resolution).
- **All eight programs are scoreable on both platforms**, 87.5–98.5% shared; none is dropped by the coverage thresholds.
- **Development expression is genuinely raw**: not log-transformed (45.8–73,351.6), not quantile-normalised (sorted-column max difference 28,685.4), per-sample medians varying ~24×. GEO's "normalised using Lumi" describes the GSM `VALUE` column, not this file.
- **`probe_detection` = fraction of probes with detection p < 0.01**, reproduced to 6 decimal places on 5 arrays — closes a Phase 1 open item.
- **Probe reconciliation clean**: expression is a strict subset of the platform (29,372/29,377), zero orphans.
- **1,600 probes (5.4%) never detected** at p<0.01 in any of 19 sampled arrays; only 66.4% detected in >50%.
- Program gene sets fetched as JSON and hashed, **not transcribed**. A web summary claiming HALLMARK_E2F_TARGETS had 375 genes was wrong; the file says **200**.

## 3. Unresolved

| Item | Consequence |
|---|---|
| **The realistic platform mask perturbs only 1.9% of program genes** (26 of 1,361); only 0.48% of development-only genes sit in any program. | **B4 ≈ B3 by construction.** A null B4−B3 would mean "there was nothing to mask", not "coverage robustness doesn't matter". This is the phase's substantive finding and needs a supervisor decision — four options in `platform_coverage.md` §3, none chosen. |
| Alias/synonym resolution not performed. | 75.2% overlap is a lower bound; the 2017-vs-2020 annotation gap inflates apparent divergence. |
| External expression matrices not inspected. | Overlap is annotation-based. Genes annotated on GPL570 may be undetected in GSE10846/GSE87371; the detection policy must be applied there under a predeclared rule. |
| Multi-probe collapse rule provisional. | 5,719 of 20,818 development genes have multiple probes; rule may be revised in Phase 4 **before** fitting. |

## 4. Gate

**PASS.**

The pass condition is "biological inputs and coverage rules are reproducible without outcome-based feature selection."

- Gene sets are fetched from a versioned public source with systematic names, PMID and file hashes — reproducible, and not hand-written.
- The probe→gene rule is deterministic, applied identically to both platforms, and excludes multi-mapping probes; no probe was chosen by prognosis.
- Coverage thresholds, missing-gene handling, ranking universe and masking schedule are all fixed in `representation.yaml`.
- **No outcome has been touched.** No expression value has been joined to survival.
- Program coverage is sufficient in every cohort; no program fails its thresholds, so no biological scope revision is required on coverage grounds.

The gate passes on its own terms. It passes while surfacing a finding that weakens one arm of the planned ladder, which is the correct order for that to happen — before fitting, not after.

## 5. Next

**Phase 4 — write and freeze the analysis protocol.** Three decisions carried in that should be settled before the freeze:

1. **B4's scope** (`platform_coverage.md` §3) — run-and-report-null, drop, re-scope to a harsher coverage regime as a dated exploratory change, or add platform-divergent programs under an outcome-independent rule. **Supervisor decision.**
2. **Primary population** — 301-patient identity-safe subcohort versus all 556 samples, from Phase 1. My suggested framing remains (a) primary + (b) prespecified sensitivity. **Supervisor decision.**
3. **B1's status** — its labels may be partly in-sample (Phase 2); direction is favourable (inflated B1 makes B2>B1 conservative) but B1's absolute value must not be reported as an independent COO/MHG estimate.

Also to be fixed in Phase 4: minimum meaningful improvement set against the **103-patient / 36-event** final test; per-cohort horizon handling given GSE10846's 2.12 y median follow-up; and time-unit harmonisation (GSE87371 is in months, the others in years).

## 6. Compute

| Field | Value |
|---|---|
| Kaggle sessions used | **0** |
| GPU used | none — no fitting has occurred |
| Fits completed / remaining | 0 / all |
| Persistence verified | n/a |
| Downloads this phase | 11 (2 platforms, 1 expression matrix, 8 gene sets), all SHA-256 recorded |
| Local disk added | ~282 MB under `route1/data/raw/` |

No model fitted. No outcome joined to any expression value. No external cohort expression downloaded.
