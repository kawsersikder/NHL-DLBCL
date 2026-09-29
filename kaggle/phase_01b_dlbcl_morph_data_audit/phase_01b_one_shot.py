# ══════════════════════════════════════════════════════════════════════
#  PHASE 1B ONE-SHOT v2 — reproduction + HoLy-Net fetch + QC pilot
# ══════════════════════════════════════════#  Kaggle setup (do these before hitting Save & Run All):
#    1. Notebook Settings -> Internet: ON   (needs phone-verified account)
#    2. Input Datasets: attach BOTH private datasets:
#         - dlbcl-kaggle-codee     (cell_shapes.csv, clinical_data_cleaned.csv, etc.)
#         - dlbcl-kaggle-code      (LyNSeC .npy tiles)
#    3. Accelerator: GPU T4 (QC pilot uses it; total GPU time << 1 h of your 12 h)
#    4. Paste THIS ENTIRE FILE into ONE notebook cell, then:
#         Save Version -> "Save & Run All (Commit)"  -> close tab, sleep
#
#  Pipeline:
#    Step 1  locate input datasets (slug-independent search)
#    Step 2  download he.tar from Zenodo + MD5 verify -> working/output
#    Step 3  clinical-table audit                     -> audit_report.json/.txt
#    Step 4  reproduce Stanford survival_regression.ipynb, all 3 modes,
#            1000 bootstraps (target GEOMETRIC C-index 0.635)
#    Step 5  ATTEMPT: HoLy-Net inference QC pilot on 16 LyNSeC tiles
#            (overlay panels + per-tile Dice/IoU). Heavy diagnostics logged;
#            any failure is captured and does NOT affect steps 1-4.
#    Step 6  crash-safe run_summary.json + output tree printed
#
#  NOTE: DLBCL-Morph patch inference / MIL / fusion are NOT runnable tonight —
#  the 14.5 GB Patches folder is still only in your local zip. Next manual
#  step remains uploading that subset.
# ══════════════════════════════════════════════════════
import hashlib
import json
import os
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

WORK = Path("/kaggle/working")
REPRO_DIR = WORK / "phase_01b_reproduction"
QC_DIR = WORK / "qc_overlays"
HE_TAR = WORK / "he.tar"
HE_URL = "https://zenodo.org/records/8065174/files/he.tar?download=1"
HE_MD5 = "ab487b656117e7eb23f005691ace5276"
NUM_BOOTSTRAPS = 1000
SEED = 42
N_QC_TILES = 16


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def write_status(status, step, payload):
    doc = {"status": status, "last_step": step,
           "updated_at_utc": datetime.now(timezone.utc).isoformat()}
    doc.update(payload)
    (WORK / "run_summary.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ── auto-install dependencies not in Kaggle's default image ────────────
for _pkg in ("lifelines", "scikit-learn"):
    try:
        __import__(_pkg.replace("-", "_").split("_")[0])   # quick probe
    except ImportError:
        log(f"installing {_pkg} ...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", _pkg],
                       check=True, timeout=300)

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter

payload: dict = {}

# ── STEP 1 — locate inputs ────────────────────────────────────────────
log("STEP 1: locating inputs")
hits = [p for p in Path("/kaggle/input").rglob("cell_shapes.csv")]
if not hits:
    write_status("failed", "step1_locate_data",
                 {"error": "cell_shapes.csv not found — attach dlbcl-morph-tables"})
    raise SystemExit("FATAL: attach dlbcl-morph-tables")
DATA_DIR = hits[0].parent
tile_hits = sorted(p for p in Path("/kaggle/input").rglob("*.npy")
                   if DATA_DIR not in p.parents and p.name.endswith(".npy"))
log(f"data dir: {DATA_DIR}  |  ly-nsec tiles found: {len(tile_hits)}")
payload.update({"data_dir": str(DATA_DIR), "tile_count": len(tile_hits)})
write_status("running", "step1_done", payload)

# ── STEP 2 — fetch he.tar ─────────────────────────────────────────────
log("STEP 2: fetching he.tar from Zenodo")
need = True
if HE_TAR.exists() and HE_TAR.stat().st_size == 452539789 and md5_of(HE_TAR) == HE_MD5:
    need = False
    log("already present and verified")
