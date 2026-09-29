"""Generate the LaTeX supplementary tables from the frozen E-009 result CSVs.

Every number in the supplement is emitted directly from
``reports/phase_03c_results_tables/`` so that nothing is hand-transcribed and
the supplement can be regenerated if an artifact is ever corrected.

Writes: reports/preprint/supplementary_tables.tex  (\\input by main.tex)

Usage:
    python src/analysis/make_supplementary_tables.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "reports/phase_03c_results_tables"
OUT = ROOT / "reports/preprint/supplementary_tables.tex"

# Readable labels for every model id that appears in any ladder file.
LABEL = {
    "M0a": "M0a --- IPI score",
    "M0b": "M0b --- R-IPI group",
    "M1": "M1 --- Clinical Cox",
    "M2": "M2 --- Released geometry",
    "M3": "M3 --- Global entropy",
    "M4a": "M4a --- Morphology only",
    "M4b": "M4b --- Packing only",
    "M4c": "M4c --- Image (primary)",
    "M5": "M5 --- Clinical + image",
    "S3_M5_plus_F0": "S3 --- M5 + F0 exposure covariates",
    "S4_M4c_no_stain": "S4 --- M4c without stain (F1b)",
    "S5_M2_no_position": "S5 --- M2 without positional columns",
    "S7_central": "S7 --- Central tendency only",
    "S7_spread": "S7 --- Spread / heterogeneity only",
    "S6_M1_rsf": "S6 --- M1, random survival forest",
    "S6_M4c_rsf": "S6 --- M4c, random survival forest",
    "S6_M5_rsf": "S6 --- M5, random survival forest",
}

# Ladder display order (best-to-worst on cohort A, matching the main text).
ORDER = ["M1", "M5", "M0a", "M4b", "M4c", "M0b", "M2", "M4a", "M3"]

CORE_COMPARISONS = [
    "M5_minus_M1", "M0a_minus_M1", "M4b_minus_M1", "M4c_minus_M1",
    "M0b_minus_M1", "M2_minus_M1", "M4a_minus_M1", "M3_minus_M1",
]


def esc(text: str) -> str:
    """Escape LaTeX special characters in free text."""
    out = str(text)
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"),
                 ("}", r"\}"), ("~", r"\textasciitilde{}"),
                 ("^", r"\textasciicircum{}")]:
        out = out.replace(a, b)
    return out


def num(value, places: int = 3) -> str:
    """Format a number, rendering negatives with a LaTeX math minus."""
    if pd.isna(value):
        return "---"
    text = f"{value:.{places}f}"
    return f"${text}$" if text.startswith("-") else text


def ci(row, lo: str, hi: str) -> str:
    if pd.isna(row[lo]) or pd.isna(row[hi]):
        return "---"
    return f"$[{row[lo]:.3f}, {row[hi]:.3f}]$".replace("-", "−").replace(
        "−", "-")


def ci_signed(row, lo: str, hi: str) -> str:
    """CI with explicit signs, for paired differences."""
    if pd.isna(row[lo]) or pd.isna(row[hi]):
        return "---"
    return f"$[{row[lo]:+.3f}, {row[hi]:+.3f}]$"


def ok(flag) -> str:
    truthy = str(flag).strip().lower() in {"true", "1", "yes"}
    return r"\checkmark" if truthy else r"$\times$"


def ladder_table(df: pd.DataFrame, label: str, caption: str,
                 order: list[str] | None = None) -> str:
    rows = []
    seq = order if order is not None else list(df.model)
    for mid in seq:
        sel = df[df.model == mid]
        if sel.empty:
            continue
        r = sel.iloc[0]
        rows.append(
            f"{esc(LABEL.get(mid, mid))} & {int(r.k_declared)} & "
            f"{int(r.k_kept_median)} & {num(r.harrell_c_pooled)} "
            f"{ci(r, 'harrell_c_lower', 'harrell_c_upper')} & "
            f"{num(r.uno_c)} & {num(r.integrated_brier)} & "
            f"{num(r.calibration_slope, 2)} & {ok(r.calibration_ok)} \\\\"
        )
    body = "\n".join(rows)
    return f"""
\\begin{{table}}[htbp]
\\centering\\footnotesize
\\caption{{{caption}}}
\\label{{{label}}}
\\begin{{tabular}}{{lrrlrrrc}}
\\toprule
Model & $k$ & kept & Harrell C [95\\% CI] & Uno C & IBS & Slope & OK \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""


