# Delft3D FM Conversion Submodule + Repo Skeleton — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the repo skeleton and a fully working conversion submodule that turns a standardized CSV drainage dataset into a runnable, scenario-agnostic Delft3D FM 1D2D base-model folder (net.nc + `.ini`/`.ext`/`.pol` + D-RR/NWRW + `FlowFM.mdu` + `dimr_config.xml`).

**Architecture:** A `Conversion` orchestrator runs ordered stages — declare 1D branches / structures / storage / 2D domain → generate meshes (mesh1d, mesh2d, 1d2d links) → DEM fields → assemble net.nc + mdu + dimr. hydrolib-core is the file API; meshkernel does the meshing; geopandas/shapely/rasterio do GIS I/O. Rainfall is decoupled: the base model carries empty forcing slots (`[Meteo]` mask + boundary `.bc` refs + NWRW nodes) that a later scenario/simulation step fills.

**Tech Stack:** Python 3 (repo `.venv`), hydrolib-core 1.0.1, meshkernel, pyproj, numpy, geopandas, shapely, rasterio, PyYAML.

## Global Constraints

- **Environment:** repo `.venv` only. Activate `\.venv\Scripts\activate` (Windows). Run scripts as `.\.venv\Scripts\python.exe <script>`.
- **No GDAL/OGR:** `osgeo` is NOT installed. Use geopandas/shapely/rasterio for all GIS I/O. Do NOT `import osgeo`.
- **`dfm_tools` is optional and NOT installed.** Do not import it. Use hydrolib-core directly.
- **No test files / no pytest.** Verification is by CLI runs + hydrolib-core round-trip parse (a `validate.py` that re-reads the output). This is a deliberate project convention.
- **Do NOT commit.** Tasks have NO commit step. The executor must never run `git add`/`git commit`. The user handles all version control manually after reviewing the work.
- **CRS:** input CSVs are EPSG:4326 (WGS84); reproject to a projected metric CRS (config `crs.out`, default EPSG:32648 / UTM 48N) for all geometry, meshes, and Delft3D files.
- **Source of truth:** `docs/Delft3D_FM_1D2D.md` (component spec). Reference output shape: `urban_1d2d_model/` + `model.py`.
- **Standardized CSV schema** is identical to the SWMM repo; gaps are synthesized from config defaults (see Task 11 gap_analysis).
- **Vietnamese dataset folder names** are kept: `thoat_nuoc/`, `mang_luoi_song_ho_kenh_muong/`, `thuy_van/`.

---

## Task 0: Context Retrieval (run FIRST in a fresh chat)

This plan is executed in a new chat with zero prior context. Before any code,
read these to load the design and the exact APIs.

**Files (read-only):**
- Read: `docs/superpowers/specs/2026-06-25-delft3d-conversion-submodule-design.md` (the approved design — the why)
- Read: `docs/superpowers/plans/2026-06-25-delft3d-conversion-submodule.md` (this plan — the how)
- Read: `docs/Delft3D_FM_1D2D.md` (component spec — attribute tables, file layouts)
- Read: `model.py` (working hydrolib-core build — copy its import paths & class usage)
- Read: `urban_1d2d_model/crsdef.ini`, `urban_1d2d_model/structures.ini`, `urban_1d2d_model/dimr_config.xml`, `urban_1d2d_model/FlowFM.mdu` (golden output shapes)
- Read (cross-repo, for parity & schema): `G:\workspace\github\swmm\docs\conversion\standardization_submodule.md` (CSV schema to migrate), `G:\workspace\github\swmm\src\conversion\postprocess.py` (DEM `refine_elevations` to replicate — D12), `G:\workspace\github\swmm\src\tools\gis_template.py` + `gpkg_to_csv.py` + `landuses_gpkg.py` (tools to port off GDAL)

- [ ] **Step 1: Read all spec/plan/reference files above.**

- [ ] **Step 2: Verify the environment and pin the exact hydrolib-core APIs.**

Run:
```bash
cd G:/workspace/github/delft3d && ./.venv/Scripts/python.exe -c "
import hydrolib.core, meshkernel, geopandas, shapely, rasterio, pyproj, yaml, numpy
print('hydrolib-core', hydrolib.core.__version__)
from hydrolib.core.dflowfm.net.models import Branch, Network, NetworkModel
from hydrolib.core.dflowfm.crosssection.models import CrossDefModel, CrossLocModel, CircleCrsDef, RectangleCrsDef, YZCrsDef, ZWCrsDef, CrossSection
from hydrolib.core.dflowfm.friction.models import FrictionModel, FrictGlobal, FrictBranch
from hydrolib.core.dflowfm.structure.models import StructureModel, Pump, Weir, Orifice
from hydrolib.core.dflowfm.storagenode.models import StorageNodeModel, StorageNode
from hydrolib.core.dflowfm.obs.models import ObservationPointModel, ObservationPoint
from hydrolib.core.dflowfm.ext.models import ExtModel, Boundary, Lateral, Meteo
from hydrolib.core.dflowfm.bc.models import ForcingModel, Constant, TimeSeries, QuantityUnitPair
from hydrolib.core.dflowfm.inifield.models import IniFieldModel, InitialField, ParameterField
from hydrolib.core.dflowfm.polyfile.models import PolyFile, PolyObject
from hydrolib.core.dflowfm.mdu.models import FMModel
from hydrolib.core.dimr.models import DIMR, FMComponent, RRComponent, Start, StartGroup, Coupler
from hydrolib.core.rr.models import RainfallRunoffModel
print('ALL IMPORTS OK')
"
```
Expected: prints `hydrolib-core 1.0.1` and `ALL IMPORTS OK`.

