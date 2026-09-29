"""Signature-audit pilot, step 3: record the extraction and compute feasibility metrics.

Every value below was read from the source (Europe PMC full text for records
with a PMCID, otherwise the PubMed abstract) and is backed by the quoted
passage. Values were read by one reviewer (LLM, 17b1027d); the real registry
needs a human second reviewer. Opens no expression or outcome data.

Roles for our four cohorts: T = training/model fitting, S = gene screening used
for selection, V = reported validation, '' = not named.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OURS = ["GSE181063", "GSE31312", "GSE87371", "GSE10846"]

# draw, pmid, source, genes, complete, coef, roles{cohort: role}, other cohorts, quote, notes
REC = [
    (1, 39663278, "abstract", "", "N", "unknown", {}, "GEO + TCGA (unspecified)",
     "After developing a prognostic risk model using 5 hypoxia-related genes",
     "5 genes not named in abstract; no OA full text"),
    (4, 36302166, "abstract", "", "N", "n/a", {}, "BC Cancer real-world cohort (1,149)",
     "digital GEP to assign cell-of-origin and the so-called \"double-hit signature\" (DHITsig)",
     "evaluates an established classifier; gene list must come from the originating DHITsig paper"),
    (6, 38446321, "abstract", "", "N", "unknown", {}, "GEO (unspecified)",
     "An 8-gene ICD-related signature was identified and validated",
     "genes not named in abstract; no OA full text"),
    (9, 41934523, "fulltext", "RFC2;RFC4", "Y", "N (formula not in text)",
     {"GSE181063": "T", "GSE10846": "V", "GSE31312": "V"}, "TCGA-DLBC (mutation), GSE32018 (DE)",
     "the GSE181063 dataset served as the training set, while the GSE10846 and GSE31312 datasets were used as two independent validation sets",
     "median cut-off 2.12 stated but coefficients not in text"),
    (10, 35754837, "fulltext",
     "ANTXR1;CD3D;TIMP1;FPR3;NID2;CTLA4;LPAR6;GPR183;LYZ;PTGDS;ITK;FBN1;FRMD6;PLAU;MICAL2;C1S",
     "Y", "N (figure only)", {"GSE87371": "T", "GSE31312": "T", "GSE10846": "V"}, "TCGA-DLBC (47) in training",
     "TGCA database (n = 47), GSE87371 (n = 221) and GSE31312 (n = 470) was regarded as the training cohort. GSE10846 (n = 392) was regarded as the validation cohort",
     "risk score = sum Exp*Coe; coefficient values not in text"),
    (15, 25940947, "fulltext", "LIMD1;MYBL1", "Y", "n/a (Bayesian classifier)", {"GSE10846": "T"},
     "local cohort (88); GSE53786 (Scott, 68)",
     "we used the unselected samples from Lenz et al. dataset to train the Bayesian classifier",
     "DLBCL-1 = Lenz 414 (inferred from n and text). Source states the 68 Scott cases were 'drawn from the Lenz et al. dataset': GSE53786 overlaps GSE10846"),
    (19, 42715516, "abstract", "", "N", "n/a (nearest shrunken centroid, 294 genes)", {},
     "NCI/BCCA RNA-seq (764) training; POLARIX (678) application",
     "294 genes being optimal for classification using a nearest shrunken centroid classifier",
     "RNA-seq-trained classifier; gene list not in abstract; array transfer uncertain"),
    (20, 41142795, "fulltext", "TCF7;CEBPA;BBC3;GALR3;BMP8B;BAALC", "Y", "Y", {},
     "GSE11318 training; GSE32018/GSE107943 discovery; TCGA-DLBC validation",
     "risk score = (-0.26622943) x TCF7 expression level + (-0.285915897) x CEBPA",
     "GSE11318 and GSE10846 are both LLMPP series: possible patient overlap, UNVERIFIED; treated as excluding GSE10846 conservatively"),
    (23, 37716978, "fulltext", "HIF1A;CXCL2;CDH1;SPP1;PPARGC1A;PARVB;LYZ;S100A9", "Y", "Y", {"GSE10846": "T"},
     "GSE11318, GSE34171 validation",
     "GSE10846 (n = 400, GPL570) was used as the training dataset and divided into training and testing sets in a 7:3 ratio",
     "source spells PPARGC1A as 'PPARGCIA' (typo reconciled)"),
    (24, 36551263, "fulltext", "HTRA1;RBBP7;NFE2L2;SCAF11;ABL1;PAK2;CPTP;ADORA3", "Y", "Y", {"GSE10846": "T"},
     "GSE4475, TCGA validation",
     "we utilized a random 80% of GSE10846 as training set", ""),
    (26, 38091844, "abstract", "GAB1;GPR132 (partial)", "N", "unknown", {}, "three public datasets + a fourth (unnamed)",
     "R-IPI Poor patients with High levels of GAB1",
     "endpoints binarised at 12/36/60 months; full signature not in abstract"),
    (30, 40633211, "abstract", "", "N", "unknown", {}, "8 cohorts / 3,428 patients (unnamed)",
     "A 17-gene PCDS developed by machine learning", "genes and cohorts not named in abstract"),
    (31, 35774514, "fulltext", "BCL2;SPAG16;PXK;BTG1;LRRC37A2;EXT1;TGFBR2;ANKRD12;MYCBP2;PAX5;MYC", "Y",
     "N (sum beta*x; values not in text)", {"GSE31312": "T", "GSE10846": "V", "GSE87371": "V"}, "",
     "GSE31312 as the training data and the two other independent datasets, GSE10846 and GSE80371, as the external validation datasets",
     "source typo 'GSE80371' for GSE87371 (reconciled from later text)"),
    (32, 39311546, "abstract", "", "N", "unknown", {}, "unnamed",
     "We developed a prognostic immune-related gene pairs (IRGPs) signature", "nothing extractable from abstract"),
    (33, 40687219, "fulltext", "IL7R;TOX;TNFRSF9;RGS13;LYZ;TIMP1;TMEM123;RAC2;CCL3", "Y", "Y", {"GSE10846": "T"},
     "GSE4475 validation",
     "A random 50% of GSE10846 as training set was used to perform least absolute shrinkage and selection operator (LASSO) regression",
     "one sentence lists 8 of the 9 genes (omits TNFRSF9); formula has 9"),
    (35, 29097500, "fulltext", "MYC;BCL2", "Y", "n/a (0-4 points score with clinical factors)", {},
     "CCTG LY12 trial (NanoString)",
     "A bioclinical score using these four factors predicted outcome",
     "RELAPSED/REFRACTORY population and platform-specific thresholds: not transferable to first-line array cohorts"),
    (37, 42803950, "abstract", "IRF4;AKT1S1;PIEZO1;POLR1A;EML6;TTN;FCRL5;IGHG2", "Y", "unknown", {},
     "three bulk cohorts (unnamed)",
     "an eight-gene M-C2-associated panel comprising IRF4, AKT1S1, PIEZO1, POLR1A, EML6, TTN, FCRL5, and IGHG2",
     "GCB-only; cohorts unnamed so lineage unknown"),
    (38, 32228625, "fulltext", "", "N", "Y (on derived drug-resistance probabilities + clinical)",
     {"GSE31312": "T", "GSE10846": "V"}, "",
     "Dataset GSE31312 was used for train prognosis models, and GSE10846 was used to validate",
     "score uses drug-resistance probabilities, not a gene list"),
    (39, 35498426, "fulltext", "HK2;GAB1;RASAL1;CAPG;PDPN;GRPEL1;RCSD1;PLAC8L1", "Y", "Y",
     {"GSE10846": "S+V", "GSE31312": "S+V"}, "GSE117556 training; TCGA-NCICCR, local (45) validation",
     "we used univariate Cox analysis to screen genes related to the OS of DLBCL patients in the GSE117556, GSE10846, and GSE31312 datasets",
     "GSE117556 (REMoDL-B) shares lab and platform with GSE181063: patient overlap UNVERIFIED; source also writes 'GSE10864'"),
    (40, 41549103, "fulltext",
     "NEFL;GABRG1;DNM3;CACNB4;PLXNB3;SYNE1;RTN4;SULF1;PAFAH1B1;KEL;EGR2;MCF2;ALK;PSCA;DTNBP1;SEMA4F;TRPV2;MYO9A;LYPD1;GATA3;OXTR",
     "Y", "Y", {"GSE181063": "T", "GSE87371": "V"}, "GSE117556, NCICCR validation",
     "In the GSE181063 dataset, a total of 828 DLBCL patients treated with first-line R-CHOP chemotherapy were selected as the training cohort",
     ""),
]

# Conservative extra exclusions for UNVERIFIED cross-accession overlaps (see notes).
EXTRA_EXCLUDE = {20: {"GSE10846"}}
NOT_TRANSFERABLE = {35}


def eligible(draw, roles, rule):
    if draw in NOT_TRANSFERABLE:
        return []
    out = []
    for c in OURS:
        role = roles.get(c, "")
        if rule == "conservative" and role:
            continue
        if rule == "training_only" and ("T" in role or "S" in role):
            continue
        if c in EXTRA_EXCLUDE.get(draw, set()):
            continue
        out.append(c)
    return out


def main() -> None:
    with open(ROOT / "manifests" / "sig_pilot_extraction.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["draw_order", "pmid", "source", "n_genes", "genes", "gene_list_complete",
                    "coefficients_in_text", *[f"role_{c}" for c in OURS], "other_cohorts",
                    "lineage_known", "eligible_conservative", "eligible_training_only",
                    "quote", "notes", "extractor"])
        for d, pmid, src, genes, comp, coef, roles, other, quote, notes in REC:
            known = bool(roles) or d in (4, 19, 20, 35)
            scoreable = comp == "Y"
            ec = eligible(d, roles, "conservative") if (scoreable and known) else []
            et = eligible(d, roles, "training_only") if (scoreable and known) else []
            w.writerow([d, pmid, src, len(genes.split(";")) if comp == "Y" else "", genes, comp, coef,
                        *[roles.get(c, "") for c in OURS], other, "Y" if known else "N",
                        ";".join(ec), ";".join(et), quote, notes, "LLM, single reviewer"])

    n = len(REC)
    ft = sum(r[2] == "fulltext" for r in REC)
    comp = [r for r in REC if r[4] == "Y"]
    coef = [r for r in REC if r[5].startswith("Y")]
    known = [r for r in REC if r[6] or r[0] in (4, 19, 20, 35)]
    print(f"included {n} | OA full text {ft} | complete gene list {len(comp)} | coefficients in text {len(coef)}")
    print(f"lineage traceable for our four cohorts: {len(known)}")
    for c in OURS:
        touched = [r[0] for r in known if r[6].get(c)]
        print(f"  {c}: touched by {len(touched)}/{len(known)} traceable  {touched}")
    scor = [r for r in comp if r[0] in {k[0] for k in known}]
    for rule in ("conservative", "training_only"):
        per = {c: 0 for c in OURS}
        tot = 0
        for r in scor:
            e = eligible(r[0], r[6], rule)
            tot += len(e)
            for c in e:
                per[c] += 1
        print(f"{rule}: {tot} eligible signature x cohort pairs from {len(scor)} scoreable+traceable signatures; per cohort {per}")


if __name__ == "__main__":
    main()
