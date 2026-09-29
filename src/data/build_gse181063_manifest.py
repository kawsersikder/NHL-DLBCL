"""Parse GSE181063 sample metadata and report the actually-eligible cohort.

Route 1 of the 2026-09-10 research assessment names GSE181063 as the development
cohort for cross-cohort molecular prognosis. The assessment is explicit that the
deposited sample count is not the analysable patient count, and that advertising
1,310 usable cases would be wrong. This script establishes the real number by
applying an eligibility cascade and reporting N and events at every step.

Input is the GEO ``targ=gsm&form=text&view=brief`` dump — all 1,310 sample
records in one response, so no per-sample requests are needed. Provenance
(URL, byte count, SHA-256) is recorded alongside the manifest.

Two traps this script exists to avoid:

1. ``diagnostic_group == "DLBCL"`` selects 1,149 samples, but that group still
   contains primary mediastinal (45), T-cell/histiocyte-rich (31),
   plasmablastic (26) and primary CNS (5) large B-cell lymphomas. The intended
   DLBCL-NOS scope is the ICD-O-3 subtype field, not the diagnostic group. The
   assessment specifically warns to apply DLBCL-NOS scope explicitly.
2. The series mixes treatment eras and intents: 110 supportive/palliative-only
   and 30 radiotherapy-only cases sit alongside 828 CHOP-R. A prognostic model
   trained across those is not answering a treatment-matched question.

NOTHING here is selected on outcome. ``os_status`` is read only to COUNT events
per stratum and to drop records with no survival data; no feature is filtered,
no threshold is tuned, and no model is fitted. Event counts are reported because
the assessment requires eligible patients AND events to be stated up front.

Time origin is NOT established by this script. ``os_followup_y`` has no stated
origin in the GEO metadata; DLBCL-Morph measures OS from END OF TREATMENT while
most cohorts measure from diagnosis. That must be resolved against the source
publications before any cross-cohort join. The script prints a warning to that
effect rather than silently assuming.

Usage:
    python src/data/build_gse181063_manifest.py
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/gse181063/GSE181063_gsm_brief.txt"
OUT_CSV = ROOT / "reports/route1_gse181063_manifest.csv"
OUT_PROV = ROOT / "data/raw/gse181063/PROVENANCE.md"

SOURCE_URL = (
    "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi"
    "?acc=GSE181063&targ=gsm&form=text&view=brief"
)
RETRIEVED = "2026-09-10"

# The intended scope. Everything else in diagnostic_group=DLBCL is a distinct
# entity with its own biology and prognosis.
DLBCL_NOS = "Diffuse large B-cell lymphoma, NOS"
# Treatment-matched primary analysis. CHOP-R/Bortezomib (34) is a trial arm and
# is deliberately NOT folded in here; it is reported separately so the choice is
# visible rather than buried.
RCHOP = "CHOP-R"

SAMPLE_RE = re.compile(r"^\^SAMPLE = (\S+)")
CHAR_RE = re.compile(r"^!Sample_characteristics_ch1 = ([^:]+):\s*(.*)$")
PLATFORM_RE = re.compile(r"^!Sample_platform_id = (\S+)")


def parse(path: Path) -> pd.DataFrame:
    """Turn the GEO brief dump into one row per sample.

    Characteristic keys vary per sample (only 888 of 1,310 carry ``ipi_score``),
    so rows are built as dicts and DataFrame construction fills the gaps with
    NaN rather than requiring a fixed schema.
    """
    rows: list[dict[str, str]] = []
    cur: dict[str, str] | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = SAMPLE_RE.match(line)
        if m:
            if cur is not None:
                rows.append(cur)
            cur = {"gsm": m.group(1)}
            continue
        if cur is None:
            continue
        m = CHAR_RE.match(line)
        if m:
            cur[m.group(1).strip()] = m.group(2).strip()
            continue
        m = PLATFORM_RE.match(line)
        if m:
            cur["platform"] = m.group(1)
    if cur is not None:
        rows.append(cur)
    return pd.DataFrame(rows)


def numeric(df: pd.DataFrame, cols: list[str]) -> None:
    """Coerce known-numeric characteristic columns in place.

    GEO ships everything as text and uses sentinel strings such as
    "Treatment data not available"; ``errors="coerce"`` turns those into NaN so
    missingness is counted rather than silently parsed as a category.
    """
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")


def cascade(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the eligibility filters in order, reporting N and events at each."""
    bar = "=" * 78
    print(bar)
    print("ELIGIBILITY CASCADE — GSE181063")
    print(bar)
    print(f"{'step':<52}{'N':>7}{'events':>8}{'lost':>8}")

    def line(label: str, sub: pd.DataFrame, prev: int) -> None:
        ev = int((sub["os_status"] == 1).sum())
        print(f"{label:<52}{len(sub):>7}{ev:>8}{prev - len(sub):>8}")

    step = df
    line("0. deposited samples", step, len(df))

    prev = len(step)
    step = step[step["case_diagnostic_subtype_icdo3"] == DLBCL_NOS]
    line("1. ICD-O-3 subtype = DLBCL, NOS", step, prev)

    prev = len(step)
    step = step[step["qc_fail"] == 0]
    line("2. expression QC clean (qc_fail == 0)", step, prev)

    prev = len(step)
    step = step[step["sample_pre_active_treatment"] == "Yes"]
    line("3. biopsy pre-treatment", step, prev)

    prev = len(step)
    step = step[step["curative_intent"] == 1]
    line("4. curative intent", step, prev)

    prev = len(step)
    step = step[step["firstline_regimen"] == RCHOP]
    line(f"5. first-line regimen == {RCHOP}", step, prev)

    prev = len(step)
    step = step[step["os_followup_y"].notna() & step["os_status"].notna()]
    line("6. OS time and status present", step, prev)

    analysis = step.copy()

    prev = len(step)
    with_ipi = step[step["ipi_score"].notna()]
    line("7. IPI score present (clinical baseline)", with_ipi, prev)

    print()
    print("Step 7 is reported separately, NOT applied as a hard filter: the")
    print("clinical-baseline comparison needs IPI, but a molecular-only model")
    print("does not. Which cohort is primary is a protocol decision, not a")
    print("parsing decision, so both numbers are carried forward.")
    return analysis


