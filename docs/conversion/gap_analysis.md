# Gap Analysis: CSV Schema to Delft3D FM

This document maps every standardized CSV field to the corresponding Delft3D FM attribute,
with status and synthesis rule for each row. "Missing" or "default" rows explain what real
data would replace the fallback.

**Status legend:**
- `direct` — field maps 1-to-1 (possibly with unit conversion) to a Delft3D attribute.
- `derive` — Delft3D attribute is computed from one or more CSV fields + config.
- `default` — no CSV field exists; a config constant is used.
- `missing` — data exists conceptually but is not yet collected in the dataset.

---

## Component: River / Canal (branches.py, crosssections.py)

| CSV Field | Delft3D Attribute | Status | Synthesis Rule |
|-----------|-------------------|--------|----------------|
| `RouteShape` (GeoJSON LineString) | `Branch.geometry` (projected metric coords) | direct | Reprojected EPSG:4326 -> metric CRS via pyproj |
| `Name` | `Branch.name`, `CrossSection.id`, `CrossSection.branchid` | direct | Sanitized + globally unique (numeric suffix on collision) |
| `Material` | `FrictGlobal.frictionid` (via `f_{material}`) | direct | If empty, falls back to kind string (`'river'` / `'canal'`) |
| `Material` -> `cfg['roughness']` | `FrictGlobal.frictionvalue` (Manning n) | derive | Lookup in roughness table; default `0.013` if key absent |
| `Width_m` | `YZCrsDef.ycoordinates` (bottom width `b`) | direct | Used as b in 5-point trapezoid; default `cfg['river/canal']['default_width']` if absent/zero |
| `BedElev_m` | `YZCrsDef.zcoordinates` (datum z_bed) | direct | Absolute z reference for YZ profile; `0.0` if absent |
| `BankElev_m` | `YZCrsDef.zcoordinates` (z_bank) | derive | depth h = BankElev_m - BedElev_m; default `cfg['river/canal']['default_depth']` if absent or non-positive |
| `SlopCoef` | `YZCrsDef.ycoordinates` (side slope m H:V) | direct | `m` in trapezoid geometry; default `cfg['river/canal']['side_slope']` if absent/negative |
| (none) | `CrossSection.chainage` | derive | Placed at mid-chainage of each branch (length / 2) |
| `XSType` | (informational only) | default | Rivers/canals always use YZ trapezoid in first pass; XSType is not consumed |
| (none) | YZ survey profile | **missing** | Real YZ/ZW survey profiles do not exist in the dataset. The conversion derives a symmetric 5-point trapezoid from Width/Bed/Bank/SlopCoef. When measured cross-sections become available, replace `_yz_trapezoid()` with a direct `YZCrsDef` from survey data. |
| `BedElev_m`, `BankElev_m` | DEM-refined invert/street levels | **missing** | If no surveyed elevations are available AND a DEM is provided, stage 12 (fields.py) refines storage node and outfall levels from the DEM. Channel cross-section elevations (BedElev_m / BankElev_m) are NOT DEM-refined in this pass. |

**Config defaults consulted (src/conversion/config.yaml):**

| Config key | Default value | Meaning |
|------------|--------------|---------|
| `river.default_width` | 5.0 m | Trapezoid bottom width when `Width_m` absent |
| `river.default_depth` | 2.0 m | Trapezoid depth when BankElev-BedElev not positive |
| `river.side_slope` | 1.0 (H:V) | Trapezoid side slope when `SlopCoef` absent |
| `canal.default_width` | 1.0 m | Same for canals |
| `canal.default_depth` | 0.5 m | Same for canals |
| `canal.side_slope` | 1.0 | Same for canals |
| `default_roughness` | 0.013 | Manning n fallback when material not in roughness table |
| `roughness.BTCT` | 0.013 | Example: concrete roughness |
| `roughness.PVC` | 0.011 | PVC pipe roughness |
| `roughness.HDPE` | 0.012 | HDPE pipe roughness |

---

## Component: Sewer (branches.py, crosssections.py)

