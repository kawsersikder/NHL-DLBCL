# Phase 3 — platform characterisation and program coverage

**Date:** 2026-09-10
**Artifacts:** `route1/manifests/gene_mapping.csv`, `program_gene_sets.csv`,
`platform_summary.csv`, `route1/configs/representation.yaml`
**Script:** `route1/src/phase3_platform_coverage.py`

No expression value has been joined to any outcome. The entire representation
was fixed before the first model.

---

## 1. Platform annotation

| | GPL14951 (development) | GPL570 (all external) |
|---|---|---|
| Title | Illumina HumanHT-12 WG-DASL V4.0 R2 | [HG-U133_Plus_2] Affymetrix HG U133 Plus 2.0 |
| Technology | oligonucleotide beads | in situ oligonucleotide |
| Annotation dated | **2017-12-22** | **2020-12-14** |
| Symbol column | `Symbol` | `Gene Symbol` |
| Probes total | 29,377 | 54,675 |
| Blank symbol | 0 | **8,893** |
| Multi-mapping (excluded) | **0** | **2,796** |
| Usable probes | 29,377 | 42,986 |
| **Genes measured** | **20,818** | **21,653** |

The annotation versions differ by three years, and the platforms differ in
annotation practice: Affymetrix probe sets frequently name several genes
(`///`-separated) and 16% carry no symbol at all, whereas every Illumina probe
names exactly one. Both were handled by the same rule — a probe is usable only
if it names exactly one gene — so the asymmetry is absorbed by an identical
rule rather than by two different ones.

SHA-256: GPL14951 `372432a3…`, GPL570 `9ef4cf16…`.

## 2. Cross-platform gene overlap

| | Genes |
|---|---:|
| GPL14951 only | 5,171 |
| GPL570 only | 6,006 |
| **Shared** | **15,647** |
| Shared / GPL14951 | **75.2%** |

**This is a lower bound.** No synonym or alias resolution was applied, because
an alias table is a versioned dependency needing its own provenance. Genes that
differ only by symbol nomenclature between a 2017 Illumina annotation and a
2020 Affymetrix annotation will appear as non-shared here.

So the headline platform shift is real: **about a quarter of development genes
are not retrievable on the external platform.**

## 3. Program coverage — and the finding that matters

| Program | Set genes | On dev | dev % | Shared | shared % | **Lost moving to external** |
|---|---:|---:|---:|---:|---:|---:|
| angiogenesis | 36 | 36 | 100.0 | 35 | 97.2 | 1 |
| inflammatory_macrophage | 200 | 197 | 98.5 | 197 | 98.5 | **0** |
| stromal_ecm | 200 | 195 | 97.5 | 193 | 96.5 | 2 |
| nfkb_signalling | 200 | 194 | 97.0 | 190 | 95.0 | 4 |
| interferon_antigen_presentation | 200 | 193 | 96.5 | 189 | 94.5 | 4 |
| proliferation_myc | 200 | 184 | 92.0 | 176 | 88.0 | 8 |
| proliferation_e2f | 200 | 183 | 91.5 | 180 | 90.0 | 3 |
| oxidative_phosphorylation | 200 | 179 | 89.5 | 175 | 87.5 | 4 |

Every program clears both coverage thresholds (≥10 genes, ≥50% of set) on both
platforms by a wide margin. As a representation, this is a good result: the
programs are scoreable in every cohort without any program being dropped.

### ⚠ But it largely removes B4's reason to exist

- Program genes on the development platform: **1,361**
- Of those, lost when moving to GPL570: **26 (1.9%)**
- Of the 5,171 development-only genes, how many sit in any program: **25
  (0.48%)**

**The realistic platform mask removes about 2% of program genes.** The genome
loses 25% of its genes across this platform move; the *programs* lose almost
nothing — because Hallmark sets are built from well-characterised, widely-assayed
genes, which is exactly the population both arrays cover well.

B4 is defined as B3 plus prespecified gene-coverage masking during training,
and the plan is explicit that "improvement of B4 over B3 is the relevant test of
the proposed training modification". With the realistic mask perturbing ~2% of
inputs, **B4 and B3 will be near-identical by construction, and a null B4−B3
result would carry almost no information** — it would say the masking scheme
didn't matter *because there was nothing to mask*, not because coverage
robustness is unimportant.

This is a property of the chosen representation, discovered before fitting. It
is not a reason to go looking for a mask that produces a better number.

### Options, for the supervisor to decide — not chosen here

1. **Run B4 anyway and report the null as uninformative**, with the 1.9% figure
   stated up front so the reader can see why. Honest, cheap, low value.
2. **Drop B4** and narrow the study to the scientific increment (B2 vs B1),
   declaring that the coverage-robustness question was abandoned once measured
   to be vacuous for this representation. Removes the methodological novelty.
3. **Re-scope the coverage question to a regime where it bites** — e.g. a
   targeted-panel scenario of ~50–200 genes, or a deliberately degraded
   coverage schedule. This is a **different question** than "does the model
   survive Illumina→Affymetrix", and choosing it *after* seeing these numbers
   must be declared as such, dated, and labelled exploratory.
4. **Keep Hallmark but add programs with genuinely platform-divergent
   membership.** Would need an outcome-independent selection rule defined
   before looking at any result, and I have not identified one.

My reading: option 3 is the only one that preserves a real methodological
question, and it must be declared as a dated re-scope rather than slipped in.
Option 1 is the most conservative. I have not implemented any of them.

## 4. Expression state (development)

Resolved empirically and **contrary to the metadata** — see
`representation.yaml`:

| Property | Finding |
|---|---|
| Log-transformed | **No** — values span 45.8 – 73,351.6 |
| Quantile-normalised | **No** — max abs difference between sorted columns 28,685.4 |
| Between-sample scale | per-sample medians 338.2 – 8,149.0 (~24×) |
| Detection p-values | present, per probe per sample |
| `probe_detection` | = fraction of probes with detection p **< 0.01**, reproduced to 6 d.p. on 5 arrays |
| Probe reconciliation | expression is a strict subset, 29,372 / 29,377; 0 orphans |

GEO's `!Sample_data_processing` says "normalised using Lumi for R"; that
describes the per-sample GSM `VALUE` column, **not** the supplementary matrix.
The usual error is logging twice — here the error would be trusting the
metadata and never normalising at all.

Detection is also not the same as presence: **1,600 of 29,372 probes (5.4%)
were never detected** at p<0.01 in any of 19 sampled arrays, and only 66.4%
were detected in more than half. A detection filter is therefore specified, to
be fitted on development training folds only.

## 5. Unresolved

1. **Alias resolution not performed** — 75.2% overlap is a lower bound, and the 2017-vs-2020 annotation gap inflates the apparent divergence.
2. **External expression not inspected.** Overlap here is computed from platform annotation, not from the external cohorts' actual matrices; genes annotated on GPL570 may still be undetected in GSE10846/GSE87371. The same detection logic should be applied there under a predeclared policy.
3. **Multi-probe collapse rule** (`median_of_probe_ranks`) is provisional and may be revised in Phase 4 **before** fitting. 5,719 of 20,818 development genes have multiple probes.
4. **B4's scope**, per §3 — the substantive open decision from this phase.
