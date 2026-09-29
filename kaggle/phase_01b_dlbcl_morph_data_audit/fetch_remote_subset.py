"""Extract only the tabular files from the remote DLBCL-Morph figshare zip.

Downloads via HTTP range requests: ~374 MB instead of the 31.8 GB archive.

Usage:
    python fetch_remote_subset.py --output-dir data/raw/dlbcl_morph
"""

from __future__ import annotations

import argparse
import hashlib
from collections import defaultdict
from pathlib import Path

from remotezip import RemoteZip

URL = "https://ndownloader.figshare.com/files/24697142"

WANTED = [
    "DLBCL-Morph/Cells/cell_shapes.csv",
    "DLBCL-Morph/clinical_data.xlsx",
    "DLBCL-Morph/TMA/core.csv",
    "DLBCL-Morph/TMA/annotations.csv",
]


def md5sum(path: Path, chunk: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with RemoteZip(URL) as z:
        # Depth-2 folder stats for planning the Kaggle upload
        agg = defaultdict(lambda: [0, 0])
        for i in z.infolist():
            if i.is_dir():
                continue
            parts = i.filename.split("/")
            key = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
            agg[key][0] += 1
            agg[key][1] += i.file_size
        print("Second-level structure (files, size):")
        for key, (n, b) in sorted(agg.items()):
            print(f"  {key:40s} {n:8d} files  {b/1e9:8.2f} GB")

        for name in WANTED:
            target = args.output_dir / name.rsplit("/", 1)[-1]
            print(f"\nExtracting {name} -> {target}")
            with z.open(name) as src, target.open("wb") as dst:
                while True:
                    block = src.read(8 * 1024 * 1024)
                    if not block:
                        break
                    dst.write(block)
            size = target.stat().st_size
            print(f"  done: {size:,} bytes  md5={md5sum(target)}")


if __name__ == "__main__":
    main()
