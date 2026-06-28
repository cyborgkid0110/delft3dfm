# run_conversion — Build a Delft3D FM Base Model from the CLI

## Purpose

A command-line wrapper around the conversion submodule (`src/conversion/`). It takes a
standardized CSV dataset directory and an output target, and produces a single
**scenario-agnostic Delft3D FM base model** folder — a DIMR-ready model with no rainfall data
baked in.

Under the hood it constructs `src.conversion.conversion.Conversion(dataset_dir, out_dir, …)` and
calls `.run()`, which executes the 13-stage conversion pipeline (branches → cross-sections →
roughness → storage → structures → boundaries → observations → planning map → mesh1d → mesh2d →
links → fields → write+validate). See `docs/conversion/conversion.md` for the stage-by-stage
architecture.

> **Rainfall is decoupled.** The conversion emits a base model with **no rainfall values**. A
> rainfall scenario (`.bui` hyetograph / boundary `.bc` values) is authored separately and
> combined into the base model at simulation time — see the `scenario/` and `simulation/` stages.
> That is why this tool has no `--scenario` / per-scenario output: one dataset yields one reusable
> base model.

## How It Works

```
run_conversion.py
    │  reads the standardized CSV dataset (+ optional DEM and planning map)
    ↓
Conversion(dataset, out, dem_path, planning_map, bbox).run()
    │  13 stages → hydrolib-core model + DIMR config
    ↓
<out>/                          (one Delft3D FM base model folder)
    │  round-trip validated (output parses + re-serializes without error)
```

## Input Dataset Layout

The dataset directory must follow the standardized CSV layout (e.g. as produced by
`gpkg_to_csv.py`, schema in `docs/dataset.md`):

```
<dataset>/
  thoat_nuoc/
    manholes.csv, sewers.csv, pumps.csv, weir.csv, orifices.csv, outfalls.csv
  mang_luoi_song_ho_kenh_muong/
    canals.csv, rivers.csv, lakes.csv
  thuy_van/
    hyetographs.csv
```

The 2D domain (`ground`/`roof`/`cat_landuses`) is supplied separately as a **planning-map
GeoPackage** via `--planning-map` (author it with `src/tools/planning_map.py`). Without it, the
build is 1D-only.

## Usage

```bash
# Minimal (1D-only, no DEM, no planning map)
./.venv/Scripts/python.exe src/tools/run_conversion.py \
    --dataset dataset/ --out output/base_model/

# Full (DEM bed-level + 2D planning map + bbox clip)
./.venv/Scripts/python.exe src/tools/run_conversion.py \
    --dataset dataset/ --out output/base_model/ \
    --dem dem.tif \
    --planning-map dataset/planning_map.gpkg \
    --bbox 105.7 20.9 106.0 21.1
```

| Argument | Required | Description |
|---|---|---|
| `--dataset` | Yes | Path to the standardized CSV dataset directory |
| `--out` | Yes | Output directory for the Delft3D FM base model |
| `--dem` | No | DEM raster (`.tif`/`.asc`) for bed-level initialisation (stage 12, `inifield`) |
| `--planning-map` | No | Planning-map GeoPackage (`ground`/`roof`/`cat_landuses` layers) for the 2D domain + NWRW |
| `--bbox` | No | Bounding-box clip `MIN_LON MIN_LAT MAX_LON MAX_LAT` in EPSG:4326 (space-separated, 4 values) |

Paths can be relative to the repository root or absolute.

## Typical Workflow

```
Step 1: gis_template.py   →  Empty drawing GPKG (1D layers)
    ↓
Step 2: Draw features in QGIS Desktop
    ↓
Step 3: gpkg_to_csv.py    →  Export standardized CSVs into <dataset>/
    ↓
Step 4: Fill required fields in the CSVs (elevations, dimensions, names)
    ↓
Step 4b (optional): planning_map.py  →  planning_map.gpkg (2D ground/roof/landuses)
    ↓
Step 5: run_conversion.py →  Scenario-agnostic Delft3D FM base model in <out>/
    ↓
Step 6 (later): attach a rainfall scenario  →  simulate  (scenario/ + simulation/ stages)
```

## Notes

- **Scenario-agnostic output** — the base model is reusable: attach different rainfall scenarios
  at simulation time without re-running conversion. There is no per-scenario GPKG loop here.
- **CRS** — input CSV/planning-map/bbox are EPSG:4326 (WGS84); the model is built in the
  projected metric CRS (default EPSG:32648 / UTM 48N, configurable via `crs.out`).
- **Validation** — stage 13 round-trips every produced file through hydrolib-core (parse +
  re-serialize) and runs cross-reference checks. A failure is reported in the run output.
- **DEM paths with spaces** — quote the `--dem` value if the filename contains spaces.
- **Bed-level vs. mesh** — the DEM drives bed-level/`inifield` and node-level refinement; mesh
  generation (mesh1d/mesh2d/links) is a stage **inside** conversion, not a separate tool. See
  `docs/conversion/mesh_generation.md`.
- **Environment** — run with the project `.venv` (`./.venv/Scripts/python.exe`). Requires
  `hydrolib-core`, `meshkernel`, `geopandas`, `shapely`, `rasterio`, `pyproj`.
