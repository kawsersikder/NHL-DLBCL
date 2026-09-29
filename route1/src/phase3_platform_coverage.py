"""Phase 3 — characterise expression platforms and measure program coverage.

Measures the premise the whole study rests on and which has so far only been
asserted: how much of each biological program actually survives the move from
Illumina WG-DASL HT v4 (GPL14951, development) to Affymetrix HG-U133 Plus 2.0
(GPL570, all three validation candidates).

Nothing here touches expression values or outcomes. It reads only the two
platform annotation tables and the eight MSigDB gene sets, so the entire
representation is defined before any expression matrix is opened — which is the
point: probe-to-gene rules chosen after seeing expression, or gene sets chosen
after seeing outcome, are the failure modes the plan forbids.

Probe-to-gene rule (deterministic, outcome-independent, identical per platform):
  * A probe maps to a gene iff the platform's own annotation names exactly one
    gene symbol for it. Probes naming several genes are recorded as
    ``multi_mapping`` and EXCLUDED -- they cannot be attributed to one program.
  * A gene is "measured" on a platform iff at least one non-multi-mapping probe
    maps to it. Genes with several probes are recorded with that count; how
    several probes are collapsed to one gene value is a Phase 4 decision and is
    NOT made here.
  * Symbols are compared verbatim, uppercased and whitespace-stripped. No
    synonym resolution or alias expansion is performed, because an alias table
    is itself a versioned dependency that would need its own provenance. The
    consequence -- overlap is a LOWER BOUND -- is reported rather than hidden.

Usage:
    python route1/src/phase3_platform_coverage.py
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "route1/data/raw"
MSIG = RAW / "msigdb"
OUT_GENES = ROOT / "route1/manifests/gene_mapping.csv"
OUT_PROGRAMS = ROOT / "route1/manifests/program_gene_sets.csv"

PLATFORMS = {
    "GPL14951": RAW / "GPL14951_platform.txt",   # Illumina WG-DASL HT v4
    "GPL570": RAW / "GPL570_platform.txt",       # Affymetrix HG-U133 Plus 2.0
}

# Candidate gene-symbol columns, most specific first. Auto-detected per
# platform and REPORTED, so the choice is visible rather than assumed.
SYMBOL_COLUMNS = ["Gene Symbol", "Symbol", "GENE_SYMBOL", "ILMN_Gene",
                  "Gene symbol", "gene_symbol"]

# program -> MSigDB set. Hallmark only: platform-neutral, consistently curated,
# and NOT derived from any DLBCL cohort used in this study. Signatures such as
# Rosenwald 2002 and Lenz 2008 Stromal-1/2 were deliberately rejected because
# they were derived on LLMPP data -- the GSE10846 lineage -- which would make
# that cohort non-independent for the programs as well as for COO.
PROGRAMS = {
    "proliferation_e2f": "HALLMARK_E2F_TARGETS",
    "proliferation_myc": "HALLMARK_MYC_TARGETS_V1",
    "nfkb_signalling": "HALLMARK_TNFA_SIGNALING_VIA_NFKB",
    "interferon_antigen_presentation": "HALLMARK_INTERFERON_GAMMA_RESPONSE",
    "stromal_ecm": "HALLMARK_EPITHELIAL_MESENCHYMAL_TRANSITION",
    "angiogenesis": "HALLMARK_ANGIOGENESIS",
    "inflammatory_macrophage": "HALLMARK_INFLAMMATORY_RESPONSE",
    "oxidative_phosphorylation": "HALLMARK_OXIDATIVE_PHOSPHORYLATION",
}

MULTI_SPLIT = re.compile(r"\s*(?:///|//|;|,)\s*")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_platform_table(path: Path) -> tuple[pd.DataFrame, dict[str, str]]:
    """Extract the SOFT platform table and the header fields around it."""
    header: dict[str, str] = {}
    rows: list[list[str]] = []
    cols: list[str] | None = None
    in_table = False
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not in_table:
                if line.startswith("!platform_table_begin"):
                    in_table = True
                    continue
                m = re.match(r"^!(Platform_\w+) = (.*)$", line)
                if m and m.group(1) != "Platform_sample_id":
                    header.setdefault(m.group(1), m.group(2))
                continue
            if line.startswith("!platform_table_end"):
                break
            parts = line.split("\t")
            if cols is None:
                cols = parts
                continue
            # Ragged rows are common in GEO annotation dumps; pad rather than drop.
            if len(parts) < len(cols):
                parts += [""] * (len(cols) - len(parts))
            rows.append(parts[:len(cols)])
    if cols is None:
        raise ValueError(f"no platform table found in {path}")
    return pd.DataFrame(rows, columns=cols), header


def pick_symbol_column(df: pd.DataFrame) -> str:
    for c in SYMBOL_COLUMNS:
        if c in df.columns:
            return c
    raise KeyError(
        f"no gene-symbol column found; available columns: {list(df.columns)[:40]}")


def map_platform(name: str, path: Path) -> tuple[pd.DataFrame, dict]:
    """Return per-gene probe counts for one platform, plus a summary."""
    df, header = read_platform_table(path)
    sym_col = pick_symbol_column(df)
    id_col = df.columns[0]

    sym = df[sym_col].fillna("").astype(str).str.strip()
    n_total = len(df)
    n_blank = int((sym == "").sum())

    split = sym.map(lambda s: [p for p in MULTI_SPLIT.split(s) if p] if s else [])
    n_multi = int(split.map(len).gt(1).sum())

    single = split.map(lambda parts: parts[0].upper() if len(parts) == 1 else None)
    ok = single.notna()
    genes = (pd.DataFrame({"gene": single[ok], "probe": df.loc[ok, id_col]})
             .groupby("gene", as_index=False)
             .agg(n_probes=("probe", "size")))

    summary = {
        "platform": name,
        "title": header.get("Platform_title", ""),
        "technology": header.get("Platform_technology", ""),
        "last_update": header.get("Platform_last_update_date", ""),
        "symbol_column": sym_col,
        "probes_total": n_total,
        "probes_blank_symbol": n_blank,
        "probes_multi_mapping_excluded": n_multi,
        "probes_usable": int(ok.sum()),
        "genes_measured": len(genes),
        "sha256": sha256(path),
    }
    return genes, summary


def load_programs() -> pd.DataFrame:
    rows = []
    for prog, setname in PROGRAMS.items():
        path = MSIG / f"{setname}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload[setname]
        for g in meta["geneSymbols"]:
            rows.append({
                "program": prog,
                "gene_set": setname,
                "systematic_name": meta.get("systematicName", ""),
                "collection": meta.get("collection", ""),
                "pmid": meta.get("pmid", ""),
                "source_sha256": sha256(path)[:16],
                "gene": g.strip().upper(),
            })
    return pd.DataFrame(rows)


def main() -> int:
    missing = [n for n, p in PLATFORMS.items() if not p.exists()]
    if missing:
        raise FileNotFoundError(f"platform annotation not downloaded: {missing}")

    per_platform, summaries = {}, []
    for name, path in PLATFORMS.items():
        genes, summary = map_platform(name, path)
        per_platform[name] = genes
        summaries.append(summary)

    bar = "=" * 78
    print(bar); print("PLATFORM ANNOTATION"); print(bar)
    for s in summaries:
        print(f"\n{s['platform']} — {s['title']}")
        print(f"  technology       {s['technology']}")
        print(f"  annotation dated {s['last_update']}")
        print(f"  symbol column    {s['symbol_column']!r}")
        print(f"  probes total     {s['probes_total']:,}")
        print(f"    blank symbol   {s['probes_blank_symbol']:,}")
        print(f"    multi-mapping  {s['probes_multi_mapping_excluded']:,}  (excluded)")
        print(f"    usable         {s['probes_usable']:,}")
        print(f"  GENES MEASURED   {s['genes_measured']:,}")

    a, b = per_platform["GPL14951"], per_platform["GPL570"]
    sa, sb = set(a.gene), set(b.gene)
    shared = sa & sb
    print()
    print(bar); print("CROSS-PLATFORM GENE OVERLAP  (lower bound: no alias resolution)")
    print(bar)
    print(f"  GPL14951 only   {len(sa - sb):,}")
    print(f"  GPL570 only     {len(sb - sa):,}")
    print(f"  SHARED          {len(shared):,}")
    print(f"  shared / GPL14951 = {len(shared) / len(sa):.1%}")

    # Per-gene manifest across both platforms.
    gm = (a.rename(columns={"n_probes": "n_probes_GPL14951"})
          .merge(b.rename(columns={"n_probes": "n_probes_GPL570"}),
                 on="gene", how="outer")
          .fillna({"n_probes_GPL14951": 0, "n_probes_GPL570": 0}))
    gm["on_GPL14951"] = gm.n_probes_GPL14951 > 0
    gm["on_GPL570"] = gm.n_probes_GPL570 > 0
    gm["shared"] = gm.on_GPL14951 & gm.on_GPL570

    progs = load_programs()
    progs["on_GPL14951"] = progs.gene.isin(sa)
    progs["on_GPL570"] = progs.gene.isin(sb)
    progs["shared"] = progs.on_GPL14951 & progs.on_GPL570
    gm["in_any_program"] = gm.gene.isin(set(progs.gene))

    print()
    print(bar); print("PROGRAM COVERAGE — this is the platform-robustness premise")
    print(bar)
    cov = (progs.groupby(["program", "gene_set", "systematic_name"])
           .agg(genes=("gene", "size"),
                on_dev=("on_GPL14951", "sum"),
                on_ext=("on_GPL570", "sum"),
                shared=("shared", "sum"))
           .reset_index())
    cov["dev_pct"] = (cov.on_dev / cov.genes * 100).round(1)
    cov["shared_pct"] = (cov.shared / cov.genes * 100).round(1)
    # Genes measured on development but LOST when moving to the external
    # platform: the realistic, non-random coverage perturbation for B4.
    cov["lost_moving_to_ext"] = cov.on_dev - cov.shared
    print(cov[["program", "genes", "on_dev", "dev_pct", "shared", "shared_pct",
               "lost_moving_to_ext"]].to_string(index=False))

    OUT_GENES.parent.mkdir(parents=True, exist_ok=True)
    gm.to_csv(OUT_GENES, index=False)
    progs.to_csv(OUT_PROGRAMS, index=False)
    pd.DataFrame(summaries).to_csv(
        ROOT / "route1/manifests/platform_summary.csv", index=False)
    print()
    print(f"wrote {OUT_GENES.relative_to(ROOT)}  ({len(gm):,} genes)")
    print(f"wrote {OUT_PROGRAMS.relative_to(ROOT)}  ({len(progs):,} program-gene rows)")
    print(f"wrote route1/manifests/platform_summary.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
