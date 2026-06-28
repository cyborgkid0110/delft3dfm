# Delft3D FM Conversion Submodule + Repo Skeleton — Design

**Date:** 2026-06-25
**Repo:** `G:\workspace\github\delft3d`
**Status:** Approved design (pre-implementation)

## 1. Purpose & Context

Migrate the hydraulic-simulation pipeline from the SWMM/IberGIS repo
(`G:\workspace\github\swmm`) to this Delft3D FM repo. The target pipeline:

```
drawing dataset → standardized CSV dataset → conversion submodule → Delft3D FM base model
                                                  (mesh generation is a STAGE inside conversion)
→ (attach rainfall scenario) → Simulation → Result
```

This effort delivers **two things**:

1. A **basic repo skeleton** with `CLAUDE.md` defining conventions.
2. A **fully implemented conversion submodule** that reads the standardized
   CSV dataset and emits a runnable, **scenario-agnostic Delft3D FM base
   model folder** (net.nc + `.ini`/`.ext` + `FlowFM.mdu` + `dimr_config.xml`).

The authoritative component spec already exists at
`docs/Delft3D_FM_1D2D.md` (maps the four real-world object groups onto
D-Flow FM concepts and hydrolib-core classes). A working reference build
exists at `model.py` → `urban_1d2d_model/` (proves hydrolib-core 1.0.1 +
meshkernel produce a valid DIMR-ready model).

### Out of scope (this effort)
- The standardization submodule (raw → standardized CSV). The standardized
  CSV dataset is **drawn directly** via the drawing-template tools; only the
  **schema documentation** is migrated.
- `scenario/` and `simulation/` are **stub directories** with READMEs only.
- No `src/result/` directory.
- NWRW rainfall-runoff schematization is **documented as a gap**, not wired.

## 2. Key Architectural Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Conversion owns the **entire** `net.nc` (Mesh1d + Mesh2d + Link1d2d) AND the `.mdu`/`dimr_config.xml` wiring. Output is a **DIMR-ready model folder**. | Matches the real Delft3D workflow (declare → mesh → link → assemble) and the `model.py` reference. Simulation = invoke the binary on the folder. |
| D2 | **Mesh generation is a STAGE inside the conversion submodule**, in a dedicated `conversion/mesh/` sub-package, with its **own config file**. | The real workflow is sequential: declare geometry → generate 1D & 2D meshes → generate 1D2D links (written into `net.nc`) → optional link params (`1D2DLinkFile`). Link generation requires both meshes in one `net.nc`, so it cannot be a separate parallel module. |
| D3 | Input = the **same standardized CSV schema** as the SWMM repo (group folders, GeoJSON geometry columns, EPSG:4326), **plus a gap analysis** of fields Delft3D needs that the schema lacks. | Maximum reuse; keeps the drawing workflow stable; the gap analysis is a core deliverable. |
| D4 | Missing Delft3D data is **synthesized from config defaults** so the pipeline runs end-to-end. Each gap documented in `gap_analysis.md`. | User chose "document gaps + sensible defaults". |
| D5 | **Rainfall scenarios are decoupled** from the model build. Conversion emits a scenario-agnostic base model with empty boundary/lateral **slots** in `forcing.ext`. A separate `scenario` module authors rainfall `.bui`/`.bc`; a `simulation` step combines a chosen scenario into the base model at run time. | User authors rainfall separately and picks which to test at simulation time. |
| D6 | GIS tooling uses **geopandas / shapely / rasterio** (already in `.venv`), NOT `osgeo.ogr`. | GDAL/OGR is absent from the `.venv`; the modern stack is present and cleaner. |
| D7 | Environment = the repo's existing **`.venv`** (hydrolib-core 1.0.1, meshkernel, pyproj, numpy, geopandas, shapely, rasterio). | User confirmed; verified present. |
| D8 | Drawing-template tools migrated: **`gis_template`** (empty drawing GPKG + QGIS project) and **`gpkg_to_csv`** (drawn GPKG → standardized CSVs), plus **`planning_map`** (2D domain polygons + roughness catalog + roof). | User selected these; planning_map is the canonical 2D-domain + roughness source. |
| D9 | Reproject input EPSG:4326 → a **projected metric CRS** (configurable, default a UTM zone) during geometry build. | Delft3D meshes are metric; mirrors the SWMM repo's WGS84→VN2000 step. |
| D10 | **planning_map surfaces split by hydraulic treatment.** `ground` → 2D direct rainfall in D-Flow FM (polygons → `.pol`, referenced as `targetMaskFile` on a `[Meteo]` block in `forcing.ext`). `roof` → **NWRW catchment in D-RR**: one NWRW node per roof polygon with matching geometry + area + surface type + slope type. | User's chosen hydraulic schematization. |
| D11 | **NWRW scaffolded now**: `converters/nwrw.py` (roof → NWRW nodes), `delft3dfm/rr_writer.py` (D-RR model skeleton), and `model_writer` wires **DIMR RR→FM coupling**. Rainfall `.bui` values come from the scenario module. | User chose to build NWRW this pass; `hydrolib.core.rr.models` verified present. |
| D12 | **Manhole/storage DEM refinement replicates the SWMM repo exactly** (`src/conversion/postprocess.py::refine_elevations`): surface/rim level = `DEM_surface`; invert/bed level = `DEM_surface − depth` (junctions/storage); outfall = `DEM_surface`. Sampled at the node's WGS84 lon/lat. → Delft3D: `streetlevel` = DEM surface, `bedlevel` = DEM surface − depth. | User requirement: parity with the existing conversion. |
| D13 | **Culvert is OUT of scope** (no culvert dataset definition exists yet). | User: no culvert data. |
| D14 | **`dfm_tools` is an OPTIONAL dependency** (convenience/postprocessing helpers). Core build uses `hydrolib-core` directly; add `dfm_tools` only if a concrete need arises. | Flagged useful by user; not installed in `.venv`; core path does not require it. |

