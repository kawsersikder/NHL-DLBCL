"""Phase 0 — inventory the executing workspace and hash every input artifact.

The supervisor plan requires that the executing code/protocol copy and its input
provenance be explicit, and that no unresolved file conflict can change the
planned analysis. Two facts make this non-trivial here:

1. The project exists twice (Windows and Mac) and the copies have diverged. The
   Mac copy reportedly lacks ``.agents/`` and ``src/analysis/``; this Windows
   copy lacks ``reports/research_2026_09_10_sources/``.
2. The repository has **zero commits and no remote**, so Git cannot answer
   "which version produced this result?". Hashes recorded here are the only
   available provenance, which is why this script exists rather than a
   ``git log``.

Selection rule: inventory the *analysis-relevant* tree — code, protocols,
configs, reports, manifests and small released tables — and skip bulk binary
data. Bulk paths are reported as directory-level summaries instead, so their
absence from the file list is visible rather than silent. Hashing 44 GB of
slide archives would add nothing: they are pointed at by ``PROVENANCE.md`` with
their own checksums.

Deliberately does NOT choose between conflicting files. It records that a
conflict exists and leaves resolution to a dated decision-log entry, because
picking by modification time is exactly the failure the plan forbids.

Usage:
    python route1/src/phase0_inventory.py
"""
from __future__ import annotations

import csv
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_CSV = ROOT / "route1/manifests/source_registry.csv"
OUT_MD = ROOT / "route1/reports/workspace_inventory.md"

# Bulk trees: summarised, not hashed. Each already carries its own provenance.
BULK = [
    "DLBCLMorph", "kaggle_upload_staging", "models", "kaggle",
    "data/raw/dlbcl_morph/cell_shapes.csv",
]
SKIP_DIRS = {".git", "__pycache__", ".ipynb_checkpoints", ".venv", "venv",
             ".tmp", "node_modules"}
# Extensions worth hashing for an analysis-provenance audit.
KEEP_EXT = {".py", ".md", ".yaml", ".yml", ".csv", ".json", ".tex", ".bib",
            ".ipynb", ".txt", ".toml", ".cfg", ".lock"}

CATEGORY = {
    ".py": "code", ".ipynb": "notebook",
    ".md": "protocol/report", ".tex": "manuscript", ".bib": "manuscript",
    ".yaml": "config", ".yml": "config", ".toml": "config", ".cfg": "config",
    ".csv": "data/manifest", ".json": "data/manifest",
    ".txt": "other", ".lock": "config",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_bulk(rel: Path) -> bool:
    s = rel.as_posix()
    return any(s == b or s.startswith(b + "/") for b in BULK)


def walk() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if is_bulk(rel):
            continue
        if rel.parts[0] == "route1":  # generated outputs, not inputs
            continue
        if path.suffix.lower() not in KEEP_EXT:
            continue
        st = path.stat()
        rows.append({
            "path": rel.as_posix(),
            "category": CATEGORY.get(path.suffix.lower(), "other"),
            "bytes": str(st.st_size),
            "mtime_utc": datetime.fromtimestamp(
                st.st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
            "sha256": sha256(path),
        })
    return sorted(rows, key=lambda r: r["path"])


def bulk_summary() -> list[tuple[str, int, int]]:
    """Report bulk trees as (path, file count, bytes) without hashing them."""
    out = []
    for b in BULK:
        p = ROOT / b
        if not p.exists():
            out.append((b, 0, 0))
        elif p.is_file():
            out.append((b, 1, p.stat().st_size))
        else:
            n, total = 0, 0
            for f in p.rglob("*"):
                if f.is_file():
                    n += 1
                    total += f.stat().st_size
            out.append((b, n, total))
    return out


def git_state() -> dict[str, str]:
    """Record version-control state. Absence of commits is itself the finding."""
    def run(*args: str) -> str:
        try:
            r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                               text=True, timeout=30)
            return (r.stdout or r.stderr).strip()
        except Exception as exc:  # git absent or unusable
            return f"<unavailable: {exc}>"
    return {
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "commit_count": run("rev-list", "--count", "--all") or "0",
        "tracked_files": str(len([
            x for x in run("ls-files").splitlines() if x.strip()])),
        "remotes": run("remote", "-v") or "<none configured>",
    }


def main() -> int:
    rows = walk()
    bulk = bulk_summary()
    git = git_state()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh, fieldnames=["path", "category", "bytes", "mtime_utc", "sha256"])
        w.writeheader()
        w.writerows(rows)

    by_cat: dict[str, int] = {}
    for r in rows:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1

    lines = [
        "# Phase 0 — workspace inventory",
        "",
        f"**Generated:** {stamp}  ",
        f"**Machine:** Windows workspace `{ROOT}`  ",
        "**Generated by:** `route1/src/phase0_inventory.py`",
        "",
        "Hashes are the only provenance available for this workspace: the "
        "repository has no commits, so Git cannot establish which version "
        "produced any existing result. See the version-control section below.",
        "",
        "## Analysis-relevant files",
        "",
        f"{len(rows)} files hashed. Full listing with SHA-256 in "
        "`route1/manifests/source_registry.csv`.",
        "",
        "| Category | Files |",
        "|---|---:|",
    ]
    for cat in sorted(by_cat):
        lines.append(f"| {cat} | {by_cat[cat]} |")
    lines += [
        f"| **total** | **{len(rows)}** |",
        "",
        "## Bulk trees — summarised, not hashed",
        "",
        "Each carries its own checksums via a tracked `PROVENANCE.md`. Listed "
        "so their exclusion is explicit rather than silent.",
        "",
        "| Path | Files | Size |",
        "|---|---:|---:|",
    ]
    for b, n, total in bulk:
        size = f"{total / 1e9:.2f} GB" if total >= 1e9 else f"{total / 1e6:.1f} MB"
        lines.append(f"| `{b}` | {n} | {size if total else '—'} |")

    lines += [
        "",
        "## Version-control state",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| branch | `{git['branch']}` |",
        f"| commits (all refs) | **{git['commit_count']}** |",
        f"| tracked files | **{git['tracked_files']}** |",
        f"| remotes | `{git['remotes']}` |",
        "",
        "A `.gitignore` exists and was verified by dry-run in O-072, but was "
        "never committed against. Per the supervisor plan this phase does not "
        "initialise a public repository or push anything; this manifest is the "
        "local provenance substitute.",
        "",
        "## Known cross-machine divergence",
        "",
        "| Path | This (Windows) copy | Mac copy |",
        "|---|---|---|",
        "| `.agents/AGENTS.md`, `.agents/skills/` | present | absent (reported) |",
        "| `src/analysis/` | present (13 scripts) | absent (reported) |",
        "| `reports/research_2026_09_10_sources/` | **absent** | present (reported) |",
        "",
        "No file was merged, renamed or overwritten across copies. The Mac "
        "research reports are treated as incoming documents; their source "
        "captures are unavailable here, which is why every count used by "
        "Route 1 was re-derived locally rather than imported.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"hashed {len(rows)} analysis-relevant files")
    for cat in sorted(by_cat):
        print(f"  {cat:<18}{by_cat[cat]:>5}")
    print()
    print("bulk trees (not hashed):")
    for b, n, total in bulk:
        print(f"  {b:<40}{n:>7} files  {total / 1e9:>8.2f} GB")
    print()
    print(f"git: branch={git['branch']} commits={git['commit_count']} "
          f"tracked={git['tracked_files']}")
    print()
    print(f"wrote {OUT_CSV.relative_to(ROOT)}")
    print(f"wrote {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
