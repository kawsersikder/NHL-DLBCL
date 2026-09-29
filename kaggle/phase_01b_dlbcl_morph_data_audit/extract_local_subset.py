"""Extract the tabular files needed for Phase 1b from the local DLBCL-Morph zip.

Usage:
    python extract_local_subset.py --zip "DLBCLMorph.zip" --output-dir data/raw/dlbcl_morph
"""

from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path

WANTED = [
    "DLBCL-Morph/Cells/cell_shapes.csv",
    "DLBCL-Morph/clinical_data.xlsx",
    "DLBCL-Morph/TMA/core.csv",
    "DLBCL-Morph/TMA/annotations.csv",
]

EXPECTED_ZIP_MD5 = "96cf88ad80f26cca82f7e346bad49936"


def md5sum(path: Path, chunk: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--skip-checksum", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_checksum:
        print("Verifying archive MD5 (takes a few minutes for 31.8 GB)...")
        digest = md5sum(args.zip)
        if digest != EXPECTED_ZIP_MD5:
            raise SystemExit(f"MD5 mismatch: {digest} != {EXPECTED_ZIP_MD5}")
        print(f"  archive MD5 OK: {digest}")

    with zipfile.ZipFile(args.zip) as archive:
        for name in WANTED:
            target = args.output_dir / name.rsplit("/", 1)[-1]
            print(f"Extracting {name} -> {target}")
            with archive.open(name) as src, target.open("wb") as dst:
                while True:
                    block = src.read(8 * 1024 * 1024)
                    if not block:
                        break
                    dst.write(block)
            print(f"  {target.stat().st_size:,} bytes  md5={md5sum(target)}")


if __name__ == "__main__":
    main()
