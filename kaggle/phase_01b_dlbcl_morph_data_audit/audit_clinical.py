"""Phase 1b — DLBCL-Morph clinical table audit.

Reads the TCIA clinical CSV and reports cohort size, survival event counts,
follow-up distributions and per-variable missingness. Read-only: this script
never writes back to the raw data.

Usage:
    python audit_clinical.py --clinical-csv <path>/clinical_data_cleaned.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

EXPECTED_N_PATIENTS = 209


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clinical-csv", type=Path, required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.clinical_csv)

    print("=" * 70)
    print("DLBCL-Morph clinical table audit")
    print("=" * 70)
    print(f"\nRows: {len(df)}   Unique patient_id: {df['patient_id'].nunique()}")
    print(f"Duplicate patient_id rows: {len(df) - df['patient_id'].nunique()}")

    # ── Survival outcomes ────────────────────────────────────────────
    event_col = "Follow-up Status"
    os_col, pfs_col = "OS", "PFS"
    events = int(df[event_col].sum())
    censored = len(df) - events
    print(f"\nOS events (Follow-up Status == 1): {events}/{len(df)} "
          f"({events / len(df):.1%})   censored: {censored}")
    for col in (os_col, pfs_col):
        s = df[col]
        print(f"\n{col} (years): min={s.min():.2f} median={s.median():.2f} "
              f"max={s.max():.2f} missing={s.isna().sum()}")
        dead = df.loc[df[event_col] == 1, col]
        alive = df.loc[df[event_col] == 0, col]
        print(f"  events:  n={dead.size} median={dead.median():.2f} "
              f"range=[{dead.min():.2f}, {dead.max():.2f}]")
        print(f"  censored: n={alive.size} median={alive.median():.2f} "
              f"range=[{alive.min():.2f}, {alive.max():.2f}]")
    neg_os = int((df[os_col] <= 0).sum())
    print(f"\nNon-positive OS times: {neg_os}")
    pfs_events_possible = "no progression-status column exists; " \
        "PFS is time-only — competing-risk/PFS modelling not supported by this table"

    # ── Missingness per variable ─────────────────────────────────────
    print("\nMissingness per variable:")
    for col in df.columns:
        n_miss = int(df[col].isna().sum())
        flag = "  <-- " if n_miss > 0 else ""
        print(f"  {col:30s} missing {n_miss:3d}/{len(df)} ({n_miss/len(df):5.1%}){flag}")

    # ── Clinical predictors for baselines ────────────────────────────
    print("\nClinical predictor summary:")
    for col in ("Age", "ECOG PS", "LDH", "EN", "Stage", "IPI Score",
                "IPI Risk Group (4 Class)", "RIPI Risk Group"):
        if col not in df.columns:
            print(f"  {col}: NOT PRESENT")
            continue
        s = df[col]
        if s.nunique() <= 12:
            counts = s.value_counts(dropna=False).sort_index()
            print(f"  {col}: {dict(counts)}")
        else:
            print(f"  {col}: median={s.median()} range=[{s.min()}, {s.max()}]")

    # IPI component availability (for Baseline 0 and NCCN-IPI feasibility)
    print("\nIPI/R-IPI availability:")
    print(f"  IPI Score present: {'IPI Score' in df.columns} "
          f"(missing {int(df['IPI Score'].isna().sum())})")
    print(f"  RIPI Risk Group present: {'RIPI Risk Group' in df.columns} "
          f"(missing {int(df['RIPI Risk Group'].isna().sum())})")
    print("  NCCN-IPI: NOT directly computable — LDH is binary (1=elevated), "
          "NCCN-IPI needs LDH as a multiple of the upper limit of normal")

    # Events-per-variable and split feasibility
    print("\nSplit feasibility (roadmap evaluation rule 2):")
    test_events = round(0.2 * events)
    print(f"  20% locked test -> ~{test_events} OS events expected "
          f"(of ~{round(0.2*len(df))} patients)")
    print(f"  R-001 guidance: if test events < ~25, prefer repeated nested "
          f"patient-level CV as the primary internal estimate")

    if len(df) != EXPECTED_N_PATIENTS:
        print(f"\nWARNING: expected {EXPECTED_N_PATIENTS} patients, got {len(df)}")
    print(f"\nNote: {pfs_events_possible}")


if __name__ == "__main__":
    main()
