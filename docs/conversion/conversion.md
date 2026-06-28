# Conversion Module Architecture

The `src/conversion/` package orchestrates the full base-model build from standardized CSVs
to a DIMR-ready Delft3D FM folder. It does not include rainfall values; those are authored
separately by the `scenario` module and injected at simulation time.

---

## Module Overview

```
src/conversion/
  conversion.py       -- Conversion orchestrator (Conversion class + run())
  config.py / .yaml   -- Roughness table, cross-section defaults, structure coeffs, NWRW defaults
  base.py             -- CSV reader, GeoJSON parser, CRS reprojection, DEM sampler, CoordRegistry
  converters/
    branches.py       -- rivers/canals/sewers -> BranchSpec objects (in-memory)
    crosssections.py  -- BranchSpec list -> crsdef.ini + crsloc.ini + friction defs
    structures.py     -- pumps/weirs/orifices -> structures.ini ; also build_roughness -> roughness.ini
    storage.py        -- manholes/lakes -> storagenodes.ini
    boundaries.py     -- outfalls -> Boundary list + ForcingModel (boundaries.bc placeholder)
    observations.py   -- manholes/pumps/outfalls -> obs.ini
    domain2d.py       -- planning_map ground polys -> 2D extent + rain_mask.pol + Meteo block
    nwrw.py           -- planning_map roof polys -> NWRW topology nodes + roof_records
    fields.py         -- DEM GeoTIFF -> inifield.ini + node-level refinement
  mesh/
    mesh1d.py         -- BranchSpec list -> Mesh1d nodes (into Network)
    mesh2d.py         -- extent polygon + config -> Mesh2d (create, optionally refine + clip)
    links.py          -- Mesh1d + Mesh2d -> Link1d2d lateral contacts (into Network)
    config.yaml       -- mesh settings
  validate.py         -- round-trip parse all produced files; cross-reference checks
```

---

## Stage Order (Conversion.run())

The `Conversion` class runs exactly 13 stages in sequence:

| Stage | Name | Function called | Output |
|-------|------|-----------------|--------|
| 1 | branches | `build_branches(rivers_csv, canals_csv, sewers_csv, registry, cfg)` | `list[BranchSpec]` in-memory |
| 2 | crosssections | `build_crosssections(branches, cfg)` | `(CrossDefModel, CrossLocModel, frictdefs)` |
| 3 | roughness | `build_roughness(frictdefs, cfg)` | `FrictionModel` |
| 4 | storage | `build_storage(manholes_csv, lakes_csv, registry, cfg)` | `StorageNodeModel` |
| 5 | structures | `build_structures(pumps_csv, weirs_csv, orifices_csv, branches, registry, cfg)` | `StructureModel` |
| 6 | boundaries | `build_boundaries(outfalls_csv, registry, cfg)` | `(list[Boundary], ForcingModel)` |
| 7 | observations | `build_observations(manholes_csv, pumps_csv, outfalls_csv, branches, registry, cfg)` | `ObservationPointModel` |
| 8 | planning map | `read_planning_map`, `build_2d_domain`, `build_rain_mask`, `build_nwrw` | extent, clips, rain_pf, meteo, rr |
| 9 | mesh1d | `build_mesh1d(network, branches, cfg)` | mutates `Network` (Mesh1d) |
| 10 | mesh2d | `build_mesh2d(network, extent, clips, cfg)` | mutates `Network` (Mesh2d) |
| 11 | links | `build_links(network, branches, cfg)` | mutates `Network` (Link1d2d) |
| 12 | fields | `build_inifield(dem_path, cfg)` + `refine_node_levels(...)` + DEM copy | `IniFieldModel` |
| 13 | write + validate | `write_model` + `write_dimr` + `validate_model` | model folder on disk |

---

## Conversion.run() Data Flow (Spec §4)

