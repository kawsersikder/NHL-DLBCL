"""Phase 3R-B — freeze the identity-safe population.

Builds the deterministic one-sample-per-patient manifest ordered by the
supervisor, reconciles repeated records, and reports patient-level feasibility
counts (events, IPI completeness, follow-up) AFTER deduplication.

Three things this script is careful about:

1. **Identifier semantics are tested, not assumed.** Before treating
   ``pid_pmid_32187361`` as a patient key, samples sharing a pid are checked
   for agreement on fields that must be constant within a patient (sex, age at
   diagnosis, OS time, OS status). Disagreement would mean the field is not a
   patient identifier — or that the records need reconciliation before one can
   be chosen.

2. **Selection is outcome-independent and deterministic.** Hierarchy, per
   supervisor 2.2:
       (a) documented pretreatment specimen
       (b) validated technical-quality criterion
       (c) deterministic accession order for ties
   No sample is ever chosen because its expression or outcome is convenient.

3. **Counts are computed after deduplication.** A sample-weighted event count
   is not a patient-level event count, and reverse-KM must be recomputed on
   the deduplicated set.

The 243 eligible samples with no identifier are written to a separate file and
are excluded from supervised development entirely — including from
representation learning, since that could expose held-out patients.

Usage:
    python route1/src/phase3R_population.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from lifelines import KaplanMeierFitter

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "route1/data/metadata/gse181063_samples.csv"
OUT_PRIMARY = ROOT / "route1/manifests/population_primary.csv"
OUT_EXCLUDED = ROOT / "route1/manifests/population_excluded_unidentified.csv"
OUT_CONFLICTS = ROOT / "route1/manifests/population_duplicate_reconciliation.csv"

PID = "pid_pmid_32187361"
# Fields that MUST be constant within a true patient. Sex and age at diagnosis
# are immutable; OS time/status are patient-level outcomes, not sample-level.
INVARIANTS = ["Sex", "age_at_diagnosis", "os_followup_y", "os_status"]
# IPI components as released. `ipi_score` is the composite.
IPI_COMPONENTS = ["age_at_diagnosis", "performance_status_ecog", "Stage",
                  "ldh", "num_extranodal"]


def load() -> pd.DataFrame:
    df = pd.read_csv(SAMPLES, low_memory=False)
    df = df[df.eligible_route1].copy()
    assert len(df) == 556, f"expected 556 eligible samples, got {len(df)}"
    return df


def test_identifier_semantics(df: pd.DataFrame) -> pd.DataFrame:
    """Check whether samples sharing a pid agree on patient-invariant fields."""
    ident = df[df[PID].notna()].copy()
    bar = "=" * 78
    print(bar)
    print("IDENTIFIER SEMANTICS — is pid_pmid_32187361 behaving like a patient key?")
    print(bar)
    multi = ident.groupby(PID).filter(lambda g: len(g) > 1)
    groups = multi[PID].nunique()
    print(f"  identified eligible samples      {len(ident)}")
    print(f"  distinct pids                    {ident[PID].nunique()}")
    print(f"  pids with >1 eligible sample     {groups}")

    rows = []
    for pid, g in multi.groupby(PID):
        rec = {"patient_id": pid, "n_samples": len(g),
               "gsms": ";".join(sorted(g.gsm))}
        for col in INVARIANTS:
            vals = g[col].dropna().unique()
            rec[f"{col}_n_distinct"] = len(vals)
            rec[f"{col}_values"] = ";".join(map(str, vals))
        rec["any_conflict"] = any(
            rec[f"{c}_n_distinct"] > 1 for c in INVARIANTS)
        rows.append(rec)
    conflicts = pd.DataFrame(rows)

    if len(conflicts):
        n_conf = int(conflicts.any_conflict.sum())
        print(f"  groups with ANY invariant conflict  {n_conf} of {len(conflicts)}")
        for col in INVARIANTS:
            bad = int((conflicts[f"{col}_n_distinct"] > 1).sum())
            print(f"    {col:<22} disagrees in {bad} group(s)")
        if n_conf == 0:
            print("  -> consistent with a patient identifier; no reconciliation needed")
        else:
            print("  -> NOT fully consistent; conflicting groups need documented "
                  "resolution or exclusion")
    return conflicts


def select_representative(df: pd.DataFrame) -> pd.DataFrame:
    """One sample per patient, by the prescribed outcome-independent hierarchy."""
    ident = df[df[PID].notna()].copy()

    # (a) documented pretreatment specimen. All eligible samples already passed
    #     sample_pre_active_treatment == "Yes" in the cascade, so this criterion
    #     is satisfied by every candidate and cannot discriminate. Recorded
    #     rather than silently skipped.
    pre = (ident["sample_pre_active_treatment"] == "Yes")
    assert pre.all(), "eligible set should be entirely pretreatment"
    ident["rank_pretreatment"] = 0

    # (b) technical quality. qc_fail == 0 for all eligible samples (cascade), so
    #     the discriminating quality measure is probe_detection: higher is
    #     better. Outcome-independent.
    assert (ident["qc_fail"] == 0).all(), "eligible set should be qc_fail == 0"
    ident["rank_quality"] = -ident["probe_detection"].astype(float)

    # (c) deterministic tie-break on accession.
    ident = ident.sort_values(
        ["rank_pretreatment", "rank_quality", "gsm"], kind="mergesort")
    chosen = ident.groupby(PID, as_index=False).head(1).copy()
    chosen["selection_reason"] = "highest probe_detection; GSM order on ties"
    return chosen.sort_values("gsm").reset_index(drop=True)


def feasibility(primary: pd.DataFrame) -> None:
    """Patient-level counts AFTER deduplication."""
    bar = "=" * 78
    print()
    print(bar)
    print("PATIENT-LEVEL FEASIBILITY (after deduplication)")
    print(bar)
    n = len(primary)
    ev = int((primary.os_status == 1).sum())
    print(f"  patients                     {n}")
    print(f"  deaths (patient-level)       {ev}  ({ev / n:.1%})")

    km = KaplanMeierFitter().fit(primary.os_followup_y, 1 - primary.os_status)
    print(f"  reverse-KM median follow-up  {km.median_survival_time_:.2f} y")
    print(f"  follow-up range              {primary.os_followup_y.min():.4f} – "
          f"{primary.os_followup_y.max():.4f} y")

    print()
    print("  IPI availability:")
    obs = primary.ipi_score.notna()
    print(f"    observed ipi_score         {int(obs.sum())}  "
          f"(events {int((primary.os_status[obs] == 1).sum())})")
    comp = primary[IPI_COMPONENTS].notna().all(axis=1)
    print(f"    all 5 components present   {int(comp.sum())}  "
          f"(events {int((primary.os_status[comp] == 1).sum())})")
    either = obs | comp
    print(f"    observed OR reconstructable{int(either.sum()):>4}  "
          f"(events {int((primary.os_status[either] == 1).sum())})")
    print()
    print("  per-component missingness:")
    for c in IPI_COMPONENTS:
        miss = int(primary[c].isna().sum())
        print(f"    {c:<26}{miss:>4} missing ({miss / n:.1%})")

    print()
    print("  molecular subtype (pred_combine):")
    for k, v in primary.pred_combine.value_counts().items():
        print(f"    {k:<6}{v:>5}")


def main() -> int:
    df = load()
    conflicts = test_identifier_semantics(df)
    primary = select_representative(df)
    unidentified = df[df[PID].isna()].copy()

    print()
    print(f"  representative samples selected  {len(primary)}")
    print(f"  eligible samples with NO pid     {len(unidentified)}  "
          f"(EXCLUDED from all supervised development)")

    feasibility(primary)

    for path, frame in ((OUT_PRIMARY, primary),
                        (OUT_EXCLUDED, unidentified),
                        (OUT_CONFLICTS, conflicts)):
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(f"\nwrote {path.relative_to(ROOT)}  ({len(frame)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
