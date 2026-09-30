"""Duplicate scan, step 1: download GEO series matrices and record SHA-256.

Files land in the git-ignored route1/data/raw/series_matrix/. The tracked
manifest records URL, size and hash so the inputs are auditable.
"""
from __future__ import annotations

import csv
import hashlib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "raw" / "series_matrix"
FILES = [
    ("GPL570", "GSE10846", "GSE10846_series_matrix.txt.gz"),
    ("GPL570", "GSE11318", "GSE11318-GPL570_series_matrix.txt.gz"),
    ("GPL570", "GSE53786", "GSE53786_series_matrix.txt.gz"),
    ("GPL570", "GSE31312", "GSE31312_series_matrix.txt.gz"),
    ("GPL570", "GSE87371", "GSE87371_series_matrix.txt.gz"),
    ("GPL570", "GSE23501", "GSE23501_series_matrix.txt.gz"),
    ("GPL570", "GSE19246", "GSE19246_series_matrix.txt.gz"),
    ("GPL570", "GSE12195", "GSE12195_series_matrix.txt.gz"),
    ("GPL570", "GSE34171", "GSE34171-GPL570_series_matrix.txt.gz"),
    ("GPL570", "GSE56315", "GSE56315_series_matrix.txt.gz"),
    ("GPL570", "GSE57611", "GSE57611_series_matrix.txt.gz"),
    ("GPL14951", "GSE181063", "GSE181063_series_matrix.txt.gz"),
    ("GPL14951", "GSE117556", "GSE117556_series_matrix.txt.gz"),
    ("GPL14951", "GSE69051", "GSE69051_series_matrix.txt.gz"),
    ("GPL8432", "GSE32918", "GSE32918_series_matrix.txt.gz"),
]


def url(acc: str, name: str) -> str:
    return f"https://ftp.ncbi.nlm.nih.gov/geo/series/{acc[:-3]}nnn/{acc}/matrix/{name}"


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    rows = []
    for plat, acc, name in FILES:
        path = DEST / name
        if not path.exists():
            tmp = path.with_suffix(".part")
            with urllib.request.urlopen(url(acc, name), timeout=600) as r, open(tmp, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            tmp.replace(path)
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append([plat, acc, name, url(acc, name), path.stat().st_size, h])
        print(f"{acc:10s} {path.stat().st_size/1e6:7.1f} MB  {h[:16]}")
    with open(ROOT / "manifests" / "dup_scan_inputs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["platform_expected", "series", "file", "url", "bytes", "sha256"])
        w.writerows(rows)


if __name__ == "__main__":
    main()
