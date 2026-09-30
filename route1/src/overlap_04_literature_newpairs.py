"""How do papers use the overlapping pairs found by the expression scan (O-090)?

Pairs (duplicated samples, from dup_scan_reported_duplicates.csv):
  GSE181063 x GSE117556   68 shared samples (5.2% of GSE181063, 7.3% of GSE117556)
  GSE10846  x GSE23501     4 shared samples (1.0% of GSE10846, 5.8% of GSE23501)

Same method as overlap_02: Europe PMC hits (full text) naming both members of a
pair with signature/risk-model terms; open-access full texts fetched; every
sentence naming a relevant accession extracted and tagged for reading. The
per-paper class is assigned by reading (overlap_05_classification_newpairs.py).
Opens no expression or outcome data.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from overlap_02_literature_roles import TAGS  # noqa: E402  same tag rubric

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "geo_brief"
FT = RAW / "overlap_fulltext"
B = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
SIG = '(signature OR "risk score" OR "risk model" OR "prognostic model" OR nomogram)'
PAIRS = {"GSE181063|GSE117556": ["GSE181063", "GSE117556", "GSE69051"],
         "GSE10846|GSE23501": ["GSE10846", "GSE23501", "GSE53786", "GSE11318"]}


def search(q: str) -> list[dict]:
    out, cursor = [], "*"
    while True:
        u = B + "?" + urllib.parse.urlencode({"query": q, "format": "json", "resultType": "lite",
                                              "pageSize": 1000, "cursorMark": cursor})
        d = json.load(urllib.request.urlopen(u, timeout=60))
        time.sleep(0.3)
        out += d["resultList"]["result"]
        nxt = d.get("nextCursorMark")
        if not nxt or nxt == cursor or len(out) >= d["hitCount"]:
            return out
        cursor = nxt


def main() -> None:
    FT.mkdir(parents=True, exist_ok=True)
    result = {}
    for pair, accs in PAIRS.items():
        a, b = pair.split("|")
        hits = search(f'"{a}" AND "{b}" AND {SIG}')
        papers = []
        for r in hits:
            meta = {k: r.get(k) for k in ["id", "source", "pmid", "pmcid", "doi", "title", "pubYear",
                                         "isOpenAccess", "journalTitle"]}
            if r.get("isOpenAccess") != "Y" or not r.get("pmcid"):
                papers.append({**meta, "status": "not_open_access"})
                continue
            dest = FT / f"{r['pmcid']}.xml"
            if not dest.exists():
                try:
                    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{r['pmcid']}/fullTextXML"
                    with urllib.request.urlopen(url, timeout=60) as resp:
                        dest.write_bytes(resp.read())
                    time.sleep(0.4)
                except Exception as exc:
                    papers.append({**meta, "status": f"fetch_failed {exc}"})
                    continue
            try:
                root = ET.fromstring(dest.read_bytes())
            except ET.ParseError as exc:
                papers.append({**meta, "status": f"parse_failed {exc}"})
                continue
            for rl in root.iter("ref-list"):
                rl.clear()
            body = root.find(".//body")
            txt = re.sub(r"\s+", " ", "".join((body if body is not None else root).itertext()))
            sents = re.split(r"(?<=[.;])\s+(?=[A-Z(])", txt)
            found = [{"acc": [x for x in accs if x in s],
                      "tags": [t for t, p in TAGS.items() if re.search(p, s, re.I)],
                      "s": s[:500]} for s in sents if any(x in s for x in accs)]
            dedup = [s[:400] for s in sents if re.search(TAGS["D"], s, re.I)
                     and re.search(r"sample|patient|dataset|cohort|GSE", s, re.I)]
            papers.append({**meta, "status": "ok", "sentences": found, "dedup_mentions": dedup[:6]})
        result[pair] = papers
        print(f"{pair}: {len(hits)} hits | OA parsed {sum(p['status']=='ok' for p in papers)} | "
              f"not OA {sum(p['status']=='not_open_access' for p in papers)}")
    json.dump(result, open(RAW / "overlap_newpairs_roles.json", "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
