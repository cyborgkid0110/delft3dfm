# Tool Docs Migration (swmm → delft3d), Adapted to Delft3D FM

**Date:** 2026-06-26
**Status:** Approved

## Problem

The old repo `G:\workspace\github\swmm` holds CLI tool docs under `docs/tools/`. Four of
those tools have already been migrated into this repo's `src/tools/`. Their docs have not.
The old docs describe an Iber+SWMM / IberGIS / QGIS stack (IberPlus.exe, SWMM INP, `.gpkg`
IberGIS model, conda `qgis-env`, EPSG:3405). This repo targets **Delft3D FM** (hydrolib-core,
DIMR binary, `.mdu`/`.bui`/`.bc`, `.venv`, EPSG:32648). The docs cannot be copied verbatim;
they must be **adapted** to the Delft3D FM stack and the current tool signatures.

## Scope

Migrate docs only for the four tools actually present in `src/tools/`:

| New doc | Source doc (swmm) | Tool |
|---|---|---|
| `docs/tools/gis_template.md` | `docs/tools/gis_template.md` | `src/tools/gis_template.py` |
| `docs/tools/gpkg_to_csv.md` | `docs/tools/gpkg_to_csv.md` | `src/tools/gpkg_to_csv.py` |
| `docs/tools/planning_map.md` | `docs/tools/landuses_gpkg.md` | `src/tools/planning_map.py` |
| `docs/tools/run_conversion.md` | `docs/tools/run_conversion.md` | `src/tools/run_conversion.py` |

**Out of scope** (different engine, no migrated tool here): `run_simulation.md`,
`iber/simulation.md`, `iber/mesh_generation.md`, `iber/linux_setup.md`, `run_mesh.md`,
`run_batch.md`. The `scenario/` and `simulation/` stages are STUBs; their docs land when those
tools land.

## Decisions

- **Location:** new `docs/tools/` directory (mirrors the old layout; keeps CLI docs separate
  from architecture docs in `docs/conversion/`).
- **Fidelity:** each doc is verified against the actual migrated source (argparse args,
  layer/column lists, validation behavior) — not merely translated. Commands a reader copies
  must run.
- **run_conversion:** document the current code only — a single **scenario-agnostic base model
  folder** output with args `--dataset`/`--out`/`--dem`/`--planning-map`/`--bbox`. No
  `--scenario`/`--base` multi-scenario loop (rainfall is decoupled to the future `scenario/`
  stage; cross-link the STUB).

## Per-doc adaptation notes

**gis_template.md** — Output is a single `.gpkg`; no `.qgz`, no PyQGIS, no `--crs`/`--force`.
Single `--gpkg` arg. 10 layers (rivers, canals, sewers = LineString/`RouteShape`; lakes,
manholes, pumps, weirs, orifices, outfalls, hyetograph = Point/`Shape`). CRS hardwired
EPSG:4326. `.venv/Scripts/python.exe` runner.

**gpkg_to_csv.md** — Args `--gpkg`/`--dst`/`--no-validate`. Same dataset folder layout
(`mang_luoi_song_ho_kenh_muong/`, `thoat_nuoc/`, `thuy_van/`). Validation: ERROR tier =
`hyetograph.SeriesName` empty + structural no-outfall check (`validate_network_structure`);
WARN tier = advisory fields the converter defaults. Downstream is the **Delft3D FM base model**,
not an IberGIS GPKG. `.venv` runner, `utf-8-sig`, 8-dp WGS84 rounding.

**planning_map.md** — Tool renamed from `landuses_gpkg.py`. Subcommands limited to
`create`/`add-landuse`/`add-ground`/`add-roof`/`list`/`validate`. **No** boundary-condition /
`cat_bscenario` / `add-layer` content. Three layers: `cat_landuses`, `ground`, `roof`. Roof
schema is the Task-9 contract `--surface`/`--slope` (plus `--roughness`/`--width`/`--cellsize`),
not the Iber roof fields. Output feeds `--planning-map` in run_conversion. `.venv` runner.

**run_conversion.md** — Single base-model folder output. Args `--dataset`/`--out`/`--dem`/
`--planning-map`/`--bbox` (EPSG:4326 bbox). `.venv` runner, EPSG:32648 output CRS. Cross-link
`docs/conversion/conversion.md` (13-stage architecture) and the `scenario/` STUB for rainfall
attachment.

## Verification

Each doc's commands and tables are checked against the migrated source. No code changes; docs
only. Round-trip/CLI verification is not applicable to prose, but every documented flag/layer/
column is confirmed to exist in `src/tools/*.py`.
