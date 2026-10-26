# NHL-DLBCL: Leakage-Safe Prognostic Modelling in Diffuse Large B-Cell Lymphoma

Code, protocols and results for two studies on evaluation rigour in diffuse large B-cell lymphoma (DLBCL) research.

- **Study 1** asks whether nuclear morphology from H&E slides adds prognostic value beyond clinical factors.
- **Study 2** audits hidden sample overlap between public DLBCL gene-expression cohorts and measures how often the literature treats overlapping cohorts as independent.

**Status:** The Study 1 manuscript is complete and will be shared once the preprint is posted. Study 2 is in progress.

## Key findings

### Study 1: H&E morphology and overall survival

- **Cohort.** DLBCL-Morph is a public single-centre US cohort. 170 patients have H&E tissue-microarray images, with 58 overall-survival events.
- **Pipeline.** U-Net and watershed segmentation of 30,007 patches gave about 1.96 million nuclei and 65 patient-level features.
- **Protocol.** The analysis plan was hash-locked before any outcome data was read.
- **Primary result.** Image features did not improve on the clinical model. The paired difference in out-of-fold C-index was ΔC = −0.023 (95% CI −0.050 to +0.001).
- **Clinical baseline.** The clinical model reached a C-index of 0.706. Every image-only model scored between 0.456 and 0.589.
- **Reproducibility.** A published segmentation checkpoint scored Dice 0.282 on its own source data. A published geometric baseline fell from C = 0.635 to 0.521 under fold-safe refitting.
- **Power.** With 58 events, the study could detect a large improvement only. It cannot rule out a small one.

### Study 2: Hidden overlap between public expression cohorts

- **GSE53786 is 96% GSE10846.** 114 of its 119 samples are the same GEO sample records.
- **GSE11318 is 80% GSE10846.** 163 of its 203 expression samples are the same records.
- **The overlap is undocumented.** None of the affected GEO series summaries mentions it.
- **The literature rarely checks.** 66 open-access papers used an overlapping pair as analysis cohorts. 39 trained on one member and validated on the other. Only 1 removed the shared samples.
- **Outcome-blind design.** No outcome field was used to detect overlap.

## Repository structure

```
NHL-DLBCL/
├── configs/              Protocol and feature-extraction configs (YAML)
├── data/
│   ├── manifests/        Patient manifest and frozen patient-level splits
│   └── raw/              PROVENANCE.md files only: download steps and checksums
├── docs/                 Research roadmap and project updates
├── kaggle/               Kaggle-ready code for each pipeline phase
├── models/               PROVENANCE.md for third-party model weights
├── reports/              Phase reports, protocols and result tables
├── route1/               Study 2: cohort-overlap and gene-signature audit
│   ├── configs/
│   ├── data/             GEO sample metadata (raw downloads are excluded)
│   ├── kaggle/           Synthetic smoke test
│   ├── manifests/        Identity keys, overlap pairs and paper classifications
│   ├── reports/          Findings, plans and decision log
│   └── src/              Scripts, numbered in run order
├── src/
│   ├── analysis/         Survival models, statistics, tables and figures
│   ├── data/             Manifest builders
│   └── validation/       Output and QC audits
└── PROJECT_STATUS.md     Project log, output register and decision record
```

## Reproducing the analysis

1. **Install dependencies.** Use Python 3.12.

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Download the data.** Follow `data/raw/dlbcl_morph/PROVENANCE.md` for DLBCL-Morph and `models/PROVENANCE.md` for the segmentation weights. Each file lists its source, licence and checksums.
3. **Run the pipeline.** Heavy compute runs on Kaggle with a T4 GPU. `kaggle/README.md` lists the phases in order, and each phase folder has its own runbook.
4. **Run the survival analysis.** The signed protocol is `reports/phase_03b_statistical_analysis_protocol.md`. The frozen splits are in `data/manifests/split_ids.csv`. The run order is in `kaggle/phase_03b_survival_analysis/README.md`.
5. **Run the cohort audit.** The scripts in `route1/src/` are numbered in run order. Raw GEO and PMC downloads are not included. Their SHA-256 hashes are listed in `route1/manifests/source_registry.csv`.

## Pre-registration

The Study 1 protocol was written, signed and SHA-256 hash-locked on 1 September 2026, before any outcome data was accessed. The split generator aborts if the protocol changes after signing. The protocol was not deposited in a public registry. Here, "pre-registered" means frozen before outcome access.

## Use of AI tools

AI tools assisted with code, documentation, segmentation QC review and literature screening. Every AI-assisted record is labelled in the file where it appears. The AI segmentation review is a computational check and not a pathologist review. The paper classifications in Study 2 come from a single AI-assisted reviewer, and each one includes a written rationale. The author directed the study and is responsible for all analysis decisions.

## Data and licence

- **Code:** MIT licence. See `LICENSE`.
- **Source datasets are not redistributed.** DLBCL-Morph is released under CC BY-NC 4.0. Download it from the original source using the provenance files.
- **Derived tables** from DLBCL-Morph follow the source licence, CC BY-NC 4.0.
- **No dates finer than year** are included for any patient. Row-level extracts with calendar dates are excluded and can be regenerated from the hashed source files.

## Citation

If you use this code or these results, please cite the repository. Citation metadata is in `CITATION.cff`. A manuscript reference will be added once the preprint is posted.

## Author

**Kawser Sikder**
Department of Electrical and Computer Engineering, North South University, Dhaka, Bangladesh
[GitHub](https://github.com/kawsersikder) · [LinkedIn](https://www.linkedin.com/in/kawsersikder)
