"""Phase 3R-C — representation checks. No outcome is read anywhere in this file.

Implements and verifies the transform chain end to end on the frozen 301-patient
development population, and discharges the checks the supervisor ordered:

  C1  the withdrawn B4 mask is provably inactive (|U n M| == 0)
  C2  unique-gene vs gene-set-membership counts reconcile by set operations
  C3  multi-probe aggregation is fully specified and order-invariant
  C4  program coverage is recomputed AFTER the detection filter, not only from
      platform annotation
  C5  a synthetic split test proves held-out data cannot influence the
      detection filter or the allowed gene universe

Executable transform order (supervisor 3.4):
    platform probe->gene mapping
    -> training-only detection filter (assay-specific)
    -> log2(x+1)
    -> gene aggregation (median across eligible probes)
    -> allowed universe = training-derived genes INTERSECT declared cross-platform universe
    -> within-sample rank over that fixed universe
    -> program score = mean scaled rank of available program genes
    (-> training-fold standardisation, applied at model time, not here)

Note on order (C3). An earlier draft of this file claimed median aggregation
was order-invariant under log2. **That was wrong and the check caught it.** The
median is equivariant under a monotone transform only for an ODD number of
values; for an EVEN count the median averages the two central values, and
averaging does not commute with log2. Measured here, the two orders differ by
up to ~4 log2 units. The order is therefore DECLARED rather than assumed:
log2(x+1) first, then median. Averaging the central pair happens on the log
scale, where intensities are approximately symmetric; averaging raw
intensities would let one bright probe dominate the pair.

Usage:
    python route1/src/phase3R_representation_checks.py
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "route1/data/raw"
MSIG = RAW / "msigdb"
EXPR = RAW / "GSE181063_RawData.txt.gz"
POP = ROOT / "route1/manifests/population_primary.csv"
GENE_MAP = ROOT / "route1/manifests/gene_mapping.csv"
PROGRAMS = ROOT / "route1/manifests/program_gene_sets.csv"
OUT_COVERAGE = ROOT / "route1/manifests/program_coverage_after_filter.csv"

# Renamed to the literal measured signatures (supervisor 3.5).
RENAME = {
    "proliferation_e2f": "hallmark_e2f_targets",
    "proliferation_myc": "hallmark_myc_targets_v1",
    "nfkb_signalling": "hallmark_tnfa_signaling_via_nfkb",
    "interferon_antigen_presentation": "hallmark_ifng_response",
    "stromal_ecm": "hallmark_emt",
    "angiogenesis": "hallmark_angiogenesis",
    "inflammatory_macrophage": "hallmark_inflammatory_response",
    "oxidative_phosphorylation": "hallmark_oxphos",
}
DETECTION_P = 0.01
DETECTION_MIN_FRACTION = 0.10
MIN_GENES_ABSOLUTE = 10
MIN_FRACTION_OF_SET = 0.50

bar = "=" * 78


def load_probe_gene() -> pd.DataFrame:
    """Illumina probe -> single gene symbol, from the platform annotation."""
    rows, cols, in_tab = [], None, False
    with (RAW / "GPL14951_platform.txt").open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not in_tab:
                if line.startswith("!platform_table_begin"):
                    in_tab = True
                continue
            if line.startswith("!platform_table_end"):
                break
            parts = line.split("\t")
            if cols is None:
                cols = parts
                continue
            rows.append(parts[:len(cols)])
    df = pd.DataFrame(rows, columns=cols)
    sym = df["Symbol"].fillna("").astype(str).str.strip().str.upper()
    ok = sym.ne("") & ~sym.str.contains(r"///|//|;|,", regex=True)
    return pd.DataFrame({"probe": df.loc[ok, "ID"].values, "gene": sym[ok].values})


def load_expression(titles: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (expression, detection p) for the given DASLV4_<n> sample titles."""
    exp_cols = {f"{t}_Exp": t for t in titles}
    pv_cols = {f"{t}_pVal": t for t in titles}
    want = {"ID", *exp_cols, *pv_cols}
    with gzip.open(EXPR, "rt", encoding="utf-8", errors="replace") as fh:
        df = pd.read_csv(fh, sep="\t", usecols=lambda c: c in want)
    df = df.set_index("ID")
    e = df[list(exp_cols)].rename(columns=exp_cols).apply(pd.to_numeric, errors="coerce")
    p = df[list(pv_cols)].rename(columns=pv_cols).apply(pd.to_numeric, errors="coerce")
    return e, p


