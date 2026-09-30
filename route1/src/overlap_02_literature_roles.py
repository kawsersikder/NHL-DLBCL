"""How do published DLBCL signature papers use GEO series that share arrays?

Input: Europe PMC hits for papers naming both members of an overlapping pair
(GSE10846 with GSE11318 / GSE53786 / GSE4732, and GSE11318 with GSE53786).
For each open-access paper, extract every sentence naming one of the four
accessions and tag it:
  T  training / discovery / model construction
  V  validation / testing
  M  merged / combined / pooled
  D  any mention of duplicates, overlap, shared or removed samples
The tags are a reading aid; the per-paper classification is made by reading the
extracted sentences and is recorded with its supporting quote.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "geo_brief"
FT = RAW / "overlap_fulltext"
ACC = ["GSE10846", "GSE11318", "GSE53786", "GSE4732"]
TAGS = {
    "T": r"train|discover|construct|develop|establish|derive|identif(y|ied) .*genes",
    "V": r"validat|test(ing)? (set|cohort|data)|verif|external|independent",
    "M": r"merg|combin|integrat|pool|batch|ComBat|concatenat",
    "D": r"duplicat|overlap|shared samples|same (patients|samples)|redundan|removed .*(repeat|same)",
}


def main() -> None:
    FT.mkdir(parents=True, exist_ok=True)
    hits = json.load(open(RAW / "epmc_pair_hits.json", encoding="utf-8"))
    papers = {}
    for pair, rows in hits.items():
        for r in rows:
            if r.get("isOpenAccess") == "Y" and r.get("pmcid"):
                papers.setdefault(r["pmcid"], {**r, "pairs": []})["pairs"].append(pair)
    out = []
    for pmcid, meta in sorted(papers.items()):
        dest = FT / f"{pmcid}.xml"
        if not dest.exists():
            try:
                url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
                with urllib.request.urlopen(url, timeout=60) as resp:
                    dest.write_bytes(resp.read())
                time.sleep(0.4)
            except Exception as exc:
                out.append({**meta, "status": f"fetch_failed {exc}"})
                continue
        try:
            root = ET.fromstring(dest.read_bytes())
        except ET.ParseError as exc:
            out.append({**meta, "status": f"parse_failed {exc}"})
            continue
        for rl in root.iter("ref-list"):
            rl.clear()
        body = root.find(".//body")
        txt = re.sub(r"\s+", " ", "".join((body if body is not None else root).itertext()))
        sents = re.split(r"(?<=[.;])\s+(?=[A-Z(])", txt)
        found = []
        for s in sents:
            accs = [a for a in ACC if a in s]
            if not accs:
                continue
            tags = [t for t, p in TAGS.items() if re.search(p, s, re.I)]
            found.append({"acc": accs, "tags": tags, "s": s[:500]})
        dedup = [s[:400] for s in sents if re.search(TAGS["D"], s, re.I)
                 and re.search(r"sample|patient|dataset|cohort|GSE", s, re.I)]
        out.append({**meta, "status": "ok", "sentences": found, "dedup_mentions": dedup[:6]})
    json.dump(out, open(RAW / "overlap_paper_roles.json", "w", encoding="utf-8"), indent=1)
    print(f"{len(papers)} open-access papers; ok={sum(o['status']=='ok' for o in out)}")


if __name__ == "__main__":
    main()