```
INPUT                          STAGE                         OUTPUT
rivers/canals/sewers.csv  -->  branches.py      -->  list[BranchSpec] (reprojected, in-memory)
                               crosssections.py -->  crsdef.ini + crsloc.ini
                                                     rivers/canals: YZ trapezoid (Width_m,
                                                       BedElev_m, SlopCoef, BankElev_m + config)
                                                     sewers: circle/rect closed (Diam_mm/Size_mm)
config roughness table    -->  roughness        -->  roughness.ini (Manning n per material)
manholes.csv, lakes.csv   -->  storage.py       -->  storagenodes.ini
pumps/weirs/orifices.csv  -->  structures.py    -->  structures.ini (Pump/Weir/Orifice)
outfalls.csv              -->  boundaries.py    -->  Boundary slots + boundaries.bc (placeholder)
manholes/pumps/outfalls   -->  observations.py  -->  obs.ini
planning_map ground polys -->  domain2d.py      -->  2D extent/clip (in-memory)
                                                     + rain_mask.pol
                                                     + [Meteo] block in forcing.ext
planning_map roof polys   -->  nwrw.py          -->  NWRW topology nodes (D-RR model)
-- MESH STAGE --
branches (in-memory)      -->  mesh/mesh1d.py   -->  Mesh1d (discretized nodes in Network)
2D extent + mesh cfg      -->  mesh/mesh2d.py   -->  Mesh2d (create, refine, clip in Network)
Mesh1d + Mesh2d           -->  mesh/links.py    -->  Link1d2d contacts (in Network -> net.nc)
DEM GeoTIFF               -->  fields.py        -->  inifield.ini (bedlevel)
                                                     + DEM refinement of storage/outfall levels
-- ASSEMBLY --
all of the above          -->  model_writer.py  -->  FlowFM_net.nc, FlowFM.mdu, forcing.ext,
                                                     dimr_config.xml
                               rr_writer.py     -->  rr/Sobek_3b.fnm + rr/3b_nod.tp (NWRW)
                               validate.py      -->  integrity check + round-trip parse
```

---

## Per-Converter API Summary

### `build_branches`
```python
def build_branches(
    rivers_csv,         # path to mang_luoi.../rivers.csv, or None
    canals_csv,         # path to mang_luoi.../canals.csv, or None
    sewers_csv,         # path to thoat_nuoc/sewers.csv, or None
    registry: CoordRegistry,
    cfg: dict,
) -> list[BranchSpec]
```
Reads three CSVs, reprojects `RouteShape` GeoJSON LineStrings from EPSG:4326 to the metric
output CRS, registers endpoints in `CoordRegistry`, and returns a flat list of `BranchSpec`
objects (sewers first, then canals, then rivers). Missing files are silently tolerated.
`BranchSpec.material` = `Material` column if non-empty, otherwise the kind string
(`'river'`, `'canal'`, `'sewer'`). Names are globally unique across all kinds.

### `build_crosssections`
```python
def build_crosssections(
    branches: list[BranchSpec],
    cfg: dict,
) -> tuple[CrossDefModel, CrossLocModel, list[FrictDef]]
```
Builds one cross-section definition per branch:
- sewer -> `CircleCrsDef` (default diameter 0.5 m) or `RectangleCrsDef` (from `Size_mm`),
  chosen by `XSType` containing `'RECT'` or `Size_mm` containing `'x'`/`'*'`.
- river/canal -> symmetric 5-point `YZCrsDef` trapezoidal profile derived from `Width_m`,
  `BedElev_m`, `BankElev_m`, `SlopCoef`; falls back to config defaults when fields are absent.

One `CrossSection` location is placed at mid-chainage of each branch. Returns a 3-tuple;
`frictdefs` is a list of `(frictionid, 'Manning', Manning_n)` tuples for stage 3.

### `build_roughness`
```python
def build_roughness(
    frictdefs: list,    # list of (frictionid, frictiontype, value) tuples from stage 2
    cfg: dict,
) -> FrictionModel
```
Deduplicates `frictdefs` by `frictionid` and builds a `FrictionModel` (`roughness.ini`).
Emits a single `f_default` global entry when `frictdefs` is empty.