| CSV Field | Delft3D Attribute | Status | Synthesis Rule |
|-----------|-------------------|--------|----------------|
| `RouteShape` | `Branch.geometry` | direct | Same reprojection as rivers/canals |
| `Diam_mm` | `CircleCrsDef.diameter` (m) | direct | `Diam_mm / 1000.0`; default `0.5 m` (DN500) when absent or zero |
| `Size_mm` (WxH or W*H) | `RectangleCrsDef.width`, `.height` (m) | direct | Parsed as mm; default `canal.default_width`/`canal.default_depth` when absent |
| `XSType` | Shape selector (circle vs rectangle) | direct | 'RECT' in XSType, or 'x'/'X'/'*' in Size_mm -> rectangle; otherwise circle |
| (none) | `RectangleCrsDef.closed` | default | Always `'yes'` (sewers are closed-section pipes) |
| `Material` | `FrictGlobal.frictionid` / `frictionvalue` | direct | Same roughness lookup as rivers/canals |
| (none) | `CrossSection.chainage` | derive | Mid-chainage of each sewer branch |

---

## Component: Manhole (storage.py, observations.py, fields.py)

| CSV Field | Delft3D Attribute | Status | Synthesis Rule |
|-----------|-------------------|--------|----------------|
| `Shape` (GeoJSON Point) | `StorageNode.nodeid` (`f"{x:.6f}_{y:.6f}"`) | derive | Reprojected to metric, formatted as coordinate-string nodeid |
| `InvElev_m` | `StorageNode.bedlevel` | direct | Raw value; refined from DEM at stage 12 when DEM provided |
| `RimElev_m` | `StorageNode.streetlevel` | direct | Raw value; refined from DEM at stage 12; fallback = bedlevel + 3.0 when RimElev_m < bedlevel |
| `Area_m2` | `StorageNode.area` | direct | Used as-is; default `1.0 m2` when absent/zero |
| (none) | `StorageNode.streetstoragearea` | default | `cfg['storage']['street_storage_factor'] * area` (default factor = 1.0, so area = streetstoragearea) |
| (none) | `StorageNode.usetable` | default | Always `'false'` (area-form storage, not tabulated) |
| (none) | `StorageNode.storagetype` | default | `cfg['storage']['storage_type']` = `'reservoir'` |
| `Name` / `ID` | `StorageNode.id`, `.name` | direct | Sanitized + numeric suffix on collision |
| (none) | Loss coefficients (entrance/exit) | default | `cfg['storage']['entrance_loss']` = 0.5, `cfg['storage']['exit_loss']` = 1.0 (not yet wired to StorageNode — future improvement) |
| `Shape` (Point) | `ObservationPoint` location | direct | Manholes become observation points in obs.ini (placed on nearest branch) |

**DEM refinement (stage 12):**
When a DEM is provided, `refine_node_levels` samples the DEM at each manhole's WGS84 lon/lat:
- `streetlevel = round(DEM_surface, 3)`
- `bedlevel = round(DEM_surface - depth, 3)` where `depth = prior (streetlevel - bedlevel)` if > 0, else `0.0`.

The depth-zero fallback mirrors SWMM `refine_elevations` exactly: when the prior depth
is non-positive (e.g. because InvElev_m and RimElev_m are absent or inverted), depth = 0.0
so invert == surface. This is NOT a synthetic default depth — it preserves SWMM parity.

**Real data that would replace defaults:**
- `streetstoragearea`: Real street storage area above the manhole (m2). Currently derived as
  `factor x area` because dedicated street-storage surveys are not in the dataset.
- Loss coefficients: Real entrance/exit K values from hydraulic engineering specs.

---

## Component: Lake / Detention Pond (storage.py)

| CSV Field | Delft3D Attribute | Status | Synthesis Rule |
|-----------|-------------------|--------|----------------|
| `Shape` (GeoJSON Point) | `StorageNode.nodeid` | derive | Same coordinate-string format as manholes |
| `BedElev_m` | `StorageNode.bedlevel` | direct | Raw value; fallback `0.0` |
| `CrestElv` | `StorageNode.streetlevel` | direct | Priority 1; fallback to BankElev_m, then bedlevel + 3.0 |
| `BankElev_m` | `StorageNode.streetlevel` | direct | Priority 2 (after CrestElv); fallback bedlevel + 3.0 |
| `Area_ha` | `StorageNode.area` (m2) | direct | `Area_ha * 1e4`; default `1.0 ha` when absent/zero |
| `Vol_m3` | (currently unused) | **missing** | Tabulated storage (usetable='true') is a documented gap. Currently the lake uses area-form (`usetable='false'`) with `Area_ha -> m2`. A future improvement would set `usetable='true'` and build a depth-volume table from `Vol_m3` and lake geometry. |
| (none) | `StorageNode.streetstoragearea` | default | `cfg['storage']['street_storage_factor'] * area` |
| `NatWtrLvl`, `WetLvl_m`, `DryLvl_m` | (currently unused) | **missing** | Seasonal control levels are not yet wired to any Delft3D attribute. They could drive initial water level conditions or operational rules in a future pass. |

