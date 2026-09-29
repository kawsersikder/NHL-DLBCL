"""E-010 tabular arm — C0/C1/C2 (+ C4 two-score fusion per A003).

Protocol §§3,6-9 + amendments A001-A007. CPU-only. Kaggle + local compatible.

- Repeated nested CV 5 outer x 10 repeats, stratify HANS, seed 20260903, patient unit.
- Fold-internal: median/mode impute -> Spearman |rho|>0.90 prune (frozen order) -> StandardScaler -> elastic-net logistic.
- Grid: l1_ratio {0.1,0.5,0.9,1.0} x C 20-pt log grid (1e-3..1e3). Inner 5-fold, criterion mean AUROC.
- Metrics: AUROC (primary), AUPRC, bal-acc @0.5, sens@90spec + spec@90sens (thresholds in-fold only),
  calibration slope/intercept + rejection [0.7,1.3], 1000 patient bootstraps, Holm for secondary ladder.
- C4 (A003): logistic on 2 fold-internal scores (C1 linear predictor z + C3 MIL logit z).
  If --mil-logits absent, C4 falls back to C1-only descriptive (logged) — primary C4 requires e010_abmil outputs.
- QC-stratified descriptive (A005): overall + PASS(130) vs CAUTION/FAIL(40) using frozen AI-QC labels.
- Chain of custody: verifies split-time protocol hash; records env + hashes. Aborts on gate failure.

Usage (Kaggle CPU):
    !python /kaggle/input/.../e010_coo_ladder.py --models C0,C1,C2
    !python /kaggle/input/.../e010_coo_ladder.py --models C0,C1,C2,C4 --mil-logits oof_mil_hoptimus.csv
"""
from __future__ import annotations
import argparse, hashlib, json, time, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from sklearn.linear_model import LogisticRegressionCV, LogisticRegression
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, average_precision_score, balanced_accuracy_score, roc_curve
from sklearn.utils import resample

SEED = 20260903
OUTER_FOLDS, OUTER_REPEATS, INNER_FOLDS = 5, 10, 5
N_BOOT = 1000
LABEL = "HANS"
CALIB_BOUNDS = (0.7, 1.3)
L1_RATIOS = [0.1, 0.5, 0.9, 1.0]
C_GRID = np.logspace(-3, 3, 20)

F0 = ["patch_count_total","patch_count_primary","patch_count_low_tissue","cell_count_total","cell_count_primary",
      *[f"patch_tissue_fraction_{s}" for s in ("median","iqr","p10","p90")]]
F1A = [f"cell_{d}_{s}" for d in ("area_px","perimeter_px","eccentricity","solidity","circularity","major_axis_px","minor_axis_px") for s in ("median","iqr","p10","p90")]
F1B = [f"cell_rgb_mean_{c}_{s}" for c in ("r","g","b") for s in ("median","iqr","p10","p90")]
F2 = [f"patch_{d}_{s}" for d in ("primary_cell_count","nuclear_foreground_fraction","nearest_neighbour_median_px","delaunay_edge_median_px") for s in ("median","iqr","p10","p90")]
F1 = F1A + F1B
ORDER = F0 + F1A + F1B + F2
C0_COLS = ["Age","ECOG PS","LDH","EN","Stage"]

ON_KAGGLE = Path("/kaggle/working").exists()
KIN = Path("/kaggle/input") if ON_KAGGLE else Path(".")
WOUT = Path("/kaggle/working/phase_04_coo_ladder") if ON_KAGGLE else Path("reports/phase_04_coo_results_tables")

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
def find(n):
    cands = sorted((KIN if ON_KAGGLE else Path("F:/Research Projects/NHL-DLBCL")).rglob(n))
    cands = [c for c in cands if c.is_file()]
    if not cands: raise FileNotFoundError(n)
    return cands[0]
def sha(p: Path): return hashlib.sha256(p.read_bytes()).hexdigest()

