"""Cross-accession patient/array overlap among public DLBCL GEO series.

The signature-audit pilot found a source stating that GSE53786 was "drawn from
the Lenz et al. dataset" (GSE10846). This script tests overlap directly from
GEO sample metadata, using IDENTIFIER keys only:

  K1  the same GSM accession listed in two series (GEO allows one GSM in many)
  K2  the same microarray-database ID (e.g. LLMPP 'mAdbID') in two series
  K3  the same submitter case/patient identifier in two series, where both
      series come from the same network (reported, never merged, since case
      numbers from different networks can collide by chance)

Outcome fields are never read or used for matching. Raw GEO text goes to the
git-ignored raw folder; the tracked output is the key table and a summary.
"""
from __future__ import annotations

import csv
import re
import time
import urllib.request
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "geo_brief"
MAN = ROOT / "manifests"

SERIES = [
    "GSE10846", "GSE11318", "GSE53786", "GSE34171", "GSE4475", "GSE4732",
    "GSE31312", "GSE87371", "GSE181063", "GSE117556", "GSE32918", "GSE23501",
    "GSE22470", "GSE69051", "GSE19246", "GSE12195",
]
URL = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={}&targ=gsm&form=text&view=brief"
# Fields that can carry identity. Outcome-bearing characteristics are skipped.
OUTCOME = re.compile(r"follow|surviv|status|death|dead|alive|censor|os[_ ]|pfs|efs|event|time", re.I)


def fetch(acc: str) -> str:
    dest = RAW / f"{acc}_gsm_brief.txt"
    if not dest.exists():
        with urllib.request.urlopen(URL.format(acc), timeout=300) as r:
            dest.write_bytes(r.read())
        time.sleep(0.5)
    return dest.read_text(encoding="utf-8", errors="replace")


def parse(acc: str, txt: str) -> list[dict]:
    out, cur = [], None
    for line in txt.splitlines():
        if line.startswith("^SAMPLE"):
            cur = {"series": acc, "gsm": line.split("=", 1)[1].strip(), "fields": []}
            out.append(cur)
        elif cur is not None and line.startswith("!Sample_") and "=" in line:
            k, v = (s.strip() for s in line[1:].split("=", 1))
            if k in ("Sample_title", "Sample_source_name_ch1", "Sample_platform_id"):
                cur[k] = v
            elif k == "Sample_characteristics_ch1" and not OUTCOME.search(v.split(":", 1)[0]):
                cur["fields"].append(v)
            elif k == "Sample_relation":
                cur.setdefault("relations", []).append(v)
    return out


def keys(s: dict) -> dict:
    blob = " | ".join([s.get("Sample_title", ""), s.get("Sample_source_name_ch1", ""), *s["fields"]])
    k = {}
    m = re.search(r"mAdb ?ID[:= ]*(\d+)", blob, re.I)
    if m:
        k["madb"] = m.group(1)
    m = re.search(r"(?:individual|patient|case)(?: id| number| no\.?)?\s*[:=]\s*([A-Za-z0-9_.-]+)", blob, re.I)
    if m:
        k["case"] = m.group(1)
    return k


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    samples = []
    for acc in SERIES:
        try:
            txt = fetch(acc)
        except Exception as exc:
            print(f"{acc}: FETCH FAILED {exc}")
            continue
        s = parse(acc, txt)
        for x in s:
            x.update(keys(x))
        samples += s
        plat = sorted({x.get("Sample_platform_id", "") for x in s})
        nk = sum("madb" in x for x in s), sum("case" in x for x in s)
        print(f"{acc:10s} {len(s):5d} samples  platforms={plat}  madb={nk[0]}  case={nk[1]}")

    with open(MAN / "geo_identity_keys.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["series", "gsm", "platform", "title", "madb_id", "case_id"])
        for x in samples:
            w.writerow([x["series"], x["gsm"], x.get("Sample_platform_id", ""),
                        x.get("Sample_title", ""), x.get("madb", ""), x.get("case", "")])

    print("\nPairwise overlap (K1 same GSM | K2 same mAdbID | K3 same case id):")
    by = defaultdict(lambda: defaultdict(set))
    for x in samples:
        by[x["series"]]["gsm"].add(x["gsm"])
        if "madb" in x:
            by[x["series"]]["madb"].add(x["madb"])
        if "case" in x:
            by[x["series"]]["case"].add(x["case"])
    rows = []
    for a, b in combinations([s for s in SERIES if s in by], 2):
        k1 = len(by[a]["gsm"] & by[b]["gsm"])
        k2 = len(by[a]["madb"] & by[b]["madb"])
        k3 = len(by[a]["case"] & by[b]["case"])
        if k1 or k2 or k3:
            rows.append((a, b, len(by[a]["gsm"]), len(by[b]["gsm"]), k1, k2, k3))
            print(f"  {a} x {b}: n={len(by[a]['gsm'])}/{len(by[b]['gsm'])}  K1={k1}  K2={k2}  K3={k3}")
    with open(MAN / "geo_overlap_pairs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["series_a", "series_b", "n_a", "n_b", "k1_same_gsm", "k2_same_madb", "k3_same_case_id"])
        w.writerows(rows)


if __name__ == "__main__":
    main()
