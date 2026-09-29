"""Signature-audit pilot, step 2: retrieve open-access full texts and build reading digests.

For each INCLUDED record with a PMCID, fetch the Europe PMC full-text XML and
write a digest of the passages extraction needs:
  - sentences naming a cohort accession or a named DLBCL series;
  - sentences giving the signature formula / genes / coefficients;
  - tables whose text mentions coefficients.
The digest is a reading aid only. Every extracted value is still taken from,
and quoted against, the source text. Opens no expression or outcome data.
"""
from __future__ import annotations

import csv
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "signature_pilot" / "fulltext"
DIG = ROOT / "data" / "raw" / "signature_pilot" / "digests"

COHORT = re.compile(
    r"\b(GSE\d{3,6}|GPL\d{2,5}|E-MTAB-\d+|EGA[SD]\d+|phs\d{6}|TCGA[-\w]*|"
    r"NCICCR[-\w]*|HMRN|LLMPP|REMoDL-?B|Lenz|Reddy|Chapuy|Schmitz|Sha\b|"
    r"GOYA|POLARIX|CALGB|LYSA|GHEDI)", re.I)
FORMULA = re.compile(
    r"(risk ?score|riskscore|coefficient|formula|signature (consist|compris|includ)|"
    r"-gene (signature|model|panel)|genes? (were|was) (selected|identified|retained)|"
    r"×|\*\s*exp|\bexpr?\b)", re.I)


def sentences(txt: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.;])\s+(?=[A-Z(])", txt) if s.strip()]


def flat(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    DIG.mkdir(parents=True, exist_ok=True)
    scr = {r["pmid"]: r for r in csv.DictReader(open(ROOT / "manifests" / "sig_pilot_screening.csv", encoding="utf-8"))}
    status = []
    for pmid, r in scr.items():
        if r["decision"] != "include" or not r["pmcid"]:
            continue
        pmcid = r["pmcid"]
        dest = RAW / f"{pmcid}.xml"
        if not dest.exists():
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
            try:
                with urllib.request.urlopen(url, timeout=60) as resp:
                    dest.write_bytes(resp.read())
            except Exception as exc:  # recorded, not hidden
                status.append((pmid, pmcid, f"fetch_failed: {exc}"))
                continue
            time.sleep(0.5)
        root = ET.fromstring(dest.read_bytes())
        body = root.find(".//body")
        if body is None:
            status.append((pmid, pmcid, "no_body_in_xml"))
            continue
        # Methods/Results prose, excluding the reference list.
        paras = [flat(p) for p in body.iter("p")]
        sents = [s for p in paras for s in sentences(p)]
        coh = [s for s in sents if COHORT.search(s)]
        frm = [s for s in sents if FORMULA.search(s) and s not in coh]
        tabs = []
        for tw in root.iter("table-wrap"):
            t = flat(tw)
            if re.search(r"coef|β|beta|lasso", t, re.I):
                tabs.append(t[:3000])
        abstract = flat(root.find(".//abstract")) if root.find(".//abstract") is not None else ""
        with open(DIG / f"{pmid}_{pmcid}.txt", "w", encoding="utf-8") as f:
            f.write(f"PMID {pmid}  {pmcid}\n\n## ABSTRACT\n{abstract}\n\n## COHORT SENTENCES ({len(coh)})\n")
            f.writelines(f"- {s}\n" for s in coh)
            f.write(f"\n## FORMULA/GENE SENTENCES ({len(frm)})\n")
            f.writelines(f"- {s}\n" for s in frm[:40])
            f.write(f"\n## COEFFICIENT TABLES ({len(tabs)})\n")
            f.writelines(f"- {t}\n\n" for t in tabs)
        status.append((pmid, pmcid, f"ok: {len(coh)} cohort / {len(frm)} formula sentences / {len(tabs)} tables"))
    for s in status:
        print(*s, sep="  ")


if __name__ == "__main__":
    main()
