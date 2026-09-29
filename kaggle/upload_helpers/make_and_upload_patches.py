#!/usr/bin/env python
"""Package DLBCL-Morph Patches as ONE Kaggle dataset and upload via kaggle CLI.

Produces a private Kaggle dataset:

    kawsersikder/dlbcl-morph-patches          (slug: dlbcl-morph-patches)
    contents: dlbcl_morph_patches.zip         (single store-mode zip, ~14.5 GB)
              -> <STAIN>/<patient_id>/<patch_id>.png   (HE, MYC, BCL2, CD10, MUM1, BCL6)

Why a single zip: 152k tiny files kill browser/CLI folder uploads (the browser
uploader already stalled twice on a 453 MB file — Decision Log 2026-08-23).
PNGs are incompressible, so ZIP_STORED builds fast and verifies cleanly.
In notebooks: unzip on demand, or extract once and Save Data as an
extracted dataset (same pattern as the he.tar weights decision).

Usage:
    python make_and_upload_patches.py            # build + verify only
    python make_and_upload_patches.py --upload   # also run kaggle datasets create

Prerequisites:
    pip install kaggle
    API token at C:\\Users\\<you>\\.kaggle\\kaggle.json  (kaggle.com -> Settings -> API)
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(r"F:\Research Projects\NHL-DLBCL")
SRC = ROOT / "DLBCLMorph" / "Patches"
ORIG_ZIP = ROOT / "DLBCLMorph.zip"
PREFIX = "DLBCL-Morph/Patches/"
STAGING = ROOT / "kaggle_upload_staging"
OUT_ZIP = STAGING / "dlbcl_morph_patches.zip"
META = STAGING / "dataset-metadata.json"
SLUG = "kawsersikder/dlbcl-morph-patches"
TITLE = "dlbcl-morph-patches"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(16 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def expected_manifest():
    with zipfile.ZipFile(ORIG_ZIP) as z:
        return {i.filename[len(PREFIX):] for i in z.infolist()
                if i.filename.startswith(PREFIX) and not i.is_dir()}


def local_manifest():
    out = set()
    for root, _, files in os.walk(SRC):
        for f in files:
            out.add(Path(os.path.relpath(os.path.join(root, f), SRC)).as_posix())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upload", action="store_true",
                    help="run `kaggle datasets create` after building")
    ap.add_argument("--force", action="store_true",
                    help="rebuild the zip even if it already exists")
    args = ap.parse_args()

    log("verifying local extraction against DLBCLMorph.zip manifest")
    exp, loc = expected_manifest(), local_manifest()
    if exp != loc:
        log(f"MISMATCH: missing={len(exp - loc)} extra={len(loc - exp)} — aborting")
        log(f"  sample missing: {sorted(exp - loc)[:5]}")
        sys.exit(1)
    log(f"OK: {len(loc):,} files match the archive exactly")

    free = shutil.disk_usage(STAGING.parent).free
    src_bytes = sum((SRC / p).stat().st_size for p in list(loc)[:200])
    approx = sum(1 for _ in loc) * (src_bytes / max(1, min(len(loc), 200)))
    if OUT_ZIP.exists() and not args.force:
        log(f"{OUT_ZIP} already exists ({OUT_ZIP.stat().st_size/1e9:.2f} GB); "
            "keeping it (use --force to rebuild)")
    else:
        if free < 15e9:
            log(f"only {free/1e9:.1f} GB free — need ~15 GB for the staged zip")
            sys.exit(1)
        STAGING.mkdir(exist_ok=True)
        tmp = OUT_ZIP.with_suffix(".part")
        log("building store-mode zip (PNGs are already compressed)")
        n = 0
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_STORED) as zf:
            for p in sorted(loc):
                zf.write(SRC / p, arcname=p)
                n += 1
                if n % 25000 == 0:
                    log(f"  {n:,}/{len(loc):,}")
        tmp.rename(OUT_ZIP)

    # log("re-verifying staged zip integrity")
    # with zipfile.ZipFile(OUT_ZIP) as zf:
    #     bad = zf.testzip()
    #     got = set(zf.namelist())
    # if bad or got != loc:
    #     log(f"ZIP VERIFY FAILED (bad={bad}, diff={len(got ^ loc)}) — delete and rerun")
    #     sys.exit(1)
    # digest = md5_of(OUT_ZIP)
    # log(f"staged OK: {len(got):,} members, "
    #     f"{OUT_ZIP.stat().st_size/1e9:.2f} GB, md5 {digest}")

    META.write_text(json.dumps({
        "title": TITLE,
        "id": SLUG,
        "licenses": [{"name": "CC BY-NC-SA"}],  # closest Kaggle option to CC BY-NC 4.0
    }, indent=2), encoding="utf-8")

    if not args.upload:
        log("dry run complete — rerun with --upload to push to Kaggle")
        return

    token = Path(os.environ.get("KAGGLE_CONFIG_DIR", Path.home() / ".kaggle")) / "kaggle.json"
    if not token.exists():
        log(f"kaggle token not found at {token} (kaggle.com -> Settings -> API)")
        sys.exit(1)
    log("uploading — this takes 0.5–6 h depending on upstream bandwidth; keep the machine awake")
    r = subprocess.run(["kaggle", "datasets", "create", "-p", str(STAGING)])
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
