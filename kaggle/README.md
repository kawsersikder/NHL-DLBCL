# Kaggle execution workspace

This directory holds self-contained, Kaggle-ready code for each project phase. Attach the directory as a private Kaggle Dataset, or upload a single phase folder, and run the phase from `/kaggle/input/...`.

| Phase | Directory | Purpose | Status |
|---|---|---|---|
| 1a | `phase_01_lynsec_he_nuclei_baseline/` | H&E nuclei segmentation baseline on LyNSeC | Complete (2026-08-22). Best validation Dice 0.878 (E-001). Engineering baseline only. |
| 1b | `phase_01b_dlbcl_morph_data_audit/` | Clinical-table audit and reproduction of the published baseline | Complete. Patient-level image inventory done. |
| 2 | `phase_02_segmentation_qc/` | Instance-level segmentation QC on LyNSeC and DLBCL-Morph overlays | Complete. Automatic gate passed. Visual gate 19/20. |
| 3a | `phase_03_morphology_survival/` | Outcome-blind, patient-level morphology feature extraction | Complete (2026-08-28). E-007 cache frozen: 170 patients, 30,007 patches, 65 features. |
| 3b | `phase_03b_survival_analysis/` | Entropy comparator (E-008), frozen splits and survival model ladder (E-009) | Complete. Results are reported in the manuscript. |
| 4B | `phase_04_coo/` | Cell-of-origin prediction from H&E with frozen pathology encoders and ABMIL | Scripts ready. Protocol drafted and not yet signed, so no run has started. |
| Helpers | `upload_helpers/` | Scripts that package patches and inputs as Kaggle Datasets | Utility |

## Rules

- Kaggle input directories are read-only. Write extracted data, checkpoints and outputs to `/kaggle/working/`.
- Use a separate private Kaggle Dataset for each raw-data release. Do not redistribute data under a restrictive licence.
- Keep the source DOI, licence, readme and checksums with every raw dataset.
- Phase 1a uses a tile-level split because the LyNSeC release has no patient IDs. Its validation score is an engineering check, not a publication result.
- Prognostic analysis uses patient-level manifests and grouped splits only.

Read the phase README before launching a run.
