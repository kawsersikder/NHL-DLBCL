"""Build the per-patient stain availability manifest for DLBCL-Morph.

Route 2 of the 2026-09-10 research assessment proposes distilling a multistain
IHC teacher into an H&E-only Hans-subtype student, with explicit handling of
*missing* stains. Whether that proposal is worth pursuing depends on a number
nobody had computed: how many patients actually have a complete stain panel as
IMAGES.

This distinction matters and is easy to get wrong. The clinical table carries
scored percent-positive columns (``CD10 IHC``, ``BCL6 IHC``, ``MUM1 IHC``) and a
derived ``HANS`` label. Those are *scores*, not images. A multistain teacher
consumes patch directories under ``DLBCLMorph/Patches/<STAIN>/<patient_id>/``,
which are released for a smaller set of patients. ``phase_04_coo_study_scope.md``
reports 158 patients with a complete Hans panel; that is the scored-column count.
The image count is materially lower, and using 158 to size a teacher would
overstate its training set.

The manifest below is emitted per patient so downstream code never has to
re-derive availability, and so the teacher/student/masking partitions are
auditable rather than implicit.

Definitions used here:
    student-trainable  H&E images AND a non-missing HANS label
    teacher-trainable  student-trainable AND all three Hans stain IMAGES
                       (CD10, BCL6, MUM1) present
    masking-required   student-trainable but NOT teacher-trainable

No outcome or subtype modelling happens in this script, and nothing is filtered
on OS/PFS. It is a pure availability audit.

Usage:
    python src/analysis/build_stain_availability_manifest.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CLINICAL = ROOT / "data/raw/dlbcl_morph/clinical_data_cleaned.csv"
PATCHES = ROOT / "DLBCLMorph/Patches"
OUT_CSV = ROOT / "reports/phase_04_stain_availability_manifest.csv"

# HE first: it is the student's input. The rest are the released IHC stains.
STAINS = ["HE", "CD10", "BCL6", "MUM1", "BCL2", "MYC"]
# The Hans decision tree (Hans et al., Blood 2004) reads exactly these three.
HANS_STAINS = ["CD10", "BCL6", "MUM1"]


def scan_patches() -> tuple[dict[str, set[int]], dict[tuple[str, int], int]]:
    """Return, per stain, the patient ids present and the patch count for each.

    Patient ids are directory names under each stain directory. They are
    integers in the released archive; a non-integer directory would be a
    packaging change worth failing loudly on rather than silently skipping.
    """
    present: dict[str, set[int]] = {}
    counts: dict[tuple[str, int], int] = {}
    for stain in STAINS:
        stain_dir = PATCHES / stain
        if not stain_dir.is_dir():
            raise FileNotFoundError(
                f"missing stain directory {stain_dir} — is DLBCLMorph extracted?"
            )
        ids: set[int] = set()
        for child in stain_dir.iterdir():
            if not child.is_dir():
                continue
            ids.add(int(child.name))
            counts[(stain, int(child.name))] = sum(
                1 for f in child.iterdir() if f.is_file()
            )
        present[stain] = ids
    return present, counts


def build(df: pd.DataFrame, present: dict[str, set[int]],
          counts: dict[tuple[str, int], int]) -> pd.DataFrame:
    """Assemble the per-patient manifest.

    The union of clinical rows and imaged patients is used, not just the
    clinical table: the archive ships stain images for patients absent from the
    cleaned clinical file, and hiding them would misreport coverage.
    """
    all_ids = set(df.patient_id) | set().union(*present.values())
    rows = []
    scored = df.set_index("patient_id")
    for pid in sorted(all_ids):
        row: dict[str, object] = {"patient_id": pid}
        row["in_clinical"] = pid in scored.index
        for stain in STAINS:
            row[f"img_{stain}"] = pid in present[stain]
            row[f"n_patches_{stain}"] = counts.get((stain, pid), 0)
        # Scored columns, kept alongside the image flags so the two notions of
        # "has CD10" can be compared directly rather than conflated.
        for stain in HANS_STAINS:
            col = f"{stain} IHC"
            row[f"scored_{stain}"] = (
                bool(pd.notna(scored.at[pid, col])) if pid in scored.index else False
            )
        has_label = (
            bool(pd.notna(scored.at[pid, "HANS"])) if pid in scored.index else False
        )
        row["hans_label"] = (
            scored.at[pid, "HANS"] if has_label else pd.NA
        )
        row["has_hans_label"] = has_label
        row["hans_panel_images"] = all(row[f"img_{s}"] for s in HANS_STAINS)
        row["hans_panel_scored"] = all(row[f"scored_{s}"] for s in HANS_STAINS)

        row["student_trainable"] = row["img_HE"] and has_label
        row["teacher_trainable"] = row["student_trainable"] and row["hans_panel_images"]
        row["masking_required"] = (
            row["student_trainable"] and not row["teacher_trainable"]
        )
        rows.append(row)
    return pd.DataFrame(rows)


def report(man: pd.DataFrame) -> None:
    """Print the counts that decide whether Route 2 is feasible."""
    bar = "=" * 72
    print(bar)
    print("STAIN IMAGE AVAILABILITY (patients with >=1 patch)")
    print(bar)
    for stain in STAINS:
        n = int(man[f"img_{stain}"].sum())
        patches = int(man[f"n_patches_{stain}"].sum())
        print(f"  {stain:<5} {n:>4} patients   {patches:>7} patches")

    print()
    print(bar)
    print("SCORED vs IMAGE Hans panel — these are NOT the same number")
    print(bar)
    print(f"  complete Hans panel, scored columns : {int(man.hans_panel_scored.sum()):>4}")
    print(f"  complete Hans panel, stain images   : {int(man.hans_panel_images.sum()):>4}")

    print()
    print(bar)
    print("ROUTE 2 PARTITIONS")
    print(bar)
    st = int(man.student_trainable.sum())
    te = int(man.teacher_trainable.sum())
    mk = int(man.masking_required.sum())
    print(f"  student-trainable (H&E + HANS label): {st:>4}")
    print(f"  teacher-trainable (+ Hans images)   : {te:>4}")
    print(f"  masking-required                    : {mk:>4}"
          f"  ({mk / st:.1%} of student set)" if st else "")

    print()
    print("  Hans label balance, student-trainable set:")
    vc = man.loc[man.student_trainable, "hans_label"].value_counts(dropna=False)
    for k, v in vc.items():
        print(f"    HANS={k}: {v}")

    print()
    print(bar)
    print("MISSINGNESS BY STAIN within the student-trainable set")
    print(bar)
    sub = man[man.student_trainable]
    for stain in HANS_STAINS + ["BCL2", "MYC"]:
        missing = int((~sub[f"img_{stain}"]).sum())
        print(f"  {stain:<5} missing images for {missing:>3} / {len(sub)} patients")


def main() -> int:
    df = pd.read_csv(CLINICAL)
    present, counts = scan_patches()
    man = build(df, present, counts)
    report(man)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    man.to_csv(OUT_CSV, index=False)
    print()
    print(f"wrote {OUT_CSV.relative_to(ROOT)}  ({len(man)} patients)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
