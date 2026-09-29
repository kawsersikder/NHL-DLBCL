# DLBCL / non-Hodgkin lymphoma AI research roadmap

Prepared: 21 August 2026  
Literature/novelty refresh: 28 August 2026  
Scope: recent peer-reviewed work (2024–August 2026), a reproducible four-month project plan, and a coding architecture for a computer-science researcher.

## Bottom line

The most practical publishable direction is **computational pathology for DLBCL prognosis**:

> **Can outcome-blind H&E-derived nuclear pleomorphism, cellular-packing, and patch-heterogeneity features improve survival-risk prediction beyond clinical variables in DLBCL, while remaining interpretable and reproducible?**

Start with the public **DLBCL-Morph** cohort (209 patients with H&E/IHC images, clinical/cytogenetic variables, follow-up and survival) and **LyNSeC** (fully annotated DLBCL nuclei). This is genuinely DLBCL-specific, avoids waiting for hospital ethics approval, has a feasible GPU budget, and supports a clear novelty claim. Do **not** promise a clinically deployable decision tool from one public retrospective cohort; describe it as a reproducible, hypothesis-generating prognostic study.

PET/CT is scientifically important, but the strongest recent PET papers use non-public trial data. It is a better phase-2 project after obtaining a clinical collaborator and data-access approval.

## How the shortlist was selected

I searched recent DLBCL/NHL papers through 21 August 2026 and retained peer-reviewed original studies that are recent, methodologically informative, and published in well-established journals that are Q1 in a relevant 2024 JCR/SJR category. Quartiles are category- and year-specific; verify the target journal's current rank immediately before submission.

For prognosis studies, **AUC, C-index, calibration and time-dependent Brier score** are more meaningful than ordinary accuracy because outcomes are censored and follow-up differs between patients. A paper that reports only a high accuracy for survival deserves extra scrutiny.

## Four impactful papers to read first

| Priority | Paper and venue | Dataset | Methodology | Reported primary performance | Raw data / code |
|---|---|---|---|---|---|
| 1 | Naji *et al.*, 2024, *Computers in Biology and Medicine* — **HoLy-Net** | LyNSeC: 73,931 H&E and 87,316 IHC annotated nuclei | Two DLBCL-specific HoVer-Net-derived models for nucleus instance segmentation and classification | F1: **0.899 H&E**, **0.913 IHC** | **Public:** data and pretrained H&E/IHC weights on Zenodo |
| 2 | Ferrández *et al.*, 2024, *Journal of Nuclear Medicine* | 1,132 DLBCL patients: 296 training; 836 from 5 external clinical-trial datasets | CNN using baseline PET/CT maximum-intensity projections (MIPs) to predict 2-year time-to-progression; compared with IPI and radiomic models | External AUC: DL **0.66**, IPI **0.60**, clinical-PET **0.69**, PET-radiomics **0.71** | Paper is accessible; raw trial imaging is **not an open benchmark download** |
| 3 | Dondolin *et al.*, 2025, *Leukemia* | 120 newly diagnosed R-CHOP-treated DLBCL patients | Baseline PET/CT dissemination biomarkers + CAPP-seq circulating tumour DNA (ctDNA) + LymphGen molecular clustering; multivariable Cox score | 3-factor C-index: **0.745 PFS**, **0.746 OS**; very-high-risk group (n=22) 40-month PFS **12.1%** | Data on reasonable request; no public imaging/ctDNA release |
| 4 | Alem *et al.*, 2026, *npj Precision Oncology* | 2,769 patients from the Lymphoma and Related Diseases Registry | Cox/competing-risks models, nomogram and random survival forest for OS/PFS; compared with R-IPI and NCCN-IPI | Validation 1-year OS AUC: Cox **0.770**, R-IPI **0.722**, NCCN-IPI **0.746** | Registry data require a project proposal, ethics evidence and possible fee |

### 1. HoLy-Net — the best implementation starting point

