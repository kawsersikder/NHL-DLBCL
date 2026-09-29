# E-008 — outcome-blind global grayscale entropy comparator

**Run date:** 2026-08-31 (Kaggle, CPU)
**Report date:** 2026-09-01
**Protocol:** Phase 3B §4
**Outcome access:** none. No clinical column was opened.
**Status:** complete, all gates passed, frozen.

---

## 1. Purpose

M3 in the model ladder is the comparator to the July 2026 global-entropy paper.
This experiment produces its covariates. The implementation deliberately
reproduces the published method rather than improving on it — no tissue masking,
whole-patch histogram, patient mean — so that M3 is a fair opponent. Any gain the
morphology models show over M3 must not be an artifact of us having built a
deliberately weak comparator.

## 2. Method (frozen)

| Choice | Value |
|---|---|
| Grayscale | `PIL.Image.convert("L")` = ITU-R 601-2 luma |
| Quantisation | 256 levels |
| Statistic | Shannon entropy, bits, over the whole-patch intensity histogram |
| Tissue masking | **none** (deliberate — matches the published comparator) |
| Eligibility | frozen E-007 `patch_qc.csv`; `tissue_fraction < 0.50` excluded from aggregation |
| Patient aggregation | `mean` (primary), plus `median, iqr, p10, p90` (secondary) |

Eligibility was **read from** the frozen E-007 QC table rather than recomputed.
This makes patch counts reconcile with the morphology cache by construction
rather than by coincidence.

Entropy was computed and retained for all 30,007 patches, including the 543
ineligible ones, so later sensitivity work needs no re-run.

## 3. Gates — all passed

| Gate | Required | Observed |
|---|---|---|
| Patient rows | 170 | 170 |
| Eligible patches | 29,464 | 29,464 |
| Total patches | 30,007 | 30,007 |
| All values finite | yes | yes |
| Patch counts reconcile with `patch_qc` | exact | exact |
| Image modes | — | RGB 30,007 / 30,007 |

The eligible-patch count matching E-007 exactly is the load-bearing check: it
confirms M3 and M4c are computed over an identical patch set, so the paired
comparison in §3.2 is valid. A drift of even one patch would have invalidated it
silently.

Local SHA-256 of the downloaded features file matches the Kaggle-side hash
exactly (`e26af3eb…`), confirming a clean transfer.

## 4. Outcome-blind diagnostics

### 4.1 The comparator has little dynamic range

`entropy_mean` spans **6.976 to 7.743** across 170 patients — 0.77 bits against a
theoretical ceiling of 8.0. Median patient 7.495. Within-patient IQR is under
0.15 bits for most patients.

This is a property of the feature, not a result. It is recorded now, before
outcome access, so that the later interpretation is not post-hoc: if M3
underperforms, the defensible reading is *"this comparator has limited resolving
power on this cohort"*, not *"entropy is refuted"*. If M3 performs well despite
this compression, that is more surprising than it appears.

### 4.2 Not confounded with sampling exposure

Spearman |ρ| between each entropy feature and `qc_patch_count_eligible`:

| Feature | ρ vs eligible patch count |
|---|---:|
| `entropy_mean` | −0.001 |
| `entropy_median` | +0.017 |
| `entropy_p10` | +0.050 |
| `entropy_p90` | −0.055 |
| `entropy_iqr` | −0.155 |

M3 is essentially independent of how much tissue was sampled. This is the F0
confounding concern (§2) checked directly for the entropy family, and it comes
back clean — unlike `cell_count_total`, entropy is not a disguised measure of
TMA core availability.

### 4.3 The tissue rule is removing genuinely low-information patches

| Patch set | n | Mean entropy | Min |
|---|---:|---:|---:|
| Eligible | 29,464 | 7.467 | 5.729 |
| Ineligible (low tissue) | 543 | 5.321 | 2.889 |

An independent measurement agrees with the E-006 tissue rule: excluded patches
carry substantially less image information. The rule was not tuned against this
statistic.

### 4.4 Independent corroboration of the QC outliers

