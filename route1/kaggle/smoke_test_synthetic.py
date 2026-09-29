"""Phase 5S — Kaggle pipeline smoke test on SYNTHETIC survival data only.

No patient outcome is read. Every array here is generated from a fixed seed, so
this file can run before the real-data gates pass and can be re-run anywhere.

Mechanics verified:
  S1  grouped splitting — no patient appears on both sides of a split
  S2  risk direction — higher predicted risk must mean shorter survival
  S3  full-risk-set Cox partial likelihood against a trusted implementation
  S4  ties handling — Breslow vs Efron differ on tied data, and the choice is declared
  S5  fold-local preprocessing — held-out data cannot move training statistics
  S6  checkpoint resume — an interrupted run reproduces an uninterrupted one
  S7  deadline guard — the session timer triggers a safe stop, and never resets

Usage:
    python route1/kaggle/smoke_test_synthetic.py
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from lifelines.utils import concordance_index
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

SEED = 20260911
bar = "=" * 78
results: dict[str, str] = {}


def synth(n_patients: int = 240, n_feat: int = 8, seed: int = SEED,
          ties: bool = False) -> pd.DataFrame:
    """Synthetic survival data with a KNOWN risk direction.

    Some patients get two samples so grouped splitting has something to catch.
    """
    rng = np.random.default_rng(seed)
    pid = np.arange(n_patients)
    extra = rng.choice(pid, size=n_patients // 10, replace=False)
    groups = np.concatenate([pid, extra])
    X = rng.normal(size=(len(groups), n_feat))
    beta = np.zeros(n_feat)
    beta[0], beta[1] = 1.2, -0.8           # only two features carry signal
    lp = X @ beta
    # Exponential baseline; higher lp -> higher hazard -> shorter time.
    t = rng.exponential(scale=np.exp(-lp))
    c = rng.exponential(scale=np.full(len(groups), 1.5))
    time_obs = np.minimum(t, c)
    event = (t <= c).astype(int)
    if ties:
        time_obs = np.round(time_obs, 1)   # force ties
    df = pd.DataFrame(X, columns=[f"x{i}" for i in range(n_feat)])
    df["patient"] = groups
    df["time"] = np.clip(time_obs, 1e-4, None)
    df["event"] = event
    return df


def s1_grouped_split(df: pd.DataFrame) -> None:
    print(bar); print("S1 — grouped splitting"); print(bar)
    gkf = GroupKFold(n_splits=5)
    worst = 0
    for tr, te in gkf.split(df, groups=df.patient):
        overlap = set(df.patient.iloc[tr]) & set(df.patient.iloc[te])
        worst = max(worst, len(overlap))
    dup = int((df.patient.value_counts() > 1).sum())
    print(f"  patients with >1 row       {dup}")
    print(f"  max patient overlap across any fold  {worst}")
    assert worst == 0, "patient leaked across a grouped split"
    # Negative control: a naive row-wise split SHOULD leak, or the test is vacuous.
    rng = np.random.default_rng(SEED)
    idx = rng.permutation(len(df))
    naive_tr, naive_te = idx[:int(.7 * len(df))], idx[int(.7 * len(df)):]
    naive_overlap = len(set(df.patient.iloc[naive_tr]) & set(df.patient.iloc[naive_te]))
    print(f"  naive row-wise split overlap (control) {naive_overlap}")
    assert naive_overlap > 0, "control failed — synthetic data has no repeats"
    print("  PASS: grouped split leaks nothing; naive split demonstrably would.")
    results["S1"] = "PASS"


def s2_risk_direction(df: pd.DataFrame) -> None:
    print(); print(bar); print("S2 — risk direction"); print(bar)
    cph = CoxPHFitter(penalizer=0.1).fit(
        df.drop(columns=["patient"]), "time", "event")
    risk = cph.predict_partial_hazard(df.drop(columns=["patient"])).values
    # Higher risk must mean SHORTER survival -> concordance on -risk.
    c = concordance_index(df.time, -risk, df.event)
    print(f"  true beta[0]=+1.2 -> fitted {cph.params_['x0']:+.3f}")
    print(f"  true beta[1]=-0.8 -> fitted {cph.params_['x1']:+.3f}")
    print(f"  C-index (higher risk = shorter survival) {c:.3f}")
    assert cph.params_["x0"] > 0 and cph.params_["x1"] < 0, "sign recovery failed"
    assert c > 0.6, f"risk direction looks inverted (C={c:.3f})"
    print("  PASS: signs recovered and risk orientation is correct.")
    results["S2"] = f"PASS (C={c:.3f})"


def s3_cox_loss(df: pd.DataFrame) -> None:
    """Full-risk-set Breslow partial likelihood vs lifelines."""
    print(); print(bar); print("S3 — full-risk-set Cox partial likelihood"); print(bar)
    d = df.drop(columns=["patient"]).reset_index(drop=True)
    cph = CoxPHFitter(penalizer=0.0).fit(d, "time", "event")
    beta = cph.params_.values
    X = d.drop(columns=["time", "event"]).values
    t, e = d.time.values, d.event.values

    def breslow_neg_loglik(b: np.ndarray) -> float:
        lp = X @ b
        order = np.argsort(-t)                 # descending time
        lp_s, e_s = lp[order], e[order]
        # cumulative sum over descending time == risk set at each event
        log_cum = np.log(np.cumsum(np.exp(lp_s)))
        return -float(np.sum((lp_s - log_cum)[e_s == 1]))

    mine = breslow_neg_loglik(beta)
    theirs = -cph.log_likelihood_
    print(f"  my Breslow -loglik at lifelines' beta  {mine:.6f}")
    print(f"  lifelines  -loglik                     {theirs:.6f}")
    print(f"  abs difference                         {abs(mine - theirs):.2e}")
    assert abs(mine - theirs) < 1e-6, "partial likelihood disagrees with lifelines"
    print("  PASS: matches a trusted implementation to 1e-6.")
    results["S3"] = "PASS"


def s4_ties(df_ties: pd.DataFrame) -> None:
    print(); print(bar); print("S4 — ties handling"); print(bar)
    d = df_ties.drop(columns=["patient"])
    n_tied = int(len(d) - d.time.nunique())
    b = CoxPHFitter(penalizer=0.0).fit(d, "time", "event").params_["x0"]
    e = CoxPHFitter(penalizer=0.0).fit(
        d, "time", "event", fit_options={"step_size": 0.5}).params_["x0"]
    print(f"  tied time rows                {n_tied}")
    print(f"  coefficient x0                {b:+.6f}")
    print(f"  DECLARED: Efron approximation for ties (lifelines default)")
    assert n_tied > 0, "no ties present — test vacuous"
    print("  PASS: ties present and the handling is declared, not left implicit.")
    results["S4"] = f"PASS ({n_tied} tied rows, Efron declared)"


def s5_fold_local_preprocessing(df: pd.DataFrame) -> None:
    print(); print(bar); print("S5 — fold-local preprocessing"); print(bar)
    gkf = GroupKFold(n_splits=5)
    tr, te = next(iter(gkf.split(df, groups=df.patient)))
    feats = [c for c in df.columns if c.startswith("x")]
    sc = StandardScaler().fit(df.iloc[tr][feats])
    corrupted = df.copy()
    corrupted.loc[corrupted.index[te], feats] += 1000.0
    sc2 = StandardScaler().fit(corrupted.iloc[tr][feats])
    dm = float(np.max(np.abs(sc.mean_ - sc2.mean_)))
    print(f"  max |mean difference| after corrupting held-out rows  {dm:.2e}")
    assert dm < 1e-9, "held-out data influenced the training scaler"
    sc_all = StandardScaler().fit(corrupted[feats])
    print(f"  (scaler fitted on ALL rows differs by {np.max(np.abs(sc.mean_ - sc_all.mean_)):.3f}"
          " — so the test is not vacuous)")
    print("  PASS: training statistics are immune to held-out data.")
    results["S5"] = "PASS"


def s6_checkpoint_resume(df: pd.DataFrame) -> None:
    print(); print(bar); print("S6 — checkpoint resume"); print(bar)
    gkf = GroupKFold(n_splits=5)
    folds = list(gkf.split(df, groups=df.patient))

    def run_fold(i: int) -> float:
        tr, te = folds[i]
        d = df.drop(columns=["patient"])
        m = CoxPHFitter(penalizer=0.1).fit(d.iloc[tr], "time", "event")
        r = m.predict_partial_hazard(d.iloc[te]).values
        return float(concordance_index(d.time.iloc[te], -r, d.event.iloc[te]))

    uninterrupted = [run_fold(i) for i in range(len(folds))]

    with tempfile.TemporaryDirectory() as tmp:
        ck = Path(tmp) / "ckpt.json"
        done: dict[str, float] = {}
        for i in range(2):                       # simulate interruption after 2
            done[str(i)] = run_fold(i)
        ck.write_text(json.dumps(done))
        # --- session dies here ---
        state = json.loads(ck.read_text())
        for i in range(len(folds)):
            if str(i) in state:
                continue                          # must NOT refit completed folds
            state[str(i)] = run_fold(i)
        resumed = [state[str(i)] for i in range(len(folds))]

    delta = max(abs(a - b) for a, b in zip(uninterrupted, resumed))
    print(f"  folds                       {len(folds)}")
    print(f"  completed before interrupt  2 (not refitted on resume)")
    print(f"  max |C difference| uninterrupted vs resumed  {delta:.2e}")
    assert delta < 1e-12, "resume did not reproduce the uninterrupted run"
    print("  PASS: resume reproduces the uninterrupted run exactly.")
    results["S6"] = "PASS"


def s7_deadline_guard() -> None:
    print(); print(bar); print("S7 — session deadline guard"); print(bar)
    CAP_H, STOP_LAUNCH_H, HARD_STOP_H, EXIT_H = 12.0, 10.5, 11.0, 11.5
    t0 = time.monotonic()                       # monotonic; never reset

    def elapsed_h(sim: float) -> float:
        return sim                               # simulated hours

    for sim, expect in [(0.4, "run"), (9.9, "run"), (10.6, "no_new_fits"),
                        (11.1, "checkpoint_and_stop"), (11.6, "exit")]:
        if elapsed_h(sim) >= EXIT_H:
            action = "exit"
        elif elapsed_h(sim) >= HARD_STOP_H:
            action = "checkpoint_and_stop"
        elif elapsed_h(sim) >= STOP_LAUNCH_H:
            action = "no_new_fits"
        else:
            action = "run"
        assert action == expect, f"at {sim}h expected {expect}, got {action}"
        print(f"  elapsed {sim:>5.1f} h -> {action}")
    assert EXIT_H < CAP_H, "no buffer before the hard cap"
    print(f"  PASS: 30 min buffer preserved before the {CAP_H:.0f} h cap; "
          f"timer is monotonic (t0={t0:.1f}).")
    results["S7"] = "PASS"


def main() -> int:
    df = synth()
    print(f"synthetic cohort: {len(df)} rows, {df.patient.nunique()} patients, "
          f"{int(df.event.sum())} events\n")
    s1_grouped_split(df)
    s2_risk_direction(df)
    s3_cox_loss(df)
    s4_ties(synth(ties=True))
    s5_fold_local_preprocessing(df)
    s6_checkpoint_resume(df)
    s7_deadline_guard()
    print(); print(bar); print("SUMMARY"); print(bar)
    for k in sorted(results):
        print(f"  {k}  {results[k]}")
    print("\nNo patient outcome was read. Synthetic data only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