**Citation.** Naji H, Sancere L, Simon A, *et al.* HoLy-Net: Segmentation of histological images of diffuse large B-cell lymphoma. *Computers in Biology and Medicine*. 2024;170:107978. doi: [10.1016/j.compbiomed.2024.107978](https://doi.org/10.1016/j.compbiomed.2024.107978).

**Why it matters.** This is a DLBCL-specific answer to a common pathology problem: general nuclei models are usually trained on solid tumours and can fail in densely packed lymphoid tissue. The authors adapted HoVer-Net, trained separate H&E and IHC models, and then used cell-level outputs to quantify patient-level tissue characteristics, including immune infiltration.

**Dataset used.** The accompanying **LyNSeC** dataset has 699 512×512 tiles at 40× magnification (1.9 GB download):

- H&E: 280 instance-annotated tiles (65,479 nuclei) and a 40-tile expert-labelled subset (8,452 nuclei: tumour/non-tumour); H&E covers 70 patients.
- IHC: 379 tiles, 87,316 nuclei from four cases, across CD3, Ki67 and ERG; labels are marker-positive/marker-negative.

**Results.** F1 was 0.899 on H&E and 0.913 on IHC. These are segmentation/classification F1 scores, not patient-diagnosis accuracy.

**Availability.** Fully usable now: [LyNSeC Zenodo record](https://zenodo.org/records/8065174) provides image/mask arrays and pretrained `he.tar` and `ihc.tar` models. The record explicitly defines label values (H&E: 1 non-tumour, 2 tumour; IHC: 1 negative, 2 positive). Use the original record rather than assuming a third-party conversion preserves labels.

**What to learn, and what not to copy.** Learn the DLBCL-specific segmentation setup and cell-level interpretation. Do not present a small-tile F1 as evidence of patient-level prognostic utility. Your work should have patient-grouped splits and a downstream clinical endpoint.

### 2. External PET/CT validation — a model of strong validation

**Citation.** Ferrández MC, Golla SSV, Eertink JJE, *et al.* Validation of an Artificial Intelligence-Based Prediction Model Using 5 External PET/CT Datasets of Diffuse Large B-Cell Lymphoma. *Journal of Nuclear Medicine*. 2024;65(11):1802–1807. doi: [10.2967/jnumed.124.268191](https://doi.org/10.2967/jnumed.124.268191).

**Dataset used.** 296 patients developed the model; 836 independent patients in five external clinical-trial cohorts validated it (1,132 total). The endpoint was 2-year time to progression.

**Method.** The CNN consumes baseline PET/CT MIPs, so it avoids manual tumour delineation. It was benchmarked against the International Prognostic Index (IPI), a PET-radiomics model (metabolic tumour volume, lesion spread/Dmax and SUVpeak), and a clinical-PET model that adds age and performance status.

**Results.** Across all external data, AUC was 0.66 for DL versus 0.60 for IPI. The clinical-PET model reached 0.69 and PET-radiomics 0.71. The lesson is valuable: a convenient segmentation-free CNN can beat IPI but still lose to carefully measured imaging biomarkers.

**Availability.** The article PDF is openly readable, but the five trial datasets are not provided as a public, downloadable benchmark. Treat PET work as a collaboration/data-access project, not as an immediate Kaggle project.

### 3. PET/CT plus liquid biopsy — the key multimodal biological direction

**Citation.** Dondolin R, Garrou F, Almasri M, *et al.* Integration of [18F]FDG-PET radiomics with liquid biopsy improves outcome prediction in newly diagnosed diffuse large B-cell lymphoma. *Leukemia*. 2025;39:2207–2214. doi: [10.1038/s41375-025-02688-2](https://doi.org/10.1038/s41375-025-02688-2).

**Dataset used.** A real-world cohort of 120 newly diagnosed, R-CHOP-treated DLBCL patients.

**Method.** Baseline PET/CT features used an SUV threshold of 4.0 and included SUVmax, total metabolic tumour volume (tMTV), total lesion glycolysis (tTLG) and maximum lesion distance (Dmax). CAPP-seq produced baseline ctDNA levels and LymphGen molecular clusters. Cut-points were selected with maximally selected rank statistics; Cox models formed a PET + ctDNA two-factor model and then a PET + ctDNA + molecular-cluster score.

**Results.** The final 3-factor score had C-indices of 0.745 for PFS and 0.746 for OS. It identified 22 very-high-risk patients with a 40-month PFS of 12.1%. It outperformed IPI and cell-of-origin in that cohort.

**Availability.** The paper's data-availability statement says files are available on reasonable request. This is a high-quality translational reference, but it is not a fully reproducible public-data project. Also note that it is a biomarker/survival study rather than an end-to-end deep-learning paper.

### 4. Large-registry survival modelling — the right baseline to beat

**Citation.** Alem AZ, Mohanty I, Pati N, *et al.* Prognostic survival models for diffuse large B-cell lymphoma using statistical and machine learning approaches. *npj Precision Oncology*. 2026. doi: [10.1038/s41698-026-01604-w](https://doi.org/10.1038/s41698-026-01604-w).

**Dataset used.** 2,769 registry patients. Predictors included age, stage, performance status, chemo-immunotherapy, creatinine, LDH and anaemia; extranodal involvement was added for OS and BCL6 expression for PFS.

**Method.** Conventional Cox survival modelling, competing-risk analysis, nomogram and random survival forest were evaluated for OS and PFS. This is important because it tests whether ML really beats a transparent regression baseline rather than assuming it does.

**Results.** In validation, 1-year OS AUC was 0.770 for Cox, versus 0.722 for R-IPI and 0.746 for NCCN-IPI. The authors found similar discrimination for ML and regression, while Cox/nomogram and RSF provided stronger 5-year risk separation than conventional indices. External validation is still needed.

**Availability.** The registry's de-identified data require a proposal, data-access form and relevant ethics certification; this is not an open download. The useful lesson is that a simple, well-validated baseline may be as good as a sophisticated ML model.

## A cautionary current paper

Wang *et al.* (2026, *Frontiers in Oncology*) reported an AUC of 0.974 and accuracy of 0.921 in a 63-patient held-out subset of 209 single-centre PET/CT cases after feature extraction, selection and fusion with clinical variables ([paper](https://doi.org/10.3389/fonc.2026.1849942)). It is useful as an implementation example, but its raw data are restricted and its single-centre 7:3 split is much less convincing than multi-cohort external validation. Do not build a project around chasing this headline AUC.

### Pathology novelty update — 28 August 2026

Two 2026 H&E studies narrow the novelty space. Carreras *et al.* used a
DarkNet-19 patch classifier to predict death within two years in 114 DLBCL
patients ([Biomedicines paper](https://doi.org/10.3390/biomedicines14051134)).
A subsequent study in the same-sized series found that patient-mean grayscale
histological entropy was associated with OS, using a same-cohort optimized
cut-point and univariate Cox analysis
([Cancers paper](https://doi.org/10.3390/cancers18142279)). These studies make
“H&E predicts DLBCL outcome” and “global entropy is prognostic” insufficient as
novel claims. They do not, however, provide a leakage-safe repeated nested
censored-survival comparison of cell-resolved pleomorphism/packing features
against IPI/R-IPI, calibration, and the released DLBCL-Morph baseline.

Spatial imaging and transcriptomic studies now show recurrent DLBCL cellular
neighborhoods and survival-associated ecosystems
([99-patient multiplex study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12485370/);
[2026 spatial-transcriptomic study](https://pmc.ncbi.nlm.nih.gov/articles/PMC13102037/)).
They motivate analysis of tissue organization, but their molecular/cell-type
resolution must not be imputed to an all-nucleus H&E mask.

ImmunoBench already exposes DLBCL-Morph as a 170-patient, 1,009-slide
H&E/IHC OS task across multiple pathology foundation models
([official repository](https://github.com/yanfang-research/ImmunoBench)). A
generic frozen encoder or multistain MIL experiment is therefore a comparator,
not the primary novelty. See
`reports/dlbcl_novelty_landscape_2026-08-28.md` for the current gap analysis.

## Public data that make a four-month project feasible

| Dataset | What it contains | Best use | Access / constraints |
|---|---|---|---|
| [LyNSeC](https://zenodo.org/records/8065174) | 699 DLBCL H&E/IHC annotated tiles; instance masks and selected cell labels; pretrained HoLy-Net weights | Nucleus segmentation/classification; stain-robustness and uncertainty experiments | Open download, about 1.9 GB; verify licence/terms on the record |
| [DLBCL-Morph](https://www.cancerimagingarchive.net/collection/dlbcl-morphology/) | 209 Stanford DLBCL patients; 42 TMA scans; 204 H&E WSIs from 149 cases; H&E + CD10/BCL6/MUM1/BCL2/MYC, ROIs, clinical/cytogenetic and survival data | Patient-level prognosis and interpretable morphology | TCIA lists CC BY-NC 4.0; its complete collection is large. The authors supply [code/notebooks](https://github.com/stanfordmlgroup/DLBCL-Morph) and a data link. Cache ROI crops rather than all WSIs first. |
| [TCGA-DLBC](https://portal.imaging.datacommons.cancer.gov/collections/tcga_dlbc/) | 48 DLBCL subjects with public slide microscopy | Exploratory external morphology/stain stress test | More than 1 TB for the IDC image collection; too small for a standalone outcome study |
| [CGCI-HTMCP-DLBCL](https://portal.imaging.datacommons.cancer.gov/collections/cgci_htmcp_dlbcl/) | 43 HIV-positive DLBCL subjects and 496 H&E/IHC slides | Domain-shift / stain generalisation test only | More than 1 TB; HIV-associated disease is biologically distinct, so do not call it general-population validation |
| [GSE10846](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE10846) and [GSE31312](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE31312) | Public DLBCL gene-expression cohorts with treatment/subtype information; GSE10846 has 181 CHOP and 233 R-CHOP samples, GSE31312 has 498 FFPE cases | Low-compute multi-cohort transcriptomic prognosis/subtyping | Public, but platform/treatment differences must be handled before pooling |

**Licensing note.** Download from the source selected for the study and retain its licence/readme in the repository. The Figshare and TCIA mirrors of DLBCL-Morph have displayed different licences historically; the current TCIA listing is the safer governing source if you download from TCIA.

## Recommended project: H&E morphology plus clinical survival prediction

### Research question and claim

**Primary question:** In previously untreated DLBCL, does an H&E-derived spatial morphology representation add prognostic value over a pre-specified clinical model for overall survival?

**Primary claim to test, not assume:** A morphology + clinical model has a higher patient-level, bootstrapped C-index and better calibration than clinical-only and morphology-only baselines on held-out patients.

**Secondary questions:**

1. Which interpretable nuclear and spatial features drive the score?
2. Does performance remain stable under stain perturbations and across H&E sources (LyNSeC/DLBCL-Morph/optional TCGA)?
3. Does a weakly supervised slide representation add signal beyond engineered cell features?

### The novelty that could justify publication

"Use deep learning" is not novelty. A defensible novelty package is:

1. **DLBCL-specific, outcome-blind cell measurement:** use the LyNSeC-trained
   E-001/E-007 all-nucleus branch, with the released DLBCL-Morph tumour-nucleus
   geometry as an explicit comparator rather than treating either as perfect
   ground truth.
2. **Distribution and architecture beyond averages:** test nuclear-shape tails,
   patch-to-patch heterogeneity, and within-patch nearest-neighbour/Delaunay
   packing against both the released mean/SD baseline and a simple global
   entropy comparator.
3. **Clinically incremental censored survival:** ask whether the frozen image
   representation adds to a *pre-specified* IPI/R-IPI clinical model under
   repeated nested patient-level CV, calibration, Brier score, and paired
   bootstrap uncertainty.
4. **Robustness as a result:** report stain/scanner perturbation,
   segmentation-artifact sensitivity, feature-family ablations and negative
   results rather than hiding them.
5. **Open, reproducible artefacts:** release patient-level split IDs (where
   licence permits), preprocessing configuration, code, model cards, and a
   reproducible environment.

The current E-007 branch has no validated tumour/non-tumour phenotype. Do not
compute or claim tumour–immune mixing unless a separate classifier is trained,
group-validated, and reviewed on DLBCL-Morph.

This is stronger than an unvalidated attention-MIL model with a single accuracy number. A haematopathologist collaborator is essential for interpreting the top spatial features and for checking a small blinded sample of heatmaps/cell labels.

### Architecture

```text
DLBCL-Morph H&E ROI/WSI                         Clinical baseline variables
            |                                                |
  tissue QC + patient-level split                    imputation within training fold
            |                                                |
  256–512 px patches at fixed magnification                 |
            |                                                |
  ┌─────────┴──────────────────┐                    standardised covariates
  |                            |                            |
DLBCL-specific nuclei       frozen pathology encoder         |
segmenter/classifier         (foundation encoder or baseline) |
  |                            |                            |
morphology + spatial graph  patch embeddings                  |
  |                            |                            |
elastic-net Cox / RSF       attention MIL slide embedding     |
  └───────────────┬────────────┴───────────────┬──────────────┘
                  |   late fusion (regularised Cox first)    |
                  └────────► OS risk / survival curve ◄──────┘
                                  |
                C-index, time-AUC, Brier, calibration, CIs,
                IPI/clinical comparison, feature/heat-map review
```

### Build the model in four increasing levels

| Level | Model | Why it is necessary |
|---|---|---|
| Baseline 0 | Clinical-only penalised Cox model; R-IPI/NCCN-IPI if all fields are available | Establishes the clinical benchmark |
| Baseline 1 | Existing DLBCL-Morph geometric features → elastic-net Cox / random survival forest | Reproduces and improves on an openly available baseline before deep learning |
| Model 2 | LyNSeC-initialised segmentation → nuclear morphology, density and spatial graph features → elastic-net Cox | Interpretable, low-power and directly DLBCL-specific |
| Model 3 | Frozen pathology encoder → attention-MIL slide embedding → Cox survival head | Tests representation learning with limited trainable parameters |
| Final | Late fusion of clinical variables + selected morphology features + MIL score | The primary proposed model; retain it only if it improves the locked evaluation honestly |

Start with a **regularised Cox** fusion model, not cross-attention. With 209 patients, a large transformer fusion layer is much more likely to overfit than to reveal biology. Use deep cross-attention only as an explicitly labelled exploratory ablation if sample size/events justify it.

### Feature families for the interpretable branch

- Per-cell morphology: area, perimeter, eccentricity, solidity, circularity, major/minor axis, colour/stain intensity.
- Patient-level distributions: median, IQR, tails, entropy and mixture proportions; never feed every cell directly to a survival model.
- Density and topology: cells/mm², nearest-neighbour distances, Delaunay-edge statistics, Ripley's K/L at several pre-specified radii, tumour/non-tumour mixing score and clustering.
- IHC extension, only if labels/registration are validated: CD3 and Ki67 positive fractions and their distance to tumour nuclei. Do not claim precise cell phenotypes from H&E alone.

### Patient split and evaluation protocol (non-negotiable)

1. Create `patient_id` first. All cores, stains, tiles, serial sections and patches from one patient must stay in one split.
2. Reserve a patient-stratified **20% locked test set** once, if event count permits; use the remaining 80% for repeated/nested cross-validation and tuning. If events are too few, use repeated nested patient-level CV as the primary internal estimate and state that no independent test set was possible.
3. Fit stain normalisation, imputation, scaling, feature selection, PCA and hyperparameter selection **inside each training fold only**.
4. Pre-specify models, endpoint and horizon before looking at test results. Tune on C-index or integrated Brier score, not the locked test AUC.
5. Use 1,000 patient-level bootstrap resamples for 95% CIs and paired bootstrap comparison with clinical-only. Report the number of patients and number of events in every split.
6. Report discrimination (Harrell/Uno C-index; time-dependent AUC), calibration at 1/2/3 years, integrated Brier score, calibration plots, and Kaplan–Meier groups with a cut-point selected in training only.
7. For external morphology testing, report it as **domain generalisation**, not clinical outcome validation unless outcome/treatment compatibility is confirmed.

## Coding blueprint

### Suggested repository structure

```text
dlbcl-pathology/
  README.md                    # question, cohort, licence, commands, limitations
  environment.yml / requirements.txt
  configs/
    data.yaml  model.yaml  experiment.yaml
  data/                         # gitignored; manifests only in Git
    manifests/                  # patient IDs, slide IDs, checksums, split IDs
  src/
    data/qc.py                  # slide/ROI QC; no outcome access
    data/splits.py              # grouped, stratified patient splits
    data/patches.py             # reproducible patch coordinates
    nuclei/infer.py             # HoLy-Net inference and QC overlays
    features/morphology.py      # cell and spatial aggregates
    features/encoder.py         # frozen patch embedding extraction
    models/cox.py               # clinical/morphology/fusion baseline
    models/mil_survival.py      # gated attention MIL + survival loss
    evaluation/survival.py      # C-index, IPCW AUC, Brier, calibration, bootstrap
    evaluation/robustness.py    # stain perturbations / ablations
  notebooks/
    00_data_audit.ipynb         # read-only inspection only
    01_qc_overlays.ipynb
    02_results_figures.ipynb
  tests/
  reports/
    TRIPOD_AI_checklist.md
    PROBAST_AI_self_audit.md
```

### Recommended Python stack

```bash
pip install torch torchvision pytorch-lightning timm openslide-python \
  tiatoolbox albumentations pandas pyarrow scikit-learn scikit-survival \
  lifelines pycox matplotlib seaborn mlflow
```

- **OpenSlide / TIAToolbox:** read SVS/WSI and make deterministic ROI patches.
- **PyTorch + timm:** patch encoders and attention-MIL.
- **HoLy-Net weights / HoVer-Net implementation:** DLBCL-aware nucleus starting point.
- **scikit-survival / lifelines:** transparent survival baselines, calibration and C-index.
- **MONAI:** add only for PET/CT option; it is unnecessary for the pathology-first project.
- **MLflow or an equivalent local experiment log:** record seed, split file, Git commit, data-manifest hash, encoder version and all hyperparameters.

### First three executable milestones

```text
1. data audit
   - Download LyNSeC and the DLBCL-Morph clinical table/ROI subset.
   - Produce a patient–slide–stain manifest; count events and missing values.
   - Freeze patient-level split IDs before extracting model features.

2. reproduce a simple baseline
   - Run the supplied DLBCL-Morph survival notebook/code.
   - Reproduce its morphology Cox result approximately (reported C-index 0.635,
     95% CI 0.574–0.691) before changing anything.

3. cell-QC pilot
   - Run the LyNSeC H&E pretrained model on 50 held-out LyNSeC tiles and 10–20
     DLBCL-Morph ROIs.
   - Save overlay panels; have a pathology collaborator score obvious failure modes.
   - Only then extract morphology features for the entire development cohort.
```

### Minimal model pseudocode

```python
# Every row below is a patient, never a patch.
clinical = preprocess_within_fold(train_clinical)
morph = aggregate_cells_to_patient(segmentation_outputs, radii_um=[20, 50, 100])

cox_morph = CoxnetSurvivalAnalysis(l1_ratio=0.5).fit(morph_train, y_train)

# MIL encoder remains frozen initially: far fewer trainable parameters for n=209.
patch_features = frozen_encoder(patches_by_patient)
slide_embedding, attention = gated_attention_mil(patch_features)

# Fuse only pre-specified, fold-trained features. Fit on training patients only.
X = concatenate([clinical, selected_morph_features, slide_embedding])
final_model = penalised_cox(X_train, y_train)
evaluate_locked_test(final_model, X_test, y_test, bootstrap_patients=1000)
```

### Compute plan that respects a 30-hour Kaggle session

- **Do not train a pathology foundation model from scratch.** Start frozen, cache one embedding file per patch and train only MIL/survival heads.
- Start on ROI crops, not the complete 350 GB TCIA collection. A pilot of 20–50 patients should finish within a few GPU hours.
- Run preprocessing/feature extraction once; save versioned Parquet embeddings and masks. Reusing cached features avoids spending GPU time on repeated WSI reads.
- A 5-fold frozen-encoder MIL experiment and ablations should be feasible in roughly 15–35 GPU-hours depending on patch count and GPU. First measure a 10-patient pilot and scale the estimate; do not rely on multiple accounts or repeat expensive runs blindly.
- Use mixed precision, 256 px patches, 20× initially, and a fixed maximum of 200–500 tissue patches/patient. Run 40× only as a pre-specified ablation.

## Alternative projects if you prefer a different balance

| Option | Project | Data and compute | Novelty route | Main risk |
|---|---|---|---|---|
| **A — recommended** | H&E morphology + clinical DLBCL survival model | DLBCL-Morph + LyNSeC; moderate GPU | DLBCL-specific nuclei, spatial microenvironment features, rigorous survival validation | Single main outcome cohort; requires careful claims and a pathology collaborator |
| B — focused pathology method | Uncertainty-aware, stain-robust DLBCL nuclei segmentation/classification | LyNSeC public; low/moderate GPU | Compare HoLy-Net, Cellpose/HoVer-Net and a domain-adaptation strategy; evaluate calibration and cross-stain robustness | Strong segmentation paper needs a truly new method and external annotations, not just a new backbone |
| C — low-compute bioinformatics | Treatment-aware multi-cohort DLBCL transcriptomic survival score | GEO GSE10846/GSE31312 plus independent public cohorts; CPU/small GPU | Train by cohort, test leave-one-cohort-out; stable gene programs rather than opaque high-dimensional classifier | Batch effects, differing CHOP/R-CHOP eras, and a crowded literature |
| D — future clinical collaboration | PET/CT + clinical + ctDNA prediction | Requires PET/CT/ctDNA access; high storage/GPU | External validation and biologically meaningful multimodal fusion | Not feasible on public Kaggle data alone; ethics and data use take time |

### Option C architecture, if you choose transcriptomics

```text
GEO cohorts → platform-specific QC/annotation → within-training-fold batch handling
          → pathway/gene-program features + clinical predictors
          → elastic-net Cox / gradient boosting / RSF
          → leave-one-cohort-out external validation
          → calibration, C-index, biological pathway enrichment
```

The novelty must be **treatment-aware, cohort-held-out validation and stability**, not a claim that an arbitrary neural network achieves the highest internal accuracy. Do not combine CHOP and R-CHOP cohorts without modelling treatment/era or performing stratified analysis.

## Four-month schedule

| Weeks | Deliverable |
|---|---|
| 1–2 | One-page protocol; pathology collaborator; data licence check; data dictionary; patient-level split frozen; event/missingness audit |
| 3–4 | Reproduce DLBCL-Morph clinical/morphology baseline; LyNSeC inference; QC overlay review |
| 5–6 | Feature extraction and spatial-feature unit tests; clinical-only and morphology-only nested-CV results |
| 7–8 | Frozen encoder + attention-MIL baseline; ablation table; compute/data pipeline locked |
| 9–10 | Late-fusion primary model; locked evaluation; bootstrap CIs, calibration and clinical-baseline comparison |
| 11–12 | Stain/domain robustness, subgroup/missingness analyses, error analysis with pathologist, figures |
| 13–14 | Draft manuscript, supplement, TRIPOD+AI/CLAIM checklist, code/data documentation |
| 15–16 | Internal review, preprint/repository preparation, journal formatting and submission |

**Decision gate at week 6:** continue only if the data audit is sound, baseline reproduction is close, and overlays show usable cell segmentation. If not, pivot to Option C rather than forcing a weak pathology model.

## Checklist for a credible Q1 submission

- State the intended use: retrospective risk stratification/research support, not autonomous diagnosis.
- Give inclusion/exclusion criteria, treatment era, endpoint definition, censoring, follow-up and event counts.
- Prevent patient/slide/patch leakage and publish split logic.
- Compare against clinical standards (IPI/R-IPI/NCCN-IPI when the fields support it), not only another neural network.
- Use calibration and confidence intervals, not accuracy alone. Include negative ablations.
- Explain missing-data treatment and perform it within the training fold.
- Provide a data availability and licence statement, code release, environment lockfile, seeds, preprocessing configuration and model card.
- Report error analysis, robustness to stain/scan perturbations and subgroup uncertainty; do not overinterpret subgroup results with few events.
- Have a haematologist/haematopathologist verify clinical framing, outcome definitions and interpretability figures.

Use these reporting/quality standards from the first week:

- [TRIPOD+AI](https://doi.org/10.1136/bmj-2023-078378): reporting standard for prediction models using regression or ML.
- [PROBAST+AI](https://doi.org/10.1136/bmj-2024-082505): self-audit for development quality, bias and applicability.
- [CLAIM 2024](https://doi.org/10.1148/ryai.240300): AI-in-medical-imaging reporting checklist.

## Suggested journal ladder

Choose only after the final contribution is clear and verify current scope/quartile at submission.

1. **Computers in Biology and Medicine** — realistic for a carefully validated computational-pathology method; its relevant 2024 categories are Q1.
2. **Artificial Intelligence in Medicine** or **Journal of Pathology Informatics** — suitable if the clinical/pathology interpretation and external/robustness testing are strong.
3. **Medical Image Analysis** or **IEEE Transactions on Medical Imaging** — only if there is a substantive methodological advance and convincing multi-site external validation; they are not sensible targets for a single-cohort model with minor architectural changes.
4. **npj Precision Oncology** — appropriate only for a strong clinically grounded prediction study with validation and meaningful precision-oncology implications.

No project can guarantee Q1 acceptance in four months. The controllable route is a narrow question, public reproducibility, clinical baselines, honest validation and a pathology collaborator—not a larger neural network.

## Source links

Primary papers and data are linked inline above. Key access pages used in preparing this plan:

1. [HoLy-Net PubMed record](https://pubmed.ncbi.nlm.nih.gov/38237235/) and [LyNSeC Zenodo data/weights](https://zenodo.org/records/8065174).
2. [Ferrández et al., JNM paper](https://doi.org/10.2967/jnumed.124.268191).
3. [Dondolin et al., Leukemia paper](https://doi.org/10.1038/s41375-025-02688-2).
4. [Alem et al., npj Precision Oncology paper](https://doi.org/10.1038/s41698-026-01604-w).
5. [DLBCL-Morph dataset/project repository](https://github.com/stanfordmlgroup/DLBCL-Morph) and [TCIA collection](https://www.cancerimagingarchive.net/collection/dlbcl-morphology/).
6. [NCI Imaging Data Commons TCGA-DLBC collection](https://portal.imaging.datacommons.cancer.gov/collections/tcga_dlbc/) and [CGCI-HTMCP-DLBCL collection](https://portal.imaging.datacommons.cancer.gov/collections/cgci_htmcp_dlbcl/).
7. [TRIPOD+AI](https://www.bmj.com/content/385/bmj-2023-078378), [PROBAST+AI](https://www.bmj.com/content/388/bmj-2024-082505), and [CLAIM 2024](https://pubs.rsna.org/doi/10.1148/ryai.240300).
