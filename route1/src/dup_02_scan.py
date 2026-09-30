"""Duplicate scan, step 2: outcome-blind expression-level duplicate detection.

Implements route1/reports/dup_scan_plan.md (frozen, commit 3123d56).

Parsing reads ONLY the sample accession / platform lines and the expression
table of each series matrix. Every !Sample_characteristics line (which carries
follow-up and status) is skipped without being stored.

Recorded deviations from the plan (fixed before the scan was run):
  D1  GPL14951 has no XIST probe, so DASL sex calls use chrY genes only.
  D2  Cross-version run (GPL8432 vs GPL14951) matches on shared ILMN probe IDs
      rather than gene symbols (no GPL8432 annotation needed), and takes its
      threshold from GSE32918-vs-other pairs only, because cross-version
      correlations are expected to be lower overall. Labelled EXPLORATORY.
  D3  GSE57611's matrix is GPL96, not GPL570 as listed. Per the plan it is
      analysed on its true platform: an EXPLORATORY cross-platform run against
      the GPL570 series on shared probe IDs (GPL96 IDs are a subset of GPL570),
      threshold from GSE57611-vs-other pairs, XIST/chrY sex probes as on GPL570.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SM = ROOT / "data" / "raw" / "series_matrix"
MAN = ROOT / "manifests"

SETS = {
    "GPL570": ["GSE10846", "GSE11318", "GSE53786", "GSE31312", "GSE87371", "GSE23501",
               "GSE19246", "GSE12195", "GSE34171", "GSE56315", "GSE57611"],
    "GPL14951": ["GSE181063", "GSE117556", "GSE69051"],
}
FILE = {"GSE11318": "GSE11318-GPL570", "GSE34171": "GSE34171-GPL570"}
SEX = {
    "GPL570": {"x": ["214218_s_at", "221728_x_at", "224588_at", "224589_at", "224590_at", "227671_at", "243712_at"],
               "y": ["201909_at", "205000_at", "205001_s_at", "1570359_at", "1570360_s_at",
                     "206700_s_at", "204409_s_at", "204410_at"]},
    "GPL14951": {"x": [], "y": ["ILMN_1783142", "ILMN_1732039", "ILMN_1685690", "ILMN_2228976", "ILMN_1755537"]},
}


def read_matrix(acc: str) -> tuple[pd.DataFrame, dict]:
    """Return (probes x samples) expression table and {gsm: platform}. Skips all characteristics."""
    name = FILE.get(acc, acc) + "_series_matrix.txt.gz"
    plats, gsms, table, inside = None, None, [], False
    with gzip.open(SM / name, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if inside:
                if line.startswith("!series_matrix_table_end"):
                    break
                table.append(line)
            elif line.startswith("!Sample_platform_id"):
                plats = [x.strip('"') for x in line.rstrip("\n").split("\t")[1:]]
            elif line.startswith("!Sample_geo_accession"):
                gsms = [x.strip('"') for x in line.rstrip("\n").split("\t")[1:]]
            elif line.startswith("!series_matrix_table_begin"):
                inside = True
            # every other line, including !Sample_characteristics_ch1, is ignored
    df = pd.read_csv(io.StringIO("".join(table)), sep="\t", index_col=0, na_values=["null", "NA", ""])
    df.index = df.index.astype(str)
    return df.apply(pd.to_numeric, errors="coerce"), dict(zip(gsms or [], plats or []))


def two_means(v: np.ndarray) -> np.ndarray:
    """Exact 1-D 2-means; returns boolean 'high' membership and the separation."""
    o = np.argsort(v)
    s = v[o]
    best, cut = np.inf, 1
    for k in range(1, len(s)):
        a, b = s[:k], s[k:]
        sse = ((a - a.mean()) ** 2).sum() + ((b - b.mean()) ** 2).sum()
        if sse < best:
            best, cut = sse, k
    high = np.zeros(len(v), bool)
    high[o[cut:]] = True
    return high


def build(dfs: dict[str, pd.DataFrame], feats: list[str], sex: dict) -> tuple:
    Zs, labels, sexcall = [], [], []
    for acc, df in dfs.items():
        x = df.loc[feats]
        rk = x.rank(axis=0).to_numpy(np.float32) / len(feats)            # (a) within-sample rank
        # sex score on ranks, before centring
        xi = [feats.index(p) for p in sex["x"] if p in feats]
        yi = [feats.index(p) for p in sex["y"] if p in feats]
        score = (rk[xi].mean(0) if xi else 0) - rk[yi].mean(0)
        female = two_means(np.asarray(score))
        res = rk - rk.mean(1, keepdims=True)                               # (b) centre within series
        res = (res - res.mean(0)) / res.std(0)                             # (c) z-score per sample
        Zs.append(res.T)
        labels += [(acc, g) for g in x.columns]
        sexcall += ["F" if f else "M" for f in female]
    return np.vstack(Zs).astype(np.float32), labels, sexcall


def scan(tag: str, dfs: dict[str, pd.DataFrame], sex: dict, threshold_from=None) -> dict:
    feats = sorted(set.intersection(*[set(df.dropna(axis=0).index) for df in dfs.values()]))
    Z, lab, sx = build(dfs, feats, sex)
    n, p = Z.shape
    R = (Z @ Z.T) / p
    ser = np.array([s for s, _ in lab])
    gsm = np.array([g for _, g in lab])
    iu = np.triu_indices(n, 1)
    same_gsm = gsm[iu[0]] == gsm[iu[1]]
    between = (ser[iu[0]] != ser[iu[1]]) & ~same_gsm
    if threshold_from is not None:
        between &= (ser[iu[0]] == threshold_from) | (ser[iu[1]] == threshold_from)
    vals = R[iu][between]
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med)))
    T = med + 10 * mad
    # best match outside own GSM (excludes self and identical-accession copies)
    Rb = R.copy()
    Rb[gsm[:, None] == gsm[None, :]] = -np.inf
    best = Rb.argmax(1)
    cand = []
    for i, j in zip(*iu):
        if gsm[i] == gsm[j] or R[i, j] < T:
            continue
        cand.append({
            "run": tag, "series_a": ser[i], "gsm_a": gsm[i], "series_b": ser[j], "gsm_b": gsm[j],
            "r": round(float(R[i, j]), 4), "robust_z": round((float(R[i, j]) - med) / mad, 1),
            "mutual_best": bool(best[i] == j and best[j] == i),
            "within_series": bool(ser[i] == ser[j]),
            "sex_a": sx[i], "sex_b": sx[j], "sex_agree": sx[i] == sx[j],
        })
    ident = R[iu][same_gsm]
    q = np.quantile(vals, [0.001, 0.01, 0.5, 0.99, 0.999, 0.9999])
    return {
        "tag": tag, "n_samples": int(n), "n_features": int(p),
        "series_n": dict(Counter(ser.tolist())),
        "between_median": med, "between_mad": mad, "threshold": T,
        "between_quantiles": dict(zip(["0.1%", "1%", "50%", "99%", "99.9%", "99.99%"], map(float, q))),
        "between_max": float(vals.max()),
        "identical_gsm_pairs": int(same_gsm.sum()),
        "identical_gsm_above_T": int((ident >= T).sum()),
        "identical_gsm_r_min": float(ident.min()) if len(ident) else None,
        "candidates": cand,
    }


def main() -> None:
    out, allc = {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                 "machine": platform.platform()}, []
    loaded = {}
    for plat, accs in SETS.items():
        dfs = {}
        for acc in accs:
            df, pmap = read_matrix(acc)
            keep = [c for c in df.columns if pmap.get(c, plat) == plat]
            dropped = len(df.columns) - len(keep)
            if df.shape[0] == 0 or not keep:
                print(f"{acc}: no usable expression table ({df.shape}); skipped")
                out.setdefault("skipped", []).append(acc)
                continue
            dfs[acc] = df[keep]
            loaded[acc] = dfs[acc]
            print(f"{plat} {acc:10s} {df.shape[0]:6d} probes x {len(keep):4d} samples (dropped {dropped} off-platform)")
        res = scan(plat, dfs, SEX[plat])
        out[plat] = {k: v for k, v in res.items() if k != "candidates"}
        allc += res["candidates"]
        print(f"  -> {res['n_features']} common features; threshold r >= {res['threshold']:.3f}; "
              f"candidates {len(res['candidates'])}")
    # exploratory cross-platform run: GSE57611 (GPL96) vs the GPL570 series
    df96, _ = read_matrix("GSE57611")
    dfs = {"GSE57611": df96, **{a: loaded[a] for a in SETS["GPL570"] if a in loaded}}
    res = scan("GPL96xGPL570", dfs, SEX["GPL570"], threshold_from="GSE57611")
    out["GPL96xGPL570"] = {k: v for k, v in res.items() if k != "candidates"}
    allc += [c for c in res["candidates"] if "GSE57611" in (c["series_a"], c["series_b"])]
    print(f"  -> GPL96 cross-platform: {res['n_features']} shared probes; threshold r >= {res['threshold']:.3f}; "
          f"GSE57611 candidates {sum('GSE57611' in (c['series_a'], c['series_b']) for c in res['candidates'])}")
    # exploratory cross-version run
    df32, pmap = read_matrix("GSE32918")
    dfs = {"GSE32918": df32, **{a: loaded[a] for a in SETS["GPL14951"] if a in loaded}}
    res = scan("GPL8432xGPL14951", dfs, SEX["GPL14951"], threshold_from="GSE32918")
    out["GPL8432xGPL14951"] = {k: v for k, v in res.items() if k != "candidates"}
    allc += [c for c in res["candidates"] if "GSE32918" in (c["series_a"], c["series_b"])]
    print(f"  -> cross-version: {res['n_features']} shared probes; threshold r >= {res['threshold']:.3f}; "
          f"GSE32918 candidates {sum('GSE32918' in (c['series_a'], c['series_b']) for c in res['candidates'])}")

    with open(MAN / "dup_scan_candidates.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(allc[0].keys()) if allc else ["run"])
        w.writeheader()
        w.writerows(allc)
    counts = defaultdict(lambda: [0, 0])
    for c in allc:
        k = (c["run"], *sorted([c["series_a"], c["series_b"]]))
        counts[k][0 if c["mutual_best"] else 1] += 1
    with open(MAN / "dup_scan_series_counts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["run", "series_a", "series_b", "primary_mutual_best", "secondary_threshold_only"])
        for k, v in sorted(counts.items()):
            w.writerow([*k, *v])
    # controls, as defined in the frozen plan: a "candidate" is the PRIMARY call
    # (threshold AND mutual best match). Threshold-only pairs are secondary and are
    # reported alongside, never counted as candidates. (Implementation correction:
    # the first run summarised the negative control over primary + secondary.)
    g10 = {c["gsm_b"] if c["series_a"] == "GSE23501" else c["gsm_a"] for c in allc
           if c["run"] == "GPL570" and c["mutual_best"] and "GSE23501" in (c["series_a"], c["series_b"])}
    ident10 = set(loaded["GSE10846"].columns)
    pc2 = [c for c in allc if c["run"] == "GPL570" and c["mutual_best"]
           and "GSE23501" in (c["series_a"], c["series_b"])
           and (c["gsm_b"] if c["series_a"] == "GSE23501" else c["gsm_a"]) in ident10]
    def n_pair(a, b, primary=True):
        return sum(1 for c in allc if {c["series_a"], c["series_b"]} == {a, b} and c["mutual_best"] == primary)
    prim = [c for c in allc if c["mutual_best"]]
    out["controls"] = {
        "PC1_identical_gsm_above_threshold": {k: (out[k]["identical_gsm_above_T"], out[k]["identical_gsm_pairs"])
                                              for k in out if isinstance(out.get(k), dict) and "identical_gsm_pairs" in out[k]},
        "PC2_distinct_GSE23501_primary_matched_to_a_GSE10846_gsm": len({(c["gsm_a"], c["gsm_b"]) for c in pc2}),
        "PC2_of_which_r_ge_0.9": sum(c["r"] >= 0.9 for c in pc2),
        "NC_GSE87371xGSE10846_primary": n_pair("GSE87371", "GSE10846"),
        "NC_GSE87371xGSE10846_secondary": n_pair("GSE87371", "GSE10846", False),
        "sex_agreement_primary_between_series": [sum(c["sex_agree"] for c in prim if not c["within_series"]),
                                                 sum(1 for c in prim if not c["within_series"])],
        "sex_agreement_primary_within_series": [sum(c["sex_agree"] for c in prim if c["within_series"]),
                                                sum(1 for c in prim if c["within_series"])],
    }
    (MAN / "dup_scan_summary.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out["controls"], indent=2))


if __name__ == "__main__":
    main()