If any import path differs in this hydrolib-core version, note the corrected
path and use it consistently for the rest of the plan. (StorageNode, RRComponent,
Coupler are the most likely to differ — confirm them here before Task 6/9/10.)

- [ ] **Step 3: Confirm the NWRW node attribute names** (needed for Task 9).

Run:
```bash
cd G:/workspace/github/delft3d && ./.venv/Scripts/python.exe -c "
import hydrolib.core.rr.topology.models as t
print('NODE:', list(t.Node.model_fields.keys()))
from hydrolib.core.rr.models import RainfallRunoffModel
print('RR:', list(RainfallRunoffModel.model_fields.keys()))
"
```
Expected: prints the `Node` and `RainfallRunoffModel` field lists. Record the
NWRW catchment node type / area / surface-type field names for Task 9. If the
installed hydrolib-core exposes NWRW only via raw RR node records, Task 9's
note covers the fallback.

No commit for this task.

---

## Task 1: Repo skeleton + CLAUDE.md

**Files:**
- Create: `src/__init__.py`, `src/conversion/__init__.py`, `src/conversion/converters/__init__.py`, `src/conversion/mesh/__init__.py`, `src/delft3dfm/__init__.py`, `src/tools/__init__.py`
- Create: `src/scenario/README.md`, `src/simulation/README.md`
- Create: `CLAUDE.md`
- Create: `.gitignore` (if absent: ignore `.venv/`, `__pycache__/`, `*.cache`, `DFM_OUTPUT_*/`, `out/`)

**Interfaces:**
- Produces: the package tree all later tasks import under (`src.conversion.*`, `src.delft3dfm.*`).

- [ ] **Step 1: Create the package directories and empty `__init__.py` files** listed above (each `__init__.py` is an empty file).

- [ ] **Step 2: Write `src/scenario/README.md`** — one paragraph: "STUB. Authors rainfall scenarios as `.bui` hyetographs / boundary `.bc` files, decoupled from the model build. A scenario is combined into a base model at simulation time. Not implemented yet."

- [ ] **Step 3: Write `src/simulation/README.md`** — one paragraph: "STUB. Combines a conversion base model with a chosen rainfall scenario (fills the `[Meteo]` `.bui` slot, boundary `.bc` values, and NWRW rain), then invokes the Delft3D/DIMR binary on the folder. Not implemented yet."

- [ ] **Step 4: Write `CLAUDE.md`** with these sections (prose, accurate to this plan):
  - Purpose & the 4-stage pipeline diagram (drawing → standardized CSV → conversion[incl. mesh] → base model → +scenario → simulation → result).
  - Full directory tree (copy from spec §3).
  - Conventions: `.venv` only (`\.venv\Scripts\python.exe`); hydrolib-core is the file API; geopandas/shapely/rasterio for GIS (NO GDAL); CRS in=4326 out=projected metric; conversion emits a scenario-agnostic base model; mesh generation is a STAGE inside conversion; no test files (verify via CLI + round-trip); commits need user approval.
  - Environment setup + the Task 0 import-check command.
  - Reference files table (spec, component spec, model.py, urban_1d2d_model).

- [ ] **Step 5: Verify the tree imports.**

Run:
```bash
cd G:/workspace/github/delft3d && ./.venv/Scripts/python.exe -c "import src.conversion, src.delft3dfm, src.conversion.converters, src.conversion.mesh; print('skeleton OK')"
```
Expected: `skeleton OK`.


---

## Task 2: Config loaders + config files

**Files:**
- Create: `src/delft3dfm/config.yaml`, `src/delft3dfm/config.py`
- Create: `src/conversion/config.yaml`, `src/conversion/config.py`
- Create: `src/conversion/mesh/config.yaml`

**Interfaces:**
- Produces: `src.delft3dfm.config.load() -> dict` (global model opts) and `src.conversion.config.load() -> dict` (conversion + mesh defaults, with mesh config merged under key `mesh`).

- [ ] **Step 1: Write `src/delft3dfm/config.yaml`:**
```yaml
crs:
  in: 4326          # WGS84 input CSVs
  out: 32648        # UTM 48N (projected metric) for Delft3D files
model:
  refdate: 20200101
  tstart: 0.0
  tstop: 3600.0
  dtuser: 60.0
  bedlevuni: 0.0
  waterlevini: 0.05
  allowbndatbifurcation: 1
output:
  hisinterval: 60.0
  mapinterval: 300.0
```