## 3. Directory Structure

```
delft3d/
  CLAUDE.md                     # master summary, conventions, env, full tree, pipeline diagram
  model.py                      # (existing) reference working build → urban_1d2d_model/
  urban_1d2d_model/             # (existing) reference output, kept as the golden example
  docs/
    Delft3D_FM_1D2D.md          # (existing) authoritative component spec — source of truth
    dataset.md                  # migrated: standardized CSV schema (from SWMM repo)
    conversion/
      conversion.md             # conversion module architecture + API + field mappings
      gap_analysis.md           # per-component CSV→Delft3D map + missing-data table  ◄ CORE
      mesh_generation.md        # mesh stage docs (mesh1d / mesh2d / links + config)
  src/
    delft3dfm/                  # hydrolib-core-facing helpers (the SWMM "ibergis" analogue)
      __init__.py               #   exports model writers, CRS/constants
      config.py                 #   loads global model options
      config.yaml               #   CRS, mdu time/datum/output defaults, dimr defaults
      model_writer.py           #   assemble net.nc + FlowFM.mdu + forcing.ext + dimr_config.xml
      rr_writer.py              #   D-RR (NWRW) model skeleton + DIMR RR→FM coupling wiring
    conversion/
      __init__.py
      conversion.py             #   Conversion orchestrator (stages in order)
      config.py
      config.yaml               #   roughness table, xsection/storage/structure defaults, mappings
      base.py                   #   CSV utils, GeoJSON parse, CRS reproject, DEM sampling, registries
      converters/
        branches.py             #   rivers/canals/sewers → 1D Branch centerlines (in-memory)
        crosssections.py        #   → crsdef.ini / crsloc.ini (open YZ/ZW + closed circle/rect)
        storage.py              #   manholes/lakes → storagenodes.ini
        structures.py           #   pumps/weirs/orifices → structures.ini
        boundaries.py           #   outfalls → Boundary slots in forcing.ext
        observations.py         #   manholes/pumps/outfalls → obs.ini
        domain2d.py             #   planning_map ground → 2D extent/clip polygon (in-memory)
                                #     + rain mask .pol + [Meteo] targetMaskFile slot in forcing.ext
        nwrw.py                 #   planning_map roof → NWRW catchment nodes (geom, area, surface/slope type)
        fields.py               #   DEM GeoTIFF → inifield.ini (bedlevel) + manhole/storage/outfall
                                #     DEM refinement (parity with SWMM postprocess.refine_elevations)
      mesh/
        __init__.py
        mesh1d.py               #   discretize branches → Mesh1d
        mesh2d.py               #   2D grid: create → refine → clip (meshkernel)
        links.py                #   1D2D contacts → net.nc + 1d2d_links.ini
        config.yaml             #   mesh settings: edge_length_1d, grid_2d dx/dy/type, refine, clip, link type
      postprocess.py            #   any net.nc cleanup / connectivity fixes
      validate.py               #   integrity checks (refs, branch connectivity, CRS, file presence)
    tools/
      run_conversion.py         #   CLI: dataset dir → base model folder
      gis_template.py           #   empty drawing GPKG (schema layers) + QGIS .qgz project
      gpkg_to_csv.py            #   drawn GPKG → standardized CSVs
      planning_map.py           #   create/edit/validate planning-map GPKG (2D domain + roughness + roof)
    scenario/                   # STUB + README.md  (rainfall .bui/.bc authoring; decoupled forcing)
    simulation/                 # STUB + README.md  (combine base + chosen scenario, run DIMR binary)
```

