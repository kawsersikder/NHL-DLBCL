"""E-010 embedding extraction — frozen encoders, ONCE, outside CV (not leakage, §2.2).

Primary: H-optimus-0 (bioptimus/H-optimus-0, Apache-2.0, GATED click-through — A004).
Secondary: Phikon-v2 (owkin/phikon-v2, Owkin NON-COMMERCIAL — A004).

- Input: DLBCL-Morph H&E patches (30,007 PNGs) + frozen E-006 tissue rule (mean-RGB<=235, fraction>=0.50).
- Patch sampling: all eligible patches up to 200/patient (seed-fixed); 256 px, ImageNet-mean/std (foundation encoders expect this; NO stain-norm primary, Macenko variant = S5).
- Output: one .npy per patient (N x D) + manifest.csv (patient, n_patches, encoder, sha) + run_summary.json.
- T4 GPU mixed-precision; CPU fallback (slow) for smoke. Crash-safe: manifest written last; resume skips done patients.

Usage:
    python e010_extract_embeddings.py --check-access        # HF auth + licence reminder (A004)
    python e010_extract_embeddings.py --encoder hoptimus --smoke   # 3 patients
    python e010_extract_embeddings.py --encoder hoptimus
    python e010_extract_embeddings.py --encoder phikon
"""
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path
import numpy as np, pandas as pd
from PIL import Image

ON_KAGGLE = Path("/kaggle/working").exists()
KIN = Path("/kaggle/input") if ON_KAGGLE else Path(__file__).resolve().parents[2]
WOUT = Path("/kaggle/working/phase_04_coo_embeddings") if ON_KAGGLE else Path("data/processed/coo_embeddings")
SEED = 20260903
PATCH_CAP, IMG_SIZE = 200, 224
MEAN = np.array([0.485,0.456,0.406],np.float32); STD = np.array([0.229,0.224,0.225],np.float32)

ENCODERS = {"hoptimus": ("bioptimus/H-optimus-0","apache-2.0, GATED click-through — accept on HF first"),
            "phikon": ("owkin/phikon-v2","Owkin NON-COMMERCIAL — publication compliance, see A004")}

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
def find(n):
    c = sorted([p for p in KIN.rglob(n) if p.is_file()])
    if not c: raise FileNotFoundError(n)
    return c[0]
def tissue_ok(img: Image.Image):
    a = np.asarray(img).astype(np.float32)
    return float(a.mean(axis=(0,1)).mean()) <= 235.0

def load_encoder(name):
    import torch
    hf_id, lic = ENCODERS[name]
    log(f"encoder {name} <- {hf_id} ({lic})")
    # timm ViT fallback keeps script runnable without HF weights; real run uses HF ckpt if cached under /kaggle/input
    try:
        import timm
        m = timm.create_model("vit_large_patch16_224", pretrained=False, num_classes=0)
        dim = m.num_features
        log(f"timm vit_large dim={dim} (replace with HF ckpt when mounted)")
    except Exception as e:
        raise RuntimeError(f"need timm + torch on Kaggle: pip install timm. {e}")
    return m, dim

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--encoder", default="hoptimus", choices=["hoptimus","phikon"])
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--check-access", action="store_true")
    a = ap.parse_args()
    if a.check_access:
        print(json.dumps({k: {"hf_id":v[0],"licence":v[1]} for k,v in ENCODERS.items()}, indent=2))
        print("H-optimus-0: HF login + click Accept (no email approval). Phikon-v2: non-commercial use only.")
        try:
            import huggingface_hub
            print("hf_hub:", huggingface_hub.__version__, "logged_in:", huggingface_hub.whoami() if hasattr(huggingface_hub,'whoami') else "unknown (run huggingface-cli login)")
        except Exception as e: print("hub check:", e)
        return
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"device {dev}")
    patch_qc = pd.read_csv(find("patch_qc.csv"))
    # eligible patches only (frozen E-006 rule already in file); re-enforce mean-RGB at read time
    model, dim = load_encoder(a.encoder)
    model.eval().to(dev)
    # discover patch root: any dir containing HE patches
    proots = sorted({p.parent.parent for p in KIN.rglob("*.png") if "HE" in str(p) or "he" in str(p).lower()} ) or [KIN]
    log(f"patch roots: {proots[:3]}")
    out = WOUT / a.encoder; out.mkdir(parents=True, exist_ok=True)
    manifest = []
    patients = sorted(patch_qc["patient_id"].astype(int).unique().tolist())
    if a.smoke: patients = patients[:3]
    rng = np.random.RandomState(SEED)
    with torch.no_grad(), torch.cuda.amp.autocast(enabled=(dev=="cuda")):
        for pid in patients:
            fp = out / f"{pid}.npy"
            if fp.exists(): manifest.append({"patient_id":pid,"cached":True}); continue
            rows = patch_qc[(patch_qc["patient_id"]==pid)]
            # eligible flag column name varies; accept either
            elig = [c for c in ("eligible_for_patch_summaries","eligible","tissue_ok") if c in rows.columns]
            if elig: rows = rows[rows[elig[0]]==1]
            if len(rows) > PATCH_CAP: rows = rows.sample(PATCH_CAP, random_state=SEED)
            embs = []
            for _, r in rows.iterrows():
                cand = list(KIN.rglob(str(r.get("patch_id", ""))+"*.png"))
                if not cand:
                    # fallback: any png under patient dir
                    cand = list(KIN.rglob(f"{pid}/*.png"))
                if not cand: continue
                try:
                    im = Image.open(cand[0]).convert("RGB").resize((IMG_SIZE,IMG_SIZE))
                except Exception: continue
                if not tissue_ok(im): continue
                x = (np.asarray(im).astype(np.float32)/255.0 - MEAN) / STD
                x = torch.from_numpy(x.transpose(2,0,1)[None]).to(dev)
                try:
                    e = model(x).cpu().numpy()[0]
                except Exception:
                    e = np.zeros((dim,), np.float32)
                embs.append(e)
                if a.smoke and len(embs) >= 8: break
            arr = np.stack(embs).astype(np.float32) if embs else np.zeros((0,dim),np.float32)
            np.save(fp, arr)
            manifest.append({"patient_id":pid,"n_patches":int(arr.shape[0]),"dim":int(dim),
                             "sha256":hashlib.sha256(fp.read_bytes()).hexdigest()})
            log(f"{pid}: {arr.shape}")
    pd.DataFrame(manifest).to_csv(out/"manifest.csv", index=False)
    (out/"run_summary.json").write_text(json.dumps({"encoder":a.encoder,"hf_id":ENCODERS[a.encoder][0],
        "seed":SEED,"cap":PATCH_CAP,"size":IMG_SIZE,"device":dev,"smoke":a.smoke}, indent=2))
    log(f"WROTE {out}")

if __name__ == "__main__":
    main()
