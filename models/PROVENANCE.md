# Model weights — provenance

| Field | Value |
|---|---|
| File | `models/he.tar` |
| Downloaded | 2026-08-23 |
| Source | https://zenodo.org/records/8065174/files/he.tar?download=1 |
| Size | 452,539,789 bytes |
| MD5 | `ab487b656117e7eb23f005691ace5276` — verified ✅ (matches Zenodo API record) |
| Licence | CC BY 4.0 |
| What it is | HoLy-Net pretrained H&E model (HoVer-Net-derived, DLBCL-specific) — Naji et al. 2024, *Computers in Biology and Medicine*, doi:10.1016/j.compbiomed.2024.107978 |
| Original intended use | Phase 2 QC pilot on LyNSeC + DLBCL-Morph, then Model-2 nucleus segmentation |
| Current status | **Frozen after failed functional QC (2026-08-28).** The current TIAToolbox-compatible architecture loads 798/798 tensors with zero missing/unexpected keys, but source-tile Dice is 0.2819 (best RGB/BGR/threshold diagnostic about 0.305) with unusable overlays. Retain for provenance; do not use for feature extraction unless the authors' original runtime/inference code is reproduced. |
| Recovery route | `kaggle/phase_02_segmentation_qc/phase_02_unet_recovery_qc.py`; rationale in `reports/phase_02_recovery_plan.md` |
