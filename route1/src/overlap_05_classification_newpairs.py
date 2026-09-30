"""Classify how papers use the scan-detected overlapping pairs (O-090).

Rubric as overlap_03 (C cross-use, R replication counting, M merged, N not
analysis cohorts, U unclassifiable), plus:
  D  cross-use WITH reported de-duplication of the shared samples (correct practice)
Overlap magnitude differs from O-089's pairs and is reported alongside:
  GSE181063 x GSE117556: 68 shared samples (5.2% / 7.3%)
  GSE10846  x GSE23501 :  4 shared samples (1.0% / 5.8%)
One reviewer (LLM); second review needed before publication.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CLS = {
    "GSE181063|GSE117556": {
        0: ("C", "train GSE181063 (828 R-CHOP); GSE117556 'independent validation cohort'"),
        1: ("R", "signature validated in GSE181063 and GSE117556 as separate independent cohorts"),
        2: ("R", "single-gene survival association in seven 'independent' GEO sets incl. both"),
        3: ("M", "GPL14951 sets GSE117556 and GSE181063 combined (SVA) for modelling"),
        4: ("M", "GSE117556 and GSE181063 'mixed into a single matrix file'"),
        5: ("R", "associations across seven 'independent' cohorts incl. both"),
        6: ("N", "systematic review"),
        7: ("C", "train GSE117556; GSE181063 as validation dataset"),
        8: ("M", "'all of DLBCL patients in GSE117556 and GSE181063 datasets were integrated into one dataset'"),
        9: ("R", "associations across seven GEO sets incl. both"),
        10: ("C", "training pool incl. GSE117556 (723) + GSE181063 (326); validation on 'remaining' GSE181063 (484)"),
        11: ("R", "validation in GSE181063 and GSE117556 separately"),
        12: ("R", "Cox meta-analysis across GEO sets incl. both"),
        13: ("U", "MHG vs DZsig comparison; per-cohort roles not extractable"),
        14: ("C", "classification (COO) model built on GSE181063; GSE117556 as external dataset - non-prognostic task"),
        15: ("N", "dataset list"),
        16: ("R", "survival analysis in GSE117556 repeated in 'independent datasets' incl. GSE181063"),
        17: ("U", "datasets listed; per-cohort roles not extractable"),
    },
    "GSE10846|GSE23501": {
        0: ("R", "validation sets GSE10846, GSE32918, GSE23501, GSE4475"),
        1: ("R", "GSE10846 and a merged cohort as separate cohorts"),
        2: ("M", "machine-learning model on combined datasets incl. GSE10846 and GSE23501"),
        3: ("C", "19-GPS trained on GSE19246 + GSE23501 (themselves sharing 37 samples); validated in GSE10846"),
        4: ("N", "systematic review"),
        5: ("C", "GSE23501 in DEG discovery; GSE10846 as 'independent validation'"),
        6: ("C", "train TCGA+GSE10846; external validation incl. GSE23501"),
        7: ("M", "677 patients pooled from GSE10846, GSE23501 and others"),
        8: ("N", "review"),
        9: ("C", "train GSE10846; external validation GSE4732 and GSE23501"),
        10: ("R", "train GSE31312; validation GSE10846, GSE53786, GSE87371, GSE23501"),
        11: ("N", "no GSE23501 analysis role"),
        12: ("N", "review"), 13: ("N", "review"),
        14: ("C", "train GSE10846; validation 'ComBatData' incl. GSE23501"),
        15: ("C", "train GSE10846; external validation combined GSE31312+GSE87371+GSE23501"),
        16: ("N", "dataset list"), 17: ("N", "database mining, roles unclear"),
        18: ("C", "discovery GSE10846; validation GSE32918, GSE53786, GSE23501"),
        19: ("N", "GSE23501 only in a dataset table"),
        20: ("N", "GSE23501 excluded; separately de-duplicates GSE32918/GSE69051 'common samples'"),
        21: ("D", "train GSE10846, test GSE23501; 'we used Spearman correlation to rule out duplicate samples' (4 removed)"),
        22: ("N", "narrative review"),
        23: ("R", "GSE10846 and GSE23501 as separate R-CHOP validation cohorts"),
        24: ("R", "serum-derived model validated in GSE10846, GSE32918, GSE23501"),
        25: ("N", "dataset listing"),
        26: ("C", "train Lenz R-CHOP (GSE10846); validation Lenz CHOP and Melnick (GSE23501)"),
        27: ("N", "review"),
        28: ("C", "GERS trained on GSE10846 (414); 'independent cohort of 69 patients' (GSE23501)"),
        29: ("R", "single gene across Lenz CHOP/R-CHOP, Hummel, Shaknovich cohorts"),
    },
}


def main() -> None:
    data = json.load(open(ROOT / "data/raw/geo_brief/overlap_newpairs_roles.json", encoding="utf-8"))
    rows, summary = [], {}
    for pair, cls in CLS.items():
        P = [p for p in data[pair] if p["status"] == "ok"]
        assert len(P) == len(cls), (pair, len(P), len(cls))
        for i, p in enumerate(P):
            c, why = cls[i]
            rows.append([pair, i, p["pmcid"], p.get("pmid"), p.get("pubYear"), p.get("title"), c, why,
                         "LLM, single reviewer"])
        n = Counter(c for c, _ in cls.values())
        users = n["C"] + n["R"] + n["M"] + n["D"]
        summary[pair] = {**n, "analysis_users": users, "not_open_access": sum(p["status"] == "not_open_access" for p in data[pair])}
        print(pair, dict(n), f"| analysis users {users} | de-duplicated {n['D']}/{users}")
    with open(ROOT / "manifests/overlap_literature_classification_newpairs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "idx", "pmcid", "pmid", "year", "title", "class", "rationale", "classifier"])
        w.writerows(rows)
    # union with the O-089 classification (distinct papers across all overlapping pairs)
    prev = list(csv.DictReader(open(ROOT / "manifests/overlap_literature_classification.csv", encoding="utf-8")))
    best = {}
    rank = {"C": 0, "M": 1, "R": 2, "D": 3, "U": 4, "N": 5}
    for r in prev:
        best[r["pmcid"]] = min(best.get(r["pmcid"], "N"), r["class"], key=rank.get)
    for r in rows:
        best[r[2]] = min(best.get(r[2], "N"), r[6], key=rank.get)
    u = Counter(best.values())
    users = u["C"] + u["R"] + u["M"] + u["D"]
    print(f"UNION distinct OA papers: {len(best)} | analysis users {users} | "
          f"worst-class counts {dict(u)} | any de-duplication {u['D']}")
    summary["union"] = {"distinct_papers": len(best), "analysis_users": users, **u}
    (ROOT / "manifests/overlap_literature_summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