- [ ] **Step 2: Write `src/conversion/config.yaml`:**
```yaml
roughness:           # Manning n by material/class
  BTCT: 0.013
  concrete: 0.013
  PVC: 0.011
  HDPE: 0.012
default_roughness: 0.013
canal: { roughness: 0.025, default_width: 1.0, default_depth: 0.5, side_slope: 1.0 }
river: { roughness: 0.035, default_width: 5.0, default_depth: 2.0, side_slope: 1.0 }
crosssection:
  yz_points: 5       # points per derived trapezoidal YZ profile
storage:
  street_storage_factor: 1.0   # streetStorageArea = factor * area
  storage_type: reservoir
  entrance_loss: 0.5
  exit_loss: 1.0
structure:
  weir_corrcoeff: 1.0
  orifice_corrcoeff: 0.63
coupling:
  default_type: lateral        # branch->2D
  sewer_type: vertical         # street-inlet (gully) coupling
nwrw:
  roof_surface_type: closed_paved
  roof_slope_type: sloped
```

- [ ] **Step 3: Write `src/conversion/mesh/config.yaml`:**
```yaml
edge_length_1d: 100.0    # m along branch centerlines
grid_2d:
  type: rectilinear      # rectilinear | triangular
  dx: 100.0
  dy: 100.0
refine:
  enabled: false
  levels: 1
clip:
  to_ground_polygons: true
link:
  type: lateral          # 1d2d coupling default
```

- [ ] **Step 4: Write `src/delft3dfm/config.py`** — `load()` reads `config.yaml` next to it with `yaml.safe_load`, returns dict. Cache in a module global.

```python
import os, yaml
_CFG = None
def load():
    global _CFG
    if _CFG is None:
        p = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(p, "r", encoding="utf-8") as f:
            _CFG = yaml.safe_load(f)
    return _CFG
```

- [ ] **Step 5: Write `src/conversion/config.py`** — same pattern; additionally load `mesh/config.yaml` and attach as `cfg["mesh"]`.

```python
import os, yaml
_CFG = None
def load():
    global _CFG
    if _CFG is None:
        here = os.path.dirname(__file__)
        with open(os.path.join(here, "config.yaml"), "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        with open(os.path.join(here, "mesh", "config.yaml"), "r", encoding="utf-8") as f:
            cfg["mesh"] = yaml.safe_load(f)
        _CFG = cfg
    return _CFG
```

- [ ] **Step 6: Verify.**
```bash
cd G:/workspace/github/delft3d && ./.venv/Scripts/python.exe -c "
from src.delft3dfm import config as gc
from src.conversion import config as cc
print('out crs:', gc.load()['crs']['out'])
print('mesh edge:', cc.load()['mesh']['edge_length_1d'])
print('sewer coupling:', cc.load()['coupling']['sewer_type'])
"
```
Expected: `out crs: 32648`, `mesh edge: 100.0`, `sewer coupling: vertical`.


---

## Task 3: base.py — CSV/GeoJSON/CRS/DEM/registry utilities

**Files:**
- Create: `src/conversion/base.py`

**Interfaces:**
- Produces:
  - `read_csv_rows(path) -> list[dict]` (utf-8, tolerant of empty file → `[]`)
  - `parse_geojson(s) -> shapely.geometry` (Point/LineString/Polygon from a GeoJSON string)
  - `reproject_geom(geom, src_epsg, dst_epsg) -> shapely.geometry` (pyproj Transformer, cached)
  - `class CoordRegistry` with `get_or_create(x, y, name, **attrs) -> str` (snap within `tol` m, returns node id) and `.nodes -> dict[id]->{x,y,lon,lat,attrs}` and `.wgs84_of(name) -> (lon,lat)|None`
  - `class DEMSampler(path)` with `.sample(lon, lat) -> float|None` (rasterio; reprojects sample point to raster CRS; returns None outside/ nodata)

- [ ] **Step 1: Implement `read_csv_rows`** — `csv.DictReader`, utf-8-sig; returns `[]` if file missing/empty.

- [ ] **Step 2: Implement `parse_geojson`** — `json.loads` then `shapely.geometry.shape(...)`. Raise `ValueError` on empty/malformed with the offending snippet.

- [ ] **Step 3: Implement `reproject_geom`** — `pyproj.Transformer.from_crs(f"EPSG:{src}", f"EPSG:{dst}", always_xy=True)` cached per (src,dst); apply via `shapely.ops.transform`.

- [ ] **Step 4: Implement `CoordRegistry`** — store nodes keyed by an auto id (`node_1`...). `get_or_create` snaps to an existing node if within `tol` (default from a constructor arg, projected metres) using a simple linear scan or a rounded-grid dict; records both projected (x,y) and original (lon,lat). Keep both so DEM sampling (Task 8) can use WGS84.

- [ ] **Step 5: Implement `DEMSampler`** — open with rasterio; build a Transformer from EPSG:4326 to the raster CRS; `sample()` returns the band value at the point or None for nodata/out-of-bounds. If the file can't be opened, set an internal flag so callers can skip gracefully (mirror SWMM `dem._band is None`).

- [ ] **Step 6: Verify with an inline smoke test (no test file — run a one-liner).**
```bash
cd G:/workspace/github/delft3d && ./.venv/Scripts/python.exe -c "
from src.conversion.base import parse_geojson, reproject_geom, CoordRegistry
g = parse_geojson('{\"type\":\"Point\",\"coordinates\":[105.8,21.0]}')
p = reproject_geom(g, 4326, 32648)
print('reprojected x>100000:', p.x > 100000)
r = CoordRegistry(tol=10.0)
a = r.get_or_create(p.x, p.y, 'MH1', lon=105.8, lat=21.0)
b = r.get_or_create(p.x+2, p.y+2, 'MH1b', lon=105.8, lat=21.0)  # within 10 m -> same node
print('snapped same node:', a == b)
print('wgs84:', r.wgs84_of('MH1'))
"
```
Expected: `reprojected x>100000: True`, `snapped same node: True`, a `wgs84:` tuple near (105.8, 21.0).


