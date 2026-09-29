"""WP1 — source-auditable extraction of the GSE31312 clinical supplement.

Two tables, joined on ``Case #`` only (never by row or page position):
  table 1, pages 0-8  : demographics, IPI components, response, dates
  table 2, pages 9-17 : death date, censors, PFS/OS, IHC, subtype, GEO id

Parsing strategy: the text layer gives space-separated tokens with
variable-width fields ("AAS III-IV", "0 or 1", "low, int-low",
"DLBCL GEP data N0001"), so a naive split is wrong. Fields are instead
ANCHORED from both ends of each line inward, because the leading and trailing
fields have unambiguous shapes. Anything that does not resolve cleanly is
marked ``status != ok`` and retained verbatim -- never coerced to zero or to a
plausible date.

Two independent engines (pypdf and PyMuPDF) extract the text layer and their
token streams are compared per line. Agreement is recorded but is NOT treated
as proof of correctness; ambiguous rows are listed for inspection.

A known ambiguity, deliberately not guessed: table 1 may carry 1, 2 or 3 dates.
With three, they are diagnosis / progression / last follow-up. With two, the
second could be either progression or last follow-up. Those rows are flagged
``dates_ambiguous`` and are resolved later against table 2's PFS/OS values
rather than by assumption.

No outcome model is fitted. This script only extracts and reconciles.

Usage:
    python route1/src/wp1_gse31312_extract.py
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "route1/data/raw/GSE31312_clinical_supplement.pdf"
GSM = ROOT / "route1/data/raw/GSE31312_gsm_brief.txt"
OUT_T1 = ROOT / "route1/manifests/gse31312_table1_clinical.csv"
OUT_T2 = ROOT / "route1/manifests/gse31312_table2_outcome.csv"
OUT_LINK = ROOT / "route1/manifests/gse31312_linkage.csv"
OUT_DISC = ROOT / "route1/reports/gse31312_extraction_discrepancies.csv"

T1_PAGES, T2_PAGES = range(0, 9), range(9, 18)
DATE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
GEO_TAIL = re.compile(r"^(DLBCL GEP data)\s+(N\d{4})$")
AAS_CODE = {"I-II", "III-IV"}
ECOG_CODE_MULTI = ("0", "or", "1")
IPI_CODE_FIRST = {"low,", "high,"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def pages_pypdf() -> list[str]:
    from pypdf import PdfReader
    return [(p.extract_text() or "") for p in PdfReader(str(PDF)).pages]


def pages_pymupdf() -> list[str]:
    import pymupdf
    doc = pymupdf.open(str(PDF))
    return [doc[i].get_text() for i in range(doc.page_count)]


def rows_for(pages: list[str], idx) -> list[tuple[int, str]]:
    """(page, line) for data lines, dropping header lines."""
    out = []
    for p in idx:
        for line in pages[p].split("\n"):
            line = line.strip()
            if not line or line.startswith("Case #"):
                continue
            out.append((p, line))
    return out


def parse_t1(page: int, line: str) -> dict:
    t = line.split()
    rec = {"page": page, "raw": line, "status": "ok", "note": ""}
    try:
        rec["case_id"] = int(t[0])
        rec["age"] = t[1]
        rec["gender"] = t[2]
        rec["hiv_status"] = t[3]
        rec["ann_arbor_stage"] = t[4]
        i = 5
        if t[i] == "AAS" and t[i + 1] in AAS_CODE:
            rec["aas_code"] = f"{t[i]} {t[i+1]}"; i += 2
        else:
            rec["aas_code"] = t[i]; i += 1

        # ---- anchor from the right ----
        j = len(t)
        dates = []
        while j > i and DATE.match(t[j - 1]):
            dates.append(t[j - 1]); j -= 1
        dates.reverse()
        rec["n_dates"] = len(dates)
        rec["response"] = t[j - 1] if j > i else ""
        j -= 1
        rec["ldh"] = t[j - 1]; j -= 1
        rec["b_symptoms"] = t[j - 1]; j -= 1
        rec["bulky_code"] = t[j - 1]; j -= 1

        # ---- middle, left to right ----
        rec["n_extranodal"] = t[i]; i += 1
        rec["ecog"] = t[i]; i += 1
        if tuple(t[i:i + 3]) == ECOG_CODE_MULTI:
            rec["ecog_code"] = "0 or 1"; i += 3
        else:
            rec["ecog_code"] = t[i]; i += 1
        rec["ipi_score"] = t[i]; i += 1
        if t[i] in IPI_CODE_FIRST:
            rec["ipi_code"] = f"{t[i]} {t[i+1]}"; i += 2
        else:
            rec["ipi_code"] = t[i]; i += 1

        if i != j:
            rec["status"] = "token_mismatch"
            rec["note"] = f"left cursor {i} != right cursor {j}"

        # Dates: 3 == diagnosis/progression/last-follow-up. Fewer is ambiguous.
        rec["date_diagnosis"] = dates[0] if dates else ""
        if len(dates) == 3:
            rec["date_progression"], rec["date_last_fu"] = dates[1], dates[2]
        elif len(dates) == 2:
            rec["date_progression"], rec["date_last_fu"] = "", dates[1]
            rec["status"] = "dates_ambiguous" if rec["status"] == "ok" else rec["status"]
            rec["note"] = (rec["note"] + "; 2 dates: 2nd assigned to last_fu "
                           "PROVISIONALLY, resolve against table 2").strip("; ")
        else:
            rec["date_progression"] = rec["date_last_fu"] = ""
            if len(dates) < 2:
                rec["status"] = "few_dates" if rec["status"] == "ok" else rec["status"]
    except Exception as exc:                      # keep the row, flag it
        rec["status"] = "parse_error"
        rec["note"] = repr(exc)
    return rec


def parse_t2(page: int, line: str) -> dict:
    t = line.split()
    rec = {"page": page, "raw": line, "status": "ok", "note": ""}
    try:
        rec["case_id"] = int(t[0])
        # ---- anchor from the right: "DLBCL GEP data N####" ----
        tail = " ".join(t[-4:])
        m = GEO_TAIL.match(tail)
        if not m:
            rec["status"] = "geo_id_unparsed"
            rec["note"] = f"tail={tail!r}"
            return rec
        rec["geo_depository"] = tail
        rec["geo_sample_id"] = m.group(2)
        j = len(t) - 4
        rec["gep_class"] = t[j - 1]; j -= 1
        rec["three_marker_class"] = t[j - 1]; j -= 1
        ihc = t[j - 5:j]
        rec["CD10"], rec["BCL6"], rec["FOXP1"], rec["GCET"], rec["MUM1"] = ihc
        j -= 5
        rec["os_months"] = t[j - 1]; j -= 1
        rec["pfs_months"] = t[j - 1]; j -= 1
        rec["os_censor"] = t[j - 1]; j -= 1
        rec["pfs_censor"] = t[j - 1]; j -= 1
        # whatever remains between case_id and here is the death date (or nothing)
        mid = t[1:j]
        if len(mid) == 0:
            rec["date_death"] = ""
        elif len(mid) == 1 and DATE.match(mid[0]):
            rec["date_death"] = mid[0]
        else:
            rec["date_death"] = " ".join(mid)
            rec["status"] = "death_date_unexpected"
            rec["note"] = f"mid={mid!r}"
    except Exception as exc:
        rec["status"] = "parse_error"
        rec["note"] = repr(exc)
    return rec


def compare_engines(a: list[str], b: list[str], idx, label: str) -> int:
    """Count data lines whose token streams differ between the two engines."""
    ra = {r[1] for r in rows_for(a, idx)}
    rb = {r[1] for r in rows_for(b, idx)}
    only_a, only_b = ra - rb, rb - ra
    print(f"  {label}: pypdf {len(ra)} lines, pymupdf {len(rb)} lines, "
          f"differing {len(only_a) + len(only_b)}")
    return len(only_a) + len(only_b)


def main() -> int:
    bar = "=" * 78
    print(bar); print("WP1 — GSE31312 supplement extraction"); print(bar)
    print(f"  PDF sha256 {sha256(PDF)}")

    pp, pm = pages_pypdf(), pages_pymupdf()
    print(f"  pages: pypdf {len(pp)}, pymupdf {len(pm)}")
    print()
    print("INDEPENDENT ENGINE COMPARISON (agreement is evidence, not proof)")
    d1 = compare_engines(pp, pm, T1_PAGES, "table 1")
    d2 = compare_engines(pp, pm, T2_PAGES, "table 2")

    t1 = pd.DataFrame([parse_t1(p, l) for p, l in rows_for(pp, T1_PAGES)])
    t2 = pd.DataFrame([parse_t2(p, l) for p, l in rows_for(pp, T2_PAGES)])

    print()
    print(bar); print("STRUCTURAL VALIDATION"); print(bar)
    for name, df in (("table 1", t1), ("table 2", t2)):
        ids = df.case_id.dropna().astype(int)
        expected = set(range(1, 476))
        print(f"  {name}: rows {len(df)}  unique case_id {ids.nunique()}  "
              f"duplicated {int(ids.duplicated().sum())}")
        print(f"    missing case numbers vs 1..475: {sorted(expected - set(ids))[:10]}")
        print(f"    status counts: {df.status.value_counts().to_dict()}")
        print(f"    rows per page: {df.page.value_counts().sort_index().to_dict()}")

    merged = t1.merge(t2, on="case_id", how="outer", suffixes=("_t1", "_t2"),
                      indicator=True, validate="one_to_one")
    print()
    print(f"  JOIN on case_id (validate=one_to_one): {dict(merged._merge.value_counts())}")

    # ---------------- linkage to GEO ----------------
    g = GSM.read_text(encoding="utf-8", errors="replace")
    titles = re.findall(r"^!Sample_title = (.*)$", g, re.M)
    accs = re.findall(r"^!Sample_geo_accession = (.*)$", g, re.M)
    geo = pd.DataFrame({"sample_title": [t.strip() for t in titles],
                        "gsm": [a.strip() for a in accs]})
    geo["geo_sample_id"] = geo.sample_title.str.extract(r"(N\d{4})")
    link = merged.merge(geo, on="geo_sample_id", how="outer", indicator="link")
    print()
    print(bar); print("LINKAGE TO GEO"); print(bar)
    print(f"  supplement ids {merged.geo_sample_id.nunique()}  "
          f"GEO ids {geo.geo_sample_id.nunique()}")
    print(f"  link outcome: {dict(link.link.value_counts())}")
    both = link[link.link == "both"]
    print(f"  LINKED: {len(both)}")
    print(f"  supplement-only: {sorted(link.loc[link.link=='left_only','geo_sample_id'].dropna())}")
    only_geo = sorted(link.loc[link.link == 'right_only', 'geo_sample_id'].dropna())
    print(f"  GEO-only ({len(only_geo)}): {only_geo[:12]}{' ...' if len(only_geo)>12 else ''}")
    assert both.geo_sample_id.is_unique, "non-unique linkage key"
    assert both.gsm.is_unique, "non-unique GSM in linkage"
    print("  uniqueness assertions PASSED (geo_sample_id and gsm both unique)")

    # ---------------- discrepancy export ----------------
    disc = pd.concat([
        t1[t1.status != "ok"].assign(table="t1"),
        t2[t2.status != "ok"].assign(table="t2"),
    ], ignore_index=True)
    OUT_DISC.parent.mkdir(parents=True, exist_ok=True)
    disc.to_csv(OUT_DISC, index=False)
    t1.to_csv(OUT_T1, index=False)
    t2.to_csv(OUT_T2, index=False)
    link.to_csv(OUT_LINK, index=False)
    print()
    print(f"  engine-difference lines: table1 {d1}, table2 {d2}")
    print(f"  flagged rows exported: {len(disc)}")
    for p, f in ((OUT_T1, t1), (OUT_T2, t2), (OUT_LINK, link), (OUT_DISC, disc)):
        print(f"  wrote {p.relative_to(ROOT)} ({len(f)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