### `build_storage`
```python
def build_storage(
    manholes_csv,       # path to thoat_nuoc/manholes.csv, or None
    lakes_csv,          # path to mang_luoi.../lakes.csv, or None
    registry: CoordRegistry,
    cfg: dict,
) -> StorageNodeModel
```
Converts manholes and lakes to `StorageNode` objects (`storagenodes.ini`).
Each node is registered in `CoordRegistry` (for DEM refinement in stage 12).
`nodeid` is formatted as `f"{x:.6f}_{y:.6f}"` matching how hydrolib-core names mesh1d nodes.
Lakes use area-form (`usetable='false'`); tabulated storage from `Vol_m3` is a documented gap.
`streetstoragearea` = `cfg['storage']['street_storage_factor']` x `area`.

### `build_structures`
```python
def build_structures(
    pumps_csv,          # path to thoat_nuoc/pumps.csv, or None
    weirs_csv,          # path to thoat_nuoc/weir.csv, or None
    orifices_csv,       # path to thoat_nuoc/orifices.csv, or None
    branches: list[BranchSpec],
    registry: CoordRegistry,
    cfg: dict,
) -> StructureModel
```
Converts pump, weir, and orifice CSVs to `StructureModel` (`structures.ini`).
Each structure is placed on the nearest branch by chainage (`line.project(point)`);
no maximum-distance cutoff is applied. Rows missing geometry or required fields are skipped.
Culvert conversion is intentionally omitted (gap D13).

### `build_boundaries`
```python
def build_boundaries(
    outfalls_csv,       # path to thoat_nuoc/outfalls.csv, or None
    registry: CoordRegistry,
    cfg: dict,
) -> tuple[list[Boundary], ForcingModel]
```
Converts outfalls to `Boundary` objects with `quantity='waterlevelbnd'` and a placeholder
`Constant` value (FixedStage -> Elev_m -> 0.0). The shared `ForcingModel` is given
`filepath='boundaries.bc'`. All outfall types (FREE/NORMAL/TIDAL/FIXED) map to
`waterlevelbnd`; tidal/timeseries refinement is a documented gap.

### `build_observations`
```python
def build_observations(
    manholes_csv,
    pumps_csv,
    outfalls_csv,
    branches: list[BranchSpec],
    registry: CoordRegistry,
    cfg: dict,
) -> ObservationPointModel
```
Produces one `ObservationPoint` per valid source location. Points are placed on the nearest
branch (branchid + chainage) when possible; fall back to (x, y) coordinates otherwise.
Names are globally unique with numeric suffix on collision.

### `read_planning_map`
```python
def read_planning_map(gpkg_path: str) -> tuple[GeoDataFrame, GeoDataFrame, dict]
```
Reads the planning-map GPKG produced by `planning_map.py`. Returns:
`(ground_gdf, roof_gdf, landuse_catalog)`. Each layer is wrapped in a try/except so
a missing layer does not block the others. `landuse_catalog` maps `idval -> manning`.

### `build_2d_domain`
```python
def build_2d_domain(ground_gdf: GeoDataFrame, cfg: dict) -> tuple
```
Returns `(extent_polygon, clip_polygons)` where `extent_polygon` is the unary_union of
all reprojected ground geometries and `clip_polygons` is the list of individual polygons.
Returns `(None, [])` when ground_gdf is empty.

### `build_rain_mask`
```python
def build_rain_mask(ground_gdf: GeoDataFrame, cfg: dict) -> tuple[PolyFile, Meteo]
```
Builds a `PolyFile` (named `rain_mask.pol`) from ground polygon exterior rings
and a `Meteo` block with `targetmaskfile=polyfile`, `quantity='rainfall'`,
`forcingfiletype='bcAscii'`, and an empty `ForcingModel(filepath='rainfall.bc')`.
Returns `(None, None)` when ground_gdf is empty.

