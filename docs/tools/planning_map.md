# planning_map — Create, Edit & Validate a Planning-Map GeoPackage

## Purpose

A standalone CLI for building a **planning-map GeoPackage** (`planning_map.gpkg`) — the 2D side
of the model. Where `gis_template.py` scaffolds the 1D drainage-network layers (see
[gis_template.md](gis_template.md)), this tool authors the three layers the Delft3D FM conversion
pipeline needs for the 2D domain:

| Layer | Geometry | Role |
|---|---|---|
| `cat_landuses` | none (catalog) | Manning's roughness catalog (`idval`, `descript`, `manning`) |
| `ground` | Polygon | 2D domain polygons — the extent that becomes the 2D mesh + rain mask |
| `roof` | Polygon | Building rooftop polygons — NWRW roof catchments (per-roof rainfall routing) |

All geometry is stored in **EPSG:4326 (WGS84)**; the conversion module reprojects to the project
CRS (default EPSG:32648) when it folds the planning map into the base model.

> This tool is the Delft3D FM successor of the old `landuses_gpkg.py`. Boundary-condition layers
> (`boundary_conditions` / `cat_bscenario`) are **not** part of it — Delft3D FM boundaries are
> derived from outfalls during conversion (`docs/conversion/conversion.md`, stage 6), and
> rainfall is decoupled to the `scenario/` stage.

## Where It Fits

```
planning_map.py  →  planning_map.gpkg  (cat_landuses + ground + roof)
        │
        ▼  passed via --planning-map
run_conversion.py / Conversion  →  stage 8 (planning map):
        │      build_2d_domain (ground → 2D extent + rain_mask.pol + Meteo)
        │      build_nwrw      (roof   → NWRW roof catchments)
        ▼
scenario-agnostic Delft3D FM base model
```

If no planning-map GPKG is supplied to the conversion, the build runs **1D-only** — there is no
2D domain to mesh and no NWRW roof catchments. Use this tool to author a real planning map.

## Layer Schemas

**`cat_landuses`** — roughness catalog (`add-landuse`): `idval`, `descript`, `manning`.

**`ground`** (`add-ground`): `code`, `custom_code`, `descript`, `cellsize`, `annotation`,
`landuse`, `custom_roughness`, `scs_cn` + Polygon geometry. Each polygon needs **either** a
`landuse` (FK into `cat_landuses`) **or** a `custom_roughness`.

**`roof`** (`add-roof`): `code`, `custom_code`, `descript`, `cellsize`, `slope`, `width`,
`roughness`, `isconnected`, `outlet_code`, `outlet_vol`, `street_vol`, `infiltr_vol`,
`annotation`, `surface` + Polygon geometry. The `surface` (String) and `slope` (Real) columns
are the **Task 9 contract** — `build_nwrw` reads them as per-roof overrides.

## Subcommands

All commands take `--gpkg <path>`. Run with the project `.venv`.

### `create` — make an empty planning-map GPKG
```bash
./.venv/Scripts/python.exe src/tools/planning_map.py create --gpkg planning_map.gpkg
```
Creates the three empty layers (`ground`, `roof`, `cat_landuses`) in EPSG:4326.

### `add-landuse` — add a roughness catalog entry
```bash
./.venv/Scripts/python.exe src/tools/planning_map.py add-landuse \
    --gpkg planning_map.gpkg --id STREET --manning 0.017 --descript "Asphalt street"
```
| Arg | Required | Description |
|---|---|---|
| `--id` | Yes | Land-use identifier (`idval`, e.g. `STREET`, `OPEN_SPACE`) |
| `--manning` | Yes | Manning's n roughness coefficient (float) |
| `--descript` | No | Human-readable description |

### `add-ground` — add a 2D domain polygon
```bash
./.venv/Scripts/python.exe src/tools/planning_map.py add-ground \
    --gpkg planning_map.gpkg --geojson domain.geojson --landuse STREET --cellsize 10
```
| Arg | Required | Description |
|---|---|---|
| `--geojson` | Yes | Polygon geometry — a GeoJSON **file path**, an inline GeoJSON string, or a WKT string |
| `--cellsize` | Yes | Target 2D mesh cell size for this polygon (m) |
| `--landuse` | No | FK into `cat_landuses` (`idval`) — sets roughness by catalog |
| `--custom_roughness` | No | Per-polygon Manning's n (overrides the `--landuse` lookup) |
| `--scs_cn` | No | SCS curve number for infiltration losses |
| `--code` | No | Polygon code/label |
| `--descript` | No | Description |

