"""Phase 2 — audit candidate external cohorts and emit the cohort catalog.

Applies the Phase 1 discipline to GSE31312, GSE10846 and GSE87371: what is
actually present in the released metadata, how many samples survive a
treatment-matched and disease-scoped filter, and how many events remain.

Three findings this script encodes so they cannot be lost:

1. **GSE31312 carries no outcome or clinical data in GEO at all** — only
   ``immunohistochemistry subgroup`` and ``gene expression profiling
   subgroup``. Its 498 samples cannot be used for survival without obtaining
   the publication's separate clinical supplement.

2. **GSE10846's 6 unexplained accessions are GSM361239-GSM361244**, which carry
   ``NA`` for every clinical field. 420 deposited = 414 annotated + these 6.

3. **GSE87371 inverts the event indicator.** ``cens_os = 1`` means
   censored/alive and ``0`` means died — the opposite of GSE181063's
   ``os_status``. Established empirically (the ``cens_os = 0`` group has median
   OS 14.8 months versus 40.0 for ``cens_os = 1``; deaths are observed earlier)
   and asserted below so a future edit cannot silently flip it. Reading it the
   conventional way would invert every survival conclusion.

Units differ across cohorts and are NOT harmonised here: GSE181063 and
GSE10846 record years, GSE87371 records months. Harmonisation belongs in
Phase 3/4 under an explicit rule.

Usage:
    python route1/src/phase2_cohort_audit.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "route1/data/raw"
OUT = ROOT / "route1/manifests/cohort_catalog.csv"


def parse(path: Path) -> pd.DataFrame:
    """One row per sample. ``Clinical info`` sub-keys are flattened to ci_*."""
    rows = []
    for block in path.read_text(encoding="utf-8", errors="replace").split(
            "^SAMPLE = ")[1:]:
        rec = {"gsm": block.split("\n", 1)[0].strip()}
        for key, val in re.findall(
                r"^!Sample_characteristics_ch1 = ([^:]+):\s*(.*)$", block, re.M):
            key = key.strip()
            if key == "Clinical info" and ":" in val:
                sub, sv = val.split(":", 1)
                rec[f"ci_{sub.strip()}"] = sv.strip()
            elif key != "Clinical info":
                rec[key] = val.strip()
        m = re.search(r"^!Sample_platform_id = (.*)$", block, re.M)
        if m:
            rec["platform"] = m.group(1).strip()
        rows.append(rec)
    return pd.DataFrame(rows)


def audit_31312() -> dict:
    df = parse(RAW / "GSE31312_gsm_brief.txt")
    fields = [c for c in df.columns if c not in ("gsm", "platform")]
    return {
        "accession": "GSE31312", "platform": df.platform.iloc[0],
        "deposited_samples": len(df),
        "patient_key_field": "", "unique_patients": "",
        "has_os_time": False, "has_os_event": False, "has_ipi_components": False,
        "treatment_field": "", "treatment_matched_n": 0, "events_in_matched": 0,
        "time_units": "",
        "usable_from_geo_alone": False,
        "note": ("only fields are " + "; ".join(fields) +
                 " — no outcome, treatment or clinical data in GEO; "
                 "requires the publication clinical supplement (475 cases)"),
    }


def audit_10846() -> dict:
    df = parse(RAW / "GSE10846_gsm_brief.txt")
    orphans = sorted(df.loc[df["ci_Chemotherapy"] == "NA", "gsm"])
    assert orphans == ["GSM361239", "GSM361240", "GSM361241", "GSM361242",
                       "GSM361243", "GSM361244"], \
        f"the 6 unannotated accessions changed: {orphans}"
    r = df[df["ci_Chemotherapy"] == "R-CHOP-Like Regimen"]
    return {
        "accession": "GSE10846", "platform": df.platform.iloc[0],
        "deposited_samples": len(df),
        "patient_key_field": "Individual",
        "unique_patients": int(df.loc[df["Individual"] != "NA",
                                      "Individual"].nunique()),
        "has_os_time": True, "has_os_event": True, "has_ipi_components": True,
        "treatment_field": "Clinical info: Chemotherapy",
        "treatment_matched_n": len(r),
        "events_in_matched": int((r["ci_Follow up status"] == "DEAD").sum()),
        "time_units": "years",
        "usable_from_geo_alone": True,
        "note": ("R-CHOP-Like 233 / CHOP-Like 181 / NA 6 "
                 "(the NA 6 are GSM361239-GSM361244, no clinical data). "
                 "COMPROMISED AS FINAL TEST: used for COO classifier "
                 "development in Care 2013 (PMC3570548)"),
    }


def audit_87371() -> dict:
    df = parse(RAW / "GSE87371_gsm_brief.txt")
    t = pd.to_numeric(df["os_time"], errors="coerce")
    # Assert the inverted coding rather than trusting the column name.
    med0 = t[df.cens_os == "0"].median()
    med1 = t[df.cens_os == "1"].median()
    assert med0 < med1, (
        "GSE87371 cens_os coding assumption broken: expected cens_os=0 (deaths) "
        f"to have shorter median OS, got {med0:.1f} vs {med1:.1f}")
    sub = df[(df.treatment.isin(["R-CHOP21", "R-CHOP14"])) & (df.coo != "PMBL")]
    return {
        "accession": "GSE87371", "platform": df.platform.iloc[0],
        "deposited_samples": len(df),
        "patient_key_field": "ID",
        "unique_patients": int(df["ID"].nunique()),
        "has_os_time": True, "has_os_event": True, "has_ipi_components": True,
        "treatment_field": "treatment",
        "treatment_matched_n": len(sub),
        # cens_os == "0" is DEATH -- see module docstring and assertion above.
        "events_in_matched": int((sub.cens_os == "0").sum()),
        "time_units": "months",
        "usable_from_geo_alone": True,
        "note": ("EVENT INDICATOR IS INVERTED: cens_os=1 censored, 0 died. "
                 "Treatments R-CHOP21 76 / R-ACVBP+Conso 73 / R-CHOP14 33 / "
                 "ACVBP 17 / R-Mini-CHOP21 13 / R-ACVBP+ASCT 11; "
                 "coo includes 20 PMBL which are excluded. ipi complete (0 missing)"),
    }


def main() -> int:
    rows = [audit_31312(), audit_10846(), audit_87371()]
    cat = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cat.to_csv(OUT, index=False)
    with pd.option_context("display.width", 200, "display.max_colwidth", 60):
        print(cat.drop(columns=["note"]).to_string(index=False))
    print()
    for r in rows:
        print(f"{r['accession']}: {r['note']}")
    print()
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