---

## Task 4: branches.py — 1D branch centerlines

**Files:**
- Create: `src/conversion/converters/branches.py`

**Interfaces:**
- Consumes: `base.read_csv_rows`, `base.parse_geojson`, `base.reproject_geom`, `base.CoordRegistry`; `src.conversion.config.load`.
- Produces: `build_branches(rivers_csv, canals_csv, sewers_csv, registry, cfg) -> list[BranchSpec]` where
  `BranchSpec = dataclass(name:str, geometry:np.ndarray(Nx2), kind:str in {'river','canal','sewer'}, material:str, from_node:str, to_node:str, attrs:dict)`.
  Geometry is reprojected metric coordinates from `RouteShape` GeoJSON LineString. Registers both endpoints in `registry`.

- [ ] **Step 1: Implement `BranchSpec` dataclass and `_rows_to_branches(rows, kind, geom_col, registry, cfg)`** — parse `RouteShape` LineString → reproject → `np.array` of (x,y); register endpoints via `registry.get_or_create`; `name` from `Name` (fallback `f"{kind}_{ID}"`); `material` from `Material` (fallback per-kind config). Skip rows with missing/short geometry, printing a count.

- [ ] **Step 2: Implement `build_branches`** — read each CSV (sewers, then canals, then rivers — sewers first so sewer junctions exist before open channels, mirroring the SWMM ordering), concatenate, return the list. Print per-kind counts.

- [ ] **Step 3: Verify** with a tiny inline dataset.
```bash
cd G:/workspace/github/delft3d && ./.venv/Scripts/python.exe -c "
import csv, tempfile, os
from src.conversion.base import CoordRegistry
from src.conversion.config import load
from src.conversion.converters.branches import build_branches
d = tempfile.mkdtemp()
p = os.path.join(d,'rivers.csv')
with open(p,'w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['ID','Name','Material','FromNode','ToNode','RouteShape'])
    w.writerow(['1','R1','concrete','A','B','{\"type\":\"LineString\",\"coordinates\":[[105.8,21.0],[105.81,21.0]]}'])
reg=CoordRegistry(tol=5.0)
bs=build_branches(None,None,p,reg,load())  # pass rivers path in sewers slot is fine; use kind via file
print('n branches:', len(bs), 'pts:', bs[0].geometry.shape if bs else None)
"
```
Expected: `n branches: 1 pts: (2, 2)` (exact wiring of which arg holds which CSV may differ — adjust the call to your `build_branches` signature; the point is one branch with a 2×2 geometry array).


---

## Task 5: crosssections.py — crsdef.ini + crsloc.ini

**Files:**
- Create: `src/conversion/converters/crosssections.py`

**Interfaces:**
- Consumes: `BranchSpec` list, the per-branch CSV attrs, `cfg`.
- Produces: `build_crosssections(branches, rows_by_kind, cfg) -> (CrossDefModel, CrossLocModel, frictdefs)` where `frictdefs` is a list of `(frictionid, frictiontype, frictionvalue)` discovered, consumed by Task 7.
  - sewers → `CircleCrsDef`(diameter=`Diam_mm`/1000) or `RectangleCrsDef`(width,height,`closed='yes'`) when `Size_mm`/XSType is rectangular.
  - rivers/canals → `YZCrsDef` trapezoid derived from width + bed + side slope + depth (D-derive). Place one `CrossSection` per branch at mid-chainage referencing the def.

- [ ] **Step 1: Implement `_circle_def(branch, row, cfg)`** → `CircleCrsDef(id=f"cd_{name}", diameter=mm/1000, frictionid=f"f_{material}")`.

- [ ] **Step 2: Implement `_rect_def(branch, row, cfg)`** → `RectangleCrsDef(id=..., width=, height=, closed='yes', frictionid=...)`. Parse `Size_mm` ("WxH") when present.

- [ ] **Step 3: Implement `_yz_trapezoid(branch, row, cfg)`** → build symmetric trapezoid `yCoordinates`/`zCoordinates` from bottom width (`Width_m` or config default), depth (`BankElev_m`-`BedElev_m` or config), side slope (`SlopCoef` or config); `zCoordinates` referenced to `BedElev_m` (or 0). Return `YZCrsDef(id=..., yzcount=, ycoordinates=, zcoordinates=, frictionid=...)`.

- [ ] **Step 4: Implement `build_crosssections`** — iterate branches by kind, build defs (dedup by id), build one `CrossSection(id=f"cs_{name}", branchid=name, chainage=<half length>, definitionid=<def id>)` per branch. Collect friction ids → `frictdefs` using the roughness table. Return `CrossDefModel(definition=[...])`, `CrossLocModel(crosssection=[...])`, `frictdefs`.

