# Kaggle execution workspace

This directory holds self-contained, Kaggle-ready code for each project phase. Attach this directory as a private Kaggle Dataset (or upload the individual phase folder) and run a phase from `/kaggle/input/...`.

| Project phase | Kaggle directory | Purpose | Status |
|---|---|---|---|
| Phase 1a | `phase_01_lynsec_he_nuclei_baseline/` | Overnight H&E nuclei segmentation engineering baseline on LyNSeC | ✅ Completed 2026-08-22 — best val Dice 0.8779 (E-001; engineering baseline only, outputs in `output_final/`) |
| Phase 1b | `phase_01b_dlbcl_morph_data_audit/` | Clinical-table audit and Stanford baseline reproduction | ✅ Clinical audit/baseline complete; patient-level image inventory complete, row-level slide/stain manifest pending |
| Phase 2 | `phase_02_segmentation_qc/` | E-001 U-Net recovery instance QC on LyNSeC + DLBCL-Morph overlays | ✅ Automatic gate passed; preliminary visual gate 19/20; pathology review pending; outputs in `output_final/` |
| Phase 3a | `phase_03_morphology_survival/` | Outcome-blind patient-level morphology feature extraction | ✅ Completed 2026-08-28 — E-007 cache frozen: 170 patients, 30,007 patches, 65 features |
| Phase 3b | `phase_03b_survival_analysis/` | Entropy comparator (E-008), frozen splits (S2), survival model ladder (E-009) | 🟡 Active — protocol frozen pending signature; see the phase runbook |
| Phase 4 | `phase_04_mil_late_fusion/` | Frozen pathology encoder, MIL and late fusion | Planned |
| Phase 5 | `phase_05_robustness_interpretation/` | Stain robustness, domain generalisation and interpretation | Planned |
| Phase 6 | `phase_06_manuscript_release/` | Reproducibility artefacts and manuscript outputs | Planned |

## Important rules

- Kaggle input directories are read-only. Write extracted data, checkpoints and outputs to `/kaggle/working/`.
- Use a separate private Kaggle Dataset for each raw-data release; do not redistribute data with a restrictive licence.
- Preserve the source DOI, licence/readme and checksums with every raw dataset.
- Phase 1a uses a tile-level split only because the LyNSeC release does not provide patient IDs. Its validation score is an engineering check, **not** a publication result.
- The prognosis project starts only once DLBCL-Morph has a patient-level manifest and grouped splits.

See the phase README before launching a run.
