# gis_template — Generate an Empty Drawing GeoPackage

## Purpose

Scaffolds an empty **drawing GeoPackage** (`.gpkg`) containing 10 typed, empty vector layers —
one per drainable 1D drainage component. The user then digitizes the 1D drainage network in
QGIS Desktop (drag-and-drop the GPKG layers) and exports the drawn features to standardized CSV
via `src/tools/gpkg_to_csv.py`.

This tool is the **entry point** of the drawing-based data-authoring workflow. It ensures each
layer has the correct geometry type and attribute schema before any drawing begins, so the
downstream CSV export and conversion always see the columns they expect.

> Unlike the old QGIS-plugin workflow, this tool writes **only the GeoPackage** — there is no
> `.qgz` project file and no PyQGIS dependency. Open the `.gpkg` directly in QGIS Desktop.

## How It Works

```
gis_template.py create --gpkg drawing.gpkg
    │
    └── creates drawing.gpkg with 10 empty layers:
          rivers       (LineString, RouteShape)   — empty, full attribute schema
          canals       (LineString, RouteShape)   — empty, full attribute schema
          sewers       (LineString, RouteShape)   — empty, full attribute schema
          lakes        (Point, Shape)             — empty, full attribute schema
          manholes     (Point, Shape)             — empty, full attribute schema
          pumps        (Point, Shape)             — empty, full attribute schema
          weirs        (Point, Shape)             — empty, full attribute schema
          orifices     (Point, Shape)             — empty, full attribute schema
          outfalls     (Point, Shape)             — empty, full attribute schema
          hyetograph   (Point, Shape)             — empty, full attribute schema
```

Key behaviors:

- The geometry column (`Shape` for Point layers, `RouteShape` for LineString layers) is the
  **layer geometry** — it is not an attribute field in the schema.
- All attribute fields match the standardized CSV schemas (the `*_COLS` lists in
  `src/tools/gpkg_to_csv.py`, documented in `docs/dataset.md`).
- The CRS for all layers is **EPSG:4326 (WGS84)** — input geometry is always authored in WGS84;
  the conversion pipeline reprojects to the projected metric CRS (default EPSG:32648).
- No features are written; every layer starts completely empty.
- If the target `.gpkg` already exists it is removed and recreated.

## Supported Layers

| Layer | Geometry | Geometry column |
|---|---|---|
| `rivers` | LineString | `RouteShape` |
| `canals` | LineString | `RouteShape` |
| `sewers` | LineString | `RouteShape` |
| `lakes` | Point | `Shape` |
| `manholes` | Point | `Shape` |
| `pumps` | Point | `Shape` |
| `weirs` | Point | `Shape` |
| `orifices` | Point | `Shape` |
| `outfalls` | Point | `Shape` |
| `hyetograph` | Point | `Shape` |

## Usage

The tool has two subcommands: `create` (scaffold the GPKG) and `autofill-name`
(post-process the manholes layer).

### `create` — scaffold the empty drawing GPKG

```bash
./.venv/Scripts/python.exe src/tools/gis_template.py create --gpkg drawing.gpkg
```

| Argument | Required | Description |
|---|---|---|
| `--gpkg` | Yes | Output path for the drawing GeoPackage (`.gpkg`) |

### `autofill` — fill a layer field for every feature

Sets `--field` on **every** feature of `--layer`, overwriting existing values.
The value is either a constant (`--value`) or taken per-row from another field
(`--value-fk`). Exactly one of the two is required.

```bash
# Name = J_{fid} for every manhole (fid = the GeoPackage feature id)
./.venv/Scripts/python.exe src/tools/gis_template.py autofill --gpkg drawing.gpkg \
    --layer manholes --field Name --value-fk fid --prefix J_

# Constant fill: every manhole gets InvElev_m = 5.0
./.venv/Scripts/python.exe src/tools/gis_template.py autofill --gpkg drawing.gpkg \
    --layer manholes --field InvElev_m --value 5.0
```

| Argument | Required | Description |
|---|---|---|
| `--gpkg` | Yes | Path to the drawing GeoPackage (`.gpkg`) |
| `--layer` | Yes | Layer to fill (must exist in the GPKG) |
| `--field` | Yes | Field to fill (must exist in the layer) |
| `--value` | One of¹ | Constant value applied to every row, **type-matched** to the field |
| `--value-fk` | One of¹ | Source field for a per-row value; the special name `fid` means the feature id |
| `--prefix` | No | Text prepended to each `--value-fk` value (string fields only) |

¹ Exactly one of `--value` / `--value-fk` is required (mutually exclusive).

**Type matching.** Whether a field is text or numeric is decided by the
standardized CSV schema (a `TEXT_FIELDS` set in the tool), because the drawing
template declares every empty attribute column as `REAL` and so cannot be relied
on for type. Consequences:

- A **numeric** field (e.g. `InvElev_m`, `Width_m`) rejects a non-numeric
  `--value` and rejects `--prefix`. Numeric literals keep their form (`5` → int,
  `5.0` → real).
- A **text** field (e.g. `Name`, `Type`) accepts any `--value`, and `--prefix`
  may be combined with `--value-fk`.
- `fid` is numeric, so `--value-fk fid` without `--prefix` writes the integer id;
  add `--prefix J_` to make it the text `J_{fid}`.

The layer is read and rewritten via pyogrio (not a raw SQL `UPDATE`), because a
GeoPackage geometry column carries RTree spatial-index triggers that call
SpatiaLite functions unavailable to a plain `sqlite3` connection; rewriting the
layer rebuilds those triggers and preserves the geometry type.

Paths can be relative to the repository root or absolute.

## Typical Workflow

```
Step 1: gis_template.py  →  Empty drawing .gpkg (10 layers, EPSG:4326)
    ↓
Step 2: Open the .gpkg in QGIS Desktop, draw drainage features into each layer
    ↓
Step 3: gpkg_to_csv.py   →  Export drawn layers to standardized CSV (ID + geometry filled)
    ↓
Step 4: Fill required fields in the CSV (elevations, dimensions, names, …)
    ↓
Step 5: run_conversion.py  →  Convert CSV dataset to a Delft3D FM base model
```

## Notes

- **Hyetograph `SeriesName` FK** — the `hyetograph` layer's `SeriesName` attribute is a foreign
  key that links a drawn rain-gauge station point to a `rainfall_*.csv` timeseries. The rainfall
  timeseries data itself (columns `SeriesName` / `Time` / `Value`) is non-geometric and authored
  separately; it is **not** a layer in this tool. Rainfall is decoupled from the base model and
  attached later at simulation time (see the `scenario/` stage).
- **2D domain is separate** — the `ground`/`roof`/`cat_landuses` 2D layers are **not** part of
  this drawing GPKG. Author those with `src/tools/planning_map.py` (see
  [planning_map.md](planning_map.md)).
- **Attribute schema** — all attribute columns are created with the names expected by
  `gpkg_to_csv.py` and downstream `conversion.py`. Do not rename or delete columns before
  exporting.
- **Environment** — run with the project `.venv` (`./.venv/Scripts/python.exe`). Requires
  `geopandas` / `shapely`; no GDAL/OGR or PyQGIS.
