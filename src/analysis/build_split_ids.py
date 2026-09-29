"""Step S2 — generate the frozen nested-CV outer splits. Blindness ends here.

This is the single authorised read of the outcome before E-009. It reads exactly
two clinical columns, `patient_id` and `Follow-up Status`, and writes
`data/manifests/split_ids.csv`. It never reads `OS`, and it never reads any
image feature. Every model in the protocol ladder consumes this one file, so
that all paired comparisons share identical outer folds.

The protocol signature is enforced mechanically. The script refuses to run
unless section 13 of the protocol carries a researcher name, a date, and the
lock hash of the protocol's own frozen body — so a protocol edited after signing
fails the gate rather than passing quietly.

    python src/analysis/build_split_ids.py --print-hash   # before signing
    python src/analysis/build_split_ids.py                # after signing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import RepeatedStratifiedKFold


EXPECTED_PATIENTS = 170
EXPECTED_EVENTS = 58
SEED = 20260830
OUTER_FOLDS = 5
OUTER_REPEATS = 10
EVENT_COLUMN = "Follow-up Status"
SIGNOFF_HEADING = "## 13. Sign-off"


def lock_hash(protocol_md: Path, protocol_yaml: Path) -> str:
    """Hash the frozen protocol body plus its machine-readable twin.

    The sign-off section itself is excluded, otherwise writing the hash into the
    document would change the hash. Line endings are normalised so a Windows and
    a Unix checkout agree.
    """
    text = protocol_md.read_text(encoding="utf-8").replace("\r\n", "\n")
    if SIGNOFF_HEADING not in text:
        sys.exit(f"ABORT: {protocol_md} has no '{SIGNOFF_HEADING}' section")
    body = text.split(SIGNOFF_HEADING)[0]
    twin = protocol_yaml.read_text(encoding="utf-8").replace("\r\n", "\n")

    body_digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    twin_digest = hashlib.sha256(twin.encode("utf-8")).hexdigest()
    return hashlib.sha256(f"{body_digest}:{twin_digest}".encode("utf-8")).hexdigest()


def require_signature(protocol_md: Path, expected: str) -> dict[str, str]:
    """Parse the section 13 Researcher row and verify it against `expected`."""
    text = protocol_md.read_text(encoding="utf-8").replace("\r\n", "\n")
    signoff = text.split(SIGNOFF_HEADING)[1]

    match = re.search(r"^\|\s*Researcher\s*\|(.*)\|\s*$", signoff, re.MULTILINE)
    if not match:
        sys.exit("ABORT: no Researcher row found in protocol section 13")
    cells = [cell.strip() for cell in match.group(1).split("|")]
    if len(cells) != 3:
        sys.exit(f"ABORT: Researcher row has {len(cells)} cells, expected 3")

    name, date, recorded = cells
    if not name or not date or not recorded:
        sys.exit(
            "ABORT: protocol is unsigned.\n"
            "  Section 13 needs a name, a date, and this lock hash:\n"
            f"    {expected}\n"
            "  Read the protocol critically first. Signing freezes sections 1-11."
        )
    if recorded.lower() != expected:
        sys.exit(
            "ABORT: protocol lock hash mismatch. The protocol changed after signing.\n"
            f"  recorded: {recorded}\n"
            f"  actual:   {expected}\n"
            "  Either revert the edit, or record it in the section 12 amendment log\n"
            "  and re-sign — before looking at any result."
        )
    return {"researcher": name, "date": date, "lock_hash": expected}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--protocol-md",
        type=Path,
        default=Path("reports/phase_03b_statistical_analysis_protocol.md"),
    )
    parser.add_argument(
        "--protocol-yaml",
        type=Path,
        default=Path("configs/phase_03b_analysis_protocol.yaml"),
    )
    parser.add_argument(
        "--clinical",
        type=Path,
        default=Path("data/raw/dlbcl_morph/clinical_data_cleaned.csv"),
    )
    parser.add_argument(
        "--features",
        type=Path,
        default=Path(
            "kaggle/phase_03_morphology_survival/output_e007_full_extraction/patient_features.csv"
        ),
        help="Cohort A membership; only the patient_id column is read.",
    )
    parser.add_argument("--out", type=Path, default=Path("data/manifests/split_ids.csv"))
    parser.add_argument(
        "--print-hash",
        action="store_true",
        help="Print the protocol lock hash and exit without touching the outcome.",
    )
    args = parser.parse_args()

    expected = lock_hash(args.protocol_md, args.protocol_yaml)
    if args.print_hash:
        print(f"Protocol lock hash (paste into section 13):\n  {expected}")
        return 0

    signature = require_signature(args.protocol_md, expected)
    print(f"protocol signed by {signature['researcher']} on {signature['date']}: gate PASS")
    print("reading the OS event indicator now. Blindness ends at this line.")

    cohort = pd.read_csv(args.features, usecols=["patient_id"], dtype=str)
    patients = sorted(cohort["patient_id"].unique(), key=int)
    if len(patients) != EXPECTED_PATIENTS:
        sys.exit(f"ABORT: cohort A has {len(patients)} patients, expected {EXPECTED_PATIENTS}")

    clinical = pd.read_csv(
        args.clinical, usecols=["patient_id", EVENT_COLUMN], dtype={"patient_id": str}
    )
    frame = pd.DataFrame({"patient_id": patients}).merge(clinical, on="patient_id", how="left")
    if frame[EVENT_COLUMN].isna().any():
        sys.exit("ABORT: cohort A patients missing an event indicator; join rule violated")

    events = frame[EVENT_COLUMN].astype(int).to_numpy()
    if set(np.unique(events)) - {0, 1}:
        sys.exit(f"ABORT: event indicator is not binary: {np.unique(events)}")
    print(f"cohort A: {len(frame)} patients, {int(events.sum())} events")
    if int(events.sum()) != EXPECTED_EVENTS:
        sys.exit(
            f"ABORT: {int(events.sum())} events, protocol section 1.4 states {EXPECTED_EVENTS}"
        )

    splitter = RepeatedStratifiedKFold(
        n_splits=OUTER_FOLDS, n_repeats=OUTER_REPEATS, random_state=SEED
    )
    rows = []
    for index, (_, test_index) in enumerate(splitter.split(np.zeros(len(frame)), events)):
        for position in test_index:
            rows.append(
                {
                    "patient_id": frame.at[position, "patient_id"],
                    "repeat": index // OUTER_FOLDS + 1,
                    "outer_fold": index % OUTER_FOLDS + 1,
                }
            )
    splits = pd.DataFrame(rows).sort_values(
        by=["repeat", "outer_fold", "patient_id"],
        key=lambda column: column.astype(int) if column.name == "patient_id" else column,
    ).reset_index(drop=True)

    # Each repeat must partition cohort A exactly once.
    expected_rows = EXPECTED_PATIENTS * OUTER_REPEATS
    if len(splits) != expected_rows:
        sys.exit(f"ABORT: {len(splits)} rows, expected {expected_rows}")
    for repeat, group in splits.groupby("repeat"):
        if sorted(group["patient_id"], key=int) != patients:
            sys.exit(f"ABORT: repeat {repeat} is not an exact partition of cohort A")

    event_map = dict(zip(frame["patient_id"], events))
    fold_events = (
        splits.assign(event=splits["patient_id"].map(event_map))
        .groupby(["repeat", "outer_fold"])["event"]
        .agg(["size", "sum"])
    )
    print(
        f"held-out events per fold: min {int(fold_events['sum'].min())}, "
        f"max {int(fold_events['sum'].max())}"
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    splits.to_csv(args.out, index=False)
    digest = hashlib.sha256(args.out.read_bytes()).hexdigest()

    summary = {
        "step": "S2",
        "protocol_section": "5.3",
        "protocol_lock_hash": signature["lock_hash"],
        "signed_by": signature["researcher"],
        "signed_date": signature["date"],
        "columns_read_from_clinical": ["patient_id", EVENT_COLUMN],
        "seed": SEED,
        "outer_folds": OUTER_FOLDS,
        "outer_repeats": OUTER_REPEATS,
        "stratified_on": EVENT_COLUMN,
        "patients": EXPECTED_PATIENTS,
        "events": int(events.sum()),
        "held_out_events_per_fold": {
            "min": int(fold_events["sum"].min()),
            "max": int(fold_events["sum"].max()),
        },
        "split_ids_sha256": digest,
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
    }
    summary_path = args.out.parent / "split_ids_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"\nwrote {args.out}")
    print(f"wrote {summary_path}")
    print(f"  sha256(split_ids.csv) = {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
