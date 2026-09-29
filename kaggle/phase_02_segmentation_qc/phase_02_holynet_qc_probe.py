# ══════════════════════════════════════════════════════════════════════
#  PHASE 2 QC PROBE — load LyNSeC HoLy-Net weights + 16-tile overlay pilot
# ══════════════════════════════════════════════════════════════════════
#  Kaggle setup (before Save & Run All):
#    1. Notebook Settings -> Internet: ON
#    2. Input Datasets: attach dlbcl-kaggle-code (LyNSeC .npy tiles)
#    3. Accelerator: GPU T4 (CPU works too, just slower)
#    4. Paste THIS ENTIRE FILE into ONE cell.
#       For a quick interactive preflight, set SMOKE_TEST=True below. Reset it
#       to False before Save & Run All (Commit).
#
#  Why this script exists (E-002 post-mortem):
#    he.tar on Zenodo is NOT a tar archive. Magic bytes are PK\x03\x04
#    with an embedded archive/data.pkl — it is a torch.save() bundle
#    (ZIP container). The MD5 always matched, so the phase-1b download
#    was correct; only the reader was wrong. This script torch.load()s
#    it directly and normalises the keys:
#      - strip the DataParallel "module." prefix
#      - preserve HoVer-Net's slash-containing module names, which TIAToolbox
#        uses in its own state dictionary
#
#  Steps:
#    1  locate LyNSeC .npy tiles
#    2  download he.tar from Zenodo + MD5 verify (resumable)
#    3  torch.load the bundle, normalise keys, log structure
#    4  build HoVerNet (tiatoolbox), non-strict weight load,
#       report key coverage + rename diagnostics
#    5  QC inference on 1 H&E tile (smoke mode) or 16 H&E tiles (pilot):
#       overlay panels + Dice
#    6  crash-safe qc_probe_run.json
#
#  NOTE: 16 tiles are indicative only (E-001 may have seen some of them).
#  The 50-held-out-tile QC + pathologist review is the next milestone.
# ══════════════════════════════════════════════════════════════════════
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

WORK = Path("/kaggle/working")
QC_DIR = WORK / "qc_overlays"
HE_TAR = WORK / "he.tar"
HE_URL = "https://zenodo.org/records/8065174/files/he.tar?download=1"
HE_MD5 = "ab487b656117e7eb23f005691ace5276"
HE_SIZE = 452539789
SMOKE_TEST = False  # Set True interactively; MUST be False for the committed pilot.
SMOKE_TILE_COUNT = 1
N_TILES = 16
SEED = 42
WIN = 256  # HoLy-Net checkpoint matches HoVer-Net's fast-mode decoder.


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_summary(doc):
    doc.setdefault("updated_at_utc", datetime.now(timezone.utc).isoformat())
    (WORK / "qc_probe_run.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")


summary: dict = {"status": "running", "smoke_test": SMOKE_TEST}

# ── STEP 1 — locate tiles ─────────────────────────────────────────────
log("STEP 1: locating LyNSeC H&E tiles (l2/l3 only)")
tile_hits = sorted(
    p for p in Path("/kaggle/input").rglob("*.npy")
    if p.stem.lower().endswith(("_l2", "_l3"))
)
if not tile_hits:
    summary.update({"status": "failed", "error": "no LyNSeC H&E l2/l3 tiles found — attach dlbcl-kaggle-code"})
    write_summary(summary)
    raise SystemExit("FATAL: attach dlbcl-kaggle-code")
tiles_to_run = SMOKE_TILE_COUNT if SMOKE_TEST else N_TILES
log(f"H&E tiles found: {len(tile_hits)} | mode: {'SMOKE (1 tile)' if SMOKE_TEST else f'PILOT ({tiles_to_run} tiles)'}")
summary.update({"he_tile_count": len(tile_hits), "tiles_requested": tiles_to_run})

# ── STEP 2 — fetch he.tar ─────────────────────────────────────────────
log("STEP 2: fetching he.tar from Zenodo")
need = True
if HE_TAR.exists() and HE_TAR.stat().st_size == HE_SIZE and md5_of(HE_TAR) == HE_MD5:
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
        summary.update({"status": "failed", "error": "he.tar download failed x20"})
        write_summary(summary)
        raise SystemExit("FATAL: he.tar download failed")
log(f"he.tar OK ({HE_TAR.stat().st_size:,} bytes)")

import numpy as np
import torch

# ── STEP 3 — load the torch bundle directly ───────────────────────────
log("STEP 3: torch.load he.tar (it is a torch.save bundle, not a tar)")
try:
    obj = torch.load(HE_TAR, map_location="cpu", weights_only=True)
except Exception as exc:
    log(f"  weights_only=True failed ({exc!r:.80}); retrying weights_only=False")
    obj = torch.load(HE_TAR, map_location="cpu", weights_only=False)

checkpoint_root = obj if isinstance(obj, Mapping) else obj.state_dict()


