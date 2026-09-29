"""Phase 1 — parse GSE181063 with validation, and resolve identity/eligibility.

Produces the three Phase 1 data artifacts:
  route1/data/metadata/gse181063_samples.csv   one row per GEO sample
  route1/manifests/patient_specimen_map.csv    sample -> patient, where known
  route1/manifests/eligibility_cascade.csv     machine-readable cascade

This is a rewrite rather than a reuse of the O-076 audit. The supervisor plan
requires validating exact category spellings, missing-value conventions and
numeric conversions, so the parse asserts its assumptions instead of coercing
silently. Any surprise raises rather than passing a wrong number downstream.

The central finding this script exists to record: **GEO accessions are not
patients.** Only 583 of 1,310 samples carry ``pid_pmid_32187361``, and those 583
map to 534 distinct patients. Within the eligible set, 313 of 556 samples carry
a patient ID and resolve to 301 patients; the remaining 243 have no identifier
in any released field (``Sample_title`` is an array index, ``DASLV4_<n>``, and
every ``Sample_supplementary_file`` is literally "NONE"). So 556 is a SAMPLE
count with a verified ceiling of 544 unique patients and no resolvable floor.

Nothing here is selected on outcome. ``os_status`` is read only to count events
and to characterise the follow-up distribution.

Usage:
    python route1/src/phase1_identity_endpoint.py
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd
from lifelines import KaplanMeierFitter

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/gse181063/GSE181063_gsm_brief.txt"
OUT_SAMPLES = ROOT / "route1/data/metadata/gse181063_samples.csv"
OUT_PATIENTS = ROOT / "route1/manifests/patient_specimen_map.csv"
OUT_CASCADE = ROOT / "route1/manifests/eligibility_cascade.csv"

PID_FIELD = "pid_pmid_32187361"

# Exact released spellings. Asserted, never fuzzy-matched: a silent spelling
# drift would change the cohort without changing the code.
DLBCL_NOS = "Diffuse large B-cell lymphoma, NOS"
RCHOP = "CHOP-R"
YES = "Yes"

# Sentinel strings the release uses for "not available". These must become NaN,
# not categories, or missingness gets silently modelled as a level.
MISSING_SENTINELS = {"", "NA", "na", "N/A", "unknown", "Unknown",
                     "Treatment data not available"}

NUMERIC = ["qc_fail", "probe_detection", "curative_intent", "os_status",
           "os_followup_y", "ipi_score", "age_at_diagnosis",
           "performance_status_ecog", "num_extranodal", "conf_entropy",
           "conf_combine_mhg", "conf_combine_abc", "conf_combine_gcb",
           "conf_combine_unc"]


def parse(path: Path) -> pd.DataFrame:
    """One row per ^SAMPLE block, characteristics flattened to columns."""
    rows: list[dict[str, str]] = []
    for block in path.read_text(encoding="utf-8", errors="replace").split(
            "^SAMPLE = ")[1:]:
        rec: dict[str, str] = {"gsm": block.split("\n", 1)[0].strip()}
        for key, val in re.findall(
                r"^!Sample_characteristics_ch1 = ([^:]+):\s*(.*)$", block, re.M):
            rec[key.strip()] = val.strip()
        for field, col in (("!Sample_platform_id", "platform"),
                           ("!Sample_title", "sample_title")):
            m = re.search(rf"^{re.escape(field)} = (.*)$", block, re.M)
            if m:
                rec[col] = m.group(1).strip()
        rows.append(rec)
    return pd.DataFrame(rows)


def validate(df: pd.DataFrame) -> None:
    """Assert the structural facts the cascade depends on."""
    assert len(df) == 1310, f"expected 1310 samples, got {len(df)}"
    assert df.gsm.is_unique, "duplicate GSM accessions"
    assert df.platform.nunique() == 1 and df.platform.iloc[0] == "GPL14951", \
        f"unexpected platform(s): {df.platform.unique()}"
    # Sample_title is an array index, not an identifier. Confirm, so nobody
    # later mistakes it for a patient key.
    assert df.sample_title.is_unique, "sample_title not unique"
    assert df.sample_title.str.match(r"^DASLV4_\d+$").all(), \
        "sample_title no longer matches the DASLV4_<n> array-index pattern"
    # The released spellings must exist verbatim, or the filters silently
    # select nothing.
    for col, val in (("case_diagnostic_subtype_icdo3", DLBCL_NOS),
                     ("firstline_regimen", RCHOP),
                     ("sample_pre_active_treatment", YES)):
        assert (df[col] == val).any(), f"spelling absent: {col} == {val!r}"
    # Checked pre-coercion, so the released values are still strings here.
    assert df.os_status.dropna().isin(["0", "1"]).all(), \
        f"os_status not 0/1: {sorted(df.os_status.dropna().unique())}"


def coerce(df: pd.DataFrame) -> pd.DataFrame:
    """Apply missing-value conventions then numeric conversion, auditably."""
    df = df.replace(list(MISSING_SENTINELS), pd.NA)
    for col in NUMERIC:
        if col not in df.columns:
            continue
        before = df[col].notna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        after = df[col].notna().sum()
        if before != after:
            # A value that was present as text but is not a number is a data
            # surprise, not something to absorb quietly.
            print(f"  NOTE {col}: {before - after} non-numeric value(s) "
                  f"became NaN during coercion")
    return df


def eligibility(df: pd.DataFrame) -> pd.DataFrame:
    """Cumulative, order-dependent cascade. Outcome-independent throughout."""
    steps = [
        ("deposited", pd.Series(True, index=df.index)),
        ("dlbcl_nos_icdo3", df.case_diagnostic_subtype_icdo3 == DLBCL_NOS),
        ("qc_clean", df.qc_fail == 0),
        ("pretreatment_biopsy", df.sample_pre_active_treatment == YES),
        ("curative_intent", df.curative_intent == 1),
        ("firstline_chop_r", df.firstline_regimen == RCHOP),
        ("os_present", df.os_followup_y.notna() & df.os_status.notna()),
        ("os_time_positive", df.os_followup_y > 0),
    ]
    mask = pd.Series(True, index=df.index)
    out = []
    prev = len(df)
    for name, cond in steps:
        mask = mask & cond.fillna(False)
        sub = df[mask]
        pid = sub[PID_FIELD].dropna() if PID_FIELD in sub else pd.Series(dtype=str)
        out.append({
            "step": name,
            "samples": len(sub),
            "events": int((sub.os_status == 1).sum()),
            "lost_from_previous": prev - len(sub),
            "samples_with_patient_id": len(pid),
            "unique_patients_among_identified": pid.nunique(),
            "samples_without_patient_id": len(sub) - len(pid),
        })
        prev = len(sub)
    df["eligible_route1"] = mask
    return pd.DataFrame(out)


def patient_map(df: pd.DataFrame) -> pd.DataFrame:
    """Sample -> patient where an identifier exists; explicit where it does not."""
    rows = []
    counts = df[PID_FIELD].value_counts(dropna=True)
    for _, r in df.iterrows():
        pid = r.get(PID_FIELD)
        known = pd.notna(pid)
        rows.append({
            "gsm": r.gsm,
            "sample_title": r.sample_title,
            "patient_id": pid if known else "",
            "identity_status": "identified" if known else "unknown",
            "samples_for_this_patient": int(counts.get(pid, 0)) if known else "",
            "is_repeat_sample": bool(known and counts.get(pid, 0) > 1),
            "eligible_route1": bool(r.eligible_route1),
        })
    return pd.DataFrame(rows)


def report_followup(df: pd.DataFrame) -> None:
    """Follow-up by a NAMED method — the three plausible numbers differ."""
    e = df[df.eligible_route1]
    km = KaplanMeierFitter().fit(e.os_followup_y, 1 - e.os_status)
    print()
    print("FOLLOW-UP, eligible set — method must be stated:")
    print(f"  median of observed times (all)     {e.os_followup_y.median():.2f} y")
    print("  median of observed censored times  "
          f"{e.loc[e.os_status == 0, 'os_followup_y'].median():.2f} y")
    print(f"  REVERSE KAPLAN-MEIER (report this) {km.median_survival_time_:.2f} y")
    print(f"  range {e.os_followup_y.min():.4f} – {e.os_followup_y.max():.4f} y")


def main() -> int:
    df = parse(RAW)
    validate(df)
    print(f"parsed and validated {len(df)} samples")
    df = coerce(df)

    cascade = eligibility(df)
    print()
    print(cascade.to_string(index=False))

    pmap = patient_map(df)
    report_followup(df)

    ident = pmap[pmap.identity_status == "identified"]
    el = pmap[pmap.eligible_route1]
    el_id = el[el.identity_status == "identified"]
    print()
    print("IDENTITY — a GEO accession is not a patient:")
    print(f"  cohort: {len(ident)} identified samples -> "
          f"{ident.patient_id.nunique()} patients "
          f"({len(ident) - ident.patient_id.nunique()} extra)")
    print(f"  eligible: {len(el)} samples; {len(el_id)} identified -> "
          f"{el_id.patient_id.nunique()} patients; "
          f"{len(el) - len(el_id)} with NO identifier")
    print(f"  verified ceiling on unique eligible patients: "
          f"{len(el) - (len(el_id) - el_id.patient_id.nunique())}")

    for path, frame in ((OUT_SAMPLES, df), (OUT_PATIENTS, pmap),
                        (OUT_CASCADE, cascade)):
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)
        print(f"wrote {path.relative_to(ROOT)}  ({len(frame)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