if need:
    import requests
    tmp = HE_TAR.with_suffix(".part")
    for attempt in range(1, 21):
        try:
            pos = tmp.stat().st_size if tmp.exists() else 0
            headers = {"Range": f"bytes={pos}-"} if pos else {}
            with requests.get(HE_URL, headers=headers, stream=True, timeout=(20, 120)) as r:
                r.raise_for_status()
                with open(tmp, "ab" if pos else "wb") as f:
                    for chunk in r.iter_content(8 * 1024 * 1024):
                        f.write(chunk)
            if md5_of(tmp) != HE_MD5:
                raise IOError("md5 mismatch")
            tmp.rename(HE_TAR)
            need = False
            break
        except Exception as exc:
            log(f"  attempt {attempt}: {exc}; retry in 10s")
            time.sleep(10)
    if need:
        write_status("failed", "step2_he_tar", {"error": "download failed x20"})
        raise SystemExit("FATAL: he.tar download failed")
log(f"he.tar OK ({HE_TAR.stat().st_size:,} bytes)")
payload["he_tar_md5"] = HE_MD5
write_status("running", "step2_done", payload)

# ── STEP 3 — clinical audit ───────────────────────────────────────────
log("STEP 3: clinical audit")
clin = pd.read_csv(DATA_DIR / "clinical_data_cleaned.csv")
events = int((clin["Follow-up Status"] == 1).sum())
audit = {"patients": len(clin), "os_events": events,
         "os_events_pct": round(events / len(clin), 4),
         "missingness": {c: int(clin[c].isna().sum()) for c in clin.columns}}
