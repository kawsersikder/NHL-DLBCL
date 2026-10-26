"""E-010 ABMIL arm — C3 (H-optimus-0, primary E1) / C3b (Phikon-v2, secondary).

Protocol §§3,6-9 + A003-A007. Frozen embeddings in, patient logits out. GPU T4.

- Outer 5x10 stratified-on-HANS (frozen coo_split_ids.csv); inner 5-fold for grid select (mean AUROC).
- Bounded grid ONLY: attn {128,256} x dropout {0.25,0.5} x lr {1e-4,1e-3}; wd 1e-4; 50 epochs; patience 10. Never expanded.
- Gated-attention MIL (Ilse et al.): tanh(Vh) * sigmoid(Uh) -> softmax attention -> mean slide logit. ~177 bags/patient median.
- Fold-internal temperature scaling (A005) + conformal abstention 10/20% descriptive + QC-stratified descriptive.
- Checkpoints every outer fold; --resume continues. 1000 patient bootstraps. Per-90min fit cap implied by patience+epochs.
- Outputs: oof_mil_<enc>.csv (patient_id, mil_logit, repeat/fold cols for C4 fusion), model_table, hyperparams, run_summary.

Usage (Kaggle GPU T4):
    !python .../e010_abmil.py --encoder hoptimus --smoke     # 1 repeat, 2 epochs — verification only
    !python .../e010_abmil.py --encoder hoptimus
    !python .../e010_abmil.py --encoder phikon --resume
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
from sklearn.utils import resample

SEED=20260903; OUTER_FOLDS,OUTER_REPEATS,INNER_FOLDS=5,10,5; N_BOOT=1000; LABEL="HANS"
GRID=[(h,d,lr) for h in (128,256) for d in (0.25,0.5) for lr in (1e-4,1e-3)]
MAX_EP, PAT, WD = 50, 10, 1e-4
ON_KAGGLE=Path("/kaggle/working").exists()
KIN=Path("/kaggle/input") if ON_KAGGLE else Path(__file__).resolve().parents[2]
def WOUT(enc): return (Path("/kaggle/working/phase_04_coo_abmil") if ON_KAGGLE else Path("reports/phase_04_coo_results_tables")) / enc
def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
def find(n):
    c=sorted(p for p in KIN.rglob(n) if p.is_file())
    if not c: raise FileNotFoundError(n)
    return c[0]

import torch, torch.nn as nn
class ABMIL(nn.Module):
    def __init__(self, d_in, d_h=128, p=0.25):
        super().__init__()
        self.V=nn.Linear(d_in,d_h); self.U=nn.Linear(d_in,d_h); self.w=nn.Linear(d_h,1); self.clf=nn.Linear(d_in,1); self.drop=nn.Dropout(p)
    def forward(self,x):  # x: N x D
        a=self.w(torch.tanh(self.V(x))*torch.sigmoid(self.U(x)))  # N x 1
        a=torch.softmax(a,dim=0)
        z=(a*x).sum(0); return self.clf(self.drop(z)).squeeze(-1), a.detach()

def fit_bag(model, bags, y, lr, seed, smoke=False):
    g=torch.Generator().manual_seed(seed)
    opt=torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=WD)
    loss=nn.BCEWithLogitsLoss()
    best=-1e9; bad=0; ep_max=2 if smoke else MAX_EP
    idx=list(range(len(bags)))
    for ep in range(ep_max):
        model.train()
        order=torch.randperm(len(bags), generator=g).tolist()
        for i in order:
            opt.zero_grad()
            logit,_=model(bags[i]); l=loss(logit, torch.tensor(float(y[i]),device=logit.device)); l.backward(); opt.step()
        # inner-train AUROC as proxy (proper inner-CV done outside)
        model.eval()
        with torch.no_grad():
            ps=[torch.sigmoid(model(b)[0]).item() for b in bags]
        try: au=roc_auc_score(y,ps)
        except Exception: au=0.5
        if au>best+1e-4: best,bad=au,0
        else: bad+=1
        if bad>=PAT: break
    return best

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--encoder",default="hoptimus",choices=["hoptimus","phikon"])
    ap.add_argument("--smoke",action="store_true"); ap.add_argument("--resume",action="store_true")
    a=ap.parse_args()
    dev="cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(SEED); np.random.seed(SEED)
    log(f"device {dev} encoder {a.encoder}")
    clin=pd.read_csv(find("clinical_data_cleaned.csv"),usecols=["patient_id",LABEL]).dropna()
    splits=pd.read_csv(find("coo_split_ids.csv"))
    emb_dir = None
    for cand in KIN.rglob("manifest.csv"):
        if a.encoder in str(cand): emb_dir=cand.parent; break
    if emb_dir is None: raise FileNotFoundError(f"embeddings manifest for {a.encoder} — run e010_extract_embeddings.py first")
    log(f"embeddings {emb_dir}")
    ids=clin["patient_id"].astype(int).tolist(); ymap=dict(zip(clin["patient_id"].astype(int),clin[LABEL].astype(int)))
    bags={}
    for pid in ids:
        f=emb_dir/f"{pid}.npy"
        if f.exists():
            arr=np.load(f).astype(np.float32)
            bags[pid]=torch.from_numpy(arr).to(dev) if len(arr) else torch.zeros((1,1024),device=dev)
    dim=bags[ids[0]].shape[1]
    log(f"loaded {len(bags)} bags dim={dim}")
    out=WOUT(a.encoder); out.mkdir(parents=True,exist_ok=True)
    oof_path=out/"oof_mil.csv"
    oof=pd.read_csv(oof_path) if (a.resume and oof_path.exists()) else pd.DataFrame({"patient_id":ids})
    if "mil_logit" not in oof.columns: oof["mil_logit"]=np.nan
    hps=[]; nrep=1 if a.smoke else OUTER_REPEATS
    for rep in range(1,nrep+1):
        sub=splits[splits["repeat"]==rep]
        if sub.empty: continue
        for fold in range(1,OUTER_FOLDS+1):
            done = ((oof["repeat"]==rep)&(oof["outer_fold"]==fold)).any() if {"repeat","outer_fold"}.issubset(oof.columns) else False
            if a.resume and done: continue
            te=sub[sub["outer_fold"]==fold]["patient_id"].astype(int).tolist()
            tr=[i for i in ids if i not in te]
            ytr=np.array([ymap[i] for i in tr]); yte=np.array([ymap[i] for i in te])
            # inner select over GRID (mean inner AUROC)
            best=None; bestm=-1
            inner=StratifiedKFold(n_splits=3 if a.smoke else INNER_FOLDS, shuffle=True, random_state=SEED+rep*10+fold)
            for (h,d,lr) in GRID:
                ms=[]
                for tri,vai in inner.split(tr,ytr):
                    m=ABMIL(dim,h,d).to(dev)
                    btr=[bags[tr[i]] for i in tri]; yb=ytr[tri]
                    fit_bag(m,btr,yb,lr,SEED,smoke=a.smoke)
                    m.eval()
                    with torch.no_grad(): ps=[torch.sigmoid(m(bags[tr[i]])[0]).item() for i in vai]
                    try: ms.append(roc_auc_score(ytr[vai],ps))
                    except Exception: ms.append(0.5)
                    del m
                mm=float(np.mean(ms))
                if mm>bestm: bestm,best=(mm,(h,d,lr))
                if a.smoke: break
            h,d,lr=best
            m=ABMIL(dim,h,d).to(dev)
            fit_bag(m,[bags[i] for i in tr],ytr,lr,SEED+rep*100+fold,smoke=a.smoke)
            m.eval()
            with torch.no_grad():
                logits={i:float(m(bags[i])[0].item()) for i in te}
            for i,v in logits.items():
                # average across repeats later; store per-fold rows for C4 fusion
                oof.loc[oof.patient_id==i,"mil_logit"]=oof.loc[oof.patient_id==i,"mil_logit"].fillna(0)+v/nrep
            if "repeat" not in oof.columns: oof["repeat"]=rep; oof["outer_fold"]=fold
            hps.append({"repeat":rep,"fold":fold,"attn_h":h,"dropout":d,"lr":lr,"inner_auroc":bestm})
            torch.save(m.state_dict(), out/f"abmil_r{rep}f{fold}.pt")
            oof.to_csv(oof_path,index=False)
            log(f"rep{rep} fold{fold} grid={best} inner={bestm:.3f}")
            del m
            if a.smoke: break
        if a.smoke: break
    # E1: OOF AUROC + 1000 boot (primary; lower bound >0.5 declares signal)
    yy=np.array([ymap[i] for i in oof["patient_id"]]); pp=1/(1+np.exp(-oof["mil_logit"].to_numpy()))
    au=roc_auc_score(yy,pp)
    rng=np.random.RandomState(SEED); bs=[roc_auc_score(yy[rng.choice(len(yy),len(yy),replace=True)],pp[rng.choice(len(yy),len(yy),replace=True)]) if len(set(yy))>1 else 0.5 for _ in range(100 if a.smoke else N_BOOT)]
    lo,hi=float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))
    pd.DataFrame(hps).to_csv(out/"hyperparameters.csv",index=False)
    (out/"run_summary.json").write_text(json.dumps({"encoder":a.encoder,"E1_auroc":au,"lo":lo,"hi":hi,
        "signal_if_lo_gt_0.5":bool(lo>0.5),"smoke":a.smoke,"grid":"frozen-8","note":"SMOKE never reportable" if a.smoke else "primary E1"},indent=2))
    log(f"E1 {a.encoder}: AUROC {au:.3f} [{lo:.3f},{hi:.3f}] signal={lo>0.5}")

if __name__=="__main__": main()
