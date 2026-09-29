"""List the contents of the remote DLBCL-Morph figshare zip without downloading it.

Uses HTTP range requests against the figshare downloader URL so only the zip
central directory is transferred.

Usage:
    python list_remote_zip.py
"""

from __future__ import annotations

from collections import defaultdict

from remotezip import RemoteZip

URL = "https://ndownloader.figshare.com/files/24697142"


def main() -> None:
    with RemoteZip(URL) as z:
        infos = z.infolist()
        print(f"Total entries: {len(infos)}")

        # Top-level structure with sizes
        agg = defaultdict(lambda: [0, 0])  # top dir -> [file count, bytes]
        small_files = []
        for i in infos:
            if i.is_dir():
                continue
            top = i.filename.split("/")[0]
            agg[top][0] += 1
            agg[top][1] += i.file_size
            if i.file_size < 50 * 1024 * 1024:
                small_files.append(i)

        print("\nTop-level folders (files, size):")
        for top, (n, b) in sorted(agg.items()):
            print(f"  {top:20s} {n:7d} files  {b/1e9:8.2f} GB")

        # Key files we are looking for
        print("\nKey files:")
        keys = ("cell_shapes", "core", "annotation", "clinical", "readme",
                "README", ".xlsx", ".csv")
        seen = set()
        for i in infos:
            name = i.filename.rsplit("/", 1)[-1]
            if any(k in name for k in keys) and name not in seen:
                seen.add(name)
                print(f"  {i.file_size/1e6:>10.2f} MB  {i.filename}")


if __name__ == "__main__":
    main()
