# DLBCL Computational-Pathology Novelty Landscape

**Literature refresh:** 28 August 2026  
**Purpose:** define a defensible, testable contribution for the current public
DLBCL-Morph/LyNSeC project  
**Status:** protocol input, not a systematic review and not a claim of novelty
until the search is repeated immediately before submission

## Executive decision

The strongest feasible primary question is:

> Do outcome-blind, distribution-aware measurements of nuclear pleomorphism,
> local cellular packing, and patch-to-patch heterogeneity from routine DLBCL
> H&E add prognostic information beyond IPI/R-IPI and the released
> tumour-nucleus geometric baseline when evaluated with strict patient-level,
> leakage-safe censored-survival methods?

This is narrower and more defensible than claiming a new deep-learning
architecture, an H&E reconstruction of immune ecosystems, or clinical
deployment. The result is publishable only if the increment is stable and
uncertainty is reported; a well-powered negative result can still be useful if
the protocol and artifacts are reproducible.

## What the present project can actually measure

E-007 contains 1,959,950 watershed-separated objects from 30,007 H&E patches
for 170 patients. Its patient table contains distribution summaries of area,
perimeter, eccentricity, solidity, circularity, axes, and RGB intensity, plus
patch count, nuclear-foreground, tissue, nearest-neighbour, and Delaunay-edge
summaries.

Important boundaries:

- the E-001/E-007 branch is binary **all-nucleus** segmentation;
- it has no validated tumour/non-tumour or immune-cell phenotype;
- coordinates are patch-local pixels, not verified physical units;
- cross-patch or whole-core topology is not currently supported; and
- independent pathology review remains required before outcome joining.

Accordingly, the valid language is “nuclear pleomorphism,” “cellular packing,”
and “within-patch spatial organization.” It is not valid to call the existing
features tumour–immune mixing, macrophage neighborhoods, or a spatial-omics
surrogate.

## Closest published and emerging work

| Work | What it establishes | What it does not answer for this project |
|---|---|---|
| Vrabac et al., *Scientific Data* 2021, DLBCL-Morph | 170 H&E-eligible patients; tumour-nucleus geometric means/SDs; geometric C-index 0.635, clinical 0.674, combined 0.700 | No distribution tails, patch heterogeneity, explicit packing ablation, repeated nested CV, time-AUC/Brier/calibration, or significant proof of incremental clinical value |
| Naji et al., *Computers in Biology and Medicine* 2024, HoLy-Net/LyNSeC | DLBCL-specific nucleus instance segmentation/classification; reported H&E F1 0.899 | Segmentation performance is not patient-level prognostic validation; the released checkpoint was not functionally reproducible in this environment despite complete key coverage |
| Iyer et al., *Blood* 2023 abstract | Transformer clusters over 223 slides from TCGA/Stanford sources; alive/dead AUC 0.77; necrosis-associated cluster | Conference abstract, binary vital status rather than censored OS, and no demonstrated incremental value over IPI under a locked patient-level protocol |
| Carreras et al., *Biomedicines* 2026 | 114 DLBCL cases; DarkNet-19 patch classification of death within two years; XAI panels | Converts follow-up into a binary endpoint, relies heavily on patch-level evaluation, and does not give a full censored-survival comparison with calibration and paired clinical increment |
| Carreras et al., *Cancers* 2026 | Mean grayscale image entropy associated with OS; univariate HR 2.4 at an optimized cut-point in 114 cases | A single global texture statistic, same-cohort cut-point search, no independent cohort, no nested prediction evaluation, and no cytologic/spatial decomposition |
| Reiss/Rodig and related high-plex imaging studies | DLBCL contains recurrent spatial immune neighborhoods and distinct TIME architectures | Uses multiplex protein phenotypes unavailable in routine H&E; does not license cell-type claims from an all-nucleus mask |
| Kuusanmäki et al. and related spatial studies | In 99 treatment-naïve cases, cell interactions/neighborhood proximity were associated with outcome | Different assay and phenotype resolution; supports the biological importance of organization but is not an H&E prognostic model |
| 2026 spatial-transcriptomic ecosystem study | Six spatial ecosystems; derived expression signatures stratified survival in an external cohort exceeding 1,000 cases | Ten spatial-transcriptomic discovery samples; external validation was transcriptomic-signature validation, not validation of an H&E spatial score |
| ImmunoBench, active 2026 benchmark | DLBCL-Morph is already a 170-patient, 1,009-slide H&E/IHC OS task across 14 pathology foundation models; prognosis performance is weak/variable overall | Generic foundation embeddings or multistain MIL are no longer a safe novelty claim; the benchmark does not replace an interpretable, clinically incremental cytology/packing analysis |

## The missing comparison

No located study combines all of the following in DLBCL:

1. routine H&E-derived, cell-resolved pleomorphism and packing features;
2. distribution tails and between-patch heterogeneity rather than only means;
3. proper right-censored OS instead of alive/dead or two-year labels;
4. strict patient-level repeated nested validation with fold-internal processing;
5. paired incremental comparison over IPI/R-IPI and the released DLBCL-Morph
   baseline;
6. discrimination, calibration, Brier score, and bootstrap uncertainty; and
7. explicit pathology-QC and segmentation-artifact sensitivity analyses.

This is the current novelty package. It must be phrased as a combination of
question, representation, and evaluation—not as ownership of any single
feature such as entropy or nearest-neighbour distance.

## Pre-specified hypotheses

### Primary

Adding the frozen E-007 morphology/packing representation to a pre-specified
clinical penalised Cox model improves out-of-fold OS prediction relative to
the same clinical model alone.

The primary test is a paired patient-level difference in discrimination, with
calibration and Brier score used to reject apparently better but poorly
calibrated models. No minimum improvement is assumed.

