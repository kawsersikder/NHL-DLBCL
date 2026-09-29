"""Phase 3C figures — calibration plots and risk-tertile Kaplan-Meier curves.

Protocol §10 deliverables. Both are built from the frozen out-of-fold
predictions; nothing is refitted here.

The tertile cut-points were derived inside each training fold and applied to
held-out patients (§7.5), so no patient's own outcome informed its risk group.
This is the specific weakness identified in the July 2026 entropy paper, which
searched a cut-point on the full cohort.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
from matplotlib import pyplot as plt


HORIZONS = [2.0, 3.0, 5.0]
CALIBRATION_BINS = 5
TERTILE_LABELS = ["Low risk", "Intermediate", "High risk"]
TERTILE_COLOURS = ["#2166ac", "#f4a582", "#b2182b"]


def observed_survival(times: np.ndarray, events: np.ndarray, horizon: float) -> float:
    """Kaplan-Meier survival at `horizon`, the censoring-correct observed value."""
    fitter = KaplanMeierFitter().fit(times, events)
    return float(fitter.predict(horizon))


def calibration_panel(
    axis, predicted: np.ndarray, times: np.ndarray, events: np.ndarray, horizon: float, title: str
) -> None:
    """Observed vs predicted survival by quintile of predicted risk."""
    finite = np.isfinite(predicted)
    predicted, times, events = predicted[finite], times[finite], events[finite]

    order = np.argsort(predicted)
    groups = np.array_split(order, CALIBRATION_BINS)

    expected, observed, lower, upper = [], [], [], []
    for group in groups:
        if len(group) < 5:
            continue
        expected.append(float(np.mean(predicted[group])))
        fitter = KaplanMeierFitter().fit(times[group], events[group])
        observed.append(float(fitter.predict(horizon)))
        interval = fitter.confidence_interval_survival_function_
        position = interval.index.searchsorted(horizon, side="right") - 1
        position = max(0, min(position, len(interval) - 1))
        lower.append(float(interval.iloc[position, 0]))
        upper.append(float(interval.iloc[position, 1]))

    expected = np.asarray(expected)
    observed = np.asarray(observed)
    errors = np.vstack([observed - np.asarray(lower), np.asarray(upper) - observed])
    errors = np.clip(errors, 0, None)

    axis.plot([0, 1], [0, 1], color="0.6", linestyle="--", linewidth=1, zorder=1)
    axis.errorbar(
        expected, observed, yerr=errors, fmt="o-", color="#2166ac",
        markersize=6, capsize=3, linewidth=1.5, zorder=2,
    )
    # Predicted survival is compressed into the upper range at this event rate,
    # so a full 0-1 axis would hide the deviation that matters.
    floor = min(expected.min(), (observed - errors[0]).min())
    lower_limit = max(0.0, np.floor((floor - 0.05) * 10) / 10)
    axis.set_xlim(lower_limit, 1.0)
    axis.set_ylim(lower_limit, 1.0)
    axis.set_xlabel(f"Predicted S({horizon:g}y)")
    axis.set_ylabel(f"Observed S({horizon:g}y)")
    axis.set_title(title, fontsize=10)
    axis.set_aspect("equal")
    axis.grid(alpha=0.25, linewidth=0.5)


def kaplan_meier_panel(
    axis, tertiles: np.ndarray, times: np.ndarray, events: np.ndarray, title: str
) -> float | None:
    """KM curves by held-out risk tertile; returns the log-rank p-value."""
    finite = np.isfinite(tertiles)
    tertiles, times, events = tertiles[finite], times[finite], events[finite]

    for level in (0, 1, 2):
        mask = tertiles == level
        if mask.sum() < 5:
            continue
        fitter = KaplanMeierFitter().fit(
            times[mask], events[mask], label=f"{TERTILE_LABELS[level]} (n={int(mask.sum())})"
        )
        fitter.plot_survival_function(
            ax=axis, ci_show=False, color=TERTILE_COLOURS[level], linewidth=1.8
        )

    axis.set_xlim(0, 5)
    axis.set_ylim(0.4, 1.02)
    axis.set_xlabel("Years from end of treatment")
    axis.set_ylabel("Overall survival")
    axis.grid(alpha=0.25, linewidth=0.5)
    axis.legend(fontsize=8, loc="lower left", framealpha=0.9)

    if len(np.unique(tertiles)) < 2:
        axis.set_title(title, fontsize=10)
        return None
    p_value = float(multivariate_logrank_test(times, tertiles, events).p_value)
    rendered = f"p = {p_value:.3g}" if p_value >= 1e-4 else "p < 1e-4"
    axis.set_title(f"{title}   (log-rank {rendered})", fontsize=10)
    return p_value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tables", type=Path, default=Path("reports/phase_03c_results_tables")
    )
    parser.add_argument("--out-dir", type=Path, default=Path("reports/phase_03c_figures"))
    parser.add_argument("--cohort", default="A")
    parser.add_argument(
        "--models", nargs="+", default=["M1", "M4c", "M5"],
        help="Models to plot. M1 is the clinical baseline, M5 the primary incremental.",
    )
    args = parser.parse_args()

    suffix = f"_cohort{args.cohort}"
    oof = pd.read_csv(args.tables / f"oof_predictions{suffix}.csv", dtype={"patient_id": str})
    curves = np.load(args.tables / f"pooled_survival{suffix}.npz", allow_pickle=True)
    time_grid = curves["time_grid"]

    times = oof["OS"].to_numpy(dtype=float)
    events = oof["Follow-up Status"].to_numpy(dtype=int)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # --- Calibration -------------------------------------------------------
    figure, axes = plt.subplots(
        len(args.models), len(HORIZONS),
        figsize=(3.4 * len(HORIZONS), 3.4 * len(args.models)),
    )
    axes = np.atleast_2d(axes)
    for row, model in enumerate(args.models):
        survival = curves[model]
        for column, horizon in enumerate(HORIZONS):
            index = int(np.argmin(np.abs(time_grid - horizon)))
            calibration_panel(
                axes[row, column], survival[:, index], times, events, horizon,
                f"{model} — {horizon:g} year",
            )
    figure.suptitle(
        f"Calibration, cohort {args.cohort} (out-of-fold, quintiles of predicted risk)",
        fontsize=12,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    calibration_path = args.out_dir / f"calibration{suffix}.png"
    figure.savefig(calibration_path, dpi=200)
    plt.close(figure)
    print(f"wrote {calibration_path}")

    # --- Kaplan-Meier by held-out risk tertile ------------------------------
    figure, axes = plt.subplots(1, len(args.models), figsize=(4.6 * len(args.models), 4.2))
    axes = np.atleast_1d(axes)
    p_values = {}
    for position, model in enumerate(args.models):
        p_value = kaplan_meier_panel(
            axes[position], oof[f"tertile_{model}"].to_numpy(dtype=float),
            times, events, model,
        )
        p_values[model] = p_value
    figure.suptitle(
        f"Overall survival by held-out risk tertile, cohort {args.cohort}\n"
        "cut-points derived inside training folds only (§7.5)",
        fontsize=11,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.93))
    km_path = args.out_dir / f"kaplan_meier_tertiles{suffix}.png"
    figure.savefig(km_path, dpi=200)
    plt.close(figure)
    print(f"wrote {km_path}")

    print("\nlog-rank p-values by model:")
    for model, p_value in p_values.items():
        print(f"  {model:5s} {'n/a' if p_value is None else f'{p_value:.4g}'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
