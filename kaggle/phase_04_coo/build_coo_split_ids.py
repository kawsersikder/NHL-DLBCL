"""S_COO — generate frozen nested-CV outer splits for Phase 4B COO (E-010).

Single authorised read of the label before E-010. Reads exactly
`patient_id` + `HANS` from the clinical table restricted to the 163 labelled
image-eligible patients. Never reads OS, never reads any image feature.

Stratifies on HANS (not OS — different task from Phase 3B). Writes
`data/manifests/coo_split_ids.csv` + `coo_split_ids_summary.json`.

Signature gate mirrors Phase 3B: refuses unless §13 of
`reports/phase_04_coo_analysis_protocol.md` carries name+date+lock hash
over §§1-11 + YAML twin (v1.1 incl. A001-A007).

Usage:
    python kaggle/phase_04_coo/build_coo_split_ids.py --print-hash
    python kaggle/phase_04_coo/build_coo_split_ids.py
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path
import pandas as pd
from sklearn.model_selection import RepeatedStratifiedKFold

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_MD = ROOT / "reports" / "phase_04_coo_analysis_protocol.md"
PROTOCOL_YAML = ROOT / "configs" / "phase_04_coo_analysis_protocol.yaml"
CLINICAL = ROOT / "data" / "raw" / "dlbcl_morph" / "clinical_data_cleaned.csv"
MANIFEST = ROOT / "data" / "manifests" / "patient_manifest.csv"
OUT_CSV = ROOT / "data" / "manifests" / "coo_split_ids.csv"
OUT_JSON = ROOT / "data" / "manifests" / "coo_split_ids_summary.json"

SEED = 20260903
OUTER_FOLDS = 5
OUTER_REPEATS = 10
LABEL = "HANS"
EXPECTED_N = 163
EXPECTED_GCB = 70
SIGNOFF_HEADING = "## 13. Sign-off"

def lock_hash() -> str:
    text = PROTOCOL_MD.read_text(encoding="utf-8").replace("\r\n", "\n")
    if SIGNOFF_HEADING not in text:
        sys.exit(f"ABORT: {PROTOCOL_MD} has no '{SIGNOFF_HEADING}'")
    body = text.split(SIGNOFF_HEADING)[0]
    twin = PROTOCOL_YAML.read_text(encoding="utf-8").replace("\r\n", "\n")
    bd = hashlib.sha256(body.encode()).hexdigest()
    td = hashlib.sha256(twin.encode()).hexdigest()
    return hashlib.sha256(f"{bd}:{td}".encode()).hexdigest()

def require_signature(expected: str) -> None:
    text = PROTOCOL_MD.read_text(encoding="utf-8").replace("\r\n", "\n")
    signoff = text.split(SIGNOFF_HEADING)[1]
    m = re.search(r"^\|\s*Researcher\s*\|(.*)\|\s*$", signoff, re.MULTILINE)
    if not m:
        sys.exit("ABORT: no Researcher row in §13")
    cells = [c.strip() for c in m.group(1).split("|")]
    if len(cells) != 3 or not all(cells):
        sys.exit(f"ABORT: protocol unsigned. Expected hash:\n    {expected}\nFill §13 name|date|hash first.")
    if cells[2].lower() != expected.lower():
        sys.exit(f"ABORT: §13 hash {cells[2][:12]}… != computed {expected[:12]}… — protocol changed after signing.")

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print-hash", action="store_true")
    args = ap.parse_args()
    h = lock_hash()
    if args.print_hash:
        print(h)
        return
    require_signature(h)
    clin = pd.read_csv(CLINICAL, usecols=["patient_id", LABEL])
    man = pd.read_csv(MANIFEST)
    eligible = set(man.loc[man["image_eligible"] == 1, "patient_id"].astype(int))
    # labelled image-eligible = Cohort A_COO
    df = clin[clin["patient_id"].isin(eligible) & clin[LABEL].notna()].copy()
    df[LABEL] = df[LABEL].astype(int)
    assert len(df) == EXPECTED_N, f"n={len(df)} != {EXPECTED_N}"
    assert (df[LABEL] == 1).sum() == EXPECTED_GCB, "GCB count drift"
    assert set(df[LABEL].unique()) <= {0, 1}
    X = df["patient_id"].to_numpy()
    y = df[LABEL].to_numpy()
    rskf = RepeatedStratifiedKFold(n_splits=OUTER_FOLDS, n_repeats=OUTER_REPEATS, random_state=SEED)
    out = []
    for idx, (_, te_idx) in enumerate(rskf.split(X, y)):
        rep = idx // OUTER_FOLDS + 1
        fold = idx % OUTER_FOLDS + 1
        for i in te_idx:
            out.append({"patient_id": int(X[i]), "repeat": rep, "outer_fold": fold})
    sodd = pd.DataFrame(out)
    assert len(sodd) == EXPECTED_N * OUTER_REPEATS, f"rows {len(sodd)}"  # each repeat holds all 163 once across 5 folds
    # per-fold sizes 32-33, minority ~14
    grp = sodd.merge(df, on="patient_id")
    sizes = grp.groupby(["repeat", "outer_fold"]).size()
    assert sizes.min() >= 32 and sizes.max() <= 33, sizes.describe().to_dict()
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    sodd.to_csv(OUT_CSV, index=False)
    summary = {
        "n": int(EXPECTED_N), "gcb": int(EXPECTED_GCB), "non_gcb": int(EXPECTED_N - EXPECTED_GCB),
        "outer_folds": OUTER_FOLDS, "outer_repeats": OUTER_REPEATS, "seed_base": SEED,
        "fold_size": "32-33", "protocol_lock_hash": h,
        "sha256_coo_split_ids_csv": hashlib.sha256(OUT_CSV.read_bytes()).hexdigest(),
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"WROTE {OUT_CSV} ({len(sodd)} rows) + summary. lock {h[:12]}…")

if __name__ == "__main__":
    main()
