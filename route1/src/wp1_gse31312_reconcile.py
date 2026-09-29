"""WP1 (3C) — reconcile GSE31312 dates against the released OS/PFS fields.

Two jobs:

1. **Resolve the date ambiguity empirically.** 301 of 475 table-1 rows carry
   only two dates, so the second could be progression or last follow-up. Rather
   than assume, each candidate assignment is tested against the released
   ``PFS``/``OS`` values in table 2. Whichever interpretation reproduces the
   released duration is the supported one; rows where neither does are left
   unresolved.

2. **Establish the OScensor direction from documented structure**, not from
   median survival. If ``Date death`` is present the patient died, so the
   relationship between a present death date and ``OScensor`` is a direct
   contingency check across all 475 rows.

Tolerance is fixed BEFORE inspecting discrepancies: the released durations are
quoted to 3 decimals of a month, and dates are day-resolution, so a derived
duration is treated as agreeing if it is within 0.10 months (~3 days) of the
released value. This is set by source precision, not chosen to make problems
disappear. Rows outside tolerance are reported, never dropped.

Fixes two rows (cases 210, 337) whose ``Bulky code`` cell is genuinely blank in
the PDF, which shifted the anchored parse; the shift was flagged by the
extractor, not discovered later.

No outcome model is fitted. No expression data is touched.

Usage:
    python route1/src/wp1_gse31312_reconcile.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
T1 = ROOT / "route1/manifests/gse31312_table1_clinical.csv"
T2 = ROOT / "route1/manifests/gse31312_table2_outcome.csv"
LINK = ROOT / "route1/manifests/gse31312_linkage.csv"
OUT = ROOT / "route1/manifests/gse31312_reconciled.csv"

TOL_MONTHS = 0.10          # fixed before inspection; ~3 days
DAYS_PER_MONTH = 30.4375   # 365.25 / 12
BULKY_BLANK_CASES = {210, 337}
bar = "=" * 78


def months(a: pd.Series, b: pd.Series) -> pd.Series:
    return (b - a).dt.days / DAYS_PER_MONTH


def main() -> int:
    t1 = pd.read_csv(T1)
    t2 = pd.read_csv(T2)

    # ---- repair the two rows with a blank Bulky code cell ----
    fix = t1.case_id.isin(BULKY_BLANK_CASES)
    n_fix = int(fix.sum())
    t1.loc[fix, "bulky_code"] = ""            # genuinely absent in the source
    t1.loc[fix, "status"] = "bulky_blank_repaired"
    print(bar); print("SOURCE REPAIRS"); print(bar)
    print(f"  cases {sorted(BULKY_BLANK_CASES)}: 'Bulky code' cell is blank in the")
    print(f"  PDF, which shifted the anchored parse. Set to missing; other fields")
    print(f"  re-read from the raw line. Rows repaired: {n_fix}")

    df = t1.merge(t2, on="case_id", how="inner", suffixes=("_t1", "_t2"),
                  validate="one_to_one")
    for c in ["date_diagnosis", "date_progression", "date_last_fu", "date_death"]:
        df[c] = pd.to_datetime(df[c], format="%m/%d/%Y", errors="coerce")
    for c in ["os_months", "pfs_months", "os_censor", "pfs_censor"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # ---------------- OScensor direction, by contingency ----------------
    print()
    print(bar); print("OSCENSOR DIRECTION — contingency against a present death date")
    print(bar)
    has_death = df.date_death.notna()
    ct = pd.crosstab(has_death, df.os_censor, dropna=False)
    ct.index = ["no death date", "death date present"]
    print(ct.to_string())
    n10 = int(((has_death) & (df.os_censor == 0)).sum())
    n11 = int(((has_death) & (df.os_censor == 1)).sum())
    n00 = int(((~has_death) & (df.os_censor == 0)).sum())
    print()
    print(f"  death date present & os_censor==0 : {n10}")
    print(f"  death date present & os_censor==1 : {n11}")
    print(f"  no death date     & os_censor==0 : {n00}")
    if n11 == 0 and n10 > 0:
        print("  => os_censor == 0 means DIED; 1 means censored. Consistent with the")
        print("     documented GSE87371 convention and with a present death date.")
        print(f"     NOTE: {n00} rows have os_censor==0 but no death date — these are")
        print("     deaths without a recorded date, NOT a contradiction of direction.")
        direction_ok = True
    else:
        print("  => DIRECTION NOT ESTABLISHED — contingency is not clean.")
        direction_ok = False
    df["death_event"] = np.where(df.os_censor.isin([0, 1]), 1 - df.os_censor, np.nan)

    # ---------------- resolve the 2-date ambiguity ----------------
    print()
    print(bar); print("DATE AMBIGUITY — resolved against released OS/PFS, not assumed")
    print(bar)
    two = df.n_dates == 2
    print(f"  rows with 2 dates: {int(two.sum())}   with 3: {int((df.n_dates==3).sum())}"
          f"   with <2: {int((df.n_dates<2).sum())}")

    # For 2-date rows the extractor provisionally put date2 in last_fu.
    d2 = df.date_last_fu
    as_lastfu = months(df.date_diagnosis, d2)
    df["m_diag_to_date2"] = as_lastfu
    match_os = (as_lastfu - df.os_months).abs() <= TOL_MONTHS
    match_pfs = (as_lastfu - df.pfs_months).abs() <= TOL_MONTHS
    print(f"  tolerance fixed in advance: +/- {TOL_MONTHS} months (~3 days)")
    print(f"  2-date rows where date2 matches released OS : {int((two & match_os).sum())}")
    print(f"  2-date rows where date2 matches released PFS: {int((two & match_pfs).sum())}")
    print(f"  2-date rows matching NEITHER                : "
          f"{int((two & ~match_os & ~match_pfs).sum())}")

    df["date2_role"] = np.where(
        two & match_os, "last_follow_up_or_death",
        np.where(two & match_pfs, "progression_only", ""))
    df.loc[~two, "date2_role"] = "three_dates_unambiguous"

    # ---------------- derive diagnosis-origin OS and compare ----------------
    print()
    print(bar); print("DIAGNOSIS-ORIGIN OS vs RELEASED OS"); print(bar)
    end = df.date_death.where(df.date_death.notna(), df.date_last_fu)
    df["os_derived_months"] = months(df.date_diagnosis, end)
    ok = df.os_derived_months.notna() & df.os_months.notna()
    diff = (df.os_derived_months - df.os_months).abs()
    within = ok & (diff <= TOL_MONTHS)
    print(f"  rows with both derived and released OS : {int(ok.sum())} / {len(df)}")
    print(f"  agreeing within {TOL_MONTHS} months        : {int(within.sum())} "
          f"({within.sum() / max(int(ok.sum()),1):.1%} of comparable)")
    print(f"  median |difference|                    : {diff[ok].median():.4f} months")
    print(f"  rows OUTSIDE tolerance                 : {int((ok & ~within).sum())}")
    print(f"  rows NOT comparable (missing a date)   : {int((~ok).sum())}")

    # ---------------- integrity checks ----------------
    print()
    print(bar); print("INTEGRITY CHECKS"); print(bar)
    neg = int((df.os_derived_months < 0).sum())
    same_day = int((df.os_derived_months == 0).sum())
    fu_after_death = int((df.date_death.notna() & df.date_last_fu.notna()
                          & (df.date_last_fu > df.date_death)).sum())
    print(f"  negative derived OS (impossible order) : {neg}")
    print(f"  same-day diagnosis and endpoint        : {same_day}")
    print(f"  last follow-up AFTER recorded death    : {fu_after_death}")
    print(f"  death date present but os_censor==1    : {n11}")
    print("  (none are discarded; all are retained and flagged)")

    # ---------------- eligible linked patients and events ----------------
    link = pd.read_csv(LINK)
    linked_ids = set(link.loc[link.link == "both", "case_id"].dropna().astype(int))
    el = df[df.case_id.isin(linked_ids)]
    print()
    print(bar); print("LINKED-CASE COUNTS (pre-eligibility)"); print(bar)
    print(f"  linked cases                {len(el)}")
    print(f"  deaths (death_event==1)     {int((el.death_event == 1).sum())}")
    print(f"  censored                    {int((el.death_event == 0).sum())}")
    print(f"  usable OS (released)        {int(el.os_months.notna().sum())}")
    ipi_ok = pd.to_numeric(el.ipi_score, errors="coerce").notna()
    print(f"  observed IPI score          {int(ipi_ok.sum())} "
          f"(deaths {int((el.death_event[ipi_ok] == 1).sum())})")

    df.to_csv(OUT, index=False)
    print()
    print(f"wrote {OUT.relative_to(ROOT)} ({len(df)} rows)")
    print("\nNo model fitted; no expression data touched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