def find_nested_state_dict(root):
    """Find the nested mapping that directly contains the model tensors.

    The HoLy-Net archive stores its model under ``desc`` alongside optimizer
    and scheduler state. Do not assume the outer checkpoint is a state dict.
    """
    queue = [("checkpoint", root)]
    candidates = []
    visited = set()
    while queue:
        label, value = queue.pop(0)
        if not isinstance(value, Mapping) or id(value) in visited:
            continue
        visited.add(id(value))
        direct_tensors = {str(k): v for k, v in value.items() if torch.is_tensor(v)}
        candidates.append((label, direct_tensors))
        for key, nested in value.items():
            if isinstance(nested, Mapping):
                queue.append((f"{label}.{key}", nested))
    if not candidates:
        return None, {}, []
    best_label, best_tensors = max(candidates, key=lambda item: len(item[1]))
    counts = [{"path": label, "tensor_count": len(tensors)} for label, tensors in candidates]
    return best_label, best_tensors, counts


state_dict_path, raw_sd, candidate_counts = find_nested_state_dict(checkpoint_root)
if len(raw_sd) < 100:
    summary.update({
        "status": "failed_with_diagnostics",
        "error": "no plausible model state dictionary found in checkpoint",
        "checkpoint_candidates": candidate_counts,
        "checkpoint_top_level_keys": list(checkpoint_root)[:20],
    })
    write_summary(summary)
    raise SystemExit("FATAL: checkpoint contained fewer than 100 model tensors")

# TIAToolbox's HoVerNet intentionally uses slash-containing module names.
# Strip only DataParallel's prefix; changing '/' to '.' would break key matches.
state_dict = {
    (k[len("module."):] if k.startswith("module.") else k): v
    for k, v in raw_sd.items()
}
log(f"loaded {len(state_dict)} tensors from {state_dict_path}")
summary["checkpoint"] = {
    "tensors": len(state_dict),
    "state_dict_path": state_dict_path,
    "candidate_tensor_counts": candidate_counts,
    "first_keys": list(state_dict)[:12],
}

# ── STEP 4 — build HoVerNet and measure key coverage ──────────────────
log("STEP 4: building HoVerNet (tiatoolbox)")
try:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-deps",
                    "tiatoolbox"], check=True, timeout=600)
    from tiatoolbox.models.architecture.hovernet import HoVerNet as HVN
except Exception as bare_exc:
    log(f"  bare install/import insufficient ({bare_exc!r:.120}); full install")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                        "tiatoolbox"], check=True, timeout=1200)
        from tiatoolbox.models.architecture.hovernet import HoVerNet as HVN
    except Exception as exc:
        summary.update({"status": "failed", "error": f"tiatoolbox unavailable: {exc}"})
        write_summary(summary)
        raise SystemExit("FATAL: tiatoolbox unavailable")

ctors = [
    # H&E LyNSeC-3 labels are background, non-tumour, tumour (0/1/2).
    # The 166 extra checkpoint tensors are this three-class TP decoder branch.
    ("HoVerNet(num_types=3, mode='fast')", lambda: HVN(num_types=3, mode="fast")),
]
model, ctor_errors, ctor_used = None, [], None
for label, fn in ctors:
    try:
        model = fn()
        ctor_used = label
        log(f"architecture: {label}")
        break
    except Exception as exc:
        ctor_errors.append(f"{label}: {exc!r:.120}")
if model is None:
    summary.update({"status": "failed",
                    "error": f"could not construct HoVerNet: {ctor_errors[-1]}"})
    write_summary(summary)
    raise SystemExit(f"FATAL: {ctor_errors[-1]}")

try:
    missing, unexpected = model.load_state_dict(state_dict, strict=False)
except RuntimeError as exc:
    summary.update({
        "status": "failed_with_diagnostics",
        "error": f"state-dict load failed: {exc}",
        "candidate_state_dict_path": state_dict_path,
    })
    write_summary(summary)
    raise SystemExit("FATAL: HoLy-Net weights are incompatible with this HoVerNet architecture")
n_model_keys = len(model.state_dict())
cov = (n_model_keys - len(missing)) / max(1, n_model_keys)
log(f"key coverage: {cov:.1%}  ({len(missing)} missing, {len(unexpected)} unexpected)")
summary["checkpoint"].update({
    "ctor": ctor_used, "key_coverage": round(cov, 4),
    "missing_keys_sample": list(missing)[:40],
    "unexpected_keys_sample": [k for k in unexpected if not k.startswith("desc")][:40]})
if cov < 0.5:
    def prefixes(keys, n=2):
        return Counter(".".join(k.split(".")[:n]) for k in keys)
    log("coverage <50% — prefix histograms to guide key mapping:")
    log(f"  model prefixes:     {prefixes(model.state_dict()).most_common(15)}")
    log(f"  checkpoint prefixes:{prefixes(state_dict).most_common(15)}")
    summary["checkpoint"]["model_prefixes"] = prefixes(model.state_dict()).most_common(20)
    summary["checkpoint"]["checkpoint_prefixes"] = prefixes(state_dict).most_common(20)
if cov < 0.2:
    summary.update({"status": "failed_with_diagnostics",
                    "error": "key coverage <20% — architecture mismatch, "
                             "see checkpoint diagnostics in qc_probe_run.json"})
    write_summary(summary)
    print(json.dumps(summary, indent=2)[:4000])
    raise SystemExit("FATAL: key coverage too low — send qc_probe_run.json back for mapping")

