# DLBCL H&E → Cell-of-Origin: Hematologist Review Pack

**To:** Reviewing hematologist / hematopathologist
**From:** Kawser Sikder, Dept. of ECE, North South University, Dhaka (+ AI assistant LLM — methods draft only, all medical judgments are yours)
**Date:** 2026-09-05
**Purpose:** Independent check BEFORE we train/publish the next study. We will not train until you return this.
**Time asked:** ~60–120 min for 50 panels (H&E + overlay). No outcome data shown. No patient identifiers.
**Files to open:** `reports/phase_03_e007_expert_priority_subset.csv` (50 rows, columns `expert_review`, `expert_failure_mode`, `expert_notes` are blank for you) + overlays in `kaggle/phase_03_morphology_survival/output_e007_full_extraction/qc_overlays/` + contact sheets in `reports/phase_03_e007_ai_contact_sheets/`

> Please be strict. A “fail” from you helps us more than a polite “pass”. We publish every rating, including fails.

---

## 1. What we are planning to do (plain language)

**Question:** In diffuse large B-cell lymphoma (DLBCL), can the routine H&E slide alone give a clue about cell-of-origin (COO) — germinal-centre B-cell (GCB) vs non-GCB by the Hans IHC algorithm (CD10 / BCL6 / MUM1) — well enough to **triage which cases most need IHC where IHC is unavailable**?

We do **NOT** claim H&E replaces IHC, and we do **NOT** claim diagnosis or treatment change. Intended use only: retrospective risk/triage research aid where stains, antibodies, or staff are missing (common in South Asia / Africa / Latin America).

**Why COO, why now:** Our survival study (Phase 3C, n=170, 58 deaths, pre-registered) found H&E nuclear shape/packing adds **nothing** beyond age/stage/LDH/ECOG/extranodal sites (ΔC −0.023 [−0.050,+0.001]). That null is posted first. COO is a better-conditioned next question: 163 labelled patients (70 GCB / 93 non-GCB, 95.9% complete), balanced classes, no censoring — “merely small” instead of underpowered. Internal H&E→COO results exist (~0.87 AUC, n=115, no external cohort); **no independent-centre Hans-IHC validation from H&E exists** (only Yüce GOYA→CAVALLI trial holdout n=167, GEP labels, AUC ~0.70). That gap is the contribution. A second null will also be published.

**Label we use:** Released `HANS` column as-is. We verified `HANS=1 → GCB` at 172/174 (98.9%). CD10/MUM1 are binary {0,1}, BCL6 is % with ≥30% positive (data dictionary wrongly says all-%; we prohibit that reading). Two patients (26804, 26836) disagree with the tree; kept as 1.1% noise, not corrected. Hans↔gene-expression ceiling ~80–85% stated with every figure — AUROC vs Hans ≠ AUROC vs true biology.

**What the computer measures (and does NOT):** Binary all-nucleus segmentation (E-001 U-Net + watershed, Dice 0.888 on LyNSeC tiles) → 1.96M objects over 30,007 TMA patches → patient summaries of nuclear shape (area/perimeter/eccentricity/solidity/circularity/axes), stain intensity, local packing (nearest-neighbour, Delaunay), patch heterogeneity. **No tumour vs immune labels.** We never call anything “tumour–immune mixing” from H&E alone. Coordinates are patch-local pixels (µm pending). If you judge segmentation unusable, the study stops.

**Models (locked before training):** C0 clinical logistic (negative control — should be ~0.5; ≥0.65 means design flaw) → C1 handcrafted (56) → C2 released geometry (44) → **C3 H-optimus-0 + attention-MIL (primary)** → C3b Phikon-v2 → C4 fusion of C1+C3 scores. 5-fold × 10-repeat patient-level CV, thresholds in-fold only, 1000 bootstraps, calibration gate [0.7,1.3]. External test once on TCGA-DLBC (RNA-derived labels, GEP≠Hans stated). Full spec: `reports/phase_04_coo_analysis_protocol.md` + pre-signing fixes `reports/phase_04_coo_amendment_A001_A007.md`.