- [ ] **Step 5: Verify** — build defs for one sewer + one river branch, save, re-read with hydrolib-core, assert one circle + one yz def.
```bash
cd G:/workspace/github/delft3d && ./.venv/Scripts/python.exe -c "
import numpy as np, tempfile, os
from src.conversion.config import load
from src.conversion.converters.branches import BranchSpec
from src.conversion.converters.crosssections import build_crosssections
cfg = load()
sewer = BranchSpec(name='S1', geometry=np.array([[0.,0.],[100.,0.]]), kind='sewer',
                   material='concrete', from_node='n1', to_node='n2',
                   attrs={'Diam_mm':'800','XSType':'CIRCULAR'})
river = BranchSpec(name='R1', geometry=np.array([[0.,0.],[200.,0.]]), kind='river',
                   material='concrete', from_node='n3', to_node='n4',
                   attrs={'Width_m':'5','BedElev_m':'0','BankElev_m':'2','SlopCoef':'1'})
rows_by_kind = {'sewer':{'S1':sewer.attrs}, 'river':{'R1':river.attrs}, 'canal':{}}
crossdef, crossloc, frictdefs = build_crosssections([sewer, river], rows_by_kind, cfg)
types = sorted(d.type for d in crossdef.definition)
print('types:', types, 'locs:', len(crossloc.crosssection), 'fricts:', len(frictdefs))
assert 'circle' in types and 'yz' in types, types
assert len(crossloc.crosssection) == 2
print('CROSSSECTIONS OK')
"
```
Expected: prints `types: ['circle', 'yz'] ...` then `CROSSSECTIONS OK`. (If your `BranchSpec`/`build_crosssections` signatures differ from Task 4/5 as written, reconcile them — these are the canonical signatures the plan commits to.)


---

## Task 6: storage.py — storagenodes.ini

**Files:**
- Create: `src/conversion/converters/storage.py`

**Interfaces:**
- Consumes: `manholes.csv`, `lakes.csv`, `registry`, `cfg`.
- Produces: `build_storage(manholes_csv, lakes_csv, registry, cfg) -> StorageNodeModel`. Each manhole → `StorageNode(id, name, nodeid=<registry node at its coord>, usetable=false, bedlevel=InvElev_m, streetlevel=RimElev_m, area=Area_m2, streetstoragearea=factor*area, storagetype=cfg.storage.storage_type)`. Lakes → tabulated/`usetable` storage from `BedElev_m`/`Area_ha`/`Vol_m3` (simple area form acceptable for first pass; document in gap_analysis).

- [ ] **Step 1: Implement manhole → `StorageNode`** mapping per the interface; register/lookup node id from `registry` by coordinate.
- [ ] **Step 2: Implement lake → `StorageNode`** (area form: `area = Area_ha*1e4`, `bedlevel = BedElev_m`, `streetlevel = CrestElv` or bed+depth).
- [ ] **Step 3: Implement `build_storage`** returning the populated `StorageNodeModel`.
- [ ] **Step 4: Verify** — one manhole row → save → re-read → assert `bedlevel`/`streetlevel`/`area` survive round-trip.

---

## Task 7: structures.py + roughness + boundaries + observations

**Files:**
- Create: `src/conversion/converters/structures.py`
- Create: `src/conversion/converters/boundaries.py`
- Create: `src/conversion/converters/observations.py`

**Interfaces:**
- Produces:
  - `build_structures(pumps_csv, weirs_csv, orifices_csv, registry, cfg) -> StructureModel` (Pump from `Cap_m3s`→capacity, start/stop from `In/OutElev_m`; Weir from `CrestElv`→crestlevel,`Width_m`→crestwidth,corrcoeff=cfg; Orifice from `InvElev_m`→crestlevel,`Height_m`→gateloweredgelevel,`Form`→shape). Structures placed by `branchid`+`chainage` from registry/source branch. Culvert OUT (D13).
  - `build_roughness(frictdefs, cfg) -> FrictionModel` (global Manning per friction id; `default_roughness` fallback).
  - `build_boundaries(outfalls_csv, registry, cfg) -> (ExtModel pieces: list[Boundary], ForcingModel slots)` — each outfall → `Boundary(quantity='waterlevelbnd', nodeid=<node>, forcingfile=<.bc slot>)` with an empty/constant placeholder value (filled by scenario later).
  - `build_observations(manholes_csv, pumps_csv, outfalls_csv, registry) -> ObservationPointModel`.

- [ ] **Step 1: Implement `build_roughness`** — one `FrictGlobal` per unique friction id from `frictdefs`; type Manning.
- [ ] **Step 2: Implement `build_structures`** (Pump, Weir, Orifice). Parse `Cap_m3s` string → float (strip units). Skip rows missing required levels, printing counts.
- [ ] **Step 3: Implement `build_boundaries`** — Boundary + a `.bc` `Constant`/`TimeSeries` *slot* (value 0.0 placeholder) so the model parses; mark in a comment that scenario fills it.
- [ ] **Step 4: Implement `build_observations`** — ObservationPoint at each manhole/pump/outfall (`locationtype='1d'`, by branchid+chainage or x/y).
- [ ] **Step 5: Verify** — build each, save, re-read; assert a Pump+Weir+Orifice present and one global friction.

---

## Task 8: fields.py — DEM bedlevel + node DEM refinement (D12 parity)

**Files:**
- Create: `src/conversion/converters/fields.py`

