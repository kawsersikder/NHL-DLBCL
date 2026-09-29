"""E-009 — Phase 3B survival model ladder.

Implements protocol §§3, 5-9. Every model is fitted on identical Cohort A
patients and identical frozen outer splits, so paired comparisons are valid.
The primary estimand is the paired difference in out-of-fold discrimination
between M5 (clinical + image) and M1 (clinical alone).

Nothing here selects a model. The ladder is fixed, the folds are fixed, the
hyperparameter grids are fixed, and the complete table is published including
models that fail. Reporting only the best C-index is listed in the novelty
landscape as an invalidating practice.

Two implementation decisions the protocol does not specify, both fixed here
before any result was inspected:

1. Linear predictors from different outer folds are on different scales, so
   pooling them raw would distort ranks. Each fold's test predictions are
   standardised using that fold's *training* predictor mean and SD - no test
   information is used. Both the pooled metric and the per-fold mean are
   reported; if they disagree that is itself a finding.
2. Pooled out-of-fold predictions are averaged across the 10 repeats, giving one
   prediction per patient for the patient-level paired bootstrap of §7.4.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from joblib import Parallel, delayed, parallel_backend
from sksurv.ensemble import RandomSurvivalForest
from sksurv.functions import StepFunction
from sksurv.linear_model import CoxnetSurvivalAnalysis, CoxPHSurvivalAnalysis
from sksurv.metrics import (
    concordance_index_censored,
    concordance_index_ipcw,
    cumulative_dynamic_auc,
    integrated_brier_score,
)
from sksurv.nonparametric import kaplan_meier_estimator
from sksurv.util import Surv
from sklearn.model_selection import StratifiedKFold

import sksurv
import sklearn


SEED = 20260830
INNER_FOLDS = 5
N_BOOTSTRAP = 1000
EXPECTED_PATIENTS = 170
EXPECTED_EVENTS = 58

EVENT_COLUMN = "Follow-up Status"
TIME_COLUMN = "OS"

# Protocol §7: IBS over [0.25, 5.0]; AUC at 2/3/5 years primary, 1 year exploratory.
TIME_GRID = np.linspace(0.25, 5.0, 50)
AUC_HORIZONS = [1.0, 2.0, 3.0, 5.0]
UNO_TAU = 5.0
CALIBRATION_SLOPE_BOUNDS = (0.7, 1.3)

# RSF is fitted under joblib's threading backend with a fixed worker count.
# `n_jobs=-1` spawns a fresh loky process pool on every one of the 50 x 30 inner
# fits and deadlocks on Windows; tree building releases the GIL, so threads give
# the same parallelism without the process churn.
RSF_N_JOBS = max(1, min(6, (os.cpu_count() or 2) - 2))
RSF_BACKEND = "threading"

L1_RATIOS = [0.1, 0.5, 0.9, 1.0]
N_ALPHAS = 20
RSF_GRID = [
    {"min_samples_leaf": leaf, "max_features": features}
    for leaf in (5, 10, 20)
    for features in ("sqrt", 0.33)
]

# Protocol §2, frozen partition. Order matters: it is the §6.2 pruning tie-break.
F0 = [
    "patch_count_total", "patch_count_primary", "patch_count_low_tissue",
    "cell_count_total", "cell_count_primary",
    *[f"patch_tissue_fraction_{s}" for s in ("median", "iqr", "p10", "p90")],
]
F1A = [
    f"cell_{descriptor}_{stat}"
    for descriptor in (
        "area_px", "perimeter_px", "eccentricity", "solidity",
        "circularity", "major_axis_px", "minor_axis_px",
    )
    for stat in ("median", "iqr", "p10", "p90")
]
F1B = [
    f"cell_rgb_mean_{channel}_{stat}"
    for channel in ("r", "g", "b")
    for stat in ("median", "iqr", "p10", "p90")
]
F2 = [
    f"patch_{descriptor}_{stat}"
    for descriptor in (
        "primary_cell_count", "nuclear_foreground_fraction",
        "nearest_neighbour_median_px", "delaunay_edge_median_px",
    )
    for stat in ("median", "iqr", "p10", "p90")
]
F1 = F1A + F1B

CLINICAL_M1 = ["Age", "ECOG PS", "LDH", "EN", "Stage"]
ENTROPY = ["entropy_mean", "entropy_median", "entropy_iqr", "entropy_p10", "entropy_p90"]
POSITIONAL_GEOMETRY = [
    f"{descriptor}_{stat}"
    for descriptor in ("rectCenter_x", "rectCenter_y", "ellip_centroid_x", "ellip_centroid_y")
    for stat in ("mean", "std")
]

CENTRAL_VIEW = [c for c in F1 + F2 if c.endswith("_median")]
SPREAD_VIEW = [c for c in F1 + F2 if c.endswith(("_iqr", "_p10", "_p90"))]


ON_KAGGLE = Path("/kaggle/working").exists()
KAGGLE_INPUT = Path("/kaggle/input")


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def find_input(filename: str) -> Path:
    """Locate an input file anywhere under the Kaggle input mounts."""
    for candidate in sorted(KAGGLE_INPUT.rglob(filename)):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"{filename} not found under {KAGGLE_INPUT}; attach dlbcl-phase3b-inputs "
        "(v2 or later) and dlbcl-morph-tables"
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol_lock_hash(protocol_md: Path, protocol_yaml: Path) -> str:
    """Recompute the §13 lock hash; mirrors build_split_ids.py exactly."""
    text = protocol_md.read_text(encoding="utf-8").replace("\r\n", "\n")
    body = text.split("## 13. Sign-off")[0]
    twin = protocol_yaml.read_text(encoding="utf-8").replace("\r\n", "\n")
    body_digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    twin_digest = hashlib.sha256(twin.encode("utf-8")).hexdigest()
    return hashlib.sha256(f"{body_digest}:{twin_digest}".encode("utf-8")).hexdigest()


def prune_redundant(frame: pd.DataFrame, order: list[str], threshold: float = 0.90) -> list[str]:
    """Protocol §6.2. Drop columns correlating |rho| > threshold with an earlier one.

    `order` is the frozen family order, so the retained column is deterministic
    and cannot be tuned. Computed on the training fold only.
    """
    columns = [c for c in order if c in frame.columns]
    if len(columns) < 2:
        return columns
    correlation = frame[columns].corr(method="spearman").abs().to_numpy()
    kept: list[int] = []
    for index in range(len(columns)):
        if all(correlation[index, earlier] <= threshold for earlier in kept):
            kept.append(index)
    return [columns[i] for i in kept]


def survival_array(frame: pd.DataFrame) -> np.ndarray:
    return Surv.from_arrays(
        event=frame[EVENT_COLUMN].to_numpy().astype(bool),
        time=frame[TIME_COLUMN].to_numpy().astype(float),
    )


def tune_coxnet(x_train: np.ndarray, y_train: np.ndarray, seed: int) -> dict:
    """Inner CV over l1_ratio x alpha. Criterion: mean inner Harrell C (§6.4)."""
    events = np.array([row[0] for row in y_train])
    inner = StratifiedKFold(n_splits=INNER_FOLDS, shuffle=True, random_state=seed)
    folds = list(inner.split(x_train, events))

    best = {"score": -np.inf, "l1_ratio": L1_RATIOS[0], "alpha": None, "alphas": None}
    for l1_ratio in L1_RATIOS:
        alphas = None
        # Coxnet can diverge when the path reaches very small alphas at low EPV.
        # Back off to a shorter path rather than dropping the fold.
        for alpha_min_ratio in (0.01, 0.05, 0.1):
            try:
                path = CoxnetSurvivalAnalysis(
                    l1_ratio=l1_ratio, n_alphas=N_ALPHAS, alpha_min_ratio=alpha_min_ratio
                ).fit(x_train, y_train)
                alphas = list(path.alphas_)
                break
            except (ArithmeticError, ValueError):
                continue
        if alphas is None:
            continue

        scores = np.full((len(folds), len(alphas)), np.nan)
        for fold_index, (train_index, test_index) in enumerate(folds):
            if events[test_index].sum() < 2:
                continue
            try:
                model = CoxnetSurvivalAnalysis(
                    l1_ratio=l1_ratio, alphas=alphas
                ).fit(x_train[train_index], y_train[train_index])
            except Exception:
                continue
            for alpha_index, alpha in enumerate(alphas):
                try:
                    prediction = model.predict(x_train[test_index], alpha=alpha)
                    if np.allclose(prediction, prediction[0]):
                        continue
                    scores[fold_index, alpha_index] = concordance_index_censored(
                        np.array([row[0] for row in y_train[test_index]]),
                        np.array([row[1] for row in y_train[test_index]]),
                        prediction,
                    )[0]
                except Exception:
                    continue

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mean_scores = np.nanmean(scores, axis=0)
        if np.all(np.isnan(mean_scores)):
            continue
        position = int(np.nanargmax(mean_scores))
        if mean_scores[position] > best["score"]:
            best = {
                "score": float(mean_scores[position]),
                "l1_ratio": l1_ratio,
                "alpha": float(alphas[position]),
                "alphas": alphas,
            }
    return best


def tune_rsf(x_train: np.ndarray, y_train: np.ndarray, seed: int) -> dict:
    events = np.array([row[0] for row in y_train])
    inner = StratifiedKFold(n_splits=INNER_FOLDS, shuffle=True, random_state=seed)
    folds = list(inner.split(x_train, events))

    def score_one(params: dict, train_index: np.ndarray, test_index: np.ndarray) -> float:
        model = RandomSurvivalForest(
            n_estimators=500, random_state=seed, n_jobs=1, **params
        ).fit(x_train[train_index], y_train[train_index])
        return concordance_index_censored(
            np.array([row[0] for row in y_train[test_index]]),
            np.array([row[1] for row in y_train[test_index]]),
            model.predict(x_train[test_index]),
        )[0]

    tasks = [
        (grid_index, params, train_index, test_index)
        for grid_index, params in enumerate(RSF_GRID)
        for train_index, test_index in folds
        if events[test_index].sum() >= 2
    ]
    # Parallelise across the grid, one thread per forest. Threading inside a
    # single forest contends badly at this sample size and is ~2.5x slower.
    results = Parallel(n_jobs=RSF_N_JOBS, backend=RSF_BACKEND)(
        delayed(score_one)(params, train_index, test_index)
        for _, params, train_index, test_index in tasks
    )

    grouped: dict[int, list[float]] = {}
    for (grid_index, *_), score in zip(tasks, results):
        grouped.setdefault(grid_index, []).append(score)

    best = {"score": -np.inf, **RSF_GRID[0]}
    for grid_index, scores in grouped.items():
        if scores and np.mean(scores) > best["score"]:
            best = {"score": float(np.mean(scores)), **RSF_GRID[grid_index]}
    return best


def survival_probabilities(model, x: np.ndarray, times: np.ndarray, **kwargs) -> np.ndarray:
    """Predicted S(t) on the fixed grid, clipped to the model's support."""
    try:
        functions = model.predict_survival_function(x, **kwargs)
    except Exception:
        return np.full((len(x), len(times)), np.nan)
    output = np.empty((len(x), len(times)))
    for index, function in enumerate(functions):
        if isinstance(function, StepFunction):
            lower, upper = function.x[0], function.x[-1]
            clipped = np.clip(times, lower, upper)
            output[index] = function(clipped)
        else:
            output[index] = np.nan
    return output


