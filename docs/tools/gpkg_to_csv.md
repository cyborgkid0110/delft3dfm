# gpkg_to_csv — Export GeoPackage Layers to Standardized CSV

## Purpose

After drawing drainage-network components in QGIS (stored in a drawing GeoPackage — see
[gis_template.md](gis_template.md)), this tool exports each layer to a standardized CSV file.
The CSVs follow the schema in `docs/dataset.md` and are the input format expected by the
conversion module (`src/conversion/`).

Every attribute field that exists in **both** the GPKG layer and the CSV schema is copied;
schema fields absent from the GPKG layer are written as empty strings. The `ID` and geometry
(`Shape`/`RouteShape`) columns are always filled. So if you enter attribute values while drawing
(e.g. `Name`, `SeriesName`, `InvElev_m`), they come through directly — and the validation below
flags any required ones you left blank.

## How It Works

The tool reads named layers from a `.gpkg` and writes one CSV per layer:

```
<gpkg>                          <dst>/
  canals         ──────────→    mang_luoi_song_ho_kenh_muong/canals.csv
  rivers         ──────────→    mang_luoi_song_ho_kenh_muong/rivers.csv
  lakes          ──────────→    mang_luoi_song_ho_kenh_muong/lakes.csv
  sewers         ──────────→    thoat_nuoc/sewers.csv
  manholes       ──────────→    thoat_nuoc/manholes.csv
  pumps          ──────────→    thoat_nuoc/pumps.csv
  weirs          ──────────→    thoat_nuoc/weir.csv
  orifices       ──────────→    thoat_nuoc/orifices.csv
  outfalls       ──────────→    thoat_nuoc/outfalls.csv
  hyetograph     ──────────→    thuy_van/hyetographs.csv
```

For each feature:

- **ID** is taken from the `ID` attribute field (falls back to the feature index if absent).
- **Geometry** is converted to GeoJSON and written to the `Shape` column (Point/Polygon layers)
  or `RouteShape` column (LineString layers).
- If the source CRS is not WGS84 (EPSG:4326), coordinates are automatically reprojected to
  EPSG:4326. A layer with no CRS is assumed to already be EPSG:4326.
- All other schema columns absent from the GPKG are written as empty strings.

## Output CSV Schema

Each CSV has the full set of columns defined in the standardized schema. For example,
`manholes.csv`:

```
ID,Name,Type,Area_m2,Size_m,CoverType,InvElev_m,RimElev_m,...,Shape
1,,,,,,,,"{""type"":""Point"",""coordinates"":[105.827,21.013]}"
2,,,,,,,,"{""type"":""Point"",""coordinates"":[105.828,21.014]}"
```

The user then fills in the required fields (e.g. `Name`, `InvElev_m`, `RimElev_m` for manholes)
before running the conversion module.

## Supported Layers

| GPKG layer | CSV output path | Geometry column |
|---|---|---|
| `canals` | `mang_luoi_song_ho_kenh_muong/canals.csv` | `RouteShape` (LineString) |
| `rivers` | `mang_luoi_song_ho_kenh_muong/rivers.csv` | `RouteShape` (LineString) |
| `lakes` | `mang_luoi_song_ho_kenh_muong/lakes.csv` | `Shape` (Point) |
| `sewers` | `thoat_nuoc/sewers.csv` | `RouteShape` (LineString) |
| `manholes` | `thoat_nuoc/manholes.csv` | `Shape` (Point) |
| `pumps` | `thoat_nuoc/pumps.csv` | `Shape` (Point) |
| `weirs` | `thoat_nuoc/weir.csv` | `Shape` (Point) |
| `orifices` | `thoat_nuoc/orifices.csv` | `Shape` (Point) |
| `outfalls` | `thoat_nuoc/outfalls.csv` | `Shape` (Point) |
| `hyetograph` | `thuy_van/hyetographs.csv` | `Shape` (Point) |

Missing layers are skipped with a warning.

## Usage

```bash
./.venv/Scripts/python.exe src/tools/gpkg_to_csv.py \
    --gpkg drawing.gpkg \
    --dst  dataset/
```

| Argument | Required | Description |
|---|---|---|
| `--gpkg` | Yes | Source GeoPackage file |
| `--dst` | Yes | Destination directory for CSV files (created if needed) |
| `--no-validate` | No | Skip required-field validation after export (do not exit non-zero on missing fields) |

Paths can be relative to the repository root or absolute.

## Required-Field Validation

After exporting, the tool validates the written rows and prints a `Field validation` summary
(unless `--no-validate`). There are two tiers, because the conversion module substitutes a
default for almost every field — only a few omissions actually break the downstream pipeline:

| Tier | Output | Blocks? | What it covers |
|---|---|---|---|
| **ERROR** | per offending row / structural | yes — exits non-zero | (1) `hyetograph.SeriesName` empty (`BREAKING_FIELDS`) — a hyetograph station with no series link. (2) **Structural** (`validate_network_structure`): a 1D network (manholes/sewers drawn) with **0 outfalls** — the network has no outlet, so flow has nowhere to leave. |
| **WARN** | aggregated count per field | no | Advisory fields (`ADVISORY_FIELDS`) the converter fills with a default when blank (e.g. `manholes.InvElev_m`, `Name`, link `FromNode`/`ToNode`). Informational, so you know which attributes are using defaults. |

Example (valid pipeline — WARNs do not block):

```
Field validation
============================================================
  WARN:  sewers.Diam_mm: empty in 24/24 feature(s) (conversion will substitute a default)
  WARN:  manholes.InvElev_m: empty in 13/13 feature(s) (conversion will substitute a default)
============================================================
  Validation: PASSED (0 error(s), 2 warning(s))
```

Example (blocking error):

```
  ERROR: hyetograph 'RG_x': required field 'SeriesName' is empty
  Validation: FAILED (1 error(s), 0 warning(s))
```

Fix the **ERROR** fields in the drawing GPKG, re-export, and re-run. The `SeriesName` of each
hyetograph station must match the `SeriesName` used in the `thuy_van/rainfall_*.csv` files
(rainfall CSVs are authored separately as part of the rainfall scenario — they are not produced
by this tool).

## Typical Workflow

```
Step 1: Draw components in QGIS (stored in .gpkg)
    ↓
Step 2: gpkg_to_csv.py  →  Export to standardized CSV (ID + geometry filled)
    ↓
Step 3: Fill required fields in the CSV (elevations, dimensions, names, …)
    ↓
Step 4: run_conversion.py  →  Convert CSV dataset to a Delft3D FM base model
```

## Notes

- Coordinates are rounded to 8 decimal places in WGS84, giving sub-millimeter precision.
- The CSV uses UTF-8 BOM encoding (`utf-8-sig`) for compatibility with Excel.
- The output folder structure matches the dataset layout expected by
  `src/conversion/conversion.py` and documented in `docs/dataset.md`.
- **Environment** — run with the project `.venv` (`./.venv/Scripts/python.exe`). Uses
  `geopandas`/`shapely`; no GDAL/OGR. Layer enumeration falls back from `pyogrio` to `fiona`.