**Interfaces:**
- Consumes: `base.DEMSampler`, `registry`, the `StorageNodeModel` (manholes/lakes) and `Boundary` outfalls, `cfg`.
- Produces:
  - `build_inifield(dem_path, cfg) -> IniFieldModel|None` — `InitialField(quantity='bedlevel', datafile=<dem>, datafiletype='GeoTIFF', interpolationmethod='averaging', averagingtype='mean')`. Returns None if no DEM.
  - `refine_node_levels(dem_path, registry, storage_model, outfall_boundaries, cfg) -> int` — **replicates SWMM `refine_elevations` exactly (D12):** for each storage node, sample DEM at the node's WGS84 lon/lat; set `streetlevel = DEM_surface`, `bedlevel = DEM_surface - depth` (depth = streetlevel-bedlevel prior, or `max_depth`); for outfalls set invert/level `= DEM_surface`. Skip nodes not in registry or with nodata. Return count refined. Print `table: refined/total` like the SWMM version.

- [ ] **Step 1: Implement `build_inifield`.**
- [ ] **Step 2: Implement `refine_node_levels`** mirroring `G:\workspace\github\swmm\src\conversion\postprocess.py::refine_elevations` (surface=DEM, invert=DEM-depth for storage; outfall=DEM). Read that file again to match the rounding (`round(...,3)`) and the skip-on-None behavior.
- [ ] **Step 3: Verify** — with a small GeoTIFF (or skip-path): assert returns 0 and prints "no DEM" when `dem_path=None`; with a DEM, assert at least one node refined and `streetlevel - bedlevel == depth`.

---

## Task 9: domain2d.py + nwrw.py — ground rain mask + roof NWRW (D10/D11)

**Files:**
- Create: `src/conversion/converters/domain2d.py`
- Create: `src/conversion/converters/nwrw.py`

**Interfaces:**
- Produces:
  - `read_planning_map(gpkg_path) -> (ground_gdf, roof_gdf, landuse_catalog)` via geopandas (`layer=` per layer). Returns empty frames if file/layers absent.
  - `build_2d_domain(ground_gdf, cfg) -> (extent_polygon_shapely, clip_polygons)` — reproject ground polygons to out CRS; union → 2D extent; keep per-polygon roughness/cellsize for mesh.
  - `build_rain_mask(ground_gdf, out_dir, cfg) -> (PolyFile, Meteo)` — write `rain_mask.pol` (ground polygons as PolyObjects) and a `Meteo(quantity='rainfall', forcingfiletype='uniform', targetmaskfile='rain_mask.pol', interpolationmethod='constant')` with **no value** (scenario fills the `.bui`).
  - `build_nwrw(roof_gdf, registry, cfg) -> RainfallRunoffModel` — one NWRW catchment node per roof polygon: geometry = roof shape (centroid + area), `area = polygon area (m^2)`, surface type = `cfg.nwrw.roof_surface_type`, slope type = `cfg.nwrw.roof_slope_type`. Use the exact NWRW node field names confirmed in Task 0 Step 3.

- [ ] **Step 1: Implement `read_planning_map`** (geopandas, tolerant of missing layers).
- [ ] **Step 2: Implement `build_2d_domain`** (reproject + union + per-zone attrs).
- [ ] **Step 3: Implement `build_rain_mask`** — construct `PolyObject`s from ground polygon exteriors; write `PolyFile`; build the `Meteo` block pointing at it.
- [ ] **Step 4: Implement `build_nwrw`** — map each roof polygon to an NWRW node. If the installed hydrolib-core does not expose typed NWRW catchments, emit the RR node records via `RainfallRunoffModel`'s node/link files using the field names from Task 0; document the exact shape in a docstring.
- [ ] **Step 5: Verify** — a small planning_map.gpkg (create inline with geopandas: 1 ground polygon, 1 roof polygon) → assert `rain_mask.pol` written with 1 object, Meteo.targetmaskfile set, and 1 NWRW node with area>0.

---

## Task 10: mesh/ — mesh1d, mesh2d, links

**Files:**
- Create: `src/conversion/mesh/mesh1d.py`, `src/conversion/mesh/mesh2d.py`, `src/conversion/mesh/links.py`

**Interfaces:**
- Produces:
  - `build_mesh1d(network, branches, cfg) -> None` — for each `BranchSpec`: `Branch(geometry=spec.geometry)`, `.generate_nodes(mesh1d_edge_length=cfg.mesh.edge_length_1d)`, `network.mesh1d_add_branch(branch, name=spec.name)` (follow `model.py` exactly).
  - `build_mesh2d(network, extent_polygon, clip_polygons, cfg) -> None` — rectilinear within the extent bbox (`network.mesh2d_create_rectilinear_within_extent(extent=(xmin,ymin,xmax,ymax), dx, dy)`); if `clip.to_ground_polygons`, clip to the ground union; optional refine per config.
  - `build_links(network, cfg, branches) -> None` — `network.link1d2d_from_1d_to_2d(branchids=[...])` for branches whose coupling type is lateral; for sewer (vertical/street-inlet) branches follow the spec's coupling note. Writes contacts into the network (→ net.nc). Also emit `1d2d_links.ini` placeholder for link physical params (documented; may be empty in first pass).

