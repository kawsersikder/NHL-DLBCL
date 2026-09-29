# Phase 2 — Cell Segmentation & QC

## Current route: `phase_02_unet_recovery_qc.py`

The released HoLy-Net checkpoint is no longer the active Phase 2 route. Its
source-data smoke test loaded all 798 tensors with 100% key coverage, but gave
pixel Dice 0.2819. Direct forward and TIAToolbox `infer_batch` were identical;
RGB/BGR and threshold diagnostics could not raise Dice above about 0.305.

The recovery probe uses the successful E-001 LyNSeC H&E SmallUNet (recorded
validation Dice 0.8779), derives instances with watershed, and performs:

- semantic and instance QC on the exact validation tiles recorded in E-001's
  manifest; and
- patient-diverse overlay QC on DLBCL-Morph H&E patches.

### Recorded E-004 result (2026-08-28)

The committed 50-tile/20-patch pilot passed the automatic gate: mean Dice
0.8879, mean detection F1 0.8923, and median absolute count error 9.69%. All 20
DLBCL overlays were generated. Preliminary computational review marked 19/20
usable; this is not a pathologist review. The canonical result is in
`output_final/`, and the detailed interpretation is in
`reports/phase_02_segmentation_qc.md`.

Do not rerun or retune this completed gate. The next experiment is the
outcome-blind Phase 3A feature-extraction stress pilot.

Full rationale and decision gates are in
`reports/phase_02_recovery_plan.md`.

### Kaggle setup

1. Attach `dlbcl-kaggle-code` and
   `kawsersikder/dlbcl-morph-patches`.
   Kaggle may display the latter directly as `HE/`, `BCL2/`, and other stain
   folders rather than as `dlbcl_morph_patches.zip`; the recovery script
   supports both layouts.
   The attached inputs must also expose E-001's `best_model.pt` and
   `tile_manifest.csv`. If the current code dataset predates those outputs,
   upload `phase_01_lynsec_he_nuclei_baseline/output_final/` as a small private
   Kaggle dataset and attach it; the recovery script discovers the files
   automatically.
2. Accelerator: GPU T4. Internet is not required.
3. Paste the complete `phase_02_unet_recovery_qc.py` into one cell.
4. Keep `SMOKE_TEST = True` for the first run. It scores one recorded
   validation tile and creates two DLBCL-Morph overlays.
5. If paths, checkpoint loading, metrics, and overlays are structurally
   correct, set `SMOKE_TEST = False` and use Save & Run All (Commit). The pilot
   scores 50 validation tiles and creates 20 DLBCL-Morph overlays.

Required outputs:

```text
/kaggle/working/phase_02_unet_recovery_qc/
  run_summary.json
  lynsec_metrics.csv
  lynsec_overlays/
  dlbcl_morph_overlays/
  dlbcl_morph_review_sheet.csv
```

The automatic pilot gate requires mean semantic Dice >=0.80, mean centroid
detection F1 >=0.70, and median absolute count error <=20%. The visual gate
requires at least 80% of 20 DLBCL-Morph patches to be judged usable, with no
systematic severe failure. A pathology review is still required before full
feature extraction.

This route produces type-free all-nuclei instances. Do not claim validated
tumour/non-tumour phenotypes or compute a tumour/non-tumour mixing score from
these outputs.

## Historical diagnostic: `phase_02_holynet_qc_probe.py`

This script is retained for reproducibility of the failed checkpoint probe. Do
not launch its 16-tile pilot unless the original authors' environment or
inference code becomes available.

### Historical Kaggle setup

**Kaggle setup**

1. Notebook Settings → **Internet: ON**
2. Input Datasets → attach **`dlbcl-kaggle-code`** (LyNSeC `.npy` tiles)
3. Accelerator → **GPU T4** (CPU works, just slower)
4. Paste the whole script into **one cell**.

### Historical two-step execution

1. Set `SMOKE_TEST = True` and click **Run All** interactively. This runs the
   complete loading and inference path on one H&E tile, so it catches setup,
   checkpoint, and tensor-shape errors without generating the 16-tile pilot.
2. Inspect the console output. The 2026-08-28 smoke result failed the scientific
   QC gate, so the 16-tile run is currently frozen.

The script selects LyNSeC H&E partitions (`*_l2.npy` and `*_l3.npy`) only. It
should find 320 H&E tiles; 699 indicates that IHC tiles have been included. It
recovers the model state dictionary stored under the checkpoint's `desc`
mapping, uses TIAToolbox's documented `models.architecture.hovernet` import,
and scores its valid central output region. The pilot does not yet stitch a
full 512×512 tile, so its Dice is a preflight/QC indicator, not the formal
50-tile result. The released H&E checkpoint matches the 3×3 decoder kernels
of HoVerNet `mode="fast"`; the probe therefore uses a 256px input crop and
the three-class type head (background, non-tumour, tumour).

Expected runtime: ~10–15 min (dominated by the 453 MB Zenodo download).

**What it does:** loads `he.tar` from Zenodo (MD5-verified), loads it as a
`torch.save()` bundle — **it is not a tar archive**, that was the E-002 Step-5
failure — recovers the nested model state dictionary, strips the `module.`
prefix while preserving HoVer-Net's slash-containing names, builds TIAToolbox
`HoVerNet`, reports
non-strict key coverage with rename diagnostics, then runs nucleus-segmentation
QC on 16 tiles (overlay panels in `qc_overlays/`, per-tile Dice).

**If the original runtime becomes available**

- Paste the console output back to the agent session (key coverage + mean Dice).
- If coverage is <100%, also download `qc_probe_run.json` and share it —
  the missing/unexpected key samples drive the rename mapping for the next run.
- Optional: use *Save Data* on the committed version to persist `he.tar`
  as a Kaggle dataset (per 2026-08-23 decision log) so later runs skip the
  Zenodo download.

**Historical caveat:** this diagnostic selected the first tiles rather than the
manifest-recorded E-001 validation split. Its failed one-tile result is logged
as a checkpoint-reproducibility finding, not a formal model comparison.
