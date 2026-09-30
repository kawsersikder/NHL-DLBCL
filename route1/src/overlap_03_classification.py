"""Record the per-paper classification of how overlapping GEO series were used.

Classes (assigned by reading the sentences extracted by overlap_02; one reviewer,
LLM; to be second-reviewed before any publication):
  C  cross-use: model trained/screened on one member of an overlapping pair and
     validated on the other (or a pooled overlapping set split into train/test)
  R  replication counting: overlapping series reported as separate independent
     validation/replication cohorts (no train/test leak, but inflated evidence)
  M  merged: overlapping series pooled without reported de-duplication
  N  not used as analysis cohorts (reviews, dataset lists, unrelated use)
  U  could not be classified (e.g. language)
Overlapping pairs (verified in overlap_01 at GSM/mAdbID level, or case-ID +
demographics for GSE4732): GSE10846-GSE11318, GSE10846-GSE53786,
GSE11318-GSE53786, GSE10846-GSE4732.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CLS = {
    0: ("C", "gene screening in GSE10846+GSE11318; nomogram 'confirmed in the GSE11318 datasets (validation dataset)'"),
    1: ("C", "train GSE10846; GSE11318 as external validation"),
    2: ("N", "review"), 3: ("R", "replication across six GEO sets incl. GSE10846 and GSE53786"),
    4: ("R", "train GSE181063; GSE10846 and GSE11318 as separate validation cohorts"),
    5: ("M", "846 samples pooled from GSE11318 + GSE10846 + GSE87371"),
    6: ("C", "model built on GSE53786; GSE10846 as 'independent validation'"),
    7: ("R", "survival association across GSE181063, GSE10846, GSE53786"),
    8: ("N", "narrative review"), 9: ("R", "GSE10846 and GSE53786 as separate external validation cohorts"),
    10: ("C", "train GSE10846; validation GSE53786"), 11: ("N", "discusses another group's signature"),
    12: ("C", "train GSE10846; validation GSE11318 and GSE53786 'external independent datasets'"),
    13: ("C", "train GSE10846; validation GSE11318 and GSE87371"),
    14: ("C", "train TCGA+GSE10846; validation GSE11318, GSE23501, GSE53786"),
    15: ("C", "GSE10846+GSE11318 pooled then split train/validation; external validation GSE53786"),
    16: ("R", "GSE10846 and a merged cohort containing GSE11318 used as separate cohorts"),
    17: ("R", "association across seven GEO sets incl. GSE10846, GSE11318, GSE53786"),
    18: ("C", "train GSE11318; 'independent validation in the GSE10846 cohort'"),
    19: ("C", "train GSE10846; validated in 'three independent GEO cohorts: GSE10846, GSE11318, and GSE87371' (mentions removing duplicate entries)"),
    20: ("N", "systematic review"), 21: ("R", "association across GSE10846, GSE11318 and others as 'independent' cohorts"),
    22: ("N", "dataset list"), 23: ("C", "train GSE10846; validation GSE53786 and GSE11318"),
    24: ("C", "train GSE10846; GSE11318 'independent external validation cohort'"),
    25: ("N", "review"), 26: ("C", "train GSE10846 (lncRNA); validation GSE11318"),
    27: ("C", "train GSE10846 'to prevent overfitting and data leakage'; external validation GSE11318"),
    28: ("U", "Chinese-language text; roles not classified"),
    29: ("R", "single-gene survival association in seven sets incl. GSE11318, GSE53786, GSE10846"),
    30: ("C", "train GSE11318; validation GSE10846 and GSE53786"),
    31: ("C", "model in GSE10846 (LOOCV); validated incl. GSE53786"),
    32: ("M", "classification study pooling GSE10846 + GSE11318 (460 patients)"),
    33: ("N", "uses GSE4732 only"), 34: ("C", "train GSE10846 (Lenz); evaluated in GSE53786 (Scott)"),
    35: ("C", "train GSE10846; validation incl. GSE53786 described as 'independent subset'"),
    36: ("C", "CHOP findings in GSE11318 then GSE10846 and GSE53786 as validation cohorts"),
    37: ("C", "discovery GSE10846 R-CHOP; validation incl. GSE53786"),
    38: ("N", "dataset list"), 39: ("N", "dataset listing; describes GSE53786 as 'FFPE R-CHOP cohort'"),
    40: ("C", "training datasets incl. GSE10846; GSE11318 among validation datasets"),
    41: ("N", "ABC/GCB reference set only"), 42: ("R", "train GSE31312; validation GSE10846 and GSE11318"),
    43: ("C", "training subset of GSE10846; validation 'entire set' and GSE11318"),
    44: ("R", "train GSE32918/GSE4475/GSE69051; GSE11318 and GSE10846 as separate independent validations"),
    45: ("C", "train GSE10846; external validation GSE4732 (n=174) - probable same patients, other platform"),
    46: ("R", "single gene across datasets incl. GSE10846 and GSE11318"),
    47: ("N", "database mining, roles unclear"), 48: ("N", "validation on GSE10846 only"),
    49: ("C", "train GSE10846; validation GSE11318 and GSE32918"), 50: ("N", "review"),
    51: ("C", "model on GSE10846 (412); validation sets GSE53786 and GSE181063 (probable)"),
    52: ("C", "train GSE11318 (split); external validation GSE10846"),
    53: ("R", "train GSE181063; GSE10846 and GSE53786 as separate validation cohorts"),
    54: ("C", "train GSE10846; validation GSE11318, GSE31312, GSE87371"),
    55: ("C", "train GSE11318+GSE57611; validation GSE10846"),
    56: ("R", "train GSE31312; validation GSE10846, GSE53786, GSE87371, GSE23501"),
    57: ("C", "snoRNA model trained in GSE11318; validation incl. GSE10846, GSE53786"),
    58: ("C", "train GSE10846; validation GSE11318, GSE87371, TCGA"),
}


def main() -> None:
    P = [p for p in json.load(open(ROOT / "data/raw/geo_brief/overlap_paper_roles.json", encoding="utf-8"))
         if p["status"] == "ok"]
    assert len(P) == len(CLS) == 59
    with open(ROOT / "manifests/overlap_literature_classification.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["idx", "pmcid", "pmid", "year", "journal_source", "title", "pairs_named",
                    "class", "rationale", "classifier"])
        for i, p in enumerate(P):
            c, why = CLS[i]
            w.writerow([i, p["pmcid"], p.get("pmid"), p.get("pubYear"), p.get("source"), p.get("title"),
                        ";".join(p["pairs"]), c, why, "LLM, single reviewer"])
    n = Counter(c for c, _ in CLS.values())
    used = len(CLS) - n["N"] - n["U"]
    print(dict(n), f"| papers using an overlapping pair as analysis cohorts: {used}")
    print(f"C cross-use {n['C']}/{used} = {n['C']/used:.0%}; any overlap misuse (C+R+M) "
          f"{n['C']+n['R']+n['M']}/{used}")


if __name__ == "__main__":
    main()
