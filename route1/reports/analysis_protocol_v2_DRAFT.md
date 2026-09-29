# Route 1 — analysis protocol v2, DRAFT (Phase 4D)

> **SUPERSEDED 2026-09-30 by Route 1 decision D-008.** The primary question has
> been re-scoped to a pre-registered audit of published DLBCL prognostic
> signatures against IPI and size-matched random gene sets. This draft was never
> signed or frozen and is retained unchanged below for the record. The R0 IPI
> baseline, population, transform order and synthetic tests carry over; the
> Hallmark-program ladder (R1–R3) becomes one arm of the audit.

**Date:** 2026-09-11 · **Status: DRAFT — NOT SIGNED, NOT FROZEN**

Per supervisor 4/Phase 4D: this may be drafted now but **must not be frozen**
while the OS estimand remains an inference. Section 9 lists the freeze
prerequisites.

Supersedes the B0–B4 ladder. Old→new identifier mapping in §2.

---

## 1. Question and claim scope

*Do fixed, published biological program scores add prognostic information
beyond a clinical IPI baseline in DLBCL, and does any increment survive
transfer to an independent cohort on a different expression platform?*

**Not claimed:** that the representation is a validated assay; that it is
superior to MHG or LymphGen (those contrasts are only testable where subtype
meaning is established); that any coverage-robustness method is demonstrated
(the masking arm was withdrawn — §2.1).

## 2. Model ladder

| New | Old | Model | Role |
|---|---|---|---|
| **R0** | ~B0~ | Penalised Cox on **IPI** with a fixed encoding | Common clinical baseline |
| **R1** | B1 | R0 + verified equivalent COO/MHG categories | Established molecular comparator — **conditional, see §5** |
| **R2** | B2 | R1 + eight fixed Hallmark program scores, penalised Cox | **Main biological increment** |
| **R3** | B3 | Small neural survival model, same inputs as R2 | Optional nonlinear comparator, subject to §8 |
| — | ~B4~ | ~masking arm~ | **WITHDRAWN** — proven no-op, see §2.1 |

### 2.1 Why B4 is gone

Ranking universe `U = dev ∩ ext`; proposed mask `M = dev − ext`; therefore
`U ∩ M = ∅`. Verified: `|U|=15,647`, `|M|=5,171`, `|U ∩ M|=0`. Masking removed
**zero** model inputs. It was not a weak test but no test. Asserted in
`phase3R_representation_checks.py` C1. It will not be run to produce a null.
Random dropout inside `U` is not a substitute. A targeted-panel study is
separate and would need its own dated protocol.

**If R1 fails its gate (§5), R2 is redefined as R0 + programs** and the primary
claim is amended accordingly, before fitting.

## 3. Primary population

Identity-safe: one sample per verified patient, selected by the deterministic
outcome-independent hierarchy (pretreatment → highest `probe_detection` → GSM
order). Identifier semantics verified — all 12 multi-sample groups agree
exactly on sex, age, OS time and OS status; **zero conflicts**.

| Set | Patients | Events |
|---|---:|---:|
| Identity-safe eligible | 301 | 142 (47.2%) |
| Observed `ipi_score` | 230 | 105 |
| All five components present | 264 | 120 |
| **PRIMARY — observed OR reconstructable IPI** | **265** | **121** |

Reverse-KM follow-up after deduplication **8.79 y** (range 0.0110–14.3190).
Subtypes GCB 143 / ABC 90 / UNC 51 / **MHG 17**.

**Excluded: the 243 eligible samples with no patient identifier.** Excluded
from supervised development *and* from representation learning, since the
latter could expose held-out patients. Permitted use: descriptive technical QC
only, clearly separated. Written to `population_excluded_unidentified.csv`.

Patient-count bounds: at least 301, at most 544 patients are represented among
the eligible records; neither bound resolves the 243.

## 4. Primary estimand and contrast

- **Primary contrast:** paired ΔC (Harrell, patient-level) between **R2 and R1**
  on the untouched external cohort — or **R2 vs R0** if R1 fails §5.
- **Same patients, same outcome definition, same horizon** for every arm.
- Paired patient-level bootstrap for uncertainty; **no sample-level bootstrap**.
- Secondary: calibration and Brier at the chosen horizon; subgroup summaries
  where counts permit (note MHG n=17 — descriptive only).

## 5. R1 conditional gate — must pass BEFORE R1 enters

1. `pred_combine`'s producing classifier and version identified.
2. Equivalent assignments obtainable in the external cohort by a validated,
   platform-appropriate procedure. **No invented Lymph2Cx centroids or
   RNA-seq cut-offs.**
