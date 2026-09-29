"""Assess whether TCGA-DLBC can serve as an external validation cohort.

This produced the feasibility finding reported in the manuscript's Limitations:
TCGA-DLBC is the only publicly downloadable DLBCL cohort with H&E whole-slide
images and censored overall survival, but it carries too few deaths to resolve
anything.

Two parts:

1. **Inventory** (live GDC API). Counts slide images, separates FFPE diagnostic
   slides (``-DX``) from frozen sections (``-TS``/``-BS``/``-MS``, unusable for
   nuclear morphology), and joins to vital status.

2. **Power simulation.** Simulates the resulting setting under known true
   concordance values and reports the sampling distribution of the estimate.
   The question is not "is it underpowered" but "can any result be
   interpreted".

Usage:
    python src/analysis/assess_tcga_external_feasibility.py
    python src/analysis/assess_tcga_external_feasibility.py --offline
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np
from lifelines.utils import concordance_index

GDC_FILES = "https://api.gdc.cancer.gov/files"
GDC_CASES = "https://api.gdc.cancer.gov/cases"

# Recorded from the live query on 2026-09-03, so the simulation can be re-run
# without network access and the finding stays checkable.
CACHED = {"ffpe_patients": 44, "events": 8, "censored": 36,
          "frozen_files": 45, "slide_files": 103, "total_gb": 50.2}

SEED = 20260903
REPLICATES = 4000
TARGET_BETAS = [0.0, 0.35, 0.65, 1.05]


def query_gdc() -> dict:
    """Live inventory of TCGA-DLBC slides and vital status."""
    import urllib.request

    def post(url: str, payload: dict) -> dict:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.load(resp)

    slide_filter = {"op": "and", "content": [
        {"op": "in", "content": {"field": "cases.project.project_id",
                                 "value": ["TCGA-DLBC"]}},
        {"op": "in", "content": {"field": "data_type",
                                 "value": ["Slide Image"]}}]}
    files = post(GDC_FILES, {"filters": slide_filter, "size": 300,
                             "fields": "file_name,file_size", "format": "json"})
    hits = files["data"]["hits"]

    ffpe, frozen = set(), 0
    total = 0
    for h in hits:
        name = h["file_name"]
        total += h.get("file_size", 0)
        patient = name.split(".")[0][:12]
        if "-DX" in name:
            ffpe.add(patient)
        elif any(f"-{tag}" in name for tag in ("TS", "BS", "MS")):
            frozen += 1

    case_filter = {"op": "in", "content": {
        "field": "cases.project.project_id", "value": ["TCGA-DLBC"]}}
    cases = post(GDC_CASES, {
        "filters": case_filter, "size": 200,
        "fields": "submitter_id,demographic.vital_status", "format": "json"})
    status = {c["submitter_id"]: (c.get("demographic") or {}).get("vital_status")
              for c in cases["data"]["hits"]}

    events = sum(1 for p in ffpe if status.get(p) == "Dead")
    censored = sum(1 for p in ffpe if status.get(p) == "Alive")
    return {"ffpe_patients": len(ffpe), "events": events,
            "censored": censored, "frozen_files": frozen,
            "slide_files": len(hits), "total_gb": round(total / 1e9, 1)}


def true_concordance(beta: float, rng, n: int = 200_000) -> float:
    """Large-sample uncensored concordance for a given effect size."""
    x = rng.normal(size=n)
    t = rng.exponential(1.0 / np.exp(beta * x))
    return concordance_index(t, -x)


def simulate(beta: float, n: int, events: int, rng) -> float:
    x = rng.normal(size=n)
    t = rng.exponential(1.0 / np.exp(beta * x))
    cutoff = np.quantile(t, events / n)
    return concordance_index(np.minimum(t, cutoff), -x, (t <= cutoff).astype(int))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true",
                    help="skip the GDC query and use the cached 2026-09-03 counts")
    args = ap.parse_args()

    if args.offline:
        inv = dict(CACHED)
        print("using cached inventory (2026-09-03)\n")
    else:
        try:
            inv = query_gdc()
        except Exception as exc:  # network unavailable, blocked, or API change
            print(f"GDC query failed ({exc}); falling back to cached counts\n")
            inv = dict(CACHED)

    print("=" * 64)
    print("TCGA-DLBC INVENTORY")
    print("=" * 64)
    print(f"  slide image files                : {inv['slide_files']}")
    print(f"  total size (GB)                  : {inv['total_gb']}")
    print(f"  frozen-section files (unusable)  : {inv['frozen_files']}")
    print(f"  patients with FFPE diagnostic    : {inv['ffpe_patients']}")
    print(f"  ...deaths                        : {inv['events']}")
    print(f"  ...censored                      : {inv['censored']}")

    n = inv["ffpe_patients"]
    events = inv["events"]
    rng = np.random.default_rng(SEED)

    print()
    print("=" * 64)
    print(f"POWER SIMULATION  (n={n}, events={events}, {REPLICATES} replicates)")
    print("=" * 64)
    print(f"{'true C':>8} {'median':>9} {'2.5%':>8} {'97.5%':>8} {'width':>8}")
    print("-" * 46)

    spans = {}
    for beta in TARGET_BETAS:
        tc = true_concordance(beta, rng)
        ests = np.array([simulate(beta, n, events, rng)
                         for _ in range(REPLICATES)])
        lo, hi = np.percentile(ests, [2.5, 97.5])
        spans[round(tc, 2)] = (lo, hi)
        print(f"{tc:>8.3f} {np.median(ests):>9.3f} {lo:>8.3f} {hi:>8.3f} "
              f"{hi - lo:>8.3f}")

    keys = sorted(spans)
    nlo, nhi = spans[keys[0]]
    blo, bhi = spans[keys[-1]]
    overlap = min(nhi, bhi) - max(nlo, blo)

    print()
    print("=" * 64)
    print("VERDICT")
    print("=" * 64)
    print(f"  a TRUE C of {keys[0]:.2f} yields estimates in [{nlo:.3f}, {nhi:.3f}]")
    print(f"  a TRUE C of {keys[-1]:.2f} yields estimates in [{blo:.3f}, {bhi:.3f}]")
    print(f"  intervals overlap by {overlap:.3f}")
    print()
    if overlap > 0.05:
        print("  A pure-noise model and a genuinely good model produce")
        print("  overlapping estimates. No result from this cohort could be")
        print("  interpreted as either validation or refutation.")
        print("  ==> External validation on TCGA-DLBC is NOT worth performing.")
    else:
        print("  ==> The cohort can separate signal from noise.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