---

## Component: Pump (structures.py, observations.py)

| CSV Field | Delft3D Attribute | Status | Synthesis Rule |
|-----------|-------------------|--------|----------------|
| `Shape` (GeoJSON Point) | `Pump.branchid`, `Pump.chainage` | derive | Snapped to nearest branch by `line.project(point)` |
| `Cap_m3s` | `Pump.capacity` | direct | First number extracted from string (e.g. "2.5 m3/s"); default `0.5` on parse failure |
| (none) | `Pump.orientation` | default | Always `'positive'` |
| (none) | `Pump.controlside` | default | Always `'suctionSide'` |
| (none) | `Pump.numstages` | default | `0` (no staged operation; start/stop levels not wired) |
| `InElev_m`, `OutElev_m` | Start/stop suction levels | **missing** | Not yet wired to `startlevelsuctionside`/`stoplevelsuctionside`. When `numstages > 0` these must be supplied as lists sized to `numstages`. |
| `Name` / `ID` | `Pump.id`, `.name` | direct | Sanitized + unique |
| `Shape` (Point) | `ObservationPoint` | direct | Pumps also appear in obs.ini |

---

## Component: Weir (structures.py)

| CSV Field | Delft3D Attribute | Status | Synthesis Rule |
|-----------|-------------------|--------|----------------|
| `Shape` (GeoJSON Point) | `Weir.branchid`, `Weir.chainage` | derive | Nearest-branch snap; no max-distance cutoff |
| `CrestElv` | `Weir.crestlevel` | direct | Required; rows missing CrestElv are skipped |
| `Width_m` | `Weir.crestwidth` | direct | Default `1.0 m` when absent |
| (none) | `Weir.corrcoeff` | default | `cfg['structure']['weir_corrcoeff']` = `1.0` |
| `Name` / `ID` | `Weir.id`, `.name` | direct | Sanitized + unique |
| `Height_m`, `Openings`, `Operation` | (currently unused) | **missing** | Gate opening/closure logic and multi-opening weirs are not modeled in this pass. |

---

## Component: Orifice (structures.py)

| CSV Field | Delft3D Attribute | Status | Synthesis Rule |
|-----------|-------------------|--------|----------------|
| `Shape` (GeoJSON Point) | `Orifice.branchid`, `Orifice.chainage` | derive | Nearest-branch snap; no max-distance cutoff |
| `InvElev_m` | `Orifice.crestlevel` | direct | Required; rows missing InvElev_m are skipped |
| `Height_m` | `Orifice.gateloweredgelevel` | derive | `crestlevel + Height_m`; default `crestlevel + 1.0` when Height_m absent |
| `Width_m` | `Orifice.crestwidth` | direct | Default `1.0 m` when absent |
| (none) | `Orifice.corrcoeff` | default | `cfg['structure']['orifice_corrcoeff']` = `0.63` |
| `Name` / `ID` | `Orifice.id`, `.name` | direct | Sanitized + unique |
| `DischCoef`, `GateCtrl`, `Openings` | (currently unused) | **missing** | Gate control mechanism and per-opening modeling not wired. |

---

## Component: Outfall (boundaries.py, observations.py, fields.py)