Patient **26807** — the single AI-FAIL representative panel — is the **lowest
entropy patient in the entire cohort** (6.976, 0th percentile). Patient **13957**
sits at the 15.9th percentile.

Both were flagged by visual overlay QC, a completely unrelated method. A global
texture statistic independently placing 26807 at the extreme strengthens the
case for the pre-specified Cohort B sensitivity analysis. Note this changes
nothing: the cohorts were frozen before this was computed, and no patient is
being excluded on the strength of it.

## 5. A protocol gap found by these diagnostics

The five entropy features are strongly inter-correlated:

| Pair | ρ |
|---|---:|
| `entropy_mean` vs `entropy_median` | **+0.968** |
| `entropy_mean` vs `entropy_p10` | +0.875 |
| `entropy_mean` vs `entropy_p90` | +0.871 |
| `entropy_mean` vs `entropy_iqr` | −0.608 |

One pair exceeds the §6.2 pruning threshold of |ρ| > 0.90. But **§6.2 is
ambiguous about whether it applies to M3.** The rule is written for the E-007
features and breaks ties using "the frozen family order of §2" — and §2's
partition (F0/F1/F2) does not contain the entropy family at all.

Left unresolved, this becomes a judgement call made *after* seeing M3's
performance, which is exactly the failure mode the protocol exists to prevent.

**Resolved 2026-09-01, before outcome access.** §6.2 now states explicitly that
it applies to every model in the ladder, and fixes the entropy tie-break order
as the §4 declaration order — `mean, median, iqr, p10, p90`. Under that rule
`entropy_median` is pruned in favour of `entropy_mean` (the primary covariate),
and `p10`/`p90` survive at ρ < 0.90. **M3 carries 4 effective covariates.**

Applying the rule uniformly avoids handing M3 a collinearity handicap that M4c
does not carry, which would have made the primary paired comparison uneven.

This is a **pre-outcome** clarification, written into both §6.2 and the YAML
twin while the answer was still unknown. It is deterministic and cannot be
tuned. It is not a §12 amendment, because the protocol was unsigned when it was
made; the protocol lock hash changed as a result, from `cbe01511…` to
`364e1933…`.

## 6. Artifacts

| File | SHA-256 |
|---|---|
| `reports/phase_03b_entropy_features.csv` | `e26af3eb472aa1eb39fa08f5650d1d501e277c9b3ebe0c0c17d434cae6b4ec3c` |
| `reports/phase_03b_entropy_patch_level.csv` | `45197ad459487a8d9168c34306eca818dc489c61a93ace569554581c9b76d71a` |
| `reports/phase_03b_entropy_run_summary.json` | run manifest, environment, gates |

Code: `src/analysis/run_e008_entropy.py`, shipped inside
`kawsersikder/dlbcl-phase3b-inputs` with its SHA-256 recorded in that dataset's
`MANIFEST.json`, so the exact code version that produced these features is
auditable.

Environment: Python 3.12.13, numpy 2.0.2, pandas 2.3.3, Pillow 11.3.0 (Kaggle CPU).

The three output files are held **only** in `reports/`. They are deliberately not
mirrored into a `kaggle/…/output_e008_entropy/` folder in the E-007 style,
because protocol §1.1 names `reports/phase_03b_entropy_features.csv` as the
frozen input to E-009 and a second copy would invite drift.

## 7. Execution-order note

E-008 was executed on 2026-08-31, **before** the §13 signature. Protocol §13
nominally authorises E-008, so the true order is recorded here rather than
implied otherwise by timestamps.

The deviation is procedural, not scientific: the run never opened a clinical
column, `outcome_blind: true` is recorded in the run manifest, and the gate that
carries the real weight — Step S2, where blindness ends — remained mechanically
enforced and unsigned throughout.

## 8. Limitations

- Global grayscale entropy is a coarse texture summary. It responds to staining
  intensity, scanner, and focus as much as to biology. It is included as a
  faithful comparator, not as a feature this project endorses.
- No tissue masking is applied *within* eligible patches, by design. Background
  inside an eligible patch contributes to its entropy.
- Patch-level entropy is not comparable across studies without matching the
  patch size, magnification, and grayscale conversion used here.
