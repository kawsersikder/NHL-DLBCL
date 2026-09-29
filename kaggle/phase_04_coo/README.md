# Phase 4B COO from H&E — Kaggle runbook (E-010 / E-011)

**Protocol:** `reports/phase_04_coo_analysis_protocol.md` v1.1 (sign A001–A007 first) + `reports/phase_04_coo_amendment_A001_A007.md`
**Precondition:** Phase 3C preprint posted. No feature–label relationship examined before signing.

## Order (enforced, see amendment A007)

| Step | Where | Script | GPU? |
|---|---|---|---|
| 0. Sign §13 v1.1 | local | `python kaggle/phase_04_coo/build_coo_split_ids.py --print-hash` → paste name/date/hash | — |
| 1. Splits S_COO | local | `python kaggle/phase_04_coo/build_coo_split_ids.py` → `data/manifests/coo_split_ids.csv` | CPU 1s |
| 2. Upload inputs | local | make `dlbcl-phase4b-inputs` (~15 MB): E-007 `patient_features.csv` + `patch_qc.csv` + AI-QC review + geometry + clinical + splits + scripts (see below) | — |
| 3. C0–C2 tabular | Kaggle CPU | `!python .../e010_coo_ladder.py --models C0,C1,C2,C4tab` | None |
| 4. Embeddings once | Kaggle GPU T4 | `!python .../e010_extract_embeddings.py --encoder hoptimus` then `--encoder phikon` | T4, mixed precision |
| 5. C3/C3b ABMIL | Kaggle GPU T4 | `!python .../e010_abmil.py --encoder hoptimus` (primary E1), then `--encoder phikon` | T4, ~2–3 wks budget w/ resume |
| 6. Gate dry-run | local | `python src/analysis/derive_tcga_coo.py --offline` | — |
| 7. E-011 single-use | Kaggle GPU | locked model only, once | T4 |

Early-stop (§4.5): if C1 AND C3 upper 95% < 0.65 on A_COO, E-011 optional — report internal null.

## Datasets to attach

- C0–C2 notebook: `dlbcl-phase4b-inputs` + `dlbcl-morph-tables` (clinical). No patches.
- Embedding notebook: `dlbcl-morph-patches` + `dlbcl-phase4b-inputs`.
- ABMIL notebook: `dlbcl-phase4b-inputs` (v2+, includes embeddings + splits).

All scripts auto-discover under `/kaggle/input` (breadth-first walk), write to `/kaggle/working/phase_04_coo_*`, abort on gate failure, never write partial outputs. Chain-of-custody: every `run_summary*.json` records protocol SHA, split SHA, package versions.

## What each script does

- `build_coo_split_ids.py` — fresh 5×10 stratified-on-HANS splits, seed 20260903, n=163. Reads `patient_id`+`HANS` only. Refuses unless §13 hash matches.
- `e010_coo_ladder.py` — C0/C1/C2 + C4-2score (A003), penalised logistic, fold-internal impute→prune→scale→fit, 1000 patient bootstraps, triage sens@90spec / spec@90sens (in-fold thresholds), calibration slope/intercept + rejection [0.7,1.3], Holm for secondary, QC-stratified descriptive (A005).
- `e010_extract_embeddings.py` — frozen encoder, once, outside CV (not leakage). H-optimus-0 primary (gated click-through, A004) + Phikon-v2 secondary (non-commercial). 224–256 px, tissue ≥0.50, ≤200 patches/pt, seed-fixed sampling. Saves one `.pt`/`.npy` per patient + manifest.
- `e010_abmil.py` — ABMIL bounded grid (attn {128,256} × dropout {0.25,0.5} × lr {1e-4,1e-3}, wd 1e-4, 50 epochs, patience 10 on inner AUROC). Inner 5-fold. Temperature scaling inner-only + conformal abstention 10/20% descriptive (A005). Checkpoints every outer fold; resume with `--resume`.
