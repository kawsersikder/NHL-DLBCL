# Phase 4B COO Protocol — Pre-signing Amendments A001–A007 (Draft)

**Protocol:** `reports/phase_04_coo_analysis_protocol.md` v1.0 (DRAFT, unsigned) + twin `configs/phase_04_coo_analysis_protocol.yaml`
**Amendment date:** 2026-09-05
**Author:** LLM (draft for Kawser Sikder to review; NOT signed)
**Status:** MUST be pasted into protocol §12 and applied to §§1–11 + YAML BEFORE §13 sign-off. After sign-off this file is frozen; any further change is a new dated §12 entry.
**Precondition (unchanged):** Phase 3C preprint posted before E-010. No feature–label relationship examined to date.

Each item lists: problem → fix → exact protocol edit → YAML edit → verification.

---

## A001 — Narrow the novelty gap (Yüce holdout exists)

**Problem:** Scope §“No externally validated result” and protocol §3.2/E2 motivation overstate the gap. Yüce et al. (GOYA train/test → CAVALLI independent holdout, n=167, GEP ABC/GCB, AUC 0.67–0.70) is an external holdout, albeit GEP-labelled and modest. Gupta/TMC (n=115, 87.4±5.7% 3-fold CV, no external) and Syrykh (565 WSIs, GC AUC 0.624, internal CV) further crowd “internal-only” space. A reviewer will cite Yüce.

**Fix — replace in scope §1 and protocol §3.2:**
> “Internal COO-from-H&E results exist (best located ≈0.87 AUC, n=115, single centre, no external cohort). The only trial-holdout result located (Yüce et al., GOYA→CAVALLI, n=167, GEP labels, AUC ~0.67–0.70) used gene-expression labels with modest performance. **No independent-centre external validation of Hans-IHC COO from H&E has been published.** That is the contribution.”

Cite Yüce + Syrykh + Gupta explicitly in manuscript intro. E2 remains the contribution (Hans-trained → GEP-tested is harder, state as such).

**YAML:** no change (gap is prose, not machine-readable).

**Verify:** `grep -rn "No externally validated" reports/phase_04_coo_*` returns 0 after edit.

## A002 — Lock the TCGA-DLBC GEP derivation method (E2 fully pre-specified)

**Problem:** §4.1 defers derivation to “amendment that accompanies E-011”. E2 is then not fully locked at signing; gate §4.2 cannot be executed deterministically (unclassified rate, Hans↔GEP ceiling unhandled).

**Fix — insert new §4.1.1 (frozen):**

| Choice | Frozen value |
|---|---|
| RNA source | TCGA-DLBC HTSeq-FPKM via GDC API, gene symbols, log2(FPKM+1) |
| Classifier | Wright et al. Lymph2Cx 20-gene (8 ABC / 7 GCB / 5 HK) nearest-centroid; weights from published centroid file committed as `data/raw/tcga/lymph2cx_centroids.csv` (MD5 recorded) |
| Call rule | ABC/GCB by max centroid correlation; **Unclassified if \|Δcorr\| < 0.10 or max corr < 0.30** (pre-specified, not tuned) |
| Unclassified handling | Excluded from E2 AUROC; count + rate reported; if rate >15% E2 marked “not evaluable, high unclassified” per gate |
| Expected ceiling | Hans↔GEP concordance 72–83% (Li/Yoon/Zamò). Even a perfect Hans predictor caps E2 at AUROC ≈0.80–0.85. State with every E2 figure. |
| Repro script | `src/analysis/derive_tcga_coo.py --offline` (GDC + centroid join + balance + unclassified rate; exits non-zero if gate fails) |

**YAML — add under `external_validation`:**
```yaml
label_derivation:
  rna: tcga_htseq_fpkm_log2p1
  classifier: lymph2cx_20gene_centroid
  centroid_file: data/raw/tcga/lymph2cx_centroids.csv
  unclassified_rule: abs_dcorr_lt_0.10_or_maxcorr_lt_0.30
  unclassified_action: exclude_and_report_rate
  unclassified_fail_rate: 0.15
  hans_gep_ceiling: 0.72_to_0.83
  script: src/analysis/derive_tcga_coo.py
```

**Verify:** run `python src/analysis/derive_tcga_coo.py --offline` → prints n, balance, unclassified rate, gate PASS/FAIL without touching images.

## A003 — Lock C4 fusion spec (currently “C1 ∪ C3 risk score”)

**Problem:** C4 underspecified — stacking vs concat, fitted where, leakage risk.

**Fix — replace §3/C4 row + add §3.3:**
> **C4 = penalised logistic (same grid as §6.1) on 2 features: (a) C1 fold-internal linear predictor (z-scored on training fold), (b) C3 fold-internal MIL logit (z-scored on training fold).** Both base scores are produced by models fitted **only on the outer-training fold** (C1 logistic + C3 ABMIL at its inner-selected hyperparams), then the 2-feature fusion is fitted on the same outer-training fold. Applied unchanged to held-out fold. No OOF-reuse across folds. If either base fails to converge in a fold, C4 for that fold = C1 score (logged).

**YAML — replace `model_ladder` C4 entry:**
```yaml
- {id: C4, role: fusion, method: logistic_on_2_fold_internal_scores, inputs: [C1_linear_predictor_z, C3_mil_logit_z], fallback: C1_if_C3_fails}
```

**Verify:** `e010_coo_ladder.py` asserts C4 design matrix has exactly 2 cols per fold; logs fallback count (expect 0).

## A004 — Correct encoder access + contamination statement

