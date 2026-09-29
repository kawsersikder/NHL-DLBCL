"""Generate Table 1 (baseline characteristics) for the manuscript.

TRIPOD+AI item 20b requires a characteristics table covering demographics,
predictors, sample size, outcome events, follow-up time and missingness. This
script emits it directly from the frozen source tables so that nothing is
hand-transcribed, matching the convention used by ``make_supplementary_tables.py``.

The table contrasts the analysis cohort (the 170 image-eligible patients,
cohort A) against the 39 patients excluded for having no released H&E patch.
That contrast is the evidence for or against selection bias from the image
eligibility rule, which is a foreseeable reviewer question given 19% of the
released cohort is dropped. Standardised mean differences quantify it without
significance testing, which is inappropriate for baseline tables.

Encodings were verified against the data before labelling, not taken from the
released data dictionary, which is known to be wrong about the IHC columns
(it describes CD10 and MUM1 as "% positive" when both are binary):

  * ``Follow-up Status`` 1 = deceased            (dictionary, consistent with data)
  * ``LDH`` 1 = elevated                         (dictionary)
  * ``IPI Risk Group (4 Class)`` 0/1/2/3 = Low / Low-int / High-int / High
        verified: maps exactly onto IPI score bands 0-1 / 2 / 3 / 4-5
  * ``RIPI Risk Group`` 0/1/2 = Very good / Good / Poor
        verified: maps exactly onto IPI score bands 0 / 1-2 / 3-5
  * ``HANS`` 1 = GCB                             (established in verify_hans_encoding.py)

Writes:
    reports/preprint/table1_characteristics.tex   (\\input by main.tex)
    reports/phase_03c_results_tables/table1_characteristics.csv  (audit source)

Usage:
    python src/analysis/make_table1.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CLINICAL = ROOT / "data/raw/dlbcl_morph/clinical_data_cleaned.csv"
MANIFEST = ROOT / "data/manifests/patient_manifest.csv"
OUT_TEX = ROOT / "reports/preprint/table1_characteristics.tex"
OUT_CSV = ROOT / "reports/phase_03c_results_tables/table1_characteristics.csv"


# --------------------------------------------------------------------------
# Standardised mean differences.
#
# No p-values: a baseline table is not a hypothesis test, and with n=39 in the
# comparison group a non-significant p would reflect low power rather than
# balance. SMD is a magnitude, independent of sample size. |SMD| > 0.10 is the
# conventional threshold for a difference worth remarking on.
# --------------------------------------------------------------------------
def smd_continuous(a: pd.Series, b: pd.Series) -> float:
    a, b = a.dropna(), b.dropna()
    if len(a) < 2 or len(b) < 2:
        return np.nan
    pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2.0)
    if pooled == 0:
        return 0.0
    return float((a.mean() - b.mean()) / pooled)


def smd_binary(a: pd.Series, b: pd.Series) -> float:
    """Signed SMD for a 0/1 indicator, on the proportion of 1s.

    Positive means the characteristic is MORE common in cohort A. Kept separate
    from the multi-level routine below, whose value is an unsigned distance --
    mixing the two in one column would invite sign misreadings.
    """
    a, b = a.dropna(), b.dropna()
    if len(a) < 2 or len(b) < 2:
        return np.nan
    p1, p2 = float(a.mean()), float(b.mean())
    v = (p1 * (1 - p1) + p2 * (1 - p2)) / 2.0
    return float((p1 - p2) / np.sqrt(v)) if v > 0 else 0.0


def smd_categorical(a: pd.Series, b: pd.Series) -> float:
    """Multi-level SMD (Yang & Dalton).

    This is a Mahalanobis-type distance and is therefore always >= 0: it says how
    far apart the two distributions are, not which way. Binary variables are sent
    to smd_binary instead so their direction is preserved.
    """
    a, b = a.dropna(), b.dropna()
    if len(a) < 2 or len(b) < 2:
        return np.nan
    levels = sorted(set(a.unique()) | set(b.unique()))
    if len(levels) < 2:
        return 0.0
    if len(levels) == 2:
        lo, hi = levels
        return smd_binary((a == hi).astype(float), (b == hi).astype(float))
    # Drop the last level: proportions are linearly dependent.
    p1 = np.array([(a == lv).mean() for lv in levels[:-1]], dtype=float)
    p2 = np.array([(b == lv).mean() for lv in levels[:-1]], dtype=float)

    def cov(p):
        s = np.diag(p * (1 - p))
        for i in range(len(p)):
            for j in range(len(p)):
                if i != j:
                    s[i, j] = -p[i] * p[j]
        return s

    s = (cov(p1) + cov(p2)) / 2.0
    d = p1 - p2
    try:
        val = float(d @ np.linalg.pinv(s) @ d)
    except np.linalg.LinAlgError:
        return np.nan
    return float(np.sqrt(max(val, 0.0)))


# --------------------------------------------------------------------------
# Row builders. Each returns (label, cohort_a_cell, excluded_cell, smd, n_missing_a)
# --------------------------------------------------------------------------
def row_median_iqr(label, a, b, col, decimals=0):
    sa, sb = a[col], b[col]
    fmt = f"{{:.{decimals}f}}"

    def cell(s):
        s = s.dropna()
        if s.empty:
            return "---"
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        return f"{fmt.format(s.median())} ({fmt.format(q1)}--{fmt.format(q3)})"

    return (label, cell(sa), cell(sb), smd_continuous(sa, sb), int(sa.isna().sum()))


def row_binary(label, a, b, mask_fn, col):
    """n (%) of patients meeting mask_fn, denominator = non-missing in `col`."""
    def cell(d):
        obs = d[d[col].notna()]
        if obs.empty:
            return "---"
        k = int(mask_fn(obs).sum())
        return f"{k} ({100.0 * k / len(obs):.1f})"

    ind_a = mask_fn(a[a[col].notna()]).astype(float)
    ind_b = mask_fn(b[b[col].notna()]).astype(float)
    return (label, cell(a), cell(b), smd_binary(ind_a, ind_b),
            int(a[col].isna().sum()))


def rows_categorical(label, a, b, col, level_labels, indent="\\quad "):
    """A header row carrying the SMD and missingness, then one row per level.

    Variables with more than two levels get a dagger: their SMD is an unsigned
    distance, so a reader must not interpret its sign.
    """
    n_levels = len(set(a[col].dropna()) | set(b[col].dropna()))
    mark = "$^{\\dagger}$" if n_levels > 2 else ""
    out = [(label + mark, "", "", smd_categorical(a[col], b[col]),
            int(a[col].isna().sum()))]
    for lv, name in level_labels.items():
        def cell(d):
            obs = d[d[col].notna()]
            if obs.empty:
                return "---"
            k = int((obs[col] == lv).sum())
            return f"{k} ({100.0 * k / len(obs):.1f})"
        out.append((f"{indent}{name}", cell(a), cell(b), np.nan, None))
    return out


def _plain(label: str) -> str:
    """Strip LaTeX markup for the CSV and console views."""
    out = label
    for src, dst in (
        ("\\quad ", "  "),
        ("$^{\\dagger}$", " [unsigned SMD]"),
        ("\\textsuperscript{a}", ""),
        ("$\\geq$", ">="),
        ("$>$", ">"),
        ("\\%", "%"),
        ("--", "-"),
        ("\\textbf{", ""),
    ):
        out = out.replace(src, dst)
    return out.rstrip("}").strip()


def median_followup(d: pd.DataFrame) -> str:
    """Reverse Kaplan-Meier: censoring is the 'event', so this estimates how long
    patients were actually observed rather than how long they survived."""
    from lifelines import KaplanMeierFitter

    obs = d[d["OS"].notna()]
    if obs.empty:
        return "---"
    kmf = KaplanMeierFitter()
    kmf.fit(obs["OS"], event_observed=1 - obs["Follow-up Status"])
    med = kmf.median_survival_time_
    if not np.isfinite(med):
        return "not reached"
    return f"{med:.1f}"


def main() -> int:
    clinical = pd.read_csv(CLINICAL)
    manifest = pd.read_csv(MANIFEST)[["patient_id", "image_eligible"]]
    d = clinical.merge(manifest, on="patient_id", how="left", validate="one_to_one")

    a = d[d["image_eligible"] == 1].copy()   # cohort A, the analysis population
    b = d[d["image_eligible"] != 1].copy()   # excluded: no released H&E patch

    print(f"cohort A (image-eligible) n = {len(a)}   deaths = {int(a['Follow-up Status'].sum())}")
    print(f"excluded (no H&E patch)  n = {len(b)}   deaths = {int(b['Follow-up Status'].sum())}")
    if len(a) != 170 or len(b) != 39:
        print("!! cohort sizes do not match the manuscript (expected 170 / 39)")
        return 1

    rows: list[tuple] = []
    sec = lambda t: rows.append((f"\\textbf{{{t}}}", "", "", np.nan, None))

    sec("Demographics")
    rows.append(row_median_iqr("Age at treatment start, years", a, b, "Age"))
    rows.append(row_binary("\\quad Age $>$ 60", a, b, lambda x: x["Age"] > 60, "Age"))

    sec("Disease characteristics")
    rows += rows_categorical("ECOG performance status", a, b, "ECOG PS",
                             {0: "0", 1: "1", 2: "2", 3: "3"})
    rows.append(row_binary("\\quad ECOG $\\geq$ 2", a, b, lambda x: x["ECOG PS"] >= 2, "ECOG PS"))
    rows += rows_categorical("Ann Arbor stage", a, b, "Stage",
                             {1.0: "I", 2.0: "II", 3.0: "III", 4.0: "IV"})
    rows.append(row_binary("\\quad Stage III--IV", a, b, lambda x: x["Stage"] >= 3, "Stage"))
    rows.append(row_binary("Serum LDH elevated", a, b, lambda x: x["LDH"] == 1, "LDH"))
    # Collapse to 0 / 1 / >=2 so the displayed levels and the SMD cover the same
    # categories; the raw column runs to 7 sites with single-patient tails.
    for frame in (a, b):
        frame["EN_cat"] = frame["EN"].where(frame["EN"].isna(), frame["EN"].clip(upper=2))
    # No separate ">1 site" row: the collapsed ">= 2" level is exactly the IPI
    # cut-point, so a dichotomy row would repeat the same two numbers.
    rows += rows_categorical("Extranodal sites", a, b, "EN_cat",
                             {0.0: "0", 1.0: "1", 2.0: "$\\geq$ 2 (IPI cut-point)"})

    sec("Prognostic index")
    rows.append(row_median_iqr("IPI score", a, b, "IPI Score"))
    rows += rows_categorical("IPI risk group", a, b, "IPI Risk Group (4 Class)",
                             {0.0: "Low", 1.0: "Low-intermediate",
                              2.0: "High-intermediate", 3.0: "High"})
    rows += rows_categorical("R-IPI risk group", a, b, "RIPI Risk Group",
                             {0: "Very good", 1: "Good", 2: "Poor"})

    sec("Cell of origin and biomarkers")
    rows += rows_categorical("Hans cell of origin", a, b, "HANS",
                             {1.0: "Germinal-centre B-cell", 0.0: "Non-germinal-centre"})
    rows.append(row_binary("CD10 positive", a, b, lambda x: x["CD10 IHC"] == 1, "CD10 IHC"))
    rows.append(row_binary("MUM1 positive", a, b, lambda x: x["MUM1 IHC"] == 1, "MUM1 IHC"))
    rows.append(row_binary("BCL6 $\\geq$ 30\\%", a, b, lambda x: x["BCL6 IHC"] >= 30, "BCL6 IHC"))
    rows.append(row_median_iqr("MYC IHC, \\% positive", a, b, "MYC IHC"))
    rows.append(row_median_iqr("BCL2 IHC, \\% positive", a, b, "BCL2 IHC"))
    rows.append(row_binary("MYC rearrangement (FISH)", a, b, lambda x: x["MYC FISH"] == 1, "MYC FISH"))
    rows.append(row_binary("BCL2 rearrangement (FISH)", a, b, lambda x: x["BCL2 FISH"] == 1, "BCL2 FISH"))
    rows.append(row_binary("BCL6 rearrangement (FISH)", a, b, lambda x: x["BCL6 FISH"] == 1, "BCL6 FISH"))

    sec("Outcome")
    rows.append(row_binary("Deaths at last follow-up", a, b,
                           lambda x: x["Follow-up Status"] == 1, "Follow-up Status"))
    rows.append(("Median follow-up, years\\textsuperscript{a}",
                 median_followup(a), median_followup(b), np.nan, 0))
    rows.append(row_median_iqr("Observed overall survival, years", a, b, "OS", decimals=1))

    # ---------------------------------------------------------------- CSV ---
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "characteristic": _plain(lab),
                "cohort_a_n170": ca,
                "excluded_n39": cb,
                "smd": "" if (s is None or (isinstance(s, float) and np.isnan(s))) else round(s, 3),
                "missing_in_cohort_a": "" if m is None else m,
            }
            for lab, ca, cb, s, m in rows
        ]
    ).to_csv(OUT_CSV, index=False)

    # -------------------------------------------------------------- LaTeX ---
    lines = [
        "% Auto-generated by src/analysis/make_table1.py -- DO NOT HAND-EDIT.",
        "% Regenerate after any change to the clinical table or the manifest.",
        "\\begin{table}[htbp]",
        "\\centering\\footnotesize",
        # The document sets \arraystretch 1.15 globally; at 49 rows that inflates
        # this table past a full page. Reset locally -- the table environment
        # scopes it, so the rest of the manuscript is unaffected.
        "\\renewcommand{\\arraystretch}{1.0}",
        "\\setlength{\\tabcolsep}{5pt}",
        "\\caption{Baseline characteristics of the analysis cohort (A, $n=170$) "
        "against the 39 patients excluded for having no released H\\&E patch. "
        "Values are median (interquartile range) or $n$ (\\%). See notes below.}",
        "\\label{tab:baseline}",
        "\\begin{tabular}{@{}lccrr@{}}",
        "\\toprule",
        "Characteristic & Cohort A ($n=170$) & Excluded ($n=39$) & SMD & Missing \\\\",
        "\\midrule",
    ]
    for lab, ca, cb, s, m in rows:
        s_txt = "" if (s is None or (isinstance(s, float) and np.isnan(s))) else f"{s:.2f}"
        m_txt = "" if m is None else ("---" if m == 0 else str(m))
        lines.append(f"{lab} & {ca} & {cb} & {s_txt} & {m_txt} \\\\")
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        "",
        "\\vspace{0.3em}",
        "\\scriptsize\\raggedright",
        "Percentages are computed over non-missing values; the rightmost column "
        "is the number of cohort~A patients with the value missing. Standardised "
        "mean differences are reported instead of $p$-values, because a baseline "
        "table is not a hypothesis test and with $n=39$ in the comparison group a "
        "non-significant $p$ would reflect low power rather than balance; "
        "$|\\mathrm{SMD}|>0.10$ is the conventional threshold for a difference "
        "worth remarking on. A positive SMD means the value is higher, or the "
        "feature more common, in cohort~A. SMDs marked $^{\\dagger}$ are "
        "multi-level distances and are therefore unsigned. "
        "\\textsuperscript{a}Reverse Kaplan--Meier estimate; overall survival is "
        "measured from end of treatment, as released.",
        "\\end{table}",
        "",
    ]
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_TEX.write_text("\n".join(lines), encoding="utf-8")

    # ---------------------------------------------------------- diagnostics --
    print(f"\nwrote {OUT_TEX.relative_to(ROOT)}")
    print(f"wrote {OUT_CSV.relative_to(ROOT)}")

    big = [(lab, s) for lab, _, _, s, _ in rows
           if isinstance(s, float) and not np.isnan(s) and abs(s) > 0.10]
    print(f"\n{len(big)} characteristic(s) with |SMD| > 0.10 between cohort A and the excluded 39")
    print("(+ = higher/more common in cohort A; dagger rows are unsigned distances)")
    for lab, s in sorted(big, key=lambda t: -abs(t[1])):
        print(f"  {_plain(lab):46s} {s:+.2f}")

    miss = [(lab, m) for lab, _, _, _, m in rows if m]
    print(f"\nmissingness in cohort A (variables with any): {len(miss)}")
    for lab, m in sorted(miss, key=lambda t: -t[1]):
        print(f"  {_plain(lab):46s} {m:3d} ({100.0 * m / len(a):.1f}%)")

    # The five M1 predictors carry the model; their missingness is the one that
    # matters for the primary analysis.
    print("\nmissingness in the five M1 clinical predictors (cohort A):")
    for col in ["Age", "ECOG PS", "LDH", "EN", "Stage"]:
        n = int(a[col].isna().sum())
        print(f"  {col:42s} {n:3d} ({100.0 * n / len(a):.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
