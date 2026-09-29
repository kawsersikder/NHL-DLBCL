# Phase 1a — LyNSeC H&E nuclei segmentation baseline

## Goal

Run an overnight, reproducible **binary nucleus-vs-background segmentation** baseline on the H&E partitions of LyNSeC. This checks that the DLBCL image pipeline, GPU setup, checkpointing and output logging work before we touch the survival cohort.

This phase is deliberately modest. It is not the final HoLy-Net replication, it does not predict survival, and its tile-level validation split must not be described as patient-level or external validation.

## Why LyNSeC for the overnight run

- DLBCL-specific H&E images with instance masks: 65,479 nuclei in LyNSeC 2 plus 8,452 expert-refined H&E nuclei in LyNSeC 3.
- The archive is about 970 MB; supplied H&E HoLy-Net weights are a further 452 MB. Both fit comfortably in Kaggle.
- DLBCL-Morph is for the later patient-level survival study. Its complete TCIA collection is much larger and must first be audited for clinical variables and patient-level splits.

Data source: [LyNSeC, Zenodo record 8065174](https://zenodo.org/records/8065174)  
Expected archive MD5: `f9b1bae015ccf2af29617930c051b304`

## Kaggle setup

1. Download `lynsec.zip` from the Zenodo record and create a **private** Kaggle Dataset called, for example, `lynsec-zenodo-8065174`. Upload the archive without changing its name. Retain the source DOI and licence/readme in the dataset description.
2. Create a GPU Kaggle notebook and attach the private LyNSeC data dataset and this repository/folder as a second private Kaggle Dataset, or upload these Python files to the notebook.
3. Turn on a GPU accelerator. A T4 is sufficient. Internet access is not needed after the inputs are attached.
4. Run the following cells, adapting the two input-folder names if Kaggle assigns different slugs.

```bash
# Inputs are read-only; extract to the working volume.
python /kaggle/input/dlbcl-kaggle-code/phase_01_lynsec_he_nuclei_baseline/prepare_lynsec.py \
  --archive /kaggle/input/lynsec-zenodo-8065174/lynsec.zip \
  --output-dir /kaggle/working/lynsec

# The default 250 epochs with early stopping is suitable for an overnight run.
python /kaggle/input/dlbcl-kaggle-code/phase_01_lynsec_he_nuclei_baseline/train_unet.py \
  --data-dir /kaggle/working/lynsec \
  --output-dir /kaggle/working/phase_01_lynsec_unet \
  --epochs 250 --batch-size 4 --num-workers 2 --seed 20260821
```

## Expected outputs

```text
/kaggle/working/phase_01_lynsec_unet/
  best_model.pt             # best validation Dice checkpoint
  history.csv               # epoch-by-epoch losses and Dice/IoU
  run_config.json           # seed, device, arguments and source-data information
  tile_manifest.csv         # every discovered .npy tile used in this run
  prediction_preview.png    # validation image/mask/prediction QC panel
  run_summary.json          # best epoch and the engineering-only validation result
```

Copy these files to a Kaggle Dataset or cloud storage before the notebook session ends. Do **not** treat `best_model.pt` as a final project model; it is only a Phase 1a baseline.

## Results — completed run (E-001, 2026-08-22)

Outputs are saved in `output_final/` (byte-identical copy in `phase_01_lynsec_unet/`) and registered as O-013.

| Item | Value |
|---|---|
| Best validation Dice | **0.8779** (epoch 91 of 126; early stop, patience 35) |
| Best validation IoU | 0.7887 |
| Tiles | 320 total — 256 train / 64 validation (deterministic tile-level split, seed 20260821) |
| Hardware / stack | Tesla T4, PyTorch 2.10.0+cu128, mixed precision |
| Input format | Pre-extracted `.npy` tiles uploaded as a private Kaggle dataset |

QC review (2026-08-23): training and validation losses track closely with no overfitting; validation Dice plateaus near 0.87–0.88 after ~20 epochs. The prediction preview shows predicted masks closely matching ground truth, with minor failure modes: occasional merged nuclei in dense regions and rare misses of faint nuclei. No empty or degenerate predictions observed.

Deviations from the plan above: the run used pre-extracted tiles rather than `lynsec.zip`, so `prepare_lynsec.py` and its MD5 verification were not exercised; two runtime patches (crash-safe `run_summary.json`, `weights_only=False` for PyTorch ≥2.6) were applied in the notebook and subsequently baked into `train_unet.py`.

The tile-level validation split remains an engineering check only — LyNSeC provides no patient identifiers, so this is not patient-level or external validation.

## Scientific limitations of this run

- LyNSeC does not ship a patient-ID mapping or a predefined grouped split. The script uses a deterministic random tile split solely to exercise the training pipeline.
- LyNSeC 3 is an expert-refined H&E subset, so it must not automatically be treated as a patient-independent test cohort.
- The target here is binary nuclei segmentation (`instance_id > 0`). Tumour/non-tumour classification and survival analysis come later under patient-level splits.

## Suggested overnight settings

| GPU | Batch size | Epochs | Expected behaviour |
|---|---:|---:|---|
| T4 16 GB | 4 | 250, patience 35 | Safe default; mixed precision on |
| P100 16 GB | 4–6 | 250, patience 35 | Increase to 6 only after a smoke test |
| L4/A100 | 8 | 250, patience 35 | Faster; do not use extra compute to add an unvalidated larger model |

First run a 2-epoch smoke test if you have not used the dataset/input paths before:

```bash
python train_unet.py --data-dir /kaggle/working/lynsec \
  --output-dir /kaggle/working/smoke_test --epochs 2 --batch-size 2
```