device = "cuda" if torch.cuda.is_available() else "cpu"
model.eval().to(device)
log(f"device: {device}")

# ── STEP 5 — QC inference on H&E tiles (indicative only) ──────────────
log(f"STEP 5: {'smoke-test' if SMOKE_TEST else 'pilot'} QC inference on {tiles_to_run} H&E tile(s)")
try:
    QC_DIR.mkdir(exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

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
    for tile_index, path in enumerate(tile_hits[:tiles_to_run]):
        img, gt = load_tile(path)
        if gt is None:
            tile_results.append({"tile": path.name, "status": "skipped_no_mask"})
            continue
        if tile_index == 0:
            log(f"first tile {path.name}: shape={img.shape} "
                f"range=[{np.nanmin(img):.3f},{np.nanmax(img):.3f}] gt_shape={gt.shape}")
        h0, w0 = img.shape[:2]
        ph, pw = max(0, WIN - h0), max(0, WIN - w0)
        if ph or pw:
            img = np.pad(img, ((0, ph), (0, pw), (0, 0)))
            gt = np.pad(gt, ((0, ph), (0, pw)))
        h, w = img.shape[:2]
        y0, x0 = (h - WIN) // 2, (w - WIN) // 2
        image_patch = img[y0:y0 + WIN, x0:x0 + WIN]
        gt_patch = gt[y0:y0 + WIN, x0:x0 + WIN] > 0
        with torch.no_grad():
            # TIAToolbox's HoVerNet forward pass performs its own /255 scaling.
            t = torch.as_tensor(image_patch.transpose(2, 0, 1)[None]).float().to(device)
            out = model(t)
        if not isinstance(out, dict) or "np" not in out:
            available = list(out) if isinstance(out, dict) else type(out).__name__
            raise RuntimeError(f"expected HoVerNet output key 'np'; got {available}")
        np_logits = out["np"]
        if np_logits.ndim != 4 or np_logits.shape[1] != 2:
            raise RuntimeError(f"unexpected HoVerNet np-logit shape {tuple(np_logits.shape)}")
        prob = torch.softmax(np_logits, dim=1)[0, 1].cpu().numpy()
        output_h, output_w = prob.shape
        if output_h > WIN or output_w > WIN:
            raise RuntimeError(f"model output {prob.shape} exceeds input window {WIN}x{WIN}")
        valid_y, valid_x = (WIN - output_h) // 2, (WIN - output_w) // 2
        gt_bin = gt_patch[valid_y:valid_y + output_h, valid_x:valid_x + output_w]
        disp = to_display(image_patch)[valid_y:valid_y + output_h, valid_x:valid_x + output_w]
        pred = prob > 0.5
        d = dice(pred, gt_bin)
        tile_results.append({"tile": path.name, "dice": round(d, 4)})
        log(f"  {path.name}: dice {d:.4f}")
        if tile_index == 0:
            log(f"  HoVerNet np logits={tuple(np_logits.shape)}; valid region={prob.shape}")
            summary["model_np_logits_shape"] = list(np_logits.shape)
            summary["valid_output_shape"] = [int(output_h), int(output_w)]
        ov = disp.copy()
        ov[pred & ~gt_bin] = [255, 0, 0]
        ov[gt_bin & ~pred] = [0, 200, 255]
        fig, ax = plt.subplots(1, 4, figsize=(18, 5))
        ax[0].imshow(disp); ax[0].set_title("H&E valid region")
        ax[1].imshow(gt_bin, cmap="gray"); ax[1].set_title("GT")
        ax[2].imshow(pred, cmap="gray"); ax[2].set_title("HoLy-Net pred")
        ax[3].imshow(ov); ax[3].set_title(f"overlay (FP red / FN blue) D={d:.3f}")
        for a in ax:
            a.axis("off")
        fig.tight_layout()
        fig.savefig(QC_DIR / f"{path.stem}_qc.png", dpi=120)
        plt.close(fig)

    valid = [t["dice"] for t in tile_results if "dice" in t]
    summary.update({"tiles": tile_results,
                    "mean_dice": round(float(np.mean(valid)), 4) if valid else None,
                    "assumptions": "central 256px input crop; score only the model's valid "
                                   "output region; TIAToolbox applies /255 internally (no stain norm); "
                                   "H&E-only; indicative QC, not held-out evaluation",
                    "status": "complete"})
    log(f"QC done: mean dice {summary['mean_dice']}")
except Exception as exc:
    summary["status"] = "failed_with_diagnostics"
    summary["error"] = repr(exc)
    log(f"QC attempt failed: {exc}")
finally:
    write_summary(summary)

# ── STEP 6 — report ───────────────────────────────────────────────────
print("\n" + "=" * 68)
print(f"PROBE DONE — coverage {cov:.1%} | mean_dice {summary.get('mean_dice')}")
print("=" * 68)
for p in sorted(WORK.rglob("*")):
    if p.is_file():
        print(f"  {str(p.relative_to(WORK))[:45]:45s} {p.stat().st_size:>12,d} bytes")
