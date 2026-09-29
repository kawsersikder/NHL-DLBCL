# GSE181063 — provenance

| Field | Value |
|---|---|
| Series | GSE181063 |
| Title | Whole genome expression profiling based on paraffin embedded tissue of a large DLBCL cohort |
| Platform | GPL14951 (Illumina Whole-Genome DASL HT v4) |
| Source URL | `https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE181063&targ=gsm&form=text&view=brief` |
| Retrieved | 2026-09-10 |
| File | `GSE181063_gsm_brief.txt` |
| Bytes | 4369328 |
| SHA-256 | `cafd3057122e7a887581d089a7d729c6382bfa57bbfd3369aeb2a4d336d00466` |
| Samples parsed | 1310 |
| Eligible (see manifest) | 556 |

Only sample **metadata** was retrieved. No expression matrix has been
downloaded, and no expression values have been inspected or joined.

The series description states 1,311 biopsied patients; 1,310 samples are
deposited. Neither figure is the analysable count — see
`reports/route1_gse181063_manifest.csv` and the eligibility cascade in
`src/data/build_gse181063_manifest.py`.

Regenerate with:

```
python src/data/build_gse181063_manifest.py
```