### `build_nwrw`
```python
def build_nwrw(roof_gdf: GeoDataFrame, cfg: dict) -> tuple[RainfallRunoffModel, list[dict]]
```
Converts roof polygons to NWRW topology nodes (`rrtop.Node` with `modelnodetype=2`,
`netternodetype=44`). Returns `(RainfallRunoffModel, roof_records)` where `roof_records`
is a list of dicts with `id`, `x`, `y`, `area_m2`, `surface_type`, `slope_type`.
Per-row `surface`/`slope` columns override the config defaults
(`cfg['nwrw']['roof_surface_type']='closed_paved'`, `cfg['nwrw']['roof_slope_type']='sloped'`).

### `build_inifield`
```python
def build_inifield(dem_path, cfg) -> IniFieldModel | None
```
Wraps a GeoTIFF DEM in an `IniFieldModel` (`inifield.ini`) with a single `bedlevel`
`InitialField` using `datafiletype='GeoTIFF'`, `interpolationmethod='averaging'`,
`averagingtype='mean'`. Returns `None` when `dem_path` is absent or the file does not exist.
Stores only the DEM basename; the orchestrator copies the DEM file into `out_dir`.

### `refine_node_levels`
```python
def refine_node_levels(
    dem_path,
    registry: CoordRegistry,
    storage_model: StorageNodeModel,
    outfall_boundaries: list[Boundary],
    forcing_model: ForcingModel,
    cfg,
) -> int
```
DEM-refines storage node and outfall elevations by sampling the GeoTIFF at each node's
WGS84 lon/lat (stored in `CoordRegistry`). Mirrors SWMM `refine_elevations` exactly:
- Storage nodes: `streetlevel = DEM_surface`; `bedlevel = DEM_surface - depth` where
  `depth = prior (streetlevel - bedlevel)` if > 0, else `0.0` (depth-zero parity with SWMM).
- Outfalls: updates the matching `Constant.datablock` in `forcing_model` to `DEM_surface`.
Returns the count of nodes refined.

### `write_model`
```python
def write_model(
    out_dir,
    network: Network,
    crossdef: CrossDefModel,
    crossloc: CrossLocModel,
    friction: FrictionModel,
    storage: StorageNodeModel,
    structures: StructureModel,
    obs: ObservationPointModel,
    ext: ExtModel,
    inifield: IniFieldModel | None,
    gcfg: dict,
) -> FMModel
```
Wires all converter outputs into an `FMModel`, sets `.filepath` on every sub-model before
calling `fm.save(recurse=True)`. Time settings come from `gcfg['model']` (refdate, tstart,
tstop, dtuser, bedlevuni, waterlevini, allowbndatbifurcation). The ext/meteo
`targetmaskfile` round-trip bug in hydrolib-core 1.0.1 only affects re-parsing (not saving),
so saving is safe.

### `write_dimr`
```python
def write_dimr(out_dir, fm: FMModel, rr_model=None, gcfg=None) -> None
```
Writes `dimr_config.xml`. FM-only mode: one `FMComponent` + `Start` control. RR-coupled
mode: `FMComponent` + `RRComponent` + `Coupler(rr2flow)` + `Parallel/StartGroup` control.
Calls `write_rr(out_dir, rr_model)` first so RR files exist before DIMR is serialized.

### `write_rr`
```python
def write_rr(out_dir, rr_model: RainfallRunoffModel) -> str | None
```
Saves the `RainfallRunoffModel` and its `NodeFile` into `out_dir/rr/`. Returns
`'Sobek_3b.fnm'` (the DIMR `inputFile`) on success, or `None` on failure (triggers FM-only
fallback in `write_dimr`). The first-pass RR model contains only topology nodes; rainfall
`.bui` wiring and DWA tables are filled by the scenario module.