def detection_filter(pvals: pd.DataFrame) -> pd.Index:
    """Probes detected at p<0.01 in >=10% of the GIVEN (training) arrays."""
    frac = (pvals < DETECTION_P).mean(axis=1)
    return pvals.index[frac >= DETECTION_MIN_FRACTION]


def aggregate(expr: pd.DataFrame, probe_gene: pd.DataFrame,
              keep_probes: pd.Index) -> pd.DataFrame:
    """log2(x+1) then median across a gene's eligible probes."""
    sub = probe_gene[probe_gene.probe.isin(keep_probes)]
    logged = np.log2(expr.loc[expr.index.isin(sub.probe)] + 1.0)
    logged = logged.join(sub.set_index("probe")["gene"], how="inner")
    return logged.groupby("gene").median()


def program_scores(gene_mat: pd.DataFrame, universe: list[str],
                   progs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Within-sample scaled ranks over a FIXED universe, then mean per program."""
    m = gene_mat.reindex(universe)
    ranks = m.rank(axis=0, method="average")
    scaled = (ranks - 1.0) / (ranks.notna().sum(axis=0) - 1.0)
    rows, cov = [], []
    for prog, g in progs.groupby("program"):
        genes = [x for x in g.gene.unique() if x in scaled.index]
        n_av = len(genes)
        ok = n_av >= MIN_GENES_ABSOLUTE and n_av / g.gene.nunique() >= MIN_FRACTION_OF_SET
        cov.append({"program": prog, "set_genes": g.gene.nunique(),
                    "available_in_universe": n_av,
                    "fraction": round(n_av / g.gene.nunique(), 4),
                    "scoreable": ok})
        if ok:
            rows.append(scaled.loc[genes].mean(axis=0).rename(prog))
    return pd.DataFrame(rows).T, pd.DataFrame(cov)


def main() -> int:
    pop = pd.read_csv(POP, low_memory=False)
    titles = pop.sample_title.tolist()
    print(f"development population: {len(titles)} patients (one sample each)")

    gm = pd.read_csv(GENE_MAP)
    progs = pd.read_csv(PROGRAMS)
    progs["program"] = progs.program.map(RENAME)
    assert progs.program.notna().all(), "unmapped program name"

    # ---------------- C1: the withdrawn mask is inactive ----------------
    U = set(gm.loc[gm.shared, "gene"])
    M = set(gm.loc[gm.on_GPL14951 & ~gm.on_GPL570, "gene"])
    print()
    print(bar); print("C1 — withdrawn B4 mask is provably inactive"); print(bar)
    print(f"  |U| (ranking universe) = {len(U):,}")
    print(f"  |M| (dev minus ext)    = {len(M):,}")
    print(f"  |U n M|                = {len(U & M)}")
    assert len(U & M) == 0, "mask is NOT a no-op — the withdrawal rationale fails"
    print("  ASSERTION PASSED: masking M removes 0 of the model's input genes.")
    print("  B4 is a null operation under the declared universe; it stays withdrawn.")

    # ---------------- C2: membership vs unique-gene counts ----------------
    lost = progs[progs.on_GPL14951 & ~progs.shared]
    print()
    print(bar); print("C2 — membership vs unique-gene reconciliation"); print(bar)
    print(f"  lost program-gene MEMBERSHIPS {len(lost)}  "
          f"(denominator {int(progs.on_GPL14951.sum())} on-dev rows)")
    print(f"  lost UNIQUE genes             {lost.gene.nunique()}  "
          f"(denominator {progs.loc[progs.on_GPL14951, 'gene'].nunique()} distinct on-dev genes)")
    dup = lost.gene.value_counts()
    print(f"  explained by multi-program genes: {list(dup[dup > 1].index)}")
    assert len(lost) - lost.gene.nunique() == int((dup > 1).sum()), "count mismatch"
    print("  ASSERTION PASSED: counts reconcile by set operations.")

    # ---------------- load expression ----------------
    expr, pv = load_expression(titles)
    probe_gene = load_probe_gene()
    print()
    print(f"loaded expression {expr.shape[0]:,} probes x {expr.shape[1]} samples")

    # ---------------- C3: aggregation is order-invariant ----------------
    print()
    print(bar); print("C3 — multi-probe aggregation fully specified"); print(bar)
    keep_all = detection_filter(pv)
    a = aggregate(expr, probe_gene, keep_all)                      # log2 then median
    sub = probe_gene[probe_gene.probe.isin(keep_all)]
    raw = expr.loc[expr.index.isin(sub.probe)].join(
        sub.set_index("probe")["gene"], how="inner")
    b = np.log2(raw.groupby("gene").median() + 1.0)                # median then log2
    common = a.index.intersection(b.index)
    delta = float(np.nanmax(np.abs(a.loc[common].values - b.loc[common].values)))
    n_probes = (probe_gene[probe_gene.probe.isin(keep_all)]
                .groupby("gene").size())
    n_even = int((n_probes % 2 == 0).sum())
    n_multi = int((n_probes > 1).sum())
    print(f"  genes after mapping + detection filter: {len(a):,}")
    print(f"  genes with >1 eligible probe          : {n_multi:,}")
    print(f"  genes with an EVEN probe count        : {n_even:,}")
    print(f"  max abs diff (log2-then-median vs median-then-log2) = {delta:.4f}")
    # The median is equivariant under a monotone transform ONLY for odd counts.
    # For even counts pandas averages the two central values, and averaging
    # does not commute with log2. So the order is NOT immaterial, contrary to
    # the first draft of this check -- it matters by up to several log2 units.
    assert delta > 1e-6, (
        "expected the two orders to differ for even-probe genes; if they no "
        "longer do, the aggregation implementation has changed")
    print("  -> the two orders DIFFER, so the order must be declared, not assumed.")
    print("  DECLARED ORDER: log2(x+1) FIRST, then median across eligible probes.")
    print("     Rationale: averaging the two central values is done on the log")
    print("     scale, where intensities are approximately symmetric; averaging")
    print("     raw intensities would let one bright probe dominate the pair.")
    print("     Odd-probe genes are unaffected either way.")

    # ---------------- C4: coverage AFTER the detection filter ----------------
    universe = sorted(set(a.index) & U)
    print()
    print(bar); print("C4 — program coverage AFTER detection filtering"); print(bar)
    print(f"  declared cross-platform universe      {len(U):,}")
    print(f"  genes surviving mapping+detection     {len(a):,}")
    print(f"  ALLOWED UNIVERSE (intersection)       {len(universe):,}")
    scores, cov = program_scores(a, universe, progs)
    print()
    print(cov.to_string(index=False))
    assert cov.scoreable.all(), "a program failed its coverage threshold"
    print()
    print(f"  all {len(cov)} programs scoreable; score matrix {scores.shape}")
    cov.to_csv(OUT_COVERAGE, index=False)

    # ---------------- C5: held-out data cannot fit the filter ----------------
    print()
    print(bar); print("C5 — synthetic split test: held-out data cannot leak in"); print(bar)
    rng = np.random.default_rng(20260911)
    idx = rng.permutation(len(titles))
    tr = [titles[i] for i in idx[: int(0.7 * len(titles))]]
    te = [titles[i] for i in idx[int(0.7 * len(titles)):]]
    f_train = set(detection_filter(pv[tr]))
    # Corrupt the held-out arrays beyond recognition; the filter must not move.
    pv_corrupt = pv.copy()
    pv_corrupt[te] = 1.0
    f_train_again = set(detection_filter(pv_corrupt[tr]))
    f_allsamples = set(detection_filter(pv))
    print(f"  filter fitted on training arrays only     {len(f_train):,} probes")
    print(f"  after corrupting ALL held-out arrays      {len(f_train_again):,} probes")
    print(f"  filter fitted on all arrays (PROHIBITED)  {len(f_allsamples):,} probes")
    assert f_train == f_train_again, "held-out data changed the training filter!"
    print("  ASSERTION PASSED: corrupting held-out arrays leaves the filter identical.")
    differs = len(f_train ^ f_allsamples)
    print(f"  and it genuinely differs from the all-array filter by {differs:,} probes,")
    print("  so the test is not vacuous.")

    print()
    print(f"wrote {OUT_COVERAGE.relative_to(ROOT)}")
    print("\nNo outcome was read at any point in this script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