3. A prespecified, justified mapping between a **four-class** development label
   (GCB/ABC/UNC/MHG) and whatever the external cohort provides
   (GSE87371 `coo` is GC/ABC/Other/PMBL). **MHG must not be folded into GCB,
   and missing MHG must not be treated as absent**, without a stated rule.

**Currently unmet.** `pred_combine` provenance is unresolved.

**No directional reassurance is claimed.** The earlier assertion that an
optimistic R1 makes R2−R1 conservative is **withdrawn** — correlated errors and
shared inputs can move a paired contrast either way.

## 6. Missingness

- Primary population requires observed or exactly reconstructable IPI, so no
  IPI imputation enters the primary estimand.
- Fold-internal imputation of clinical components is permitted only in a
  **secondary** development analysis, fitted within training folds.
- An all-301 IPI-imputation sensitivity is optional and must state its
  missingness assumptions; it **must not silently replace** the primary.
- Component missingness in the identity-safe set: ECOG 5.6%, stage 8.0%,
  LDH 7.3%, extranodal 10.0%, age 0%.

## 7. Horizon, metrics, precision

**Horizon: two years, provisional.** To be confirmed against numbers at risk
and censoring support *in each cohort* before freezing. GSE10846's 2.12 y
median follow-up does not by itself decide supportability — support must be
inspected. Five-year claims are not required.

- Concordance: Harrell primary, Uno secondary, truncation stated.
- Brier/IBS with an explicitly named censoring-distribution estimator.
- Per-cohort rule for an unsupportable horizon: report, do not substitute.

### 7.1 Precision assessment — the target is not reachable externally

Simulation at the external geometry (**n=103, 36 events**, 2,000 replicates,
paired predictions on the same patients):

| Quantity | Value |
|---|---|
| SD of paired ΔC | **≈ 0.057** |
| 95% CI width | **≈ 0.22** |
| Planning target | +0.03 |
| Target ÷ CI half-width | **≈ 0.27** |

**A +0.03 increment is roughly four times smaller than the confidence
half-width.** The external cohort cannot certify it. Per supervisor 2.4, the
target is **not lowered**; instead this study is labelled a **preliminary
external assessment reporting intervals**, and must not promise detection of
small effects.

Three outcomes will be reported as distinct, never conflated: (a) a positive
point estimate; (b) an interval excluding zero; (c) an interval supporting an
increment at least as large as +0.03. Only (c) would support the planning
target, and (c) is very unlikely to be attainable here.

*(Simulation caveat: the effect-size calibration is crude — the achieved mean
increment was +0.011 when targeting +0.03. The governing quantity, the SD of
the paired difference, is stable at ≈0.057 and is what the conclusion rests on.)*

## 8. R3 (neural) gating

R3 runs **only** if: R2 is specified and fitted; the development event count
supports it (121 primary events); and the T4 queue in §10 fits. One hidden
layer of 16–32 units, float32, linear risk output, full-training-fold Cox
partial likelihood — **no minibatch risk sets**. Early stopping on inner
validation only. **Architecture is not expanded because the dataset shrank.**

## 9. Freeze prerequisites — ALL must pass

| # | Prerequisite | Status |
|---|---|---|
| 1 | OS time origin for GSE181063 **documented**, not inferred | ❌ INFERRED only |
| 2 | External OS time origin established | ❌ "duration of OS" is uninformative |
| 3 | GSE87371 `ID` → patient relationship verified | ❌ documented as "sample ID" |
| 4 | R1 gate (§5) resolved either way | ❌ unresolved |
| 5 | Horizon support inspected per cohort | ❌ not done |
| 6 | Data-use terms checked before any Kaggle upload | ❌ not done |
| 7 | GSE31312 supplement retrieved or cohort formally set aside | ❌ not attempted |

**Until 1 and 2 pass, no survival model may be fitted to real patient data.**

## 10. T4 queue estimate

Removing B4 removes its entire fit queue.

| Arm | Fits |
|---|---|
| R0, R1, R2 (penalised Cox) | CPU only — no GPU |
| R3 if gated in | ≤4 configs × 3 inner × 5 outer = **60 inner + 5 outer refits** |

Session contract unchanged: 12 h cap; stop launching at 10 h 30; safe stop at
11 h; validate/persist and exit by 11 h 30. Checkpoint every 5 min or 5 epochs
and after each fold. `/kaggle/working` is not persistent across sessions.
**No GPU time will be spent repeating Phases 0–3.** External performance will
never decide how many sessions to run.

## 11. Prohibitions

Outcome-based gene/probe selection · joint batch correction of development and
final test · double log transformation · zero-substitution for unmeasured genes
· choosing the ranking universe after seeing results · using the final test for
any selection · lowering the effect target after seeing results · expanding the
model search to rescue a negative result.