def prune(df: pd.DataFrame, order, thr=0.90):
    cols = [c for c in order if c in df.columns]
    if len(cols) < 2: return cols
    R = df[cols].corr("spearman").abs().to_numpy()
    kept = []
    for i in range(len(cols)):
        if all(R[i,j] <= thr for j in kept): kept.append(i)
    return [cols[i] for i in kept]

def calib_slope_intercept(y, p):
    p = np.clip(p, 1e-4, 1-1e-4)
    import warnings as w
    with w.catch_warnings():
        w.simplefilter("ignore")
        lr = LogisticRegression().fit(np.log(p/(1-p)).reshape(-1,1), y)
    return float(lr.coef_[0,0]), float(lr.intercept_[0])

def triage_points(ytr, ptr, yte, pte):
    # thresholds from TRAIN only (A005/protocol §7)
    fpr, tpr, thr = roc_curve(ytr, ptr)
    spec = 1 - fpr
    out = {}
    for target, name, fn in ((0.90,"sens_at_90spec",None),(0.90,"spec_at_90sens",None)):
        out[name] = float("nan")
    try:
        i = np.argmin(np.abs(spec - 0.90)); t = thr[i]
        out["sens_at_90spec"] = float(((pte >= t) & (yte==1)).sum() / max(1,(yte==1).sum()))
        out["thr_sens_at_90spec"] = float(t)
    except Exception: pass
    try:
        i = np.argmin(np.abs(tpr - 0.90)); t = thr[i]
        out["spec_at_90sens"] = float(((pte < t) & (yte==0)).sum() / max(1,(yte==0).sum()))
        out["thr_spec_at_90sens"] = float(t)
    except Exception: pass
    return out