## 4. Conversion Data Flow

The `Conversion` orchestrator runs stages in order, producing ONE
scenario-agnostic base model folder:

```
INPUT                          STAGE                         OUTPUT
rivers/canals/sewers.csv  ─►  branches.py      ─►  1D Branch centerlines (in-memory, reprojected)
                              crosssections.py ─►  crsdef.ini + crsloc.ini
                                                    • rivers/canals → YZ/ZW (derived: Width_m,
                                                      BedElev_m, SlopCoef, BankElev_m + config)
                                                    • sewers → circle/rect closed (Diam_mm/Size_mm)
config / planning catalog ─►  roughness        ─►  roughness.ini (global + per-branch Manning)
manholes.csv, lakes.csv   ─►  storage.py       ─►  storagenodes.ini
                                                    • bedlevel=InvElev_m, streetlevel=RimElev_m,
                                                      area=Area_m2, streetstoragearea=derived
pumps/weirs/orifices.csv  ─►  structures.py    ─►  structures.ini (Pump/Weir/Orifice; Culvert out, D13)
outfalls.csv              ─►  boundaries.py    ─►  Boundary slots in forcing.ext (empty .bc refs)
manholes/pumps/outfalls   ─►  observations.py  ─►  obs.ini
planning_map ground polys ─►  domain2d.py      ─►  2D extent/clip polygon (in-memory)
                                                    + rain_mask.pol + [Meteo] block in forcing.ext
                                                      (targetMaskFile=rain_mask.pol, value slot empty)
planning_map roof polys   ─►  nwrw.py          ─►  NWRW catchment nodes (geometry = roof shape,
                                                      area, surface type, slope type) → D-RR model
── MESH STAGE ──
branches (in-memory)      ─►  mesh/mesh1d.py   ─►  Mesh1d (discretized computational nodes)
2D extent + mesh config   ─►  mesh/mesh2d.py   ─►  Mesh2d (create → refine → clip)
mesh1d + mesh2d           ─►  mesh/links.py    ─►  Link1d2d (contacts, into net.nc) + 1d2d_links.ini
DEM GeoTIFF               ─►  converters/fields.py ─► inifield.ini (bedlevel) [+ 1d field]
                                                    + DEM refinement of node levels (D12):
                                                      streetlevel=DEM_surface, bedlevel=DEM_surface−depth,
                                                      outfall=DEM_surface (sampled at WGS84 lon/lat)
── ASSEMBLY ──
all of the above          ─►  delft3dfm/model_writer.py ─► FlowFM_net.nc, FlowFM.mdu,
                                                            forcing.ext (slots), dimr_config.xml
                              delft3dfm/rr_writer.py    ─► D-RR (NWRW) model files +
                                                            DIMR RR→FM coupler block
                              validate.py      ─►  integrity checks
```