---

## 2. What we ask you to check (the only gate)

**Set:** 50 panels = all 39 AI-CAUTION + 1 AI-FAIL (26807) + known artifact (17649/5053 linear structure) + 9 PASS controls. One representative overlay per patient (H&E | probability | contours). Full 170 available on request.

**For each panel, please fill in the CSV:**

| Column you fill | How |
|---|---|
| `expert_review` | `PASS` = nuclear contours usable for shape/packing measurement; `CAUTION` = usable with reservation (say why); `FAIL` = not usable (wrong objects / missed nuclei / artifact dominates) |
| `expert_failure_mode` | pick ≥1: `clean` / `merge_split` (merged or split nuclei) / `missed_nuclei` / `fibrous_capture` (spindle/stroma taken as nuclei) / `elongated_fragmentation` / `sparse_tissue` / `partial_tissue` / `linear_artifact` / `out_of_focus` / `other:<text>` |
| `expert_notes` | free text: tumour vs stroma? crush? necrosis? “would you trust a shape metric here?” |

**Three targeted questions (please answer in email even if CSV is complete):**

1. Patient **26807** (our single FAIL) — fibrous/spindle field. Is this tumour morphology or stroma/artifact? Should this patient be excluded from a morphology study (we plan sensitivity n=162 without it)?
2. Patient **13957** (23% low-tissue patches) + sparse/partial fields generally — acceptable to keep with a tissue≥50% rule, or exclude?
3. **Fibrous/elongated capture** (~25 patients flagged by AI): is the segmenter measuring lymphocytes or fibroblasts/stroma? If the latter, our “packing” features are contaminated — say so and we will report it as a limitation (or restrict to a cleaner subset as sensitivity only).

**What PASS means / does not mean:** PASS = “contours follow nuclei well enough to measure shape/packing”. It does **not** endorse any survival/COO claim, tumour-vs-immune label, or clinical use.

---

## 3. Code directory (where everything lives — for audit, you need not run it)

```
F:\Research Projects\NHL-DLBCL\
  reports/
    phase_04_coo_analysis_protocol.md        # frozen design v1.0 (unsigned) — you review §1-2/§11
    phase_04_coo_amendment_A001_A007.md      # 7 fixes to apply before signing (novelty, TCGA method, C4, encoders, QC/uncertainty, EPV, tiling)
    phase_04_coo_study_scope.md              # why COO, triage framing, power (163 vs 58 events)
    phase_03_e007_ai_overlay_review.csv      # AI 130/39/1 (NOT pathology — for comparison only)
    phase_03_e007_expert_priority_subset.csv # *** YOUR FORM (50 rows, blank expert_* cols) ***
    phase_03_e007_ai_contact_sheets/         # 22 PNG contact sheets (all 170 panels, quick browse)
    muse_spark_1_3_review.md                 # independent audit of prior run
    preprint/main.tex + references.bib + figures/  # 17-page null manuscript (builds clean, 87/87 numbers pass)
  configs/
    phase_04_coo_analysis_protocol.yaml      # machine-readable twin of protocol (hash-locked)
  data/
    raw/dlbcl_morph/clinical_data_cleaned.csv# 209 pts, HANS/CD10/BCL6/MUM1, OS (public TCIA secondary data)
    manifests/patient_manifest.csv           # 170 H&E-eligible, 30,007 patches
    manifests/coo_split_ids.csv              # NOT YET GENERATED — blocked until protocol signed + your review
  kaggle/phase_04_coo/                        # runnable, versioned scripts (CPU→GPU order)
    README.md                                # runbook (attach list, order, early-stop rule)
    build_coo_split_ids.py                   # fresh 5×10 HANS-stratified splits, seed 20260903, signature-gated
    e010_coo_ladder.py                       # C0/C1/C2/C4 tabular logistic, nested CV, 1000 boot, triage points
    e010_extract_embeddings.py               # frozen H-optimus-0 / Phikon-v2, once, outside CV (not leakage)
    e010_abmil.py                            # C3/C3b attention-MIL, frozen 8-config grid, checkpoints+resume
  kaggle/phase_03_morphology_survival/output_e007_full_extraction/
    qc_overlays/*.png                        # *** 170 overlays you sample from ***
    cells.parquet / patch_qc.csv / patient_features.csv / exclusion_log.csv / run_summary.json
  src/analysis/
    verify_hans_encoding.py                  # HANS=1=GCB proof (172/174) + BCL6 sweep
    derive_tcga_coo.py                       # TCGA GEP gate dry-run (Lymph2Cx, unclassified rule)
    assess_tcga_external_feasibility.py      # why survival external n=44/8 deaths infeasible; COO AUC on ~44 viable
    audit_manuscript_numbers.py              # 87-value manuscript↔CSV checker (currently PASS)
```