A ground polygon needs **either** `--landuse` **or** `--custom_roughness` (`validate` enforces this).

### `add-roof` — add a building rooftop polygon
```bash
./.venv/Scripts/python.exe src/tools/planning_map.py add-roof \
    --gpkg planning_map.gpkg --geojson roof.geojson --roughness 0.018 --width 30
```
| Arg | Required | Description |
|---|---|---|
| `--geojson` | Yes | Polygon geometry (file path, inline GeoJSON, or WKT) |
| `--roughness` | Yes | Roof Manning's n (must be > 0) |
| `--width` | Yes | Characteristic roof width, m (must be > 0) |
| `--cellsize` | No | Mesh cell size (default `30.0`) |
| `--slope` | No | Per-roof slope override (Task 9) |
| `--surface` | No | Per-roof surface override (Task 9) |
| `--code` | No | Polygon code/label |

### `list` — list all features
```bash
./.venv/Scripts/python.exe src/tools/planning_map.py list --gpkg planning_map.gpkg
```
Prints the `cat_landuses` catalog, then each `ground` and `roof` polygon with its roughness
(`custom_n=…` or `landuse=…`), width, slope, and surface.

### `validate` — check referential integrity
```bash
./.venv/Scripts/python.exe src/tools/planning_map.py validate --gpkg planning_map.gpkg
```
Checks:
- Every `cat_landuses` entry has a non-empty `idval` and non-NULL `manning`.
- Every `ground` polygon references a known `landuse` **or** has a `custom_roughness`, and has
  non-NULL geometry.
- Every `roof` polygon has non-NULL, **positive** `roughness` and `width`, and non-NULL geometry.

Prints `Validation: PASSED` or `Validation: FAILED`.

## Geometry Input Formats

The `--geojson` argument for `add-ground` / `add-roof` accepts any of:
- a **file path** to a GeoJSON file (first feature is used),
- an **inline GeoJSON** string (a `Feature`, `FeatureCollection`, or bare geometry),
- a **WKT** string (e.g. `POLYGON((...))`).

Both require a Polygon; non-Polygon geometry is rejected.

## End-to-End Example

```bash
# 1. Create the planning map
./.venv/Scripts/python.exe src/tools/planning_map.py create \
    --gpkg dataset/planning_map.gpkg

# 2. Define a roughness catalog
./.venv/Scripts/python.exe src/tools/planning_map.py add-landuse \
    --gpkg dataset/planning_map.gpkg --id STREET --manning 0.017
./.venv/Scripts/python.exe src/tools/planning_map.py add-landuse \
    --gpkg dataset/planning_map.gpkg --id OPEN_SPACE --manning 0.035

# 3. Add a ground domain polygon (10 m cells, STREET roughness)
./.venv/Scripts/python.exe src/tools/planning_map.py add-ground \
    --gpkg dataset/planning_map.gpkg --geojson domain.geojson --landuse STREET --cellsize 10

# 4. Validate
./.venv/Scripts/python.exe src/tools/planning_map.py validate \
    --gpkg dataset/planning_map.gpkg

# 5. Convert WITH the planning map (2D domain + NWRW roof catchments)
./.venv/Scripts/python.exe src/tools/run_conversion.py \
    --dataset dataset/ --out output/base_model/ \
    --dem dem.tif --planning-map dataset/planning_map.gpkg
```

## Notes

- **CRS** — all layers are EPSG:4326; conversion reprojects ground/roof polygons to the project
  CRS (default EPSG:32648) via pyproj.
- **QGIS editing** — because it is a plain GeoPackage, `planning_map.gpkg` can also be opened and
  edited directly in QGIS Desktop (draw `ground`/`roof` polygons, edit the catalog) instead of
  using the CLI subcommands.
- **Downstream** — ground polygons feed `build_2d_domain` (2D extent, `rain_mask.pol`, Meteo
  block); roof polygons feed `build_nwrw` (NWRW roof catchments). See
  `docs/conversion/conversion.md` (stage 8) and `docs/conversion/mesh_generation.md`.
- **Environment** — run with the project `.venv` (`./.venv/Scripts/python.exe`). Uses
  `geopandas`/`shapely`/`pyproj`; no GDAL/OGR.
