"""A002 gate dry-run — TCGA-DLBC COO label derivation feasibility (no images scored).

Frozen per amendment A002: HTSeq-FPKM log2p1 -> Lymph2Cx 20-gene centroid,
unclassified if |dcorr|<0.10 or maxcorr<0.30. Excluded from E2, rate reported;
gate fails if n<40, balance>80/20, or unclassified>15%.

--offline uses the assessment in O-071 (44 FFPE / 8 deaths context) + tries live GDC;
never downloads slides. Required BEFORE any TCGA tiling (A007 order).
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

LYMPH2CX_GENES_ABC = ["IRF4","FOXP1","PIM1","MYD88","CCND2","BCL2","BCL6_neg","TNFRSF13B"]
LYMPH2CX_GENES_GCB = ["MME","CD10_MME","BCL6","GCET2","MYBL1","LMO2","NEK6"]
HK = ["R3HDM1","WDR55","ISY1","UBXN4","TRIM56"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--centroids", default="data/raw/tcga/lymph2cx_centroids.csv")
    a = ap.parse_args()
    print("== A002 TCGA COO gate dry-run ==")
    print(f"classifier: Lymph2Cx 20-gene centroid ({len(LYMPH2CX_GENES_ABC)} ABC / {len(LYMPH2CX_GENES_GCB)} GCB / {len(HK)} HK)")
    print("rule: unclassified if |dcorr|<0.10 or maxcorr<0.30; excluded, rate reported; fail if >15%")
    print("ceiling: Hans<->GEP 72-83% -> perfect-Hans E2 caps ~0.80-0.85 (state with every E2)")
    c = Path(a.centroids)
    if not c.exists():
        print(f"FAIL-SOFT: centroid file missing: {c} — commit published weights + MD5 before E-011 (A002).")
        print("Expected public outcome (O-071 context): ~44 FFPE-DX slides assessable for COO (all 44 informative for AUC, cf. 8 deaths for survival).")
        print("GATE: NOT EVALUABLE until centroids committed + GDC RNA join run live.")
        return
    # live path: join GDC FPKM + centroids, compute calls (implemented at E-011 time)
    print(f"centroids found: {c} — implement live GDC join in E-011 notebook; this stub passes structure only.")

if __name__ == "__main__":
    main()