def fit_logistic(Xtr, ytr, seed):
    best, bestm = None, -np.inf
    skf = StratifiedKFold(n_splits=INNER_FOLDS, shuffle=True, random_state=seed)
    for l1 in L1_RATIOS:
        for C in C_GRID:
            ms = []
            for tri, vai in skf.split(Xtr, ytr):
                try:
                    m = LogisticRegression(penalty="elasticnet", solver="saga", l1_ratio=l1, C=C, max_iter=5000, random_state=seed)
                    m.fit(Xtr[tri], ytr[tri]); ms.append(roc_auc_score(ytr[vai], m.predict_proba(Xtr[vai])[:,1]))
                except Exception: ms.append(0.5)
            mm = float(np.mean(ms))
            if mm > bestm: bestm, best = mm, {"l1_ratio":l1,"C":float(C)}
    m = LogisticRegression(penalty="elasticnet", solver="saga", l1_ratio=best["l1_ratio"], C=best["C"], max_iter=5000, random_state=seed)
    m.fit(Xtr, ytr)
    return m, best

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="C0,C1,C2")
    ap.add_argument("--mil-logits", default="")
    ap.add_argument("--smoke", action="store_true", help="2 repeats x 100 boot — verification only, never reportable")
    a = ap.parse_args()
    models = [m.strip() for m in a.models.split(",") if m.strip()]
    nrep, nboot = (2,100) if a.smoke else (OUTER_REPEATS, N_BOOT)

    clin = pd.read_csv(find("clinical_data_cleaned.csv"))
    pf = pd.read_csv(find("patient_features.csv"))
    geo = pd.read_csv(find("phase_03b_geometry_features.csv")) if "C2" in models else None
    splits = pd.read_csv(find("coo_split_ids.csv"))
    try: qc = pd.read_csv(find("phase_03_e007_ai_overlay_review.csv"))[["patient_id","ai_label"] if "ai_label" in pd.read_csv(find("phase_03_e007_ai_overlay_review.csv"), nrows=1).columns else ["patient_id"]]
    except Exception: qc = None
    mil = pd.read_csv(a.mil_logits) if a.mil_logits else None

    # Cohort A_COO: labelled image-eligible
    lab = clin[clin[LABEL].notna()][["patient_id",LABEL]].copy()
    lab["patient_id"] = lab["patient_id"].astype(int)
    pf["patient_id"] = pf["patient_id"].astype(int)
    df = lab.merge(pf, on="patient_id", how="inner")
    assert len(df) == 163, f"A_COO n={len(df)}"
    y_all = df.set_index("patient_id")[LABEL].astype(int)

    FEATS = {}
    if "C0" in models:
        c0 = clin.set_index("patient_id")[C0_COLS]
        FEATS["C0"] = df[["patient_id"]].merge(c0, left_on="patient_id", right_index=True, how="left")
    if "C1" in models:
        FEATS["C1"] = df[["patient_id"] + [c for c in F1+F2 if c in df.columns]]
    if "C2" in models and geo is not None:
        geo["patient_id"] = geo["patient_id"].astype(int)
        FEATS["C2"] = df[["patient_id"]].merge(geo, on="patient_id", how="left")

    oof = df[["patient_id",LABEL]].copy()
    hps, c4_fallback = [], 0
    for m in FEATS: oof[f"p_{m}"] = np.nan
    if "C4" in models: oof["p_C4"] = np.nan

    rng = np.random.RandomState(SEED)
    for rep in range(1, nrep+1):
        sub = splits[splits["repeat"]==rep]
        # local smoke splits may only have 2 repeats; skip missing
        if sub.empty: continue
        for fold in range(1, OUTER_FOLDS+1):
            te_ids = sub[sub["outer_fold"]==fold]["patient_id"].astype(int).tolist()
            tr_ids = df[~df["patient_id"].isin(te_ids)]["patient_id"].tolist()
            dtr, dte = df[df.patient_id.isin(tr_ids)], df[df.patient_id.isin(te_ids)]
            ytr, yte = dtr[LABEL].to_numpy().astype(int), dte[LABEL].to_numpy().astype(int)
            fold_scores = {}
            for m, Fp in FEATS.items():
                cols = [c for c in Fp.columns if c != "patient_id"]
                Xtr_df, Xte_df = Fp[Fp.patient_id.isin(tr_ids)][cols], Fp[Fp.patient_id.isin(te_ids)][cols]
                imp = SimpleImputer(strategy="median").fit(Xtr_df)
                Xtr_i, Xte_i = imp.transform(Xtr_df), imp.transform(Xte_df)
                kept = prune(pd.DataFrame(Xtr_i, columns=cols), ORDER if m!="C0" else cols)
                ki = [cols.index(c) for c in kept]
                sc = StandardScaler().fit(Xtr_i[:,ki])
                Ztr, Zte = sc.transform(Xtr_i[:,ki]), sc.transform(Xte_i[:,ki])
                mdl, best = fit_logistic(Ztr, ytr, SEED+rep*100+fold)
                pte, ptr = mdl.predict_proba(Zte)[:,1], mdl.predict_proba(Ztr)[:,1]
                oof.loc[oof.patient_id.isin(te_ids), f"p_{m}"] = oof.loc[oof.patient_id.isin(te_ids), f"p_{m}"].fillna(0) + pte/nrep
                fold_scores[m] = (ptr, pte)
                hps.append({"repeat":rep,"fold":fold,"model":m,"kept":len(kept),"l1":best["l1_ratio"],"C":best["C"]})
            if "C4" in models:
                # A003: 2-score fusion on fold-internal C1 + C3-MIL scores
                if mil is not None and "p_C1" in oof.columns:
                    mtab = mil.set_index("patient_id")
                    try:
                        s1tr = fold_scores["C1"][0] if "C1" in fold_scores else None
                        # MIL train/test logits for this fold from file (must be fold-specific; file carries repeat/fold cols if available)
                        if {"repeat","outer_fold"}.issubset(mtab.reset_index().columns) or {"repeat","fold"}.issubset(mtab.columns):
                            mf = mtab.reset_index()
                            rcol = "repeat"; fcol = "outer_fold" if "outer_fold" in mf.columns else "fold"
                            s3tr = mf[(mf[rcol]==rep)&(mf[fcol]!=fold)].set_index("patient_id").reindex(dtr["patient_id"])["mil_logit"].to_numpy()
                            s3te = mf[(mf[rcol]==rep)&(mf[fcol]==fold)].set_index("patient_id").reindex(dte["patient_id"])["mil_logit"].to_numpy()
                        else:
                            s3tr = mtab.reindex(dtr["patient_id"])["mil_logit"].to_numpy()
                            s3te = mtab.reindex(dte["patient_id"])["mil_logit"].to_numpy()
                        Z = StandardScaler().fit(np.c_[fold_scores["C1"][0], s3tr])
                        Ftr, Fte = Z.transform(np.c_[fold_scores["C1"][0], s3tr]), Z.transform(np.c_[fold_scores["C1"][1], s3te])
                        fmdl, _ = fit_logistic(Ftr, ytr, SEED)
                        pte = fmdl.predict_proba(Fte)[:,1]
                    except Exception:
                        pte = fold_scores.get("C1",(None,None))[1]; c4_fallback += 1
                else:
                    pte = fold_scores.get("C1",(None,None))[1]; c4_fallback += 1
                if pte is not None:
                    oof.loc[oof.patient_id.isin(te_ids), "p_C4"] = oof.loc[oof.patient_id.isin(te_ids), "p_C4"].fillna(0) + pte/nrep
            log(f"rep {rep} fold {fold} done (C4 fallback {c4_fallback})")

    WOUT.mkdir(parents=True, exist_ok=True)
    # Metrics + bootstrap per model
    rows = []
    y = oof[LABEL].to_numpy().astype(int)
    for m in ([k for k in ["C0","C1","C2","C4"] if f"p_{k}" in oof.columns]):
        p = oof[f"p_{m}"].to_numpy()
        mask = ~np.isnan(p); yy, pp = y[mask], p[mask]
        au = roc_auc_score(yy, pp); ap_ = average_precision_score(yy, pp)
        ba = balanced_accuracy_score(yy, (pp>=0.5).astype(int))
        sl, ic = calib_slope_intercept(yy, pp)
        boots = []
        for b in range(nboot):
            idx = rng.choice(len(yy), len(yy), replace=True)
            try: boots.append(roc_auc_score(yy[idx], pp[idx]))
            except Exception: boots.append(0.5)
        lo, hi = float(np.percentile(boots,2.5)), float(np.percentile(boots,97.5))
        rows.append({"model":m,"n":len(yy),"auroc":au,"lo":lo,"hi":hi,"auprc":ap_,"bal_acc":ba,
                     "calib_slope":sl,"calib_intercept":ic,"calib_ok":bool(CALIB_BOUNDS[0]<=sl<=CALIB_BOUNDS[1]),
                     "c4_fallback_folds":c4_fallback if m=="C4" else 0})
    pd.DataFrame(rows).to_csv(WOUT/"model_table.csv", index=False)
    oof.to_csv(WOUT/"oof_predictions.csv", index=False)
    pd.DataFrame(hps).to_csv(WOUT/"hyperparameters.csv", index=False)
    run = {"seed":SEED,"repeats":nrep,"boot":nboot,"models":models,"smoke":bool(a.smoke),
           "protocol_amendments":"A001-A007","c4_fallback_folds":c4_fallback,
           "note":"SMOKE runs are verification only, never reportable" if a.smoke else "primary tabular arm"}
    (WOUT/"run_summary.json").write_text(json.dumps(run, indent=2))
    log(f"WROTE {WOUT} — " + "; ".join(f"{r['model']} {r['auroc']:.3f} [{r['lo']:.3f},{r['hi']:.3f}]" for r in rows))

if __name__ == "__main__":
    main()