### Secondary biological hypotheses

1. **Pleomorphism:** wider IQR/tails of nuclear area, axes, eccentricity, and
   circularity capture cytologic heterogeneity not represented by means alone.
2. **Packing:** nuclear foreground, count density, nearest-neighbour, and
   Delaunay distances capture local architectural disorder.
3. **Patch heterogeneity:** variability across representative tumour patches
   adds information beyond a single pooled patient average.
4. **Phenotype concordance:** stable patient signatures may associate with
   HANS/COO and MYC/BCL2/BCL6/CD10/MUM1/FISH variables, but such association is
   not evidence of cell-level phenotype or causality.
5. **Robustness:** any signal should survive exclusion/down-weighting of
   low-tissue, border, elongated/fibrous, and segmentation-stress cases.

## Locked model ladder

Use the same eligible patients and outer splits for every paired comparison:

| ID | Model | Role |
|---|---|---|
| M0 | IPI and R-IPI scores | Clinical standards |
| M1 | Raw IPI components in a penalised Cox model | Primary clinical baseline |
| M2 | Released DLBCL-Morph tumour-nucleus mean/SD geometry | Reproduced literature baseline |
| M3 | Global grayscale H&E entropy | Direct comparator to the July 2026 paper; continuous and outcome-blind |
| M4a | E-007 morphology distributions only | Pleomorphism ablation |
| M4b | E-007 patch packing/heterogeneity only | Spatial/architecture ablation |
| M4c | E-007 morphology + packing | Primary image model |
| M5 | M1 + M4c | Primary incremental model |
| M6 | One frozen pathology-encoder/MIL score | Optional benchmark, not primary novelty |

NCCN-IPI is not computable because the cohort provides binary LDH rather than
LDH as a multiple of the assay upper limit of normal.

## Validation rules

- Primary cohort: the common 170 patients with H&E features and 58 OS events.
- Endpoint: OS only; PFS lacks an event indicator.
- No 20% locked test set: approximately 12 events would be too unstable.
- Repeated nested patient-level CV is the primary internal validation design.
- Imputation, scaling, redundancy filtering, selection, PCA if used, and model
  tuning must be fitted only inside each training fold.
- Penalised Cox is the primary learner. RSF is a secondary nonlinear ablation,
  not a route to unconstrained feature searching.
- Report Harrell and Uno C-index, time-dependent AUC, integrated Brier score,
  calibration, and 1,000 patient-level paired bootstrap intervals.
- Choose KM cut-points inside training data only; do not optimize a full-cohort
  entropy or risk threshold.
- Keep a complete model/feature-family multiplicity table and label exploratory
  marker associations as such.

## What would invalidate or weaken the novelty

- pathology review finds systematic non-nuclear capture or unacceptable
  domain shift;
- the feature definition changes after inspecting outcomes;
- patch-level splits or patch-weighted survival fitting are used;
- a claim of immune-cell composition is made without validated phenotypes;
- only a best C-index is reported without calibration, uncertainty, or paired
  clinical comparison;
- the same cohort is described as external or clinical validation; or
- broad foundation-model searches replace the pre-specified interpretable
  question.

## Recommended extension after the primary analysis

A separately validated tumour/non-tumour classifier trained on the labelled
LyNSeC-3 subset could enable a future tumour/host interaction analysis. This is
not part of E-007 and should be promoted only after grouped validation,
DLBCL-Morph pathology review, and a clear failure/sensitivity plan. It is a
secondary extension, not a prerequisite for the current primary paper.

## Primary sources

1. Vrabac D, et al. DLBCL-Morph. *Scientific Data*. 2021. [doi:10.1038/s41597-021-00915-w](https://doi.org/10.1038/s41597-021-00915-w); [official code](https://github.com/stanfordmlgroup/DLBCL-Morph).
2. Naji H, et al. HoLy-Net. *Computers in Biology and Medicine*. 2024. [doi:10.1016/j.compbiomed.2024.107978](https://doi.org/10.1016/j.compbiomed.2024.107978); [LyNSeC data and weights](https://zenodo.org/records/8065174).
3. Iyer S, et al. DLBCL self-attention transformer pilot. *Blood*. 2023. [doi:10.1182/blood-2023-187291](https://doi.org/10.1182/blood-2023-187291).
4. Carreras J, et al. Histological-image deep learning and two-year mortality. *Biomedicines*. 2026. [doi:10.3390/biomedicines14051134](https://doi.org/10.3390/biomedicines14051134).
5. Carreras J, et al. Histological entropy and DLBCL survival. *Cancers*. 2026. [doi:10.3390/cancers18142279](https://doi.org/10.3390/cancers18142279).
6. Reiss DJ, et al. Spatially defined DLBCL tumour immune microenvironments. *Blood*. 2023. [PubMed Central](https://pmc.ncbi.nlm.nih.gov/articles/PMC10448427/).
7. Kuusanmäki H, et al. Clinically relevant cell interactions and recurrent cellular neighborhoods in DLBCL. *Cancer Research Communications*. 2025. [PubMed Central](https://pmc.ncbi.nlm.nih.gov/articles/PMC12485370/).
8. Multi-modal spatial characterization of targetable inflammatory niches in DLBCL. 2025. [PubMed PMID 41120574](https://pubmed.ncbi.nlm.nih.gov/41120574/).
9. Spatial transcriptomics unveils immune cellular ecosystems associated with DLBCL survival. 2026. [PubMed Central](https://pmc.ncbi.nlm.nih.gov/articles/PMC13102037/).
10. ImmunoBench project and DLBCL-Morph Lymphoma-OS task. 2026 active release. [official GitHub repository](https://github.com/yanfang-research/ImmunoBench); [feature registry](https://huggingface.co/datasets/AI4Pathology/ImmunoBench-image-features).

