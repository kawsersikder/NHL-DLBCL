"""Signature-audit pilot, step 1: frozen PubMed search, deterministic sample, abstracts.

Implements route1/reports/signature_pilot_plan.md exactly. Reads papers'
bibliographic records only; opens no expression or outcome data.

Outputs
  manifests/sig_pilot_pubmed_hits.csv   all PMIDs returned by the frozen query
  manifests/sig_pilot_sample.csv        the 40 sampled records, bibliographic metadata only
  data/raw/signature_pilot/sig_pilot_sample_with_abstracts.csv   same, with abstracts (git-ignored)
  data/raw/signature_pilot/efetch_sample.xml   raw PubMed XML (git-ignored)
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "signature_pilot"
MAN = ROOT / "manifests"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL = {"tool": "nhl_dlbcl_route1", "email": "monisikdertechnical@gmail.com"}

QUERY = (
    '("diffuse large B-cell lymphoma"[tiab] OR DLBCL[tiab]) AND (signature[tiab] '
    'OR "risk score"[tiab] OR "risk model"[tiab] OR "prognostic model"[tiab]) AND '
    '(gene[tiab] OR genes[tiab] OR expression[tiab]) AND (prognos*[tiab] OR '
    'survival[tiab])'
)
MINDATE, MAXDATE = "2013/01/01", "2026/09/30"
SEED, N_SAMPLE = 20260930, 40


def get(url: str, params: dict) -> bytes:
    q = urllib.parse.urlencode({**params, **TOOL})
    with urllib.request.urlopen(f"{url}?{q}", timeout=60) as r:
        return r.read()


def text(el) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    res = json.loads(get(f"{EUTILS}/esearch.fcgi", {
        "db": "pubmed", "term": QUERY, "retmode": "json", "retmax": 10000,
        "datetype": "pdat", "mindate": MINDATE, "maxdate": MAXDATE,
    }))["esearchresult"]
    count = int(res["count"])
    pmids = sorted(int(p) for p in res["idlist"])
    assert len(pmids) == count, f"retrieved {len(pmids)} of {count} hits"
    digest = hashlib.sha256(",".join(map(str, pmids)).encode()).hexdigest()

    with open(MAN / "sig_pilot_pubmed_hits.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pmid"])
        w.writerows([[p] for p in pmids])

    sample = random.Random(SEED).sample(pmids, N_SAMPLE)

    time.sleep(0.4)
    xml = get(f"{EUTILS}/efetch.fcgi", {
        "db": "pubmed", "id": ",".join(map(str, sample)), "retmode": "xml"})
    (RAW / "efetch_sample.xml").write_bytes(xml)
    root = ET.fromstring(xml)

    rows = {}
    for art in root.findall(".//PubmedArticle"):
        pmid = int(text(art.find(".//MedlineCitation/PMID")))
        a = art.find(".//Article")
        abstract = " ".join(
            (f"{t.get('Label')}: " if t.get("Label") else "") + text(t)
            for t in a.findall(".//Abstract/AbstractText"))
        # The article's own IDs only. A ".//ArticleIdList" search also matches the
        # ID lists inside ReferenceList, which silently overwrote these with the
        # IDs of cited papers in the first run (recorded as a pilot deviation).
        ids = {i.get("IdType"): text(i)
               for i in art.findall("./PubmedData/ArticleIdList/ArticleId")}
        rows[pmid] = {
            "pmid": pmid,
            "year": text(a.find(".//Journal/JournalIssue/PubDate/Year"))
                    or text(a.find(".//Journal/JournalIssue/PubDate/MedlineDate"))[:4],
            "journal": text(a.find(".//Journal/ISOAbbreviation")),
            "pub_types": "; ".join(text(p) for p in a.findall(".//PublicationTypeList/PublicationType")),
            "doi": ids.get("doi", ""),
            "pmcid": ids.get("pmc", ""),
            "title": text(a.find(".//ArticleTitle")),
            "abstract": abstract,
        }
    missing = [p for p in sample if p not in rows]
    assert not missing, f"efetch returned no record for {missing}"

    # Abstracts are publisher text: they stay in the git-ignored raw folder, and
    # the tracked manifest carries bibliographic metadata only.
    fields = ["draw_order", *rows[sample[0]].keys()]
    with open(RAW / "sig_pilot_sample_with_abstracts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for k, p in enumerate(sample, 1):
            w.writerow({"draw_order": k, **rows[p]})
    with open(MAN / "sig_pilot_sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[c for c in fields if c != "abstract"])
        w.writeheader()
        for k, p in enumerate(sample, 1):
            w.writerow({"draw_order": k, **{c: v for c, v in rows[p].items() if c != "abstract"}})

    meta = {"retrieved_utc": stamp, "query": QUERY, "mindate": MINDATE,
            "maxdate": MAXDATE, "hits": count, "pmid_list_sha256": digest,
            "seed": SEED, "n_sample": N_SAMPLE,
            "n_with_pmcid": sum(bool(r["pmcid"]) for r in rows.values())}
    (MAN / "sig_pilot_search_meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