- [ ] **Step 1: Implement `build_mesh1d`** (mirror `model.py` lines 40–64).
- [ ] **Step 2: Implement `build_mesh2d`** (mirror `model.py` line 70–72 for rectilinear; add clip via `network.mesh2d_clip(...)`/meshkernel if `clip.to_ground_polygons`).
- [ ] **Step 3: Implement `build_links`** — couple non-sewer branches laterally (mirror `model.py` line 78); document sewer vertical coupling. Create `1d2d_links.ini` only if link params are configured.
- [ ] **Step 4: Verify** — build a 2-branch network + small extent → assert `network._mesh1d.mesh1d_node_x.size > 0`, `network._mesh2d.mesh2d_node_x.size > 0`, and links array shape[0] ≥ 1 (mirror `model.py` summary prints).

---

## Task 11: model_writer.py + rr_writer.py — assemble net.nc + mdu + dimr + D-RR coupling

**Files:**
- Create: `src/delft3dfm/model_writer.py`
- Create: `src/delft3dfm/rr_writer.py`

**Interfaces:**
- Consumes: all converter outputs + the populated `Network`.
- Produces:
  - `write_model(out_dir, network, crossdef, crossloc, friction, storage, structures, obs, ext_boundaries, ext_laterals, meteo, inifield, gcfg) -> FMModel` — set `fm.geometry.netfile/crossdeffile/crosslocfile/frictfile/structurefile/storagenodefile`, `fm.geometry.inifieldfile`, `fm.output.obsfile`, `fm.external_forcing.extforcefilenew`, datum/time from `gcfg`; `fm.filepath = out_dir/"FlowFM.mdu"`; `fm.save(recurse=True)`. (Mirror `model.py` §5.)
  - `write_dimr(out_dir, fm, rr_model=None) -> None` — `DIMR()` with `FMComponent(name='dflowfm', ...)`; if `rr_model`, add `RRComponent` + a `Coupler` for **RR→FM** (runoff → lateral) and master/slave `Start`/`StartGroup` per spec §2.2. Save `dimr_config.xml`. (Mirror `model.py` §6, extend with RR.)
  - `rr_writer.write_rr(out_dir, rr_model) -> None` — save the `RainfallRunoffModel` files into `out_dir`.

- [ ] **Step 1: Implement `write_model`** (mirror `model.py` 188–207, add storagenode + inifield wiring).
- [ ] **Step 2: Implement `rr_writer.write_rr`.**
- [ ] **Step 3: Implement `write_dimr`** with optional RR component + RR→FM coupler.
- [ ] **Step 4: Verify** — call with a minimal network → assert `FlowFM.mdu`, `FlowFM_net.nc`, `dimr_config.xml` exist and re-read via `FMModel(filepath=...)` / `DIMR(filepath=...)` without error.

---

## Task 12: conversion.py orchestrator + validate.py

**Files:**
- Create: `src/conversion/conversion.py`
- Create: `src/conversion/validate.py`
- Create: `src/conversion/postprocess.py` (thin: any net.nc cleanup; may delegate to mesh/links)

**Interfaces:**
- Produces:
  - `class Conversion(dataset_dir, out_dir, dem_path=None, planning_map=None, bbox=None)` with `.run() -> str` (returns out_dir). Stages in spec §4 order: build branches → crosssections → roughness → storage → structures → boundaries → observations → planning map (2d domain + rain mask + nwrw) → mesh1d → mesh2d → links → fields (inifield + DEM node refinement) → assemble (model_writer + rr_writer + dimr) → validate.
  - `validate_model(out_dir) -> list[str]` — round-trip re-read every produced file via hydrolib-core; check branch connectivity, that referenced friction/def ids exist, CRS, and required files present. Return list of problems (empty = OK); print a summary.

- [ ] **Step 1: Implement `Conversion.__init__`** resolving the standardized CSV paths (`thoat_nuoc/`, `mang_luoi_song_ho_kenh_muong/`, `thuy_van/`) exactly like the SWMM `Conversion` class.
- [ ] **Step 2: Implement `Conversion.run`** calling the stages in order, threading the `Network`, registry, and cfg through. Print a per-stage banner.
- [ ] **Step 3: Implement `validate_model`** (round-trip parse + reference/connectivity checks).
- [ ] **Step 4: Verify** — run `.run()` on a hand-built tiny dataset dir; assert it returns out_dir and `validate_model(out_dir) == []`.

---

## Task 13: tools — run_conversion, gis_template, gpkg_to_csv, planning_map (geopandas)

**Files:**
- Create: `src/tools/run_conversion.py`
- Create: `src/tools/gpkg_to_csv.py`
- Create: `src/tools/gis_template.py`
- Create: `src/tools/planning_map.py`

**Interfaces:**
- `run_conversion.py` — argparse CLI: `--dataset`, `--out`, `--dem`, `--planning-map`, `--bbox`; resolves relative paths against repo root; constructs `Conversion(...).run()`. (Mirror the SWMM `run_conversion.py` arg handling, minus the scenario loop — rainfall is decoupled.)
- `gpkg_to_csv.py` — defines the column lists (`RIVERS_COLS`, `MANHOLES_COLS`, ... matching the standardized schema) and `gpkg_to_csv(gpkg, out_dir)` using **geopandas** (read each layer, write CSV with a GeoJSON geometry column `RouteShape`/`Shape`). NO osgeo.
- `gis_template.py` — create an empty multi-layer drawing GeoPackage (the schema layers) + a minimal QGIS `.qgz`, using **geopandas/fiona-free** writes (geopandas `to_file(..., driver='GPKG', layer=...)` with empty GeoDataFrames of the right schema). Import the column lists from `gpkg_to_csv`.
- `planning_map.py` — create/edit/validate a planning-map GPKG with layers `landuse_catalog`, `ground`, `roof` (port `landuses_gpkg.py` off GDAL onto geopandas; keep the create/add/list/validate subcommands).

