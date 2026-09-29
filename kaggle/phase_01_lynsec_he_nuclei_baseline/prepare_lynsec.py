"""Verify and safely extract the original LyNSeC Zenodo archive for Kaggle."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


EXPECTED_MD5 = "f9b1bae015ccf2af29617930c051b304"


def md5sum(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive: zipfile.ZipFile, output_dir: Path) -> None:
    root = output_dir.resolve()
    for member in archive.infolist():
        destination = (output_dir / member.filename).resolve()
        if root != destination and root not in destination.parents:
            raise RuntimeError(f"Unsafe archive member rejected: {member.filename}")
    archive.extractall(output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="Original lynsec.zip file")
    parser.add_argument("--output-dir", type=Path, required=True, help="Writable extraction directory")
    parser.add_argument(
        "--skip-checksum",
        action="store_true",
        help="Only use when the source provides a documented replacement archive.",
    )
    args = parser.parse_args()

    archive_path = args.archive.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not archive_path.is_file():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    checksum = md5sum(archive_path)
    if not args.skip_checksum and checksum != EXPECTED_MD5:
        raise RuntimeError(
            f"MD5 mismatch for {archive_path.name}: got {checksum}, expected {EXPECTED_MD5}. "
            "Re-download the original Zenodo archive rather than training on an unknown file."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        safe_extract(archive, output_dir)

    npy_files = sorted(path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*.npy"))
    if not npy_files:
        raise RuntimeError("Extraction completed but no .npy files were found.")

    manifest = {
        "source_record": "https://zenodo.org/records/8065174",
        "archive_name": archive_path.name,
        "archive_md5": checksum,
        "archive_md5_expected": EXPECTED_MD5,
        "npy_file_count": len(npy_files),
        "npy_files": npy_files,
    }
    (output_dir / "extraction_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