| CSV Field | Delft3D Attribute | Status | Synthesis Rule |
|-----------|-------------------|--------|----------------|
| `Shape` (GeoJSON Point) | `Boundary.nodeid` (`f"{x:.6f}_{y:.6f}"`) | derive | Coordinate-string nodeid |
| `FixedStage` | `Constant.datablock` value | direct | Priority 1; used as placeholder water level |
| `Elev_m` | `Constant.datablock` value | direct | Priority 2 (after FixedStage); DEM-refined at stage 12 |
| (none) | `Constant.datablock` value | default | `0.0` when both FixedStage and Elev_m absent |
| `Type` (FREE/NORMAL/TIDAL/FIXED) | `Boundary.quantity` | default | All types map to `'waterlevelbnd'`; tidal/timeseries refinement is a documented gap |
| (none) | `ForcingModel.filepath` | default | `'boundaries.bc'` (scenario module fills values) |
| `Shape` (Point) | `ObservationPoint` | direct | Outfalls also appear in obs.ini |
| `FlapGate`, `Receiver` | (currently unused) | **missing** | Flap gate logic and receiver water-body metadata not modeled. |

**Real data that would replace gaps:**
- `TIDAL` type: would require a tidal-curve BC block in the scenario module.
- `TIMESERIES` type: would reference a `.bc` time series authored by the scenario module.

---

## Component: Ground / 2D Domain (domain2d.py)

| CSV Field / Source | Delft3D Attribute | Status | Synthesis Rule |
|-------------------|-------------------|--------|----------------|
| planning_map `ground` layer (polygons) | `mesh2d` bounding box + clip polygon | direct | `unary_union` of reprojected ground geometries |
| planning_map `ground` layer | `PolyFile` (rain_mask.pol) | direct | One PolyObject per ground polygon exterior ring |
| planning_map `ground` layer | `Meteo.targetmaskfile` | direct | References the PolyFile in forcing.ext |
| (none) | `Meteo.forcingfile` (rainfall.bc) | default | Empty `ForcingModel(filepath='rainfall.bc')` — scenario module fills values |
| planning_map `cat_landuses` | 2D grid roughness per zone | **missing** | The `landuse_catalog` (idval -> Manning n) is read by `read_planning_map()` but is not yet applied to 2D mesh cell roughness in this pass. Spatial roughness assignment to 2D cells requires writing a spatially-varying roughness field, which is a documented gap. |
| (none) | Initial 2D water level | default | `gcfg['model']['waterlevini']` = `0.05 m` (global uniform initial condition in FlowFM.mdu) |

---

## Component: Roof / NWRW (nwrw.py, rr_writer.py)

| CSV Field / Source | Delft3D Attribute | Status | Synthesis Rule |
|-------------------|-------------------|--------|----------------|
| planning_map `roof` layer (polygons) | `rrtop.Node` (NWRW catchment node) | direct | One node per roof polygon; centroid x/y; area = polygon area in m2 |
| `roof_gdf['surface']` column | NWRW `surface_type` | direct | If column present and non-empty, used per row |
| (none) | NWRW `surface_type` | default | `cfg['nwrw']['roof_surface_type']` = `'closed_paved'` when `surface` column absent |
| `roof_gdf['slope']` column | NWRW `slope_type` | direct | If column present and non-empty, used per row |
| (none) | NWRW `slope_type` | default | `cfg['nwrw']['roof_slope_type']` = `'sloped'` when `slope` column absent |
| (none) | `rrtop.Node.modelnodetype` | default | Always `2` (NWRW node type) |
| (none) | `rrtop.Node.netternodetype` | default | Always `44` (validated NWRW combo in hydrolib-core 1.0.1) |
| (none) | NWRW rainfall `.bui` values | **missing** | Rainfall values are decoupled. The scenario module authors `.bui` content and wires it to the NWRW nodes. The first-pass RR model (`rr/Sobek_3b.fnm`) contains only topology nodes; full NWRW area records (`.3b_nod`) and DWA tables are a documented gap. |
| (none) | Sewer-to-NWRW coupling | **missing** | NWRW roof runoff coupling to sewer nodes (D-RR -> D-Flow FM via DIMR `catchments/runoff -> laterals/discharge`) is scaffolded in `write_dimr` but the per-roof sewer outlet assignments are not implemented. |

**hydrolib-core 1.0.1 note:** There is no typed NWRW catchment class in this version. Roofs
are emitted as `rrtop.Node` objects with the validated `modelnodetype=2` / `netternodetype=44`
combination. Any other combination raises during hydrolib-core serialization.

---

## Component: 1D2D Coupling (links.py)