- [ ] **Step 1: Implement `gpkg_to_csv.py`** (column lists + geopandas reader → CSV with GeoJSON geometry).
- [ ] **Step 2: Implement `gis_template.py`** (empty typed layers via geopandas; `.qgz` minimal or reuse a template string).
- [ ] **Step 3: Implement `planning_map.py`** (geopandas port of the SWMM landuses tool; ground/roof/landuse_catalog layers).
- [ ] **Step 4: Implement `run_conversion.py`** CLI.
- [ ] **Step 5: Verify** — `gis_template` creates a gpkg with the expected layers; `planning_map create` + `list` round-trips; `run_conversion.py -h` prints usage.
```bash
cd G:/workspace/github/delft3d && ./.venv/Scripts/python.exe src/tools/run_conversion.py -h
```
Expected: argparse usage with `--dataset/--out/--dem/--planning-map/--bbox`.


---

## Task 14: Docs — migrate schema + conversion/mesh/gap_analysis

**Files:**
- Create: `docs/dataset.md`, `docs/conversion/conversion.md`, `docs/conversion/mesh_generation.md`, `docs/conversion/gap_analysis.md`
- Modify: `CLAUDE.md` (add the reference-files table rows for the new docs)

- [ ] **Step 1: Write `docs/dataset.md`** — migrate the standardized CSV schema field tables verbatim from `G:\workspace\github\swmm\docs\conversion\standardization_submodule.md` (Groups 1–5 + conventions). Note the standardization *code* is not migrated.
- [ ] **Step 2: Write `docs/conversion/conversion.md`** — module architecture, the spec §4 stage table, per-converter API (signatures from Tasks 4–12).
- [ ] **Step 3: Write `docs/conversion/mesh_generation.md`** — mesh1d/mesh2d/links APIs, the mesh config reference, meshkernel notes, the DTM-under-channel caveat from the component spec §2.1.
- [ ] **Step 4: Write `docs/conversion/gap_analysis.md`** — the full per-component CSV→Delft3D table from spec §5, expanded with the synthesis rule and "real data that would replace this default" per missing row (YZ/ZW profiles, 1D2D coupling type, NWRW surface/slope type).
- [ ] **Step 5: Update `CLAUDE.md`** reference-files table.

---

## Task 15: End-to-end run on a sample dataset

**Files:**
- Create: `sample/` (a tiny drawn dataset: a few branches, manholes, outfalls, a planning_map.gpkg) — built via the tools, not hand-CSV where possible.

- [ ] **Step 1: Build a sample dataset** — use `gis_template.py` to make a drawing gpkg, add a handful of features (or write minimal standardized CSVs directly), and `planning_map.py` to make a planning_map.gpkg with 1–2 ground + 1 roof polygon.
- [ ] **Step 2: Run conversion end-to-end.**
```bash
cd G:/workspace/github/delft3d && ./.venv/Scripts/python.exe src/tools/run_conversion.py --dataset sample/dataset --out out/sample --planning-map sample/planning_map.gpkg
```
Expected: prints per-stage banners and finishes; `out/sample/` contains `FlowFM_net.nc`, `crsdef.ini`, `crsloc.ini`, `roughness.ini`, `storagenodes.ini`, `structures.ini`, `obs.ini`, `forcing.ext`, `rain_mask.pol`, `inifield.ini`, `FlowFM.mdu`, `dimr_config.xml` (+ RR files if roofs present).

- [ ] **Step 3: Validate round-trip.**
```bash
cd G:/workspace/github/delft3d && ./.venv/Scripts/python.exe -c "
from src.conversion.validate import validate_model
probs = validate_model('out/sample')
print('PROBLEMS:', probs)
assert probs == [], probs
print('END-TO-END OK')
"
```
Expected: `PROBLEMS: []` then `END-TO-END OK`.


---

## Self-Review Notes (author)

- **Spec coverage:** D1 (full net.nc+mdu+dimr) → T11/T12; D2 (mesh stage inside conversion) → T10; D3/D4 (CSV schema + config synthesis) → T3–T7, T14; D5 (decoupled forcing) → T7 boundary slots + T9 Meteo/NWRW slots + scenario/simulation stubs (T1); D6 (geopandas, no GDAL) → T3,T9,T13; D7 (.venv) → Global Constraints; D8 (drawing tools) → T13; D9 (CRS) → T2,T3; D10 (ground/roof split) → T9; D11 (NWRW now) → T9,T11; D12 (DEM parity) → T8; D13 (no culvert) → T7 note; D14 (dfm_tools optional) → Global Constraints. All covered.
- **Convention deviations (intentional):** verification is CLI/round-trip, not pytest (spec §9); commits gated on user approval (observed user preference).
- **Open item for executor:** exact NWRW node field names + RR component/coupler class names are confirmed in Task 0 Steps 2–3 before they're used in T9/T11.
