# Phase 3B — Kaggle runbook (E-008, Step S2, E-009)

Execution is split between local and Kaggle deliberately:

| Step | Where | Why |
|---|---|---|
| Sign protocol §13 | local | The signed document lives in the repo. |
| **E-008** entropy | **Kaggle** | 30,007 patch reads; heavy on a loaded workstation. |
| **Step S2** splits | **local** | ~1 second, no measurable load, and the signature gate must hash the protocol files where they actually live. |
| **E-009** ladder | **Kaggle** | CPU-only, but keeps the workstation free. |

Nothing here needs a GPU. Run both notebooks on a **CPU** accelerator — it
starts faster and does not consume GPU quota.

---

## Step 1 — sign the protocol (local)

```powershell
python src/analysis/build_split_ids.py --print-hash
```

Paste the name, today's date, and the printed hash into the Researcher row of
§13 in `reports/phase_03b_statistical_analysis_protocol.md`.

## Step 2 — upload the small inputs dataset (local)

```powershell
python kaggle/upload_helpers/make_and_upload_phase3b_inputs.py            # dry run
python kaggle/upload_helpers/make_and_upload_phase3b_inputs.py --upload   # create
```

Creates `kawsersikder/dlbcl-phase3b-inputs` (~4.6 MB): the E-008 script,
`patch_qc.csv`, and `patient_features.csv`. `MANIFEST.json` records the SHA-256
of each file, including the script, so the code version that produced the
entropy features is auditable.

Clinical tables and released geometry are **not** duplicated here — they are
already in `kawsersikder/dlbcl-morph-tables`.

## Step 3 — E-008 on Kaggle

Create a **new** notebook. Do not reuse or edit the E-007 notebook — that one is
the provenance record of the frozen feature cache, it needs a GPU and a
checkpoint, and it shares no code with E-008.

Settings → Accelerator: **None (CPU)**. **Add Data** → attach:

- `kawsersikder/dlbcl-morph-patches`
- `kawsersikder/dlbcl-phase3b-inputs`

One cell, then Save & Run All:

```python
!python /kaggle/input/datasets/kawsersikder/dlbcl-phase3b-inputs/run_e008_entropy.py
```

Kaggle mounts datasets at `/kaggle/input/datasets/<owner>/<dataset-name>/`
(verified 2026-08-31 — `os.listdir("/kaggle/input")` returns `['datasets']`).
The script's own input discovery is a breadth-first walk from `/kaggle/input`,
so it tolerates this layout; only literal paths in the notebook cell need the
full prefix. Confirm what is mounted with:

```python
import os
print(sorted(os.listdir("/kaggle/input/datasets/kawsersikder")))
```

Inputs are auto-discovered under `/kaggle/input`; outputs land in
`/kaggle/working/phase_03b_e008_entropy/`. The run aborts rather than writing
partial output if any protocol §4 gate fails — 170 patient rows, 29,464
eligible patches, all values finite, patch counts reconciling with `patch_qc`.

Download the three output files into `reports/`:

```
phase_03b_entropy_features.csv
phase_03b_entropy_patch_level.csv
phase_03b_entropy_run_summary.json
```

## Step 4 — Step S2 splits (local)

```powershell
python src/analysis/build_split_ids.py
```

**This is where outcome-blindness ends.** The script refuses to run unless §13
carries a matching lock hash. Writes `data/manifests/split_ids.csv` and
`split_ids_summary.json`; the summary carries the protocol lock hash forward as
a provenance token, so E-009 can verify the chain of custody without needing
the protocol files on Kaggle.

## Step 5 — publish v2 of the inputs dataset (local)

```powershell
python kaggle/upload_helpers/make_and_upload_phase3b_inputs.py --upload --version "add E-008 entropy + S2 splits"
```

Now picks up the entropy features and the split manifest that were skipped in
Step 2.

## Step 6 — E-009 on Kaggle

The Coxnet ladder (primary, §9 sensitivities, cohorts B and C) was run locally
and is complete. Only **S6 (Random Survival Forest)** is run here, because two
local attempts failed: a joblib/loky process-pool deadlock on Windows, then a
silent process death at 47/50 folds. Neither failure mode applies in an isolated
Linux container.

New notebook, Accelerator **None**. **Add Data** → attach:

- `kawsersikder/dlbcl-phase3b-inputs` (**v2 or later** — v1 lacks the splits,
  geometry, entropy and protocol files)
- `kawsersikder/dlbcl-morph-tables` (supplies `clinical_data_cleaned.csv`)

`dlbcl-morph-patches` is **not** attached — E-009 never touches an image.

```python
!pip install -q scikit-survival==0.28.0
!python /kaggle/input/datasets/kawsersikder/dlbcl-phase3b-inputs/run_e009_ladder.py --rsf
```

Inputs are auto-discovered under `/kaggle/input`; outputs land in
`/kaggle/working/phase_03c_results_tables/` as `*_cohortA_rsf.*`.

Expect roughly 2–3 hours — Kaggle gives ~4 vCPUs against 12 locally, and
`RSF_N_JOBS` adapts to the available count. The 9-hour session limit is ample.
A per-fold heartbeat is printed, so a stall is visible immediately rather than
after two silent hours.

The script recomputes the protocol lock hash and compares it to the value
recorded in `split_ids_summary.json`, so chain of custody is verified on Kaggle
exactly as it is locally. Record the resolved `scikit-survival` version per
protocol §6.4 — it is captured automatically in `run_summary_cohortA_rsf.json`.

Download the `*_rsf.*` files into `reports/phase_03c_results_tables/`.