### `validate_model`
```python
def validate_model(out_dir) -> list[str]
```
Round-trip validates the produced model folder. Checks required files are present, then
tries `FMModel(filepath=...)`. If that fails AND `rain_mask.pol` is present (i.e. the known
hydrolib-core 1.0.1 meteo `targetmaskfile` round-trip bug), falls back to piece-wise
parsing of each sub-file. Also runs cross-reference checks: crsloc `definitionid` in crsdef,
crsloc `branchid` in mesh1d branches, crsdef `frictionid` in roughness. Returns a list of
problem strings (empty == OK).

---

## Key Contracts

### CRS Source Rule
All converters resolve CRS via `cfg.get('crs') or src.delft3dfm.config.load()['crs']`.
The orchestrator passes the conversion config unchanged; no CRS injection. This ensures every
stage reprojects identically and the coordinate-string `nodeid` linkage holds.

### Coordinate-String nodeid
Storage nodes and boundary nodes use `nodeid = f"{x:.6f}_{y:.6f}"` (projected metric
coordinates, 6 decimal places). This matches the format hydrolib-core uses internally for
mesh1d node names, guaranteeing storage nodes attached at branch endpoints link to real
mesh1d nodes.

### Meteo targetmaskfile Round-Trip Limitation
Saving a `forcing.ext` with a meteo `targetmaskfile` (PolyFile) works in hydrolib-core 1.0.1
but re-loading it via `ExtModel(filepath=...)` or `FMModel(filepath=...)` fails (`targetmaskfile`
is re-parsed as a plain string and raises). `validate_model` detects this specific failure by
checking for `rain_mask.pol` presence and the exception message, and falls back to piece-wise
validation that validates the `.pol` file separately. This is a tooling gap in hydrolib-core.

### DEM Copy into out_dir
`build_inifield` stores only the DEM basename in `datafile`. The orchestrator (stage 12)
copies the DEM file with `shutil.copy` into `out_dir` so the basename reference resolves when
Delft3D FM reads `inifield.ini`.

### Scenario-Agnostic Forcing
`forcing.ext` carries:
- `boundary` list: `Boundary` objects with placeholder constant water-level values.
- `meteo` block: `Meteo` with `targetmaskfile=rain_mask.pol` and an empty `rainfall.bc` slot.

Rainfall values are NOT filled during conversion. The scenario module authors `.bui`/`.bc`
content and injects it at run time, feeding both the 2D `[Meteo]` ground rain and the D-RR
NWRW roof catchments.

---

## Output Folder Contents

A complete base-model run produces the following files:

| File | Description |
|------|-------------|
| `FlowFM.mdu` | D-Flow FM master settings file |
| `FlowFM_net.nc` | Network file (Mesh1d + Mesh2d + Link1d2d contacts) |
| `crsdef.ini` | Cross-section shape definitions |
| `crsloc.ini` | Cross-section locations (one per branch, at mid-chainage) |
| `roughness.ini` | Global friction (Manning n per material) |
| `structures.ini` | Hydraulic structures (Pump, Weir, Orifice) |
| `storagenodes.ini` | Storage nodes (manholes + lakes) |
| `obs.ini` | Observation points |
| `forcing.ext` | External forcing (boundary slots + meteo block) |
| `boundaries.bc` | Boundary forcing placeholder (constant water levels) |
| `rain_mask.pol` | Ground polygon mask for spatially distributed rainfall |
| `inifield.ini` | Initial/parameter field specification (DEM bed level) |
| `<dem>.tif` | DEM GeoTIFF copied from the source path |
| `dimr_config.xml` | DIMR configuration (FM-only or RR-coupled) |
| `rr/Sobek_3b.fnm` | D-RR control file (when NWRW roof polygons are present) |
| `rr/3b_nod.tp` | D-RR topology node file (NWRW nodes) |

Files `storagenodes.ini`, `inifield.ini`, `rain_mask.pol`, and the `rr/` directory are
only written when the relevant inputs (manholes/lakes CSV, DEM, planning_map) are provided.