(WORK / "audit_report.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
with open(WORK / "audit_report.txt", "w", encoding="utf-8") as f:
    f.write(f"patients={audit['patients']} OS events={events}\n")
    f.writelines(f"  {c}: {m}/{audit['patients']}\n"
                 for c, m in audit["missingness"].items() if m)
payload["clinical_audit"] = {k: v for k, v in audit.items() if k != "missingness"}
write_status("running", "step3_done", payload)

# ── STEP 4 — reproduction ─────────────────────────────────────────────
NEW_CLINICAL_COLS = ["MYC IHC", "BCL2 IHC", "BCL6 IHC", "CD10 IHC", "MUM1 IHC",
                     "HANS", "BCL6 FISH", "MYC FISH", "BCL2 FISH", "Age", "ECOG PS",
                     "LDH", "EN", "Stage", "IPI Score", "IPI Risk Group (4 Class)",
                     "RIPI Risk Group"]
GEO_COLS = ["rotate_angle_mean", "rotate_angle_std", "shortAxis_mean", "shortAxis_std",
            "longAxis_mean", "longAxis_std", "ellip_perimt_mean", "ellip_perimt_std",
            "ellip_area_mean", "ellip_area_std", "hull_area_mean", "hull_area_std",
            "minDiameter_mean", "minDiameter_std", "maxDiameter_mean", "maxDiameter_std",
            "minAngle_mean", "minAngle_std", "maxAngle_mean", "maxAngle_std",
            "esf_mean", "esf_std", "csf_mean", "csf_std", "sf1_mean", "sf1_std",
            "sf2_mean", "sf2_std", "elogation_mean", "elogation_std",
            "convexity_mean", "convexity_std", "rectCenter_x_mean", "rectCenter_x_std",
            "rectCenter_y_mean", "rectCenter_y_std", "rect_width_mean", "rect_width_std",
            "rect_height_mean", "rect_height_std", "ellip_centroid_x_mean",
            "ellip_centroid_x_std", "ellip_centroid_y_mean", "ellip_centroid_y_std",
            "OS", "FUS"]
PENALIZERS = {"GEOMETRIC": 0.0, "CLINICAL": 0.0, "ALL": 0.00005}


def load_and_aggregate():
    o = pd.read_csv(DATA_DIR / "clinical_data_cleaned.csv").fillna(
        pd.read_csv(DATA_DIR / "clinical_data_cleaned.csv").mean(numeric_only=True))
    c = pd.read_csv(DATA_DIR / "cell_shapes.csv")
    df = c.merge(o[["patient_id", "OS", "Follow-up Status"] + NEW_CLINICAL_COLS],
                 on="patient_id", how="inner", validate="m:1")
    df = df.drop(["patch_id", "cell_number"], axis=1).astype(float)
    agg = df.groupby("patient_id").agg(["mean", "std"])
    agg.columns = agg.columns.map("_".join)
    agg = agg.drop(["OS_std", "Follow-up Status_std"] +
                   [x + "_std" for x in NEW_CLINICAL_COLS], axis=1)
    return agg.rename(columns={"OS_mean": "OS", "Follow-up Status_mean": "FUS"})


def quantile_transform(df):
    # legacy leakage replicated intentionally (fitted on full frame incl. OS/FUS)
    from sklearn.preprocessing import QuantileTransformer
    qt = QuantileTransformer(n_quantiles=10, random_state=SEED)
    qt.fit(df)
    return pd.DataFrame.from_records(qt.transform(df), columns=df.columns)


def run_mode(df_agg, features):
    log(f"--- MODE {features} ---")
    if features == "ALL":
        df, pen = df_agg.copy(), PENALIZERS["ALL"]
    elif features == "GEOMETRIC":
        df, pen = df_agg[GEO_COLS].copy(), PENALIZERS["GEOMETRIC"]
    else:
        df, pen = df_agg.drop(set(GEO_COLS) - {"OS", "FUS"}, axis=1).copy(), PENALIZERS["CLINICAL"]
    df = quantile_transform(df)
    ev = int(df["FUS"].sum())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cph = CoxPHFitter(penalizer=pen).fit(df, duration_col="OS", event_col="FUS")
        c_main = cph.score(df, scoring_method="concordance_index")
        log(f"uncorrected: {c_main:.4f}")
        np.random.seed(SEED)
        cb, co = [], []
        for i in range(NUM_BOOTSTRAPS):
            smp = df.iloc[np.random.choice(len(df), len(df), replace=True)]
            b = CoxPHFitter(penalizer=pen).fit(smp, duration_col="OS", event_col="FUS")
            cb.append(b.score(smp, scoring_method="concordance_index"))
            co.append(b.score(df, scoring_method="concordance_index"))
            if (i + 1) % 250 == 0:
                log(f"  bootstrap {i+1}/{NUM_BOOTSTRAPS}")
        optimism = float(np.mean(np.array(cb) - np.array(co)))
        corrected = c_main - optimism
        np.random.seed(SEED)
        full = CoxPHFitter(penalizer=pen).fit(df, duration_col="OS", event_col="FUS")
        cs = sorted(full.score(df.iloc[np.random.choice(len(df), len(df), replace=True)],
                               scoring_method="concordance_index") for _ in range(NUM_BOOTSTRAPS))
        lo_i = max(0, round(0.025 * NUM_BOOTSTRAPS) - 1)
        hi_i = min(NUM_BOOTSTRAPS - 1, round(0.975 * NUM_BOOTSTRAPS) - 1)
        lo, hi = cs[lo_i], cs[hi_i]
    log(f"corrected={corrected:.4f} adj CI=({lo-optimism:.3f},{hi-optimism:.3f})")
    res = {"mode": features, "patients": len(df), "events": ev,
           "uncorrected_c_index": round(float(c_main), 4),
           "optimism": round(float(optimism), 4),
           "corrected_c_index": round(float(corrected), 4),
           "ci95": [round(float(lo), 4), round(float(hi), 4)],
           "adjusted_ci95": [round(float(lo - optimism), 4), round(float(hi - optimism), 4)]}
    if features == "GEOMETRIC":
        res["paper_target"] = {"corrected_c_index": 0.635, "ci": [0.574, 0.691]}
        res["abs_deviation_from_paper"] = round(abs(corrected - 0.635), 4)
    return res


log("STEP 4: reproduction")
df_agg = load_and_aggregate()
results = []
for i, mode in enumerate(["GEOMETRIC", "CLINICAL", "ALL"]):
    try:
        results.append(run_mode(df_agg, mode))
    except Exception as exc:
        results.append({"mode": mode, "status": "failed", "error": repr(exc)})
    write_status("running" if i < 2 else "complete", "step4_progress",
                 {**payload, "results": results})

REPRO_DIR.mkdir(exist_ok=True)
(REPRO_DIR / "run_summary.json").write_text(json.dumps({
    "status": "complete", "num_bootstraps": NUM_BOOTSTRAPS, "seed": SEED,
    "source_notebook": "stanfordmlgroup/DLBCL-Morph@master survival_regression.ipynb",
    "results": results}, indent=2), encoding="utf-8")
payload["results"] = results

# ── STEP 5 — HoAy-Net QC pilot (attempt; never fatal) ────────────────
log("STEP 5: HoAy-Net QC pilot (attempt)")
qc_payload = {"status": "not_started"}
try:
    QC_DIR.mkdir(exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"device: {device}")

    # 5a — extract and inventory the checkpoint
    he_dir = WORK / "holy_net_he"
    if not he_dir.exists():
        import tarfile
        with tarfile.open(HE_TAR) as t:
            t.extractall(he_dir)
    files = [p for p in he_dir.rglob("*") if p.is_file()]
    qc_payload["archive_files"] = [{"name": str(p.relative_to(he_dir)),
                                    "bytes": p.stat().st_size} for p in files]
    for p in files[:40]:
        log(f"  archive: {p.relative_to(he_dir)} ({p.stat().st_size:,} B)")

    ckpts = {}
    for p in files:
        if p.suffix.lower() in {".pt", ".pth", ".ckpt", ".pkl", ".bin"}:
            try:
                obj = torch.load(p, map_location="cpu", weights_only=False)
                sd = obj
                if isinstance(obj, dict):
                    for k in ("state_dict", "model_state_dict", "model", "weights"):
                        if k in obj and isinstance(obj[k], dict):
                            sd = obj[k]
                            break
                if isinstance(sd, dict) and any(hasattr(v, "shape") or isinstance(v, dict) for v in sd.values()):
                    ckpts[str(p)] = sd
            except Exception as exc:
                log(f"  could not load {p.name}: {exc}")
    if not ckpts:
        raise RuntimeError("no loadable torch checkpoint found in he.tar")

    # 5b — build HoAy-Net architecture (try known import paths)
    model = None
    tried = []
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-deps",
                        "tiatoolbox"], check=True, timeout=600)
        ns = {}
        exec("import tiatoolbox.models.architectures.hovernet", ns)  # probe import
    except Exception as exc:
        log(f"  bare install insufficient ({exc}); full install")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "tiatoolbox"],
                           check=True, timeout=1200)
        except Exception as exc2:
            log(f"  tiatoolbox unavailable: {exc2}")
    model = None
    tried = []
    ctors = [
        ("HoVerNet(num_classes=2, mode='fast')",
         lambda: HoVerNet(num_classes=2, mode="fast")),
        ("HoVerNet(num_classes=2)",
         lambda: HoVerNet(num_classes=2)),
        ("HoVerNet()",
         lambda: HoVerNet()),
    ]
    for imp_path in ("from tiatoolbox.models.architectures.hovernet import HoVerNet",
                     "from tiatoolbox.models.architecture.hoVerNet import HoVerNet",
                     "from tiatoolbox.models.architectures.hovernetnet import HoVerNet"):
        try:
            ns = {}
            exec(imp_path, ns)
            HVN = ns["HoVerNet"]
            break
        except Exception as exc:
            tried.append(f"{imp_path}: {exc}")
    else:
        qc_payload["architecture_attempts"] = tried
        raise RuntimeError(f"HoVerNet class not importable: {tried[-1][:100]}")
    ctor_errors = []
    for label, fn in ctors:
        try:
            model = fn()
            tried.append(f"{label} OK")
            log(f"architecture: {label}")
            break
        except Exception as exc:
            ctor_errors.append(f"{label}: {exc}")
    qc_payload["architecture_attempts"] = tried + ctor_errors
    if model is None:
        raise RuntimeError(f"could not construct HoVerNet: {ctor_errors}")

    # 5c — load weights (non-strict) and measure key coverage
    name, sd = next(iter(ckpts.items()))
    missing, unexpected = model.load_state_dict(sd, strict=False)
    n_match = len(model.state_dict()) - len(missing)
    cov = n_match / max(1, len(model.state_dict()))
    qc_payload["checkpoint"] = {"file": name, "key_coverage": round(cov, 3),
                                "missing_keys": list(missing)[:20],
                                "unexpected_keys": list(unexpected)[:20]}
    log(f"checkpoint {name}: key coverage {cov:.0%}")
    model.eval().to(device)

    # 5d — QC inference on N tiles (indicative only: these tiles may have been
    #     seen by E-001's U-Net; this is a sanity check, not held-out evaluation)
    def load_tile(path):
        obj = np.load(str(path), allow_pickle=True)
        if isinstance(obj, np.ndarray) and obj.shape == ():
            obj = obj.item()
        if isinstance(obj, dict):
            img_key = next((k for k in ("image", "img", "rgb") if k in obj), None)
            msk_key = next((k for k in ("mask", "instance", "inst", "label") if k in obj), None)
            img, msk = obj[img_key], obj.get(msk_key)
        else:
            img, msk = obj[..., :3], obj[..., 3] if obj.ndim == 3 and obj.shape[-1] >= 4 else None
        return np.asarray(img, dtype=np.float32), (None if msk is None else np.asarray(msk))

    def to_display(img):
        im = img.astype(np.float32)
        if im.max() <= 1.5:
            im = im * 255.0
        return np.clip(im, 0, 255).astype(np.uint8)

    def dice(a, b):
        inter = np.logical_and(a, b).sum()
        return float((2 * inter + 1) / (a.sum() + b.sum() + 1))

    tile_results = []
    for path in tile_hits[:N_QC_TILES]:
        img, gt = load_tile(path)
        if img is None or gt is None:
            tile_results.append({"tile": path.name, "status": "skipped_unrecognized_format"})
            continue
        if path is tile_hits[0]:
            log(f"first tile {path.name}: shape={img.shape} "
                f"range=[{np.nanmin(img):.3f},{np.nanmax(img):.3f}] gt_shape={gt.shape}")
        # pad so windowing always sees full 270x270 windows
        h0, w0 = img.shape[:2]
        ph, pw = max(0, 270 - h0), max(0, 270 - w0)
        if ph or pw:
            img = np.pad(img, ((0, ph), (0, pw), (0, 0)))
            gt = np.pad(gt, ((0, ph), (0, pw))) if gt is not None else gt
        gt_bin = gt > 0
        h, w = img.shape[:2]
        pred = np.zeros((h, w), bool)
        win, stride, margin = 270, 80, 47  # classic HoVer-Net windowing; assumption logged
        xs = list(range(0, max(1, w - win), stride)) + ([w - win] if w > win else [0])
        ys = list(range(0, max(1, h - win), stride)) + ([h - win] if h > win else [0])
        acc = np.zeros((h, w)); cnt = np.zeros((h, w))
        with torch.no_grad():
            for y in ys:
                for x in xs:
                    patch = img[y:y + win, x:x + win] / 255.0
                    t = torch.as_tensor(patch.transpose(2, 0, 1)[None]).float().to(device)
                    out = model(t)
                    prob = torch.softmax(out["NP"][0], 0)[1] if isinstance(out, dict) \
                        else torch.softmax(out[0], 0)[1]
                    prob = torch.nn.functional.interpolate(
                        prob[None, None], size=(win, win), mode="bilinear")[0, 0].cpu().numpy()
                    acc[y:y + win, x:x + win] += prob
                    cnt[y:y + win, x:x + win] += 1
        pred = (acc / np.maximum(cnt, 1)) > 0.5
        d = dice(pred, gt_bin)
        tile_results.append({"tile": path.name, "dice": round(d, 4)})
        fig, ax = plt.subplots(1, 4, figsize=(18, 5))
        disp = to_display(img)
        ax[0].imshow(disp); ax[0].set_title("HE")
        ax[1].imshow(gt_bin, cmap="gray"); ax[1].set_title("GT")
        ax[2].imshow(pred, cmap="gray"); ax[2].set_title("HoLy-Net pred")
        ov = disp.copy()
        ov[pred & ~gt_bin] = [255, 0, 0]; ov[gt_bin & ~pred] = [0, 200, 255]
        ax[3].imshow(ov); ax[3].set_title(f"overlay (FP red / FN blue) D={d:.3f}")
        for a in ax:
            a.axis("off")
        fig.tight_layout()
        fig.savefig(QC_DIR / f"{path.stem}_qc.png", dpi=120)
        plt.close(fig)
    valid = [t["dice"] for t in tile_results if "dice" in t]
    qc_payload.update({"tiles": tile_results,
                       "mean_dice": round(float(np.mean(valid)), 4) if valid else None,
                       "note": "windowing/normalisation assumptions logged; indicative QC only"})
    log(f"QC done: mean dice {qc_payload['mean_dice']}")
