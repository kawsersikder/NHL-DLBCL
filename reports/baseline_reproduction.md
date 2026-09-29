# Baseline Reproduction — Stanford DLBCL-Morph Survival Regression (E-002)

**Date:** 2026-08-23 · **Environment:** Kaggle notebook, Tesla T4, internet ON, ~8 min wall time
**Script:** `kaggle/phase_01b_dlbcl_morph_data_audit/phase_01b_one_shot.py` (O-023)
**Reference:** `data/raw/dlbcl_morph/survival_regression_original.ipynb` (O-022)
**Inputs:** `dlbcl-morph-tables` Kaggle dataset (`cell_shapes.csv`, `clinical_data_cleaned.csv`)

## Results

| Mode | Uncorrected | Optimism | Corrected C-index | Adj. 95% CI | Paper target | Verdict |
|---|---|---|---|---|---|---|
| GEOMETRIC | 0.7847 | 0.149 | **0.6358** | 0.575 – 0.692 | 0.635 [0.574 – 0.691] | ✓ reproduces |
| CLINICAL | 0.7480 | 0.074 | **0.6738** | 0.602 – 0.737 | 0.674 | ✓ reproduces |
| ALL | 0.8369 | 0.154 | **0.6827** | 0.630 – 0.730 | 0.700 | ✗ −0.017, inside CI |

Corrected = uncorrected − mean(bootstrap − original) over 1,000 resamples (seed 42);
CI percentiles taken at sorted positions 24 / 974, optimism-adjusted — identical to the original cells.

## Method fidelity checks (against the verbatim original notebook)

- Patient merge/aggregation matches cell 9 exactly: m:1 join on `patient_id`,
  drop `patch_id`/`cell_number`, mean+std aggregation, clinical `*_std` columns dropped.
- `geo_cols` verified character-for-character identical to cell 11 (46 geometric features).
- Penalizers match cells 12–13: GEOMETRIC 0, CLINICAL 0, ALL 5e-5.
- `QuantileTransformer(n_quantiles=10, random_state=42)` fitted dataset-wide including
  OS/FUS — the original's leakage quirk replicated intentionally (Decision Log 2026-08-23).
- Bootstrap loops and RNG consumption order match cells 20/24 (`np.random.seed(42)` before each).

## ALL-mode deviation analysis

- The committed original notebook's saved outputs contain **only the GEOMETRIC run**
  (uncorrected 0.786, corrected 0.635, adjusted CI 0.574–0.691) — these match our run to
  rounding. The CLINICAL 0.674 and ALL 0.700 figures exist only in the paper text, so there is
  no committed code output to diff against for ALL mode.
- Most plausible cause: library-version drift in an unstable regime (~68 covariates vs 209
  patients, penalizer 5e-5, uncorrected 0.837). Small numeric differences in Cox fitting or
  concordance computation shift the optimism-corrected estimate visibly in this regime while
  leaving the well-conditioned GEOMETRIC/CLINICAL modes at the third decimal.
- **Decision (2026-08-23): accept 0.683 as a documented deviation.** Chasing exact parity would
  require pinning a 2020-era lifelines/scikit-learn stack; not worth the effort now. Our Phase 3+
  models use fold-safe preprocessing and will be compared against these baselines with the same
  bootstrap protocol.

## By-products and open items from the same run

- Clinical audit written to `audit_report.json` / `.txt`: 209 patients, 72 OS events (34.4%);
  per-column missingness recorded (worst: BCL2 FISH 25.4%). Consistent with `reports/data_audit.md`.
- Step-5 HoLy-Net QC pilot failed: `he.tar` from Zenodo record 8065174 is a `torch.save()`
  bundle (ZIP container, PK magic + `archive/data.pkl`), not a tar archive. Root-caused by remote
  range-request byte inspection; MD5 matched throughout, so downloads were never corrupt.
  Fix shipped as `kaggle/phase_02_segmentation_qc/phase_02_holynet_qc_probe.py` (O-024):
  direct `torch.load`, `module.` prefix stripped, `/` → `.` key normalisation,
  coverage diagnostics, 16-tile overlay pilot.
- TODO: copy the run outputs from the committed Kaggle version into
  `kaggle/phase_01b_dlbcl_morph_data_audit/output_final/`
  (`run_summary.json`, `audit_report.json/.txt`, `phase_01b_reproduction/run_summary.json`).