| Data available | Delft3D Attribute | Status | Synthesis Rule |
|---------------|-------------------|--------|----------------|
| Branch `kind` == 'river' or 'canal' | `link1d2d` lateral contacts | direct | `network.link1d2d_from_1d_to_2d(branchids=lateral_names)` for all non-sewer branches |
| Branch `kind` == 'sewer' | Vertical / street-inlet coupling | **missing** | Sewers are intentionally excluded from lateral linking. Vertical/gully-inlet (street-inlet) coupling connects sewer nodes to 2D surface cells via vertically stacked 1D2D links, requiring additional street-inlet parameters (inlet geometry, efficiency). This is a documented gap. |
| (none) | 1D2D link parameters (1d2dLinkFile) | default | No `1d2d_links.ini` is produced in this pass. Physical link parameters (lateral_factor, etc.) can be added when needed. |
| planning_map cellsize per zone | Per-zone 2D mesh refinement | **missing** | The `ground` layer may carry per-polygon `cellsize` attributes (read by `read_planning_map`), but per-zone mesh refinement is not yet applied in `build_mesh2d`. All 2D cells use the global `grid_2d.dx`/`dy` from the mesh config. |

**Note on coupling type config:** `cfg['coupling']['default_type']` = `'lateral'` for rivers/canals,
`cfg['coupling']['sewer_type']` = `'vertical'` for sewers. The config key documents intent; only
lateral linking is implemented. The sewer vertical value is reserved for the future pass.

---

## Component: DEM (fields.py)

| Data available | Delft3D Attribute | Status | Synthesis Rule |
|---------------|-------------------|--------|----------------|
| DEM GeoTIFF path | `inifield.ini` `bedlevel` InitialField | direct | `datafiletype='GeoTIFF'`, `interpolationmethod='averaging'`, `averagingtype='mean'` |
| DEM GeoTIFF | `StorageNode.streetlevel` / `.bedlevel` | derive | DEM sampled at WGS84 lon/lat via rasterio; see refine_node_levels |
| DEM GeoTIFF | `Boundary` / outfall water level (`boundaries.bc`) | derive | Outfall Constant.datablock updated to DEM_surface |
| (none) | 1D bedlevel field (`*1d.ini`) | **missing** | A 1D initial bedlevel field file interpolated from the DEM onto branch nodes is not produced in this pass. Bedlevels for 1D branches come exclusively from the cross-section `BedElev_m` field (or zero datum). |
| (none) | 2D friction spatial field | **missing** | Spatially varying Manning n for 2D cells (from `cat_landuses` catalog) is not yet wired. All 2D roughness uses the global Manning n from cross-section friction definitions. |

**DEM node refinement depth-zero fallback:**
When `prior_depth = prior (streetlevel - bedlevel)` is not a positive number (e.g. because
InvElev_m/RimElev_m are absent, inverted, or zero), the refinement uses `depth = 0.0`.
This means `bedlevel = DEM_surface` (invert == surface). This mirrors SWMM
`refine_elevations`' `invert = dem_elev - (max_depth or 0.0)` exactly and is intentional
SWMM-parity behavior, not an error.

---

## Component: Structure Placement (structures.py, observations.py)

| Attribute | Status | Note |
|-----------|--------|------|
| Branch snap: nearest branch by `line.project(point)` | direct | All structures (pump, weir, orifice) snap to nearest branch; chainage = `line.project(metric_point)` |
| Max-distance cutoff | **missing** | There is no maximum snap distance. A structure drawn far from any branch will still snap (with potentially large chainage error). A configurable `max_snap_dist_m` threshold is a documented improvement. |
| Culvert | **missing** | Culvert conversion is intentionally omitted (gap D13). No culvert CSV definition exists in the dataset. |

---

## Component: Rainfall / Scenario Forcing

| Data | Delft3D Attribute | Status | Synthesis Rule |
|------|-------------------|--------|----------------|
| (none) | `boundaries.bc` Constant values | default | Placeholder: FixedStage -> Elev_m -> 0.0 |
| (none) | `rainfall.bc` content | default | Empty `ForcingModel(filepath='rainfall.bc')` |
| (none) | `.bui` hyetograph file | **missing** | Authored separately by the scenario module; referenced from the D-RR model |
| ground polygons | `rain_mask.pol` (targetmaskfile) | direct | Ground polygon rings -> PolyFile |
| (none) | Spatially distributed rainfall values | **missing** | The `[Meteo]` block in forcing.ext references `targetmaskfile=rain_mask.pol` and `forcingfile=rainfall.bc`. The scenario module fills `rainfall.bc` with actual rainfall intensities at run time. |