**Forcing is NOT filled here.** `forcing.ext` carries boundary/lateral
*slots* (e.g. outfall waterlevel boundaries referencing `.bc` files) and a
`[Meteo]` block whose `targetMaskFile` is the ground `rain_mask.pol` but whose
rainfall **value** is an empty `.bui` slot. The roof NWRW nodes likewise have
geometry/area/type built but no rain values. Rainfall `.bui` values are
authored in the separate `scenario` module and injected at run time, feeding
**both** the 2D `[Meteo]` ground rain and the D-RR NWRW roof catchments.

## 5. Gap Analysis (core deliverable — `docs/conversion/gap_analysis.md`)

Per-component tables: each standardized CSV field → Delft3D attribute, with
status **direct / derive / default / missing** and a synthesis rule. Key rows:

| Component | CSV field → Delft3D attr | Status | Synthesis rule |
|---|---|---|---|
| River/Canal | `Width_m`,`BedElev_m`,`SlopCoef`,`BankElev_m` → YZ `y/zCoordinates` | derive | trapezoid: bed width + side slope; depth = BankElev−BedElev or config |
| River/Canal | `Material` → `frictionValue` | derive | config roughness table by material |
| Sewer | `Diam_mm`/`Size_mm`,`XSType` → circle/rect `closed=yes` | direct | mm → m |
| Manhole | `InvElev_m`→`bedlevel`, `RimElev_m`→`streetlevel`, `Area_m2`→`area` | direct | — |
| Manhole | `InvElev_m`/`RimElev_m` refined from DEM (D12) | derive | streetlevel=DEM_surface, bedlevel=DEM_surface−depth (when `--dem` given) |
| Manhole | (none) → `streetstoragearea` | default | config factor × area |
| Manhole | (none) → `[Global]` loss coeffs | default | config |
| Pump | `Cap_m3s`→`capacity`, `In/OutElev_m`→start/stop levels | direct/derive | parse capacity string |
| Weir | `CrestElv`→`crestlevel`, `Width_m`→`crestwidth` | direct | `corrcoeff` default |
| Orifice | `InvElev_m`→`crestlevel`, `Height_m`→`gateloweredgelevel`, `Form`→shape | direct | `corrcoeff` default |
| Outfall | `Type`,`Elev_m`,`FixedStage` → Boundary `quantity` + `.bc` slot | direct | FREE/FIXED/TIDAL → waterlevelbnd; `Elev_m` DEM-refined |
| **Ground (planning_map)** | ground polygons → 2D domain + `rain_mask.pol` + `[Meteo]` targetMaskFile (D10) | **new source** | clip extent + per-zone roughness/cellsize; 2D direct rainfall in D-Flow FM |
| **Roof (planning_map)** | roof polygons → NWRW catchment nodes (geom, area, surface type, slope type) (D10/D11) | **new source** | one NWRW node per roof; D-RR model; DIMR RR→FM coupling |
| **1D2D coupling** | (none) → coupling type per branch | **missing→default** | config: lateral default; vertical (street-inlet) for sewers |
| **DEM** | GeoTIFF → `inifield` bedlevel + node level refinement | direct | bedlevel: averaging/mean; node levels per D12 |

The **missing** rows are precisely what the current dataset cannot provide
(real YZ/ZW survey profiles, 1D2D coupling type). Each gets a config-default
fallback so the pipeline runs, plus a note on the real data that would replace
it. NWRW surface/slope **type** per roof, when not in the data, defaults from
config (e.g. roof = closed-paved-equivalent / sloped); documented as a gap.