No protected health information. Public secondary data (TCIA DLBCL-Morph CC BY-NC 4.0, LyNSeC Zenodo). Ethics exemption for public secondary data to be confirmed by institution — we state this in the paper, not as your responsibility.

---

## 4. Analysis workflow in pseudo-steps (shodo — what runs in what order)

```
1. POST survival preprint (prerequisite; this COO work never delays it)
2. YOU review 50 panels -> we record PASS/CAUTION/FAIL (primary n=163 stays; B/C/D sensitivities drop 26807/13957/26804)
3. APPLY A001-A007 -> SIGN protocol v1.1 (§13 name/date/hash) -> GENERATE coo_split_ids.csv (reads patient_id+HANS only)
4. CPU afternoon: C0 (should ~0.5) -> C1/C2 tabular logistic (nested 5x10, in-fold impute/prune/scale, thresholds in-fold)
5. IF C1 AND C3-internal upper-AUROC <0.65 -> STOP external (report internal null; saves 2-3 wks)
6. DRY-RUN TCGA gate (slide+RNA join, balance ≤80/20, unclassified ≤15%) BEFORE any TCGA image tiling
7. GPU once: frozen embeddings (H-optimus-0 primary; Phikon-v2 secondary) -> ABMIL C3/C3b (8-config grid, patience 10)
8. C4 fusion (logistic on 2 fold-internal scores) + temperature scaling + conformal abstention (10/20% "needs IHC") + QC-stratified report
9. SINGLE-USE external scoring (locked model, no retuning) -> publish ALL models incl. failures + calibration/ROC/OOF dumps
```

Integrity rules you can hold us to: representations/ladder frozen after label access; primary encoder stays H-optimus-0 even if Phikon scores higher; no full-cohort threshold search; external scored once (any revision → labelled exploratory); segmentation never re-run against labels.

---

## 5. Limitations we already state (please add any we missed)

Single retrospective TMA cohort; 163 small (AUROC ±0.07; external ±0.14, gross-failure only); Hans proxy ceiling ~15–20%; all-nucleus (no phenotype); patch-local pixels; stain/scanner batch; TMA→WSI shift for external; foundation encoders may have seen TCGA (stated). This will not change DLBCL treatment; best case is a triage signal + open artifacts saving the next group months.

## 6. Sign-off (please return)

- [ ] I reviewed [ ]/50 panels (CSV attached / in shared folder).
- [ ] Segmentation is / is not adequate for nuclear shape/packing measurement (delete one; qualify).
- [ ] Patients to exclude in sensitivity: _____________.
- [ ] Any diagnosis/PHI concern: _____________.
- Name / date / signature: _____________ .
- May we acknowledge you by name? Y / N. Conflicts to declare? _____________.

Thank you — a strict review now is worth more than a rescue later.

*Contact: Kawser Sikder, NSU ECE Dhaka, [INSTITUTIONAL EMAIL]. Protocol hash (v1.1 draft): `34d6d589…` — splits blocked until signed.*
