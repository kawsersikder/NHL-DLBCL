"""Verify the Phase 3B feature partition against the frozen E-007 feature cache.

Outcome-blind by construction: reads only the ``patient_features.csv`` header and
the protocol YAML. No outcome column is opened.

Checks performed:
  1. each declared family expands to its declared column count;
  2. the families are pairwise disjoint;
  3. their union covers every E-007 feature column exactly (no unassigned
     column, no phantom column);
  4. the cross-cutting central/spread/heterogeneity views have the declared
     sizes; and
  5. the model-ladder feature counts are arithmetically consistent.

Run this before signing the protocol, and again before E-009, so a silent edit
to either the protocol or the feature cache cannot go unnoticed.

Usage:
    python src/analysis/verify_protocol_partition.py [--root .]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd
import yaml

FEATURES_REL = (
    "kaggle/phase_03_morphology_survival/output_e007_full_extraction/"
    "patient_features.csv"
)
CONFIG_REL = "configs/phase_03b_analysis_protocol.yaml"
DOC_REL = "reports/phase_03b_statistical_analysis_protocol.md"

SUFFIXES = ("median", "iqr", "p10", "p90")
SPREAD_SUFFIXES = {"iqr", "p10", "p90"}


def expand(bases: list[str]) -> list[str]:
    """Expand feature bases across the frozen aggregation suffixes."""
    return [f"{base}_{suffix}" for base in bases for suffix in SUFFIXES]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=Path(__file__).resolve().parents[2],
                        type=Path, help="Project root (default: inferred)")
    args = parser.parse_args()

    root: Path = args.root
    config_path = root / CONFIG_REL
    doc_path = root / DOC_REL
    features_path = root / FEATURES_REL

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    families = cfg["feature_families"]

    actual = [c for c in pd.read_csv(features_path, nrows=0).columns
              if c != "patient_id"]

    groups = {
        "F0": (list(families["F0_qc_exposure"]["columns"]),
               families["F0_qc_exposure"]["count"]),
        "F1a": (expand(families["F1_morphology"]["F1a_shape"]["bases"]),
                families["F1_morphology"]["F1a_shape"]["count"]),
        "F1b": (expand(families["F1_morphology"]["F1b_stain"]["bases"]),
                families["F1_morphology"]["F1b_stain"]["count"]),
        "F2": (expand(families["F2_packing"]["bases"]),
               families["F2_packing"]["count"]),
    }

    ok = True
    print("=== declared vs expanded family sizes ===")
    for name, (cols, declared) in groups.items():
        passed = len(cols) == declared
        ok &= passed
        print(f"  {'OK ' if passed else 'BAD'} {name:4} "
              f"expanded={len(cols):3}  declared={declared}")

    union = [c for cols, _ in groups.values() for c in cols]

    print(f"\ntotal expanded : {len(union)}")
    print(f"declared total : {families['total_feature_columns']}")
    print(f"actual in file : {len(actual)}")
    ok &= len(union) == families["total_feature_columns"] == len(actual)

    duplicates = sorted({c for c in union if union.count(c) > 1})
    if duplicates:
        ok = False
        print(f"\nDUPLICATES ACROSS FAMILIES: {duplicates}")
    else:
        print("\nno duplicates across families (partition is disjoint)")

    unassigned = sorted(set(actual) - set(union))
    phantom = sorted(set(union) - set(actual))
    if unassigned:
        ok = False
        print(f"\nIN FILE BUT UNASSIGNED ({len(unassigned)}):")
        for col in unassigned:
            print("   ", col)
    if phantom:
        ok = False
        print(f"\nIN PROTOCOL BUT NOT IN FILE ({len(phantom)}):")
        for col in phantom:
            print("   ", col)
    if not unassigned and not phantom:
        print("partition covers every E-007 column exactly")

    predictors = [c for name, (cols, _) in groups.items()
                  if name != "F0" for c in cols]
    views = families["cross_cutting_views"]
    print("\n=== cross-cutting views ===")
    for label, got, declared in [
        ("central_tendency",
         sum(c.endswith("_median") for c in predictors),
         views["central_tendency"]["count"]),
        ("spread",
         sum(c.rsplit("_", 1)[-1] in SPREAD_SUFFIXES for c in predictors),
         views["spread_heterogeneity"]["count"]),
        ("patch_heterogeneity",
         sum(c.rsplit("_", 1)[-1] in SPREAD_SUFFIXES for c in groups["F2"][0]),
         views["patch_to_patch_heterogeneity"]["count"]),
    ]:
        passed = got == declared
        ok &= passed
        print(f"  {'OK ' if passed else 'BAD'} {label:20} "
              f"got={got:3} declared={declared}")

    ladder = {m["id"]: m for m in cfg["model_ladder"]}
    n_f1 = len(groups["F1a"][0]) + len(groups["F1b"][0])
    n_f2 = len(groups["F2"][0])
    print("\n=== ladder arithmetic ===")
    for label, declared, computed in [
        ("M4a == F1", ladder["M4a"]["k"], n_f1),
        ("M4b == F2", ladder["M4b"]["k"], n_f2),
        ("M4c == F1+F2", ladder["M4c"]["k"], n_f1 + n_f2),
        ("M5 == M1+M4c", ladder["M5"]["k"],
         ladder["M1"]["k"] + ladder["M4c"]["k"]),
    ]:
        passed = declared == computed
        ok &= passed
        print(f"  {'OK ' if passed else 'BAD'} {label:16} "
              f"declared={declared:3} computed={computed}")

    print("\n=== document hashes (record these at sign-off) ===")
    for path in (doc_path, config_path):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"  {path.name:48} {digest}")

    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