## 6. Configuration Files

- `src/delft3dfm/config.yaml` — global model: CRS (in/out), mdu time
  (refdate, tstart/tstop/dtuser), vertical datum (bedlevuni, waterlevini),
  output options, dimr defaults.
- `src/conversion/config.yaml` — roughness table (by material), cross-section
  derivation defaults (default depth/side-slope/width), storage-node defaults
  (streetstoragearea factor, loss coeffs), structure defaults (corrcoeff,
  discharge coeff), **NWRW defaults** (roof surface type, slope type, area
  scaling), attribute mappings.
- `src/conversion/mesh/config.yaml` — `edge_length_1d`, 2D grid (`type`,
  `dx`, `dy`), refinement (levels, polygon), clipping, 1D2D link type per
  branch class.

## 7. Documentation to Migrate / Write

- `docs/dataset.md` — standardized CSV schema migrated verbatim from the SWMM
  repo (`docs/conversion/standardization_submodule.md` field tables), with
  CRS/encoding/naming conventions. (The standardization *code* is not migrated.)
- `docs/conversion/conversion.md` — module architecture, stage-by-stage API,
  field-mapping summary.
- `docs/conversion/mesh_generation.md` — mesh stage (mesh1d/mesh2d/links),
  config reference, meshkernel notes.
- `docs/conversion/gap_analysis.md` — §5 above, expanded per component.
- `CLAUDE.md` — project summary, full directory tree, 4-stage pipeline
  diagram, conventions: hydrolib-core as file API, `.venv` activation, EPSG
  conventions, "conversion emits scenario-agnostic base model", mesh-as-a-stage
  rule, no test files (exercise via CLI), geopandas/shapely/rasterio stack.

## 8. Environment & Dependencies

- Target the repo's existing **`.venv`**.
- Present & verified: `hydrolib-core` 1.0.1 (incl. `hydrolib.core.rr.models`
  for NWRW and `hydrolib.core.dflowfm.polyfile.models` for `.pol`),
  `meshkernel`, `pyproj`, `numpy`, `geopandas`, `shapely`, `rasterio`.
- **Absent: `osgeo.ogr` (GDAL).** Therefore GIS tools use geopandas/shapely/
  rasterio (D6). If a future need forces GDAL, document adding it; do not
  assume it.
- **`dfm_tools` (D14): optional, NOT installed.** Add only if a concrete
  postprocessing/convenience need arises; the core build uses hydrolib-core
  directly.
- Activation (Windows): `.venv\Scripts\activate`.

## 9. Testing Strategy

Per the project workflow convention: **no test files.** Validate by:
1. `tools/gis_template.py` → draw / supply a small sample dataset.
2. `tools/run_conversion.py --dataset <sample> --out <folder>` → base model.
3. Load the output folder back through hydrolib-core (round-trip parse) in
   `validate.py`; optionally run it through the DIMR binary.
4. `urban_1d2d_model/` remains the golden reference for a valid output shape.

## 10. Deliverables Checklist

- [ ] `CLAUDE.md` with conventions + full tree + pipeline diagram.
- [ ] `docs/dataset.md` (migrated CSV schema).
- [ ] `docs/conversion/{conversion,mesh_generation,gap_analysis}.md`.
- [ ] `src/delft3dfm/` (config + model_writer + rr_writer).
- [ ] `src/conversion/` (orchestrator + converters incl. nwrw + mesh/ + configs + validate).
- [ ] Manhole/storage/outfall DEM refinement with SWMM parity (D12).
- [ ] Ground → `.pol` rain mask + `[Meteo]` slot; roof → NWRW nodes + D-RR + DIMR RR→FM coupling.
- [ ] `src/tools/{run_conversion,gis_template,gpkg_to_csv,planning_map}.py`.
- [ ] `src/scenario/` and `src/simulation/` stub dirs + READMEs.
- [ ] End-to-end run on a sample dataset producing a DIMR-ready folder.