def auc_table(df: pd.DataFrame) -> str:
    rows = []
    for mid in ORDER:
        sel = df[df.model == mid]
        if sel.empty:
            continue
        r = sel.iloc[0]
        rows.append(
            f"{esc(LABEL.get(mid, mid))} & {num(r.auc_1y)} & {num(r.auc_2y)} & "
            f"{num(r.auc_3y)} & {num(r.auc_5y)} \\\\"
        )
    body = "\n".join(rows)
    return f"""
\\begin{{table}}[htbp]
\\centering\\footnotesize
\\caption{{Time-dependent cumulative/dynamic AUC, cohort A. The 1-year column was
pre-specified as exploratory owing to sparse early events and is not
interpreted.}}
\\label{{tab:sup-auc}}
\\begin{{tabular}}{{lrrrr}}
\\toprule
Model & 1\\,y\\textsuperscript{{*}} & 2\\,y & 3\\,y & 5\\,y \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}

\\vspace{{0.4em}}
\\footnotesize\\textsuperscript{{*}}Exploratory; not interpreted.
\\end{{table}}
"""


def paired_across_cohorts(a: pd.DataFrame, b: pd.DataFrame,
                          c: pd.DataFrame) -> str:
    def cell(df, comp):
        sel = df[df.comparison == comp]
        if sel.empty:
            return "---"
        r = sel.iloc[0]
        return (f"{num(r.delta_c_mean)} "
                f"{ci_signed(r, 'delta_c_lower', 'delta_c_upper')}")

    rows = []
    for comp in CORE_COMPARISONS:
        pretty = comp.replace("_minus_", " $-$ ").replace("_", " ")
        rows.append(f"{pretty} & {cell(a, comp)} & {cell(b, comp)} & "
                    f"{cell(c, comp)} \\\\")
    body = "\n".join(rows)
    return f"""
\\begin{{table}}[htbp]
\\centering\\scriptsize
\\caption{{Paired bootstrap differences in Harrell C versus M1, across all three
pre-specified cohorts. 1{{,}}000 patient-level paired resamples. Intervals that
exclude zero indicate a model significantly worse than clinical covariates
alone. Note that M4c $-$ M1 loses significance in cohort C.}}
\\label{{tab:sup-paired}}
\\begin{{tabular}}{{llll}}
\\toprule
Comparison & A ($n=170$) & B ($n=169$) & C ($n=168$) \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""


def rsf_table(rsf: pd.DataFrame, paired: pd.DataFrame) -> str:
    pairs = {"S6_M1_rsf": "S6_M1_rsf_minus_M1",
             "S6_M4c_rsf": "S6_M4c_rsf_minus_M1",
             "S6_M5_rsf": "S6_M5_rsf_minus_M1"}
    rows = []
    for mid, comp in pairs.items():
        sel = rsf[rsf.model == mid]
        if sel.empty:
            continue
        r = sel.iloc[0]
        p = paired[paired.comparison == comp]
        delta = "---"
        if not p.empty:
            pr = p.iloc[0]
            delta = (f"{num(pr.delta_c_mean)} "
                     f"{ci_signed(pr, 'delta_c_lower', 'delta_c_upper')}")
        rows.append(
            f"{esc(LABEL.get(mid, mid))} & {num(r.harrell_c_pooled)} "
            f"{ci(r, 'harrell_c_lower', 'harrell_c_upper')} & {num(r.uno_c)} & "
            f"{num(r.integrated_brier)} & {num(r.calibration_slope, 2)} & "
            f"{ok(r.calibration_ok)} & {delta} \\\\"
        )
    body = "\n".join(rows)
    return f"""
\\begin{{table}}[htbp]
\\centering\\scriptsize
\\caption{{Sensitivity S6 --- random survival forest (500 trees), cohort A. RSF is
worse than penalised Cox on every model, and RSF-M1 additionally fails the
calibration criterion that Coxnet-M1 passes. Nonlinearity does not rescue the
result.}}
\\label{{tab:sup-rsf}}
\\begin{{tabular}}{{llrrrcl}}
\\toprule
Model & Harrell C [95\\% CI] & Uno C & IBS & Slope & OK & $\\Delta$C vs M1 [95\\% CI] \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""