---

## Tooling Gap: hydrolib-core 1.0.1 Meteo targetmaskfile Round-Trip

**Problem:** Saving a `forcing.ext` that contains a `[Meteo]` block with
`targetmaskfile = <PolyFile object>` works correctly in hydrolib-core 1.0.1 — the file is
written and the `.pol` content is saved alongside. However, **re-loading** the saved
`forcing.ext` via `ExtModel(filepath=...)` or (recursively) via `FMModel(filepath=...)` fails
because the parser re-reads `targetmaskfile` as a plain string path and raises a validation error.

**Workaround implemented:** `validate_model()` tries `FMModel(filepath=...)` first. If it
fails AND `rain_mask.pol` is present (indicating the meteo path), AND the exception message
mentions `targetmaskfile` or `PolyFile`, the failure is treated as the known bug and NOT
reported as a problem. Instead, piece-wise validation is run: each sub-file is parsed
individually, and `rain_mask.pol` is validated separately via `PolyFile(filepath=...)`.

**Impact:** The produced model is valid and can be run by the Delft3D FM binary (which reads
the files directly, not via hydrolib-core). The limitation only affects Python-side
round-trip parsing of `forcing.ext` / `FlowFM.mdu` when a rain mask is present.

**Resolution path:** This should be fixed in a future hydrolib-core release. When fixed, the
workaround in `validate_model` can be removed (the `is_meteo_bug` branch becomes dead code).

---

## Summary of All Missing / Gap Items

| ID | Component | Gap Description | Config Default Used |
|----|-----------|-----------------|---------------------|
| G1 | River/Canal | YZ/ZW measured survey profiles not in dataset | 5-pt trapezoid from Width/Bed/Bank/SlopCoef |
| G2 | River/Canal | Channel cross-section elevations not DEM-refined | Raw CSV BedElev_m/BankElev_m or 0.0 |
| G3 | Lake | Tabulated storage from Vol_m3 not implemented | area-form (Area_ha -> m2, usetable=false) |
| G4 | Lake | Seasonal control levels (NatWtrLvl, WetLvl_m, DryLvl_m) not wired | - |
| G5 | Manhole | Real street storage area not in dataset | `street_storage_factor * area` |
| G6 | Manhole | Loss coefficients (entrance/exit) not wired to StorageNode | cfg defaults 0.5 / 1.0 |
| G7 | Pump | Start/stop suction levels not wired (`numstages=0`) | numstages=0, no stage levels |
| G8 | Weir | Gate opening/multi-opening logic not modeled | single `Weir` with corrcoeff=1.0 |
| G9 | Orifice | Gate control mechanism not modeled | single `Orifice` with corrcoeff=0.63 |
| G10 | Outfall | TIDAL/TIMESERIES boundary types not refined | all -> waterlevelbnd constant |
| G11 | 2D domain | Per-zone cellsize/roughness not applied to mesh | global dx/dy/Manning |
| G12 | 1D2D coupling | Sewer vertical/gully-inlet coupling not wired | sewers excluded from linking |
| G13 | Structure | Culvert conversion omitted (no dataset) | - |
| G14 | Structure | No max-distance cutoff for branch snapping | snap to nearest regardless of distance |
| G15 | NWRW | Per-roof surface/slope type not always in planning-map | cfg defaults closed_paved / sloped |
| G16 | NWRW | Full NWRW area records + DWA tables not filled | topology nodes only |
| G17 | NWRW | Sewer-to-NWRW outlet coupling not implemented | DIMR coupler scaffolded |
| G18 | DEM | 1D bedlevel field (1d.ini) not produced | BedElev_m from CSV only |
| G19 | Rainfall | All rainfall values decoupled (empty slots) | scenario module fills values |
| G20 | Tooling | hydrolib-core 1.0.1 Meteo targetmaskfile round-trip bug | validated piece-wise |