def describe(analysis: pd.DataFrame) -> None:
    """Report the composition of the eligible set."""
    bar = "=" * 78
    print()
    print(bar)
    print("ELIGIBLE COHORT COMPOSITION")
    print(bar)
    ev = int((analysis["os_status"] == 1).sum())
    print(f"  patients                 {len(analysis)}")
    print(f"  deaths                   {ev} ({ev / len(analysis):.1%})")
    print(f"  median follow-up (y)     {analysis['os_followup_y'].median():.2f}")
    print(f"  platform(s)              {sorted(analysis['platform'].dropna().unique())}")
    print()
    print("  molecular subtype (pred_combine):")
    for k, v in analysis["pred_combine"].value_counts().items():
        print(f"    {k:<6} {v:>5}")
    print()
    print("  missingness in clinical baseline fields:")
    for c in ["ipi_score", "performance_status_ecog", "Stage", "ldh",
              "num_extranodal", "age_at_diagnosis", "Sex"]:
        if c in analysis.columns:
            n = int(analysis[c].isna().sum())
            print(f"    {c:<26}{n:>5} missing ({n / len(analysis):.1%})")

    print()
    print("  prior-publication overlap (matters for independence claims):")
    for c in ["in_pmid_30408148", "in_pmid_32187361"]:
        if c in analysis.columns:
            n = int((analysis[c] == "TRUE").sum())
            print(f"    {c:<26}{n:>5} samples")

    print()
    print(bar)
    print("UNRESOLVED — must be settled before any cross-cohort join")
    print(bar)
    print("  * OS TIME ORIGIN is not stated in the GEO metadata. DLBCL-Morph")
    print("    measures OS from END OF TREATMENT; if this cohort measures from")
    print("    diagnosis, the two are not the same estimand. Resolve against")
    print("    the source publications (PMID 30408148, 32187361).")
    print("  * PATIENT vs SAMPLE identity. 'pid_pmid_32187361' exists for only")
    print("    583 samples, so repeat biopsies cannot be ruled out cohort-wide")
    print("    from these fields alone. Duplicate patients would break both")
    print("    cross-validation and any independence claim.")
    print("  * No expression matrix has been downloaded or inspected. Probe")
    print("    coverage against the Affymetrix validation cohorts is unknown.")


def write_provenance(raw: Path, n_samples: int, n_eligible: int) -> None:
    """Record where the metadata came from, so counts stay auditable."""
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    OUT_PROV.write_text(
        f"""# GSE181063 — provenance

| Field | Value |
|---|---|
| Series | GSE181063 |
| Title | Whole genome expression profiling based on paraffin embedded tissue of a large DLBCL cohort |
| Platform | GPL14951 (Illumina Whole-Genome DASL HT v4) |
| Source URL | `{SOURCE_URL}` |
| Retrieved | {RETRIEVED} |
| File | `{raw.name}` |
| Bytes | {raw.stat().st_size} |
| SHA-256 | `{digest}` |
| Samples parsed | {n_samples} |
| Eligible (see manifest) | {n_eligible} |

Only sample **metadata** was retrieved. No expression matrix has been
downloaded, and no expression values have been inspected or joined.

The series description states 1,311 biopsied patients; 1,310 samples are
deposited. Neither figure is the analysable count — see
`reports/route1_gse181063_manifest.csv` and the eligibility cascade in
`src/data/build_gse181063_manifest.py`.

Regenerate with:

```
python src/data/build_gse181063_manifest.py
```
""",
        encoding="utf-8",
    )


def main() -> int:
    if not RAW.exists():
        raise FileNotFoundError(
            f"{RAW} not found — download it from:\n  {SOURCE_URL}"
        )
    df = parse(RAW)
    print(f"parsed {len(df)} sample records from {RAW.name}\n")
    numeric(df, ["qc_fail", "curative_intent", "os_status", "os_followup_y",
                 "ipi_score", "age_at_diagnosis", "probe_detection",
                 "performance_status_ecog", "num_extranodal", "conf_entropy"])

    analysis = cascade(df)
    describe(analysis)

    df["eligible_route1"] = df["gsm"].isin(analysis["gsm"])
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    write_provenance(RAW, len(df), len(analysis))
    print()
    print(f"wrote {OUT_CSV.relative_to(ROOT)}  ({len(df)} rows, all samples, "
          f"flagged by eligible_route1)")
    print(f"wrote {OUT_PROV.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