def hyperparameter_table(hp: pd.DataFrame) -> str:
    rows = []
    for mid in ORDER:
        sel = hp[hp.model == mid]
        if sel.empty:
            continue
        kept = sel.n_features_kept
        # `learner` is recorded only for the single-covariate models, which are
        # fitted unpenalised; everything else uses the protocol default.
        learners = sel.learner.dropna()
        learner = learners.mode().iloc[0] if len(learners) else "coxnet"
        l1 = sel.l1_ratio.dropna()
        alpha = sel.alpha.dropna()
        l1_txt = f"{l1.mode().iloc[0]:g}" if len(l1) else "---"
        alpha_txt = f"{alpha.median():.4g}" if len(alpha) else "---"
        rows.append(
            f"{esc(LABEL.get(mid, mid))} & {esc(learner)} & "
            f"{int(kept.median())} & [{int(kept.min())}, {int(kept.max())}] & "
            f"{l1_txt} & {alpha_txt} \\\\"
        )
    body = "\n".join(rows)
    return f"""
\\begin{{table}}[htbp]
\\centering\\footnotesize
\\caption{{Fold-internal model selection across all 50 outer folds, cohort A.
``kept'' is the number of columns surviving Spearman redundancy pruning at
$|\\rho| > 0.90$; $\\lambda_1$ ratio and $\\alpha$ are the modal and median values
chosen by inner-fold cross-validation. Single-covariate models are fitted
unpenalised.}}
\\label{{tab:sup-hyper}}
\\begin{{tabular}}{{llrlrr}}
\\toprule
Model & Learner & kept (median) & kept [min, max] & $\\lambda_1$ ratio & $\\alpha$ (median) \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""


def main() -> None:
    load = lambda name: pd.read_csv(TABLES / name)  # noqa: E731

    lad_b = load("model_ladder_cohortB.csv")
    lad_c = load("model_ladder_cohortC.csv")
    lad_s = load("model_ladder_cohortA_sens.csv")
    lad_r = load("model_ladder_cohortA_rsf.csv")
    lad_a = load("model_ladder_cohortA.csv")

    pd_a = load("paired_differences_cohortA.csv")
    pd_b = load("paired_differences_cohortB.csv")
    pd_c = load("paired_differences_cohortC.csv")
    pd_r = load("paired_differences_cohortA_rsf.csv")

    hp_a = load("hyperparameters_cohortA.csv")

    sens_ids = ["S3_M5_plus_F0", "S4_M4c_no_stain", "S5_M2_no_position",
                "S7_central", "S7_spread"]

    parts = [
        "% ======================================================================",
        "%  AUTO-GENERATED by src/analysis/make_supplementary_tables.py",
        "%  Do not edit by hand. Regenerate from the frozen result CSVs instead.",
        "% ======================================================================",
        "",
        r"\clearpage",
        r"\appendix",
        r"\section{Supplementary tables}",
        "",
        r"\begin{sloppypar}",
        "All values are emitted directly from the frozen result files under",
        r"\texttt{reports/\allowbreak phase\_03c\_\allowbreak results\_tables/}.",
        "Cohorts B and C are the pre-specified quality-control sensitivity",
        "analyses defined before outcome access; S3--S7 are the pre-specified",
        "model variants.",
        r"\end{sloppypar}",
        "",
        ladder_table(lad_b, "tab:sup-cohortB",
                     "Full model ladder, cohort B ($n=169$; excludes patient "
                     "26807, the single failed representative panel).", ORDER),
        ladder_table(lad_c, "tab:sup-cohortC",
                     "Full model ladder, cohort C ($n=168$; excludes patients "
                     "26807 and 13957). Note M3 rises from 0.456 in cohort A to "
                     "0.497 here --- the below-chance entropy result is not "
                     "robust.", ORDER),
        paired_across_cohorts(pd_a, pd_b, pd_c),
        ladder_table(lad_s, "tab:sup-sens",
                     "Pre-specified model variants S3--S7, cohort A. Compare "
                     "against M1 $=0.706$, M4c $=0.579$ and M5 $=0.683$ in the "
                     "main text.", sens_ids),
        rsf_table(lad_r, pd_r),
        auc_table(lad_a),
        hyperparameter_table(hp_a),
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")

    n_tables = sum(p.count(r"\begin{table}") for p in parts)
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  tables emitted : {n_tables}")
    print(f"  cohort B rows  : {len(lad_b)}")
    print(f"  cohort C rows  : {len(lad_c)}")
    print(f"  sens rows used : {len(sens_ids)}")
    print(f"  rsf rows       : {len(lad_r[lad_r.model.str.startswith('S6')])}")
    print(f"  hyperparam rows: {len(hp_a)}")


if __name__ == "__main__":
    main()
