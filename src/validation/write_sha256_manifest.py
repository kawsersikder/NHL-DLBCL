"""Write a deterministic SHA-256 manifest for a preserved artifact directory."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--name", default="artifact_manifest.sha256")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    root = args.directory.resolve()
    output = root / args.name
    if args.verify:
        failures: list[str] = []
        entries = 0
        for line in output.read_text(encoding="utf-8").splitlines():
            expected, relative = line.split(" *", maxsplit=1)
            path = root / Path(relative)
            entries += 1
            if not path.is_file() or sha256(path) != expected.upper():
                failures.append(relative)
        print(f"manifest={output}")
        print(f"entries={entries}")
        print(f"verified={not failures}")
        if failures:
            for failure in failures:
                print(f"FAILED: {failure}")
            raise SystemExit(1)
        return

    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.resolve() != output.resolve()
    )
    lines = [
        f"{sha256(path)} *{path.relative_to(root).as_posix()}" for path in files
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"manifest={output}")
    print(f"entries={len(lines)}")


if __name__ == "__main__":
    main()