except Exception as exc:
    qc_payload["status"] = "failed_with_diagnostics"
    qc_payload["error"] = repr(exc)
    log(f"QC attempt failed: {exc}")
finally:
    qc_payload.setdefault("status", "complete")
    payload["qc_pilot"] = qc_payload
    write_status("complete", "step5_done", payload)

# ── STEP 6 — final report ─────────────────────────────────────────────
print("\n" + "=" * 68)
print("PIPELINE DONE — targets: GEOMETRIC 0.635 | CLINICAL 0.674 | ALL 0.700")
print("=" * 68)
for r in results:
    if "error" in r:
        print(f"  {r['mode']:10s} FAILED: {r['error'][:70]}")
    else:
        print(f"  {r['mode']:10s} corrected C-index {r['corrected_c_index']:.3f}"
              f"  adj CI ({r['adjusted_ci95'][0]:.3f}, {r['adjusted_ci95'][1]:.3f})")
q = payload["qc_pilot"]
print(f"  QC pilot: {q['status']}  mean_dice={q.get('mean_dice')}"
      + ("" if q["status"] == "complete" else f"  error={str(q.get('error'))[:70]}"))
print(f"\nOutputs in {WORK}:")
for p in sorted(WORK.rglob("*")):
    if p.is_file():
        print(f"  {str(p.relative_to(WORK))[:45]:45s} {p.stat().st_size:>12,d} bytes")
