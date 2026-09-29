# DLBCL-Morph clinical data — provenance

| Field | Value |
|---|---|
| Downloaded | 2026-08-23 |
| Source | TCIA collection page, direct links |
| clinical_data_cleaned.csv | https://www.cancerimagingarchive.net/wp-content/uploads/clinical_data_cleaned.csv |
| column_description.csv | https://www.cancerimagingarchive.net/wp-content/uploads/column_description.csv |
| MD5 (clinical_data_cleaned.csv) | `9be9d237c49506db16d3c3b53825f827` |
| MD5 (column_description.csv) | `f62031f7d3d32aca24e00a11fcc3021c` |
| Licence | CC BY-NC 4.0 — https://creativecommons.org/licenses/by-nc/4.0/ |
| Data citation | Fernandez-Pol et al. (2022), DOI 10.7937/NVA3-N783 |
| Collection page | https://www.cancerimagingarchive.net/collection/dlbcl-morphology/ |

Notes:
- Full dataset downloaded 2026-08-23 from figshare (canonical source; the Stanford
  Box link in the GitHub README is dead — 404):
  - `DLBCLMorph.zip` (31,815,858,123 bytes) in project root, MD5 verified
    against the figshare API record: `96cf88ad80f26cca82f7e346bad49936` ✅
  - Source: https://ndownloader.figshare.com/files/24697142
  - Article DOI: 10.6084/m9.figshare.12964772.v1 (CC0 per figshare; TCIA lists
    the same collection as CC BY-NC 4.0 — treat as CC BY-NC conservatively)
- Extracted via `kaggle/phase_01b_dlbcl_morph_data_audit/extract_local_subset.py`:
  - `cell_shapes.csv` — 1,035,909 nuclei rows × 25 cols, MD5 `ac5f5ccc7e38cbacf305998208684473`
  - `clinical_data.xlsx` — MD5 `4713b8299808a760931a6c9b9d911c4b`
  - `core.csv` — 514 patient→TMA→core mappings, MD5 `6fe9dbdd95c1adc40a6d1ac2bdf1b173`
  - `annotations.csv` — ROI rectangles per patient/stain, MD5 `31ddd1787af61a649f534d986be9bd8c`
- Zip contents (from directory listing): Patches/ 152,194 files (14.5 GB),
  Cells/ 1,036,975 files (1.06 GB), TMA/ 44 SVS scans (19.7 GB).
  Full extraction needs ~35 GB free — not yet extracted.
- Per-nucleus masks (Cells/*.npy) and patches remain inside the zip until needed.