**Problem:** Protocol §2.2 says H-optimus-0 “Apache 2.0, ungated” and Phikon-v2 “ungated”. HF shows H-optimus-0 gated click-through (login + accept, no institutional email); Phikon-v2 ungated-download but **Owkin non-commercial licence** (not permissive). Phikon-v2 pretrained on TCGA PANCAN-XL (likely saw TCGA-DLBC); H-optimus-0 500k proprietary undisclosed. E2 with TCGA-seen encoder is not clean external validation.

**Fix — replace §2.2 table rows:**
- H-optimus-0 (`bioptimus/H-optimus-0`): licence Apache-2.0, **access: gated click-through (HF account + accept; no approval delay)**. 1.1B params; T4 inference needs mixed precision + batching; “10–30 min/30k patches” is estimate, not promise.
- Phikon-v2 (`owkin/phikon-v2`): licence **Owkin Non-Commercial** (record for publication compliance); ungated download.
- Add §2.3: “Pretraining-contamination statement: Phikon-v2 may have seen TCGA-DLBC during pretraining; H-optimus-0 training set undisclosed. **Primary E2 uses H-optimus-0.** C3b/Phikon E2 reported as sensitivity with contamination caveat. Contamination does not affect E1 (DLBCL-Morph unseen by both).”

**YAML — patch `representations.foundation_embeddings`:**
```yaml
primary_encoder: {name: H-optimus-0, hf_id: bioptimus/H-optimus-0, license: apache_2_0, gated: true, access: hf_click_through}
secondary_encoder: {name: Phikon-v2, hf_id: owkin/phikon-v2, license: owkin_non_commercial, gated: false}
contamination: {phikon_may_have_seen_tcga: true, hoptimus_training_undisclosed: true, primary_E2: H-optimus-0}
```

**Verify:** `e010_extract_embeddings.py --check-access` prints HF auth status + licence reminder before downloading.

## A005 — Pre-specify QC-gated uncertainty + stain-robust DL (the AI/ML novelty)

**Problem:** User-requested AI/ML standout (uncertainty, QC-awareness, robustness) must be pre-specified now or it becomes fishing later.

**Fix — add §3.4 (frozen, no extra labelling):**

1. **C3-cal (part of C3, not a new model):** temperature scaling on inner folds only; report AUROC unchanged + calibration slope/intercept + curves. Rejection rule §7 applies.
2. **Abstention analysis (descriptive, not E1):** conformal score = 1 − softmax(true-class prob) on inner folds; report AUROC/coverage at fixed abstention 10%/20% (thresholds from training folds only). Motivated use: “needs IHC” flag for triage.
3. **QC-stratified reporting (descriptive):** report E1 AUROC overall + stratified PASS (130) vs CAUTION/FAIL (40) using frozen `phase_03_e007_ai_overlay_review.csv` labels. No refitting on QC; if CAUTION underperforms, that is a finding, not a reason to drop them (primary stays n=163).
4. **Stain-robustness (already S5/S_ext, tighten):** S5 = Macenko-normalised input through identical frozen encoder + identical ABMIL grid; S_ext identical externally. Primary stays no-norm.

No TransMIL/HIPT (prohibited, TMA lacks WSI hierarchy — unchanged). No grid expansion (unchanged).

**YAML — append:**
```yaml
calibration_abstention:
  temperature_scaling: inner_folds_only
  conformal_score: one_minus_softmax_true
  abstention_rates: [0.10, 0.20]
  qc_stratified_reporting: [PASS_130, CAUTION_FAIL_40]
  qc_file: reports/phase_03_e007_ai_overlay_review.csv
```

## A006 — Arithmetic, ordering, compute realism

- **EPV fix:** scope “0.8 for 61 features” → “58/61 ≈ 0.95 overall; ≈46/61 ≈ 0.75 per outer-training fold (median-kept 27 → 1.7). Still <<10.” Effective MIL params far larger — “merely small” applies to C1/C2, not C3. State explicitly in §5.1.
- **Ordering:** every GCB/non-GCB mention as “70 GCB / 93 non-GCB” (minority first). Fix scope §2 “93 vs 70” bare line.
- **Compute:** replace “1–2 weeks T4” with “budget 2–3 weeks wall-clock on Kaggle T4 with interrupt/resume; per-fit cap 90 min; checkpoint every outer fold; CPU-first C0–C2 (~1 afternoon) before any GPU.” 50 outer + 250 inner ABMIL fits is the cost driver.
- **C0/early-stop tripwires (0.65)** keep as stated, labelled “tripwires, not hypothesis tests”.

## A007 — External tiling spec + gate dry-run order

**Freeze §4.3 numbers:** DLBCL-Morph patch = PNG crops as released (record exact px in `derive_tcga_coo.py` output; match px, match µm/px where metadata permits else record mismatch); TCGA tiling 256 px at 20× (0.5 µm/px) sliding, non-overlapping, `tissue_fraction ≥ 0.50` (frozen E-006 rule, mean-RGB ≤235); cap 200 patches/patient approximating median 177; sampling seed 20260903; no stain-norm primary.

**Order (enforced in `kaggle/phase_04_coo/README.md`):** (1) post preprint → (2) sign v1.1 → (3) `build_coo_split_ids.py` → (4) C0–C2 CPU → (5) enforce early-stop literally → (6) dry-run TCGA gate (slide+RNA join, balance, unclassified rate) BEFORE any TCGA tiling → (7) embedding extraction once → (8) C3/C3b/C4 → (9) single-use E-011.

---

## Sign-off for v1.1

Applying A001–A007 to §§1–11 + twin, recomputing lock hash via `build_coo_split_ids.py --print-hash`, and completing §13 authorises split generation. Record new SHA-256 here and in `coo_split_ids_summary.json`.

| Role | Name | Date | Protocol SHA-256 (v1.1) |
|---|---|---|---|
| Researcher | | | |
| Supervisor (recommended) | | | |

*After signing, every further change is a new dated §12 row written BEFORE the affected result is seen.*