def fit_fold(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    x_test: pd.DataFrame,
    learner: str,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Return standardised test risk scores, test S(t), and chosen hyperparameters."""
    train_values = x_train.to_numpy(dtype=float)
    test_values = x_test.to_numpy(dtype=float)

    if learner == "rsf":
        chosen = tune_rsf(train_values, y_train, seed)
        with parallel_backend(RSF_BACKEND, n_jobs=RSF_N_JOBS):
            model = RandomSurvivalForest(
                n_estimators=500,
                random_state=seed,
                n_jobs=1,
                min_samples_leaf=chosen["min_samples_leaf"],
                max_features=chosen["max_features"],
            ).fit(train_values, y_train)
            train_risk = model.predict(train_values)
            test_risk = model.predict(test_values)
            test_survival = survival_probabilities(model, test_values, TIME_GRID)
    elif x_train.shape[1] == 1:
        # A single covariate is not penalised - shrinkage would simply delete it.
        model = CoxPHSurvivalAnalysis(alpha=1e-6).fit(train_values, y_train)
        chosen = {"learner": "unpenalised_cox", "reason": "single_covariate"}
        train_risk = model.predict(train_values)
        test_risk = model.predict(test_values)
        test_survival = survival_probabilities(model, test_values, TIME_GRID)
    else:
        chosen = tune_coxnet(train_values, y_train, seed)
        if chosen["alpha"] is None:
            return (
                np.full(len(x_test), np.nan),
                np.full((len(x_test), len(TIME_GRID)), np.nan),
                chosen,
                np.array([np.nan, np.nan]),
            )
        # Refit along the full warm-started path, then read off the chosen alpha.
        # Refitting at a single alpha from cold diverges at this EPV.
        model = CoxnetSurvivalAnalysis(
            l1_ratio=chosen["l1_ratio"],
            alphas=chosen["alphas"],
            fit_baseline_model=True,
        ).fit(train_values, y_train)
        train_risk = model.predict(train_values, alpha=chosen["alpha"])
        test_risk = model.predict(test_values, alpha=chosen["alpha"])
        test_survival = survival_probabilities(
            model, test_values, TIME_GRID, alpha=chosen["alpha"]
        )
        chosen = {k: v for k, v in chosen.items() if k != "alphas"}

    # Standardise on training-fold statistics only, so folds pool coherently.
    centre = float(np.mean(train_risk))
    spread = float(np.std(train_risk))
    if spread > 1e-12:
        standardised = (test_risk - centre) / spread
        standardised_train = (train_risk - centre) / spread
    else:
        standardised = test_risk - centre
        standardised_train = train_risk - centre

    # Protocol §7.5: risk-tertile cut-points come from the TRAINING fold only and
    # are applied to held-out patients. No full-cohort threshold search.
    cuts = np.percentile(standardised_train, [100 / 3, 200 / 3])
    return standardised, test_survival, chosen, cuts


def evaluate(
    risk: np.ndarray,
    survival: np.ndarray,
    y_all: np.ndarray,
    mask: np.ndarray | None = None,
) -> dict:
    """Discrimination, calibration and overall accuracy for pooled predictions."""
    if mask is None:
        mask = np.ones(len(risk), dtype=bool)
    mask = mask & np.isfinite(risk)
    y = y_all[mask]
    estimate = risk[mask]
    events = np.array([row[0] for row in y])
    times = np.array([row[1] for row in y])

    result: dict[str, float | None] = {"n": int(mask.sum()), "events": int(events.sum())}
    result["harrell_c"] = float(concordance_index_censored(events, times, estimate)[0])

    try:
        result["uno_c"] = float(
            concordance_index_ipcw(y_all, y, estimate, tau=UNO_TAU)[0]
        )
    except Exception:
        result["uno_c"] = None

    for horizon in AUC_HORIZONS:
        key = f"auc_{horizon:g}y"
        try:
            scores, _ = cumulative_dynamic_auc(y_all, y, estimate, [horizon])
            result[key] = float(scores[0])
        except Exception:
            result[key] = None

    predicted = survival[mask]
    if np.isfinite(predicted).all():
        upper = min(times.max(), TIME_GRID[-1]) - 1e-6
        grid_mask = (TIME_GRID >= TIME_GRID[0]) & (TIME_GRID <= upper)
        try:
            result["integrated_brier"] = float(
                integrated_brier_score(y_all, y, predicted[:, grid_mask], TIME_GRID[grid_mask])
            )
        except Exception:
            result["integrated_brier"] = None
    else:
        result["integrated_brier"] = None

    # Calibration slope: Cox regression of outcome on the out-of-fold predictor.
    # A perfectly calibrated model gives 1.0.
    try:
        slope_model = CoxPHSurvivalAnalysis(alpha=1e-6).fit(
            estimate.reshape(-1, 1), y
        )
        result["calibration_slope"] = float(slope_model.coef_[0])
    except Exception:
        result["calibration_slope"] = None

    # Calibration in the large: observed KM vs mean predicted survival.
    for horizon in AUC_HORIZONS:
        key = f"obs_exp_{horizon:g}y"
        try:
            grid_times, survival_probability = kaplan_meier_estimator(events, times)
            observed = float(np.interp(horizon, grid_times, survival_probability))
            expected = float(np.mean(predicted[:, np.argmin(np.abs(TIME_GRID - horizon))]))
            result[key] = observed / expected if expected > 0 else None
        except Exception:
            result[key] = None

    result["calibration_ok"] = (
        result["calibration_slope"] is not None
        and CALIBRATION_SLOPE_BOUNDS[0] <= result["calibration_slope"] <= CALIBRATION_SLOPE_BOUNDS[1]
    )
    return result


def paired_bootstrap(
    predictions: dict[str, np.ndarray],
    y_all: np.ndarray,
    pairs: list[tuple[str, str]],
    seed: int,
) -> dict:
    """Patient-level paired bootstrap (§7.4). Pairs resampled jointly."""
    rng = np.random.default_rng(seed)
    events = np.array([row[0] for row in y_all])
    times = np.array([row[1] for row in y_all])
    n = len(y_all)

    per_model: dict[str, list[float]] = {name: [] for name in predictions}
    per_pair: dict[str, list[float]] = {f"{a}_minus_{b}": [] for a, b in pairs}

    for _ in range(N_BOOTSTRAP):
        index = rng.integers(0, n, n)
        if events[index].sum() < 2:
            continue
        values: dict[str, float] = {}
        for name, risk in predictions.items():
            estimate = risk[index]
            if not np.isfinite(estimate).all() or np.allclose(estimate, estimate[0]):
                continue
            try:
                values[name] = concordance_index_censored(
                    events[index], times[index], estimate
                )[0]
            except Exception:
                continue
        for name, value in values.items():
            per_model[name].append(value)
        for first, second in pairs:
            if first in values and second in values:
                per_pair[f"{first}_minus_{second}"].append(values[first] - values[second])

    def interval(samples: list[float]) -> dict:
        if len(samples) < 100:
            return {"n": len(samples), "lower": None, "upper": None, "mean": None}
        array = np.asarray(samples)
        return {
            "n": len(samples),
            "mean": float(array.mean()),
            "lower": float(np.percentile(array, 2.5)),
            "upper": float(np.percentile(array, 97.5)),
        }

    return {
        "harrell_c": {name: interval(values) for name, values in per_model.items()},
        "paired_delta_c": {name: interval(values) for name, values in per_pair.items()},
    }


def build_models(
    features: pd.DataFrame, include_optional: bool
) -> dict[str, dict]:
    """The frozen ladder of §3, plus the §9 sensitivity variants."""
    available = set(features.columns)

    def present(columns: list[str]) -> list[str]:
        return [c for c in columns if c in available]

    geometry = [c for c in features.columns if c.endswith(("_mean", "_std")) and c not in ENTROPY]
    m4c = F1 + F2

    ladder: dict[str, dict] = {
        "M0a": {"columns": ["IPI Score"], "order": ["IPI Score"], "role": "IPI score"},
        "M0b": {"columns": ["RIPI Risk Group"], "order": ["RIPI Risk Group"], "role": "R-IPI group"},
        "M1": {"columns": CLINICAL_M1, "order": CLINICAL_M1, "role": "Clinical Cox (primary baseline)"},
        "M2": {"columns": present(geometry), "order": present(geometry), "role": "Released geometry"},
        "M3": {"columns": ENTROPY, "order": ENTROPY, "role": "Global entropy"},
        "M4a": {"columns": F1, "order": F1, "role": "Morphology only"},
        "M4b": {"columns": F2, "order": F2, "role": "Packing only"},
        "M4c": {"columns": m4c, "order": m4c, "role": "Primary image model"},
        "M5": {"columns": CLINICAL_M1 + m4c, "order": CLINICAL_M1 + m4c, "role": "Primary incremental"},
    }
    if include_optional:
        ladder.update({
            "S3_M5_plus_F0": {
                "columns": CLINICAL_M1 + m4c + F0,
                "order": CLINICAL_M1 + F0 + m4c,
                "role": "S3: does sampling exposure explain any gain?",
            },
            "S4_M4c_no_stain": {
                "columns": F1A + F2, "order": F1A + F2,
                "role": "S4: M4c without stain intensity",
            },
            "S5_M2_no_position": {
                "columns": present([c for c in geometry if c not in POSITIONAL_GEOMETRY]),
                "order": present([c for c in geometry if c not in POSITIONAL_GEOMETRY]),
                "role": "S5: M2 without positional descriptors",
            },
            "S7_central": {
                "columns": CENTRAL_VIEW, "order": CENTRAL_VIEW,
                "role": "S7: central tendency only",
            },
            "S7_spread": {
                "columns": SPREAD_VIEW, "order": SPREAD_VIEW,
                "role": "S7: spread / heterogeneity only",
            },
        })
    return ladder


def run_model(
    name: str,
    spec: dict,
    features: pd.DataFrame,
    splits: pd.DataFrame,
    patients: list[str],
    y_all: np.ndarray,
    learner: str,
) -> dict:
    position = {patient: index for index, patient in enumerate(patients)}
    repeats = sorted(splits["repeat"].unique())
    accumulated_risk = np.full((len(repeats), len(patients)), np.nan)
    accumulated_survival = np.full((len(repeats), len(patients), len(TIME_GRID)), np.nan)
    accumulated_tertile = np.full((len(repeats), len(patients)), np.nan)
    per_fold: list[dict] = []
    chosen_records: list[dict] = []

    for repeat_index, repeat in enumerate(repeats):
        repeat_rows = splits[splits["repeat"] == repeat]
        for fold in sorted(repeat_rows["outer_fold"].unique()):
            test_ids = repeat_rows.loc[repeat_rows["outer_fold"] == fold, "patient_id"].tolist()
            test_positions = [position[p] for p in test_ids]
            train_positions = [i for i in range(len(patients)) if i not in set(test_positions)]

            train_frame = features.iloc[train_positions]
            test_frame = features.iloc[test_positions]
            y_train = y_all[train_positions]

            columns = [c for c in spec["columns"] if c in features.columns]
            train_subset = train_frame[columns]

            # §6.1 imputation, training-fold statistics only.
            medians = train_subset.median()
            train_subset = train_subset.fillna(medians)
            test_subset = test_frame[columns].fillna(medians)

            # §6.2 redundancy pruning, then §6.3 scaling - both training-fold only.
            kept = prune_redundant(train_subset, spec["order"])
            train_subset, test_subset = train_subset[kept], test_subset[kept]
            centre, spread = train_subset.mean(), train_subset.std().replace(0, 1.0)
            train_scaled = (train_subset - centre) / spread
            test_scaled = (test_subset - centre) / spread

            seed = SEED + int(repeat) * 100 + int(fold)
            if learner == "rsf":
                # RSF fits are slow enough that silence is indistinguishable from
                # a hang. Emit a heartbeat per fold.
                log(f"    {name} repeat {repeat}/{len(repeats)} fold {fold}")
            risk, survival, chosen, cuts = fit_fold(
                train_scaled, y_train, test_scaled, learner, seed
            )
            accumulated_risk[repeat_index, test_positions] = risk
            if np.isfinite(cuts).all():
                accumulated_tertile[repeat_index, test_positions] = np.digitize(risk, cuts)
            accumulated_survival[repeat_index, test_positions] = survival

            if np.isfinite(risk).all() and not np.allclose(risk, risk[0]):
                fold_y = y_all[test_positions]
                per_fold.append({
                    "repeat": int(repeat), "fold": int(fold), "n_features_kept": len(kept),
                    "harrell_c": float(concordance_index_censored(
                        np.array([r[0] for r in fold_y]),
                        np.array([r[1] for r in fold_y]),
                        risk,
                    )[0]),
                })
            chosen_records.append({"repeat": int(repeat), "fold": int(fold), "n_features_kept": len(kept), **chosen})

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pooled_risk = np.nanmean(accumulated_risk, axis=0)
        pooled_survival = np.nanmean(accumulated_survival, axis=0)

    # Modal held-out tertile across repeats. Each assignment came from a
    # training-fold cut-point, so no patient's own outcome informed its group.
    pooled_tertile = np.full(len(patients), np.nan)
    for index in range(len(patients)):
        column = accumulated_tertile[:, index]
        column = column[np.isfinite(column)]
        if len(column):
            pooled_tertile[index] = np.bincount(column.astype(int), minlength=3).argmax()

    fold_scores = [record["harrell_c"] for record in per_fold]
    return {
        "model": name,
        "role": spec["role"],
        "n_features_declared": len(spec["columns"]),
        "median_features_kept": float(np.median([r["n_features_kept"] for r in chosen_records])),
        "learner": learner,
        "pooled_risk": pooled_risk,
        "pooled_survival": pooled_survival,
        "pooled_tertile": pooled_tertile,
        "per_fold_harrell_c_mean": float(np.mean(fold_scores)) if fold_scores else None,
        "per_fold_harrell_c_sd": float(np.std(fold_scores)) if fold_scores else None,
        "successful_folds": len(per_fold),
        "hyperparameters": chosen_records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path(
        "kaggle/phase_03_morphology_survival/output_e007_full_extraction/patient_features.csv"))
    parser.add_argument("--entropy", type=Path, default=Path("reports/phase_03b_entropy_features.csv"))
    parser.add_argument("--geometry", type=Path, default=Path("reports/phase_03b_geometry_features.csv"))
    parser.add_argument("--clinical", type=Path, default=Path("data/raw/dlbcl_morph/clinical_data_cleaned.csv"))
    parser.add_argument("--splits", type=Path, default=Path("data/manifests/split_ids.csv"))
    parser.add_argument("--split-summary", type=Path, default=Path("data/manifests/split_ids_summary.json"))
    parser.add_argument("--protocol-md", type=Path, default=Path("reports/phase_03b_statistical_analysis_protocol.md"))
    parser.add_argument("--protocol-yaml", type=Path, default=Path("configs/phase_03b_analysis_protocol.yaml"))
    parser.add_argument("--out-dir", type=Path, default=Path("reports/phase_03c_results_tables"))
    parser.add_argument("--cohort", choices=["A", "B", "C"], default="A")
    parser.add_argument("--rsf", action="store_true", help="S6: also fit RSF for M1/M4c/M5")
    parser.add_argument("--sensitivity", action="store_true", help="also fit the §9 model variants")
    parser.add_argument("--smoke", action="store_true", help="2 repeats, 100 bootstraps")
    args = parser.parse_args()

    global N_BOOTSTRAP
    if args.smoke:
        N_BOOTSTRAP = 100

    if ON_KAGGLE:
        args.features = find_input("patient_features.csv")
        args.entropy = find_input("phase_03b_entropy_features.csv")
        args.geometry = find_input("phase_03b_geometry_features.csv")
        args.clinical = find_input("clinical_data_cleaned.csv")
        args.splits = find_input("split_ids.csv")
        args.split_summary = find_input("split_ids_summary.json")
        args.protocol_md = find_input("phase_03b_statistical_analysis_protocol.md")
        args.protocol_yaml = find_input("phase_03b_analysis_protocol.yaml")
        if args.out_dir == Path("reports/phase_03c_results_tables"):
            args.out_dir = Path("/kaggle/working/phase_03c_results_tables")
        log(f"kaggle inputs resolved under {KAGGLE_INPUT}")

    # Chain of custody: the splits must have been generated under a signed protocol.
    split_summary = json.loads(args.split_summary.read_text(encoding="utf-8"))
    recorded = split_summary["protocol_lock_hash"]
    current = protocol_lock_hash(args.protocol_md, args.protocol_yaml)
    log(f"protocol signed by {split_summary['signed_by']} on {split_summary['signed_date']}")
    if recorded != current:
        log(f"WARNING: protocol changed since splits were generated")
        log(f"  splits generated under: {recorded}")
        log(f"  protocol now hashes to: {current}")
        log("  This must be justified in §12 before results are inspected.")
    else:
        log(f"protocol lock hash verified: {current[:16]}...")

    clinical = pd.read_csv(args.clinical, dtype={"patient_id": str})
    e007 = pd.read_csv(args.features, dtype={"patient_id": str})
    entropy = pd.read_csv(args.entropy, dtype={"patient_id": str}).drop(
        columns=["qc_patch_count_eligible", "qc_patch_count_total"], errors="ignore")
    geometry = pd.read_csv(args.geometry, dtype={"patient_id": str})
    splits = pd.read_csv(args.splits, dtype={"patient_id": str})

    frame = e007.merge(entropy, on="patient_id").merge(geometry, on="patient_id").merge(
        clinical, on="patient_id")
    if len(frame) != EXPECTED_PATIENTS:
        sys.exit(f"ABORT: join produced {len(frame)} rows, expected {EXPECTED_PATIENTS} (§1.2)")

    excluded = {"A": [], "B": ["26807"], "C": ["26807", "13957"]}[args.cohort]
    if excluded:
        frame = frame[~frame["patient_id"].isin(excluded)].reset_index(drop=True)
        splits = splits[~splits["patient_id"].isin(excluded)]
    frame = frame.sort_values("patient_id", key=lambda c: c.astype(int)).reset_index(drop=True)

    patients = frame["patient_id"].tolist()
    y_all = survival_array(frame)
    events = int(frame[EVENT_COLUMN].sum())
    log(f"cohort {args.cohort}: {len(patients)} patients, {events} events")
    if args.cohort == "A" and events != EXPECTED_EVENTS:
        sys.exit(f"ABORT: {events} events, protocol §1.4 states {EXPECTED_EVENTS}")

    if args.smoke:
        splits = splits[splits["repeat"] <= 2]
        log("SMOKE MODE: 2 repeats, 100 bootstraps")

    ladder = build_models(frame, include_optional=args.sensitivity)
    results: dict[str, dict] = {}
    for name, spec in ladder.items():
        started = time.time()
        results[name] = run_model(name, spec, frame, splits, patients, y_all, "coxnet")
        log(f"{name:16s} {spec['role'][:38]:38s} "
            f"per-fold C={results[name]['per_fold_harrell_c_mean']:.4f} "
            f"({time.time() - started:.0f}s)")

    if args.rsf:
        for name in ["M1", "M4c", "M5"]:
            started = time.time()
            key = f"S6_{name}_rsf"
            results[key] = run_model(key, ladder[name], frame, splits, patients, y_all, "rsf")
            log(f"{key:16s} RSF ablation "
                f"per-fold C={results[key]['per_fold_harrell_c_mean']:.4f} "
                f"({time.time() - started:.0f}s)")

    log("evaluating pooled out-of-fold predictions ...")
    metrics = {
        name: evaluate(result["pooled_risk"], result["pooled_survival"], y_all)
        for name, result in results.items()
    }

    pairs = [(name, "M1") for name in results if name != "M1"]
    log(f"paired bootstrap, {N_BOOTSTRAP} resamples ...")
    bootstrap = paired_bootstrap(
        {name: result["pooled_risk"] for name, result in results.items()},
        y_all, pairs, SEED,
    )

    # Smoke output never lands beside real results; it would be indistinguishable
    # from a pre-specified run once the filenames match.
    if args.smoke:
        args.out_dir = args.out_dir.with_name(args.out_dir.name + "_SMOKE")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Every variant gets its own filenames. Without this the primary, §9 and RSF
    # runs silently overwrite each other, and the survivor looks like the whole
    # analysis.
    suffix = f"_cohort{args.cohort}"
    if args.sensitivity:
        suffix += "_sens"
    if args.rsf:
        suffix += "_rsf"
    if args.smoke:
        suffix += "_SMOKE"

    table = pd.DataFrame([
        {
            "model": name,
            "role": results[name]["role"],
            "learner": results[name]["learner"],
            "k_declared": results[name]["n_features_declared"],
            "k_kept_median": results[name]["median_features_kept"],
            "harrell_c_pooled": metrics[name]["harrell_c"],
            "harrell_c_lower": bootstrap["harrell_c"][name]["lower"],
            "harrell_c_upper": bootstrap["harrell_c"][name]["upper"],
            "harrell_c_per_fold_mean": results[name]["per_fold_harrell_c_mean"],
            "harrell_c_per_fold_sd": results[name]["per_fold_harrell_c_sd"],
            "uno_c": metrics[name]["uno_c"],
            **{f"auc_{h:g}y": metrics[name][f"auc_{h:g}y"] for h in AUC_HORIZONS},
            "integrated_brier": metrics[name]["integrated_brier"],
            "calibration_slope": metrics[name]["calibration_slope"],
            "calibration_ok": metrics[name]["calibration_ok"],
            **{f"obs_exp_{h:g}y": metrics[name][f"obs_exp_{h:g}y"] for h in AUC_HORIZONS},
        }
        for name in results
    ])
    table.to_csv(args.out_dir / f"model_ladder{suffix}.csv", index=False)

    delta = pd.DataFrame([
        {
            "comparison": key,
            "delta_c_mean": value["mean"],
            "delta_c_lower": value["lower"],
            "delta_c_upper": value["upper"],
            "excludes_zero": (
                None if value["lower"] is None
                else bool(value["lower"] > 0 or value["upper"] < 0)
            ),
        }
        for key, value in bootstrap["paired_delta_c"].items()
    ])
    delta.to_csv(args.out_dir / f"paired_differences{suffix}.csv", index=False)

    oof = pd.DataFrame({"patient_id": patients,
                        TIME_COLUMN: frame[TIME_COLUMN], EVENT_COLUMN: frame[EVENT_COLUMN]})
    for name, result in results.items():
        oof[f"risk_{name}"] = result["pooled_risk"]
        oof[f"tertile_{name}"] = result["pooled_tertile"]
    # Survival curves on the fixed grid, for calibration plots.
    np.savez_compressed(
        args.out_dir / f"pooled_survival{suffix}.npz",
        time_grid=TIME_GRID,
        patient_id=np.array(patients),
        **{name: result["pooled_survival"] for name, result in results.items()},
    )
    oof.to_csv(args.out_dir / f"oof_predictions{suffix}.csv", index=False)

    hyperparameters = pd.DataFrame([
        {"model": name, **record}
        for name, result in results.items() for record in result["hyperparameters"]
    ])
    hyperparameters.to_csv(args.out_dir / f"hyperparameters{suffix}.csv", index=False)

    primary = bootstrap["paired_delta_c"].get("M5_minus_M1", {})
    run_summary = {
        "experiment": "E-009",
        "cohort": args.cohort,
        "patients": len(patients),
        "events": events,
        "excluded_patients": excluded,
        "smoke_mode": args.smoke,
        "protocol_lock_hash_at_split_generation": recorded,
        "protocol_lock_hash_now": current,
        "protocol_unchanged_since_splits": recorded == current,
        "signed_by": split_summary["signed_by"],
        "seed": SEED,
        "n_bootstrap": N_BOOTSTRAP,
        "split_ids_sha256": sha256(args.splits),
        "entropy_features_sha256": sha256(args.entropy),
        "geometry_features_sha256": sha256(args.geometry),
        "primary_estimand": {
            "definition": "paired delta Harrell C, M5 minus M1, cohort A (§3.2)",
            **primary,
        },
        "models_fitted": list(results),
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "scikit_survival": sksurv.__version__,
        },
    }
    (args.out_dir / f"run_summary{suffix}.json").write_text(
        json.dumps(run_summary, indent=2) + "\n", encoding="utf-8")

    print("\n" + "=" * 78)
    print(f"E-009 LADDER COMPLETE | cohort {args.cohort} | {len(patients)} patients | {events} events")
    print("=" * 78)
    display = table[["model", "k_kept_median", "harrell_c_pooled", "harrell_c_lower",
                     "harrell_c_upper", "harrell_c_per_fold_mean", "uno_c",
                     "calibration_slope", "calibration_ok"]]
    print(display.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    print("\nPRIMARY ESTIMAND — M5 vs M1 (paired delta Harrell C):")
    if primary.get("lower") is not None:
        print(f"  delta C = {primary['mean']:+.4f}  95% CI [{primary['lower']:+.4f}, {primary['upper']:+.4f}]")
        verdict = "EXCLUDES zero" if (primary["lower"] > 0 or primary["upper"] < 0) else "INCLUDES zero"
        print(f"  interval {verdict}")
    print(f"\nwrote {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
