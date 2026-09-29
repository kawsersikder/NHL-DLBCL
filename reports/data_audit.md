# DLBCL-Morph Data Audit — Clinical Table

**Status:** clinical-table audit and patient-level image inventory complete (updated 2026-08-28); row-level slide/stain/coordinate manifest remains.
**Source:** `data/raw/dlbcl_morph/clinical_data_cleaned.csv` (TCIA, CC BY-NC 4.0, MD5 `9be9d237c49506db16d3c3b53825f827`; provenance in `data/raw/dlbcl_morph/PROVENANCE.md`).
**Produced by:** `kaggle/phase_01b_dlbcl_morph_data_audit/audit_clinical.py`

## Cohort and outcome

| Item | Value |
|---|---|
| Patients | 209 (unique `patient_id`, no duplicates) |
| OS events (deaths) | **72 / 209 (34.4%)**; 137 censored |
| OS time (years) | median 7.42, range 0.02–13.88; no missing, no non-positive times |
| OS time, events | median 3.46, range 0.02–12.27 |
| OS time, censored | median 8.44, range 2.78–13.88 |
| PFS time (years) | present, but **no progression-status indicator column** |

### Consequence 1 — endpoint is OS only
The table provides `PFS` times but no event indicator for progression, so PFS/competing-risk modelling is impossible without unverifiable assumptions. **Pre-specify OS as the only Phase-1 endpoint.** (OS measurement is from end of treatment, per the data dictionary.)

### Consequence 2 — no locked test set; nested CV is primary
A 20% patient-level locked test set would contain only ~14 OS events (of ~42 patients) — too few for stable C-index/calibration. Per roadmap evaluation rule 2 and risk R-001: **use repeated nested patient-level CV as the primary internal estimate** and state that no independent test set was possible. Cross-source testing (TCGA-DLBC etc.) remains domain generalisation, not validation.

### Consequence 3 — the paper's geometric baseline cohort is 170 patients / 58 events
`cell_shapes.csv` covers only **170 of the 209 patients** (58 OS events among them): the geometric-feature analysis excludes patients whose TMA cores yielded no segmented cells. The published baseline (C-index 0.635) and our Baseline 1 therefore refer to n=170, not the full 209. Baseline 0 (clinical-only) can use all 209 — a cohort difference to state explicitly when comparing models.

## Missingness per variable

| Variable | Missing (n, %) |
|---|---|
| Age, ECOG PS, Stage, IPI Score, RIPI Risk Group, OS, PFS, Follow-up Status | 0 |
| EN | 2 (1.0%) |
| LDH | 4 (1.9%) |
| IPI Risk Group (4 Class) | 1 (0.5%) |
| MYC IHC / BCL2 IHC | 14 (6.7%) each |
| BCL6 IHC | 18 (8.6%) |
| MUM1 IHC / HANS | 24 (11.5%) each |
| CD10 IHC | 25 (12.0%) |
| MYC FISH | 30 (14.4%) |
| BCL6 FISH | 31 (14.8%) |
| **BCL2 FISH** | **53 (25.4%)** |

Core IPI covariates are essentially complete; IHC/FISH markers have 7–25% missingness — imputation must be fitted inside training folds only.

## Clinical baselines feasibility

- **IPI Score: complete** (distribution 0–5: 25/64/50/42/21/7). **R-IPI group: complete** (0: 25, 1: 113, 2: 71). Clinical-only penalised Cox (Baseline 0) and IPI/R-IPI comparison are immediately feasible.
- **NCCN-IPI: not computable** — requires LDH as a multiple of the upper limit of normal; this table has binary LDH only. Report IPI and R-IPI as the clinical comparators.
- Age: median 63 (24–89). ECOG 0–3. LDH elevated in 78/205 known. Stage I–IV: 42/60/41/66. EN sites 0–7.

## Next steps for this audit

1. ~~Fetch `cell_shapes.csv` + mapping files~~ — done (figshare, MD5-verified, 2026-08-23).
2. ~~Reproduce the supplied survival regression notebook~~ — E-002 complete: geometric corrected C-index **0.6358** with 1,000 bootstraps.
3. Freeze patient-level split IDs for the nested-CV protocol only after the Phase 3 feature matrix and eligibility/exclusion rules are frozen.
4. Patient-level image inventory complete in `data/manifests/patient_manifest.csv`: 209 clinical patients, 170 with H&E patches, 30,007 H&E patches, and an exact match between H&E-patch and released-cell patient sets. Row-level slide/stain/patch-coordinate reconciliation remains before cross-patch spatial features.
