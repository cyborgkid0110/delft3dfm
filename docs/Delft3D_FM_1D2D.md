# Data Analysis and Component Modeling for a 1D–2D Hydraulic Model of Urban Drainage Infrastructure

**Deliverable:** Comprehensive component-modeling report mapping urban drainage / river-network objects, hydrology and GIS data onto the Delft3D (D-Flow FM) ecosystem, with detailed attribute tables.

**Modeling stack:** D-Flow FM (1D, 2D and 1D2D), D-RR (Rainfall-Runoff), coupled via DIMR; configured/automated through the `hydrolib-core` Python API (`.ini`, `.bc`, `.tim`, `.ext`, `.bui`, `net.nc` files).

**Convention:** `[m AD]` = metres above datum (absolute vertical reference). Attribute field names are given exactly as exposed by `hydrolib-core` (case as documented). `ForcingDataUnion` / `ForcingData` means the attribute may be a constant value **or** a reference to a time series (`.bc`/`.tim`).

---

## Table of Contents

- [1. Executive Summary — How the Four Object Groups Map to Delft3D](#1-executive-summary--how-the-four-object-groups-map-to-delft3d)
- [2. Model Architecture and Coupling (BMI / DIMR)](#2-model-architecture-and-coupling-bmi--dimr)
  - [2.1 The 1D–2D coupling paradigm](#21-the-1d2d-coupling-paradigm)
  - [2.2 DIMR coupling](#22-dimr-coupling)
  - [2.3 BMI accessible variables (verbatim from the Developers Guide, Table 3.1)](#23-bmi-accessible-variables-verbatim-from-the-developers-guide-table-31)
  - [2.4 The `.ini` backbone (`INIBasedModel`)](#24-the-ini-backbone-inibasedmodel)
    - [2.4.1 The `[General]` block — present in every `.ini` file](#241-the-general-block--present-in-every-ini-file)
    - [2.4.2 The `[Global]` block — present in three component files](#242-the-global-block--present-in-three-component-files)
- [3. Group 1 — River, Lake & Canal Network](#3-group-1--river-lake--canal-network)
  - [3.1 Modeling method](#31-modeling-method)
  - [3.2 Network / grid file (`*_net.nc`)](#32-network--grid-file-_netnc)
    - [3.2.1 Mesh1D generation (1D network)](#321-mesh1d-generation-1d-network)
    - [3.2.2 Mesh2D generation (2D grid for lakes / floodplains / streets)](#322-mesh2d-generation-2d-grid-for-lakes--floodplains--streets)
    - [3.2.3 1D2D link generation](#323-1d2d-link-generation)
  - [3.3 Open-channel cross-section definitions](#33-open-channel-cross-section-definitions)
  - [3.4 Friction / roughness (`roughness*.ini`)](#34-friction--roughness-roughnessini)
  - [3.5 Observation cross-sections](#35-observation-cross-sections)
- [4. Group 2 — Urban Drainage System](#4-group-2--urban-drainage-system)
  - [4.1 Modeling method](#41-modeling-method)
  - [4.2 Closed cross-sections for pipes](#42-closed-cross-sections-for-pipes)
  - [4.3 Storage Node (manhole) — `storagenodes.ini`](#43-storage-node-manhole--storagenodesini)
  - [4.4 Hydraulic structures (`structures.ini`)](#44-hydraulic-structures-structuresini)
- [5. Group 3 — Hydrological Data (Rainfall-Runoff, Time Series)](#5-group-3--hydrological-data-rainfall-runoff-time-series)
  - [5.1 Modeling method — the NWRW urban concept](#51-modeling-method--the-nwrw-urban-concept-per-d-rainfall_runoff_user_manualpdf-1118)
  - [5.2 Rainfall event file (`.bui` hyetograph)](#52-rainfall-event-file-bui-hyetograph)
  - [5.3 External forcings (`.ext`, new format)](#53-external-forcings-ext-new-format)
  - [5.4 Time-series forcing files](#54-time-series-forcing-files)
  - [5.5 Observation points (`obs.ini`)](#55-observation-points-obsini)
- [6. Group 4 — GIS Data (DEM, 2D Maps)](#6-group-4--gis-data-dem-2d-maps)
  - [6.1 Modeling method](#61-modeling-method)
  - [6.2 Initial & parameter fields (`inifield.ini`)](#62-initial--parameter-fields-inifieldini)
  - [6.3 Polylines / polygons (`*.pli`, `*.pol`)](#63-polylines--polygons-pli-pol)
  - [6.4 XYZ depth samples (RGFGRID)](#64-xyz-depth-samples-rgfgrid)
  - [6.5 DEM → bed-level workflow (concrete, from the 1D2D tutorial §18)](#65-dem--bed-level-workflow-concrete-from-the-1d2d-tutorial-18)
  - [6.6 1D field file (`*1d.ini`)](#66-1d-field-file-1dini)
- [7. Data Usage Purposes — Hydrology (Objective 3a)](#7-data-usage-purposes--hydrology-objective-3a)
- [8. Data Usage Purposes — GIS (Objective 3b)](#8-data-usage-purposes--gis-objective-3b)
- [9. Master Cross-Reference Table (Objective 4)](#9-master-cross-reference-table-objective-4)
- [10. Source Map (Traceability)](#10-source-map-traceability)
- [11. References (URLs)](#11-references-urls)
  - [11.1 hydrolib-core documentation](#111-hydrolib-core-documentation)
  - [11.2 Deltares PDF manuals (local sources)](#112-deltares-pdf-manuals-local-sources)

---

## 1. Executive Summary — How the Four Object Groups Map to Delft3D

The problem is an integrated 1D–2D hydrological–hydraulic model. The four object groups requested map onto Delft3D concepts as follows:

| # | Real-world object group | Primary Delft3D / D-Flow FM concepts | Configuration file(s) |
|---|---|---|---|
| 1 | **River / Lake / Canal network** | `Mesh1d` (branches + computational nodes) for channels; `Mesh2d` for lakes/floodplains; `Link1d2d` for coupling; open `CrossSection` definitions (YZ/XYZ/ZW); `Friction` | `*_net.nc`, `crsdef.ini`, `crsloc.ini`, `roughness*.ini` |
| 2 | **Urban drainage system** (sewers, manholes, outfalls, structures) | Closed `CrossSection` (circle/rectangle) on `Mesh1d` for pipes; `StorageNode` for manholes; `Structure`s: `Pump`, `Weir`, `Orifice`, `Culvert`, `LongCulvert`, `GeneralStructure`, `Compound` | `crsdef.ini`, `storagenodes.ini`, `structures.ini` |
| 3 | **Hydrology** (rainfall, time series) | D-RR (NWRW urban runoff + meteo stations); `.bui` hyetographs; boundary/lateral/source-sink forcings; `.bc`/`.tim` time series | `.bui`, `.ext`, `.bc`, `.tim`, RR model files |
| 4 | **GIS data** (DEM, 2D maps) | Initial & parameter spatial fields (raster/GeoTIFF/sample/polygon); polylines/polygons for digitizing; XYZ depth samples interpolated onto the grid | `inifield.ini`, `*.pol`/`*.pli`, `*.xyz`, GeoTIFF |

The four spec objectives are addressed in turn:
- **Objective 1 (modeling methods + components):** Sections 3–6, one per group.
- **Objective 2 (key attributes):** Attribute tables in each section.
- **Objective 3 (data usage purposes):** Section 7 (hydrology data) + Section 8 (GIS data).
- **Objective 4 (synthesis + cross-reference tables):** This report; master cross-reference in Section 9.

---

## 2. Model Architecture and Coupling (BMI / DIMR)

### 2.1 The 1D–2D coupling paradigm
D-Flow FM solves the shallow-water equations on a single unstructured mesh that simultaneously hosts a **1D network** (channels, pipes) and a **2D grid** (floodplains, streets, lakes). The two are joined through **1D2D links** defined as "mesh contacts" in the network netCDF file (`§17.7.1`). Per `D-Flow_FM_User_Manual_1D2D.pdf` (§17.7), there are **four** coupling concepts:

| Coupling type | Use case (from manual) | Mechanism |
|---|---|---|
| **1D2D lateral** | A sideways link between the 1D channel and 2D floodplains on the side(s) — "in particular for river modelling". 1D and 2D parts do **not** overlap. | Links along the bank line |
| **1D2D embedded** | Similar to lateral, but for **smaller 1D channels where 2D grid cells overlap the 1D channel** — "in particular for rural/marshland modelling". | Links from 1D nodes to overlying 2D cells |
| **1D2D longitudinal** | 1D channel linked to the 2D grid **in the flow direction** (not lateral), e.g. an upstream 1D river feeding into a 2D river/estuary. | Links following the channel axis |
| **1D2D vertically stacked** | A **vertical link from 2D surface planes down to 1D underground sewer networks** — used for **street inlets (gullies) and manhole cover openings**. Default street-inlet cross-section is rectangular, width **0.2 m** (`Uniformwidth1Dstreetinlets`). | Vertical links from 2D cells to 1D sewer nodes |

> **River-modelling tip (manual §18, Magdalena tutorial):** in large rivers, including the DTM *underneath* a 1D channel double-counts storage (the cross-section already holds it). Best practice: **delete the 2D mesh beneath the 1D channel** and use **lateral 1D2D links** when river width exceeds ~2× the DTM resolution.

### 2.2 DIMR coupling
`DIMR_Technical_reference_Manual.pdf` / `DIMR_User_Manual.pdf`: **DIMR** (Deltares Integrated Model Runner) is "a small programme to run combinations of simulation cores/components, ensuring that data is exchanged at the right timing." The user describes in a **DIMR configuration file** *how components are combined* and *what data is exchanged*; a **mapping file** defines how quantities are mapped between components. Constraints the manual states:
- Each component handles time in its own way; **D-Flow 1D and D-RR must share the same start-date**; coupled components' reference-dates must be equal.
- Typical urban-drainage coupling: **D-RR → D-Flow FM/1D** (runoff timeseries injected as sewer/channel inflow), optionally with **D-RTC** (Real-Time Control) driving structures, run via `run_dimr.bat` / `run_dimr_parallel.bat` (MPI).
- An iterative coupling is implemented between **D-Flow 1D and D-Flow FM** for combined 1D-sewer / 2D-surface models.

**Practical configuration** (`DIMR_User_Manual.pdf` §2.2–2.3) — two execution modes plus a parallel-core variant:

| Mode | Behaviour | Typical urban-drainage use |
|---|---|---|
| **Sequential** | Component 1 runs its full period and produces output, then component 2 runs (optionally using that output); component 2 cannot influence component 1 | e.g. D-Flow FM → D-Water Quality |
| **Parallel** | Both components run together, exchanging data each communication interval until the full period is handled; data flows **both** ways | **Structure controlled on hydrodynamic results** (e.g. pump/gate driven by a water level) — i.e. D-Flow FM + **D-RTC**; also D-Flow FM + D-Waves |
| **Parallel core (MPI)** | A single component (e.g. D-Flow FM) runs across several partitions; `<process>0 1 2</process>` + `<mpiCommunicator>DFM_COMM_DFMWORLD</mpiCommunicator>` | Large 1D2D urban models |

- In a **parallel** simulation exactly **one component is the "master"** (`<start name="dflowfm"/>`, normally the flow component); all others are "slaves" in `<startGroup>` blocks. Execution order during an "update" follows the order in the `<control>` block.
- **Data exchange** is declared in `<coupler>` blocks (unique name; reusable in `<control>`), each naming **source/target components and source/target `itemName`s**. *Currently only scalar quantities are exchanged by DIMR.*
- **Protected file extensions** identify importers: `.mdu` → D-Flow FM, `.md1d` → D-Flow 1D, `settings.json` → D-RTC.

### 2.3 BMI accessible variables (verbatim from the Developers Guide, Table 3.1)
`D-Flow_FM_Developers_Guide.pdf` (§3.4) lists the variables exposed through the **BMI (Basic Model Interface)** for run-time `get_var`/`set_var` — used for online coupling, control and data assimilation. Selected variables most relevant to urban-drainage / 1D2D coupling:

| Variable | Unit | Description | Shape |
|---|---|---|---|
| `s0` / `s1` | m | Water level at start / end of timestep | `ndx` |
| `hs` | m | Water depth at cell centre = `s1 - bl` | `ndx` |
| `vol0` / `vol1` | m³ | Volume at start / end of timestep | `ndx` |
| `sa0` / `sa1` / `satop` | m² | Storage area (start / end / top) | `ndx` |
| `ucx` / `ucy` / `ucz` | m/s | Cell-centre velocity (x / y / z) | `ndkx` |
| `u1` | m/s | Flow velocity at end of timestep (on links) | `lnkx` |
| `frcu` | – | Friction coefficient set by initial fields | `lnx` |
| `bl` | m | Bottom (bed) level, positive upward | `ndx` |
| `bob` | m | Left/right inside lower-side tube (invert) levels | `2, lnx` |
| `wx` / `wy` | m/s | Wind x / y velocity at flow link | `lnx` |
| `sa0`/`sa1`, `tem0`/`tem1` | ppt / °C | Salinity / temperature (start / end) | `ndkx` |
| `zbnd1d2d1` / `zbnd1d2d0` | m | 1D2D boundary 1D water level (new / previous level) | `nbnd1d2d` |
| `zcrest1d2d` | m | 1D2D helper array of crest levels | `nbnd1d2d` |
| `width_1d` | m | Width of 1D (SOBEK) channel ↔ 2D FM coupling | `nbnd1d2d` |
| `qzeta_1d2d` / `qlat_1d2d` / `qtotal_1d2d` | m³ s⁻¹ | 1D2D coupling output discharges (zeta / lateral / total) | `nbnd1d2d` |
| `xk` / `yk` / `zk` | m | Net-node x / y / z coordinates | `numk` |

> New variables can be exposed via the `!$BMIEXPORT` source annotation + the BMI-generator script (§3.5).

**BMI control of hydraulic structures** (`D-Flow_FM_User_Manual.pdf` §18.3, Table 18.1) — addressed by a compound variable name whose `locationid` equals the structure `id`; which fields are available depends on the structure group. This is the mechanism by which **RTC / external controllers drive urban-drainage works at run time**:

| Structure group | Read-write field(s) | Remark |
|---|---|---|
| `pumps` | `Capacity` | Non-staged pumps only; prescribed (not necessarily actual) discharge |
| `weirs` | `CrestLevel` | — |
| `gates` | `CrestLevel`, `GateHeight`, `GateLowerEdgeLevel`, `GateOpeningWidth` | Movable-gate control |
| `generalstructures` | `CrestLevel`, `GateHeight`, `GateLowerEdgeLevel`, `GateOpeningWidth` | Combined weir+gate control |
| `longculverts` | `ValveRelativeOpening` | Valve throttling |
| `sourcesinks` | `Discharge`, `ChangeInSalinity`, `ChangeInTemperature` | Prescribed values |

**BMI access to observations** (§18.4, Table 18.2) — observation points/cross-sections expose **read-only** fields such as `water_level`; "typically used as input to hydraulic triggers in an RTC-coupling." This closes the control loop: observe water level → trigger → set structure field.

### 2.4 The `.ini` backbone (`INIBasedModel`)
All D-Flow FM configuration files share the **INI** structure (`[Header]` blocks of `key = value` lines with optional inline comments and units). In `hydrolib-core` the base class `INIBasedModel` reads/writes/validates every `.ini`-format file — it is the backbone for programmatic model construction and automation in Python.

#### 2.4.1 The `[General]` block — present in **every** `.ini` file
Every `.ini`-format file **begins with a `[General]` block** (class `INIGeneral`) holding file metadata. It always carries at least two keys, plus optional per-file extras:

| Key | Type | Description |
|---|---|---|
| `fileVersion` | str | File-format version (default per file; do not edit manually) |
| `fileType` | str | A **literal** identifying the file (e.g. `crossDef`, `structure`, `roughness`) |

The `fileType` literal and version differ by file. Consolidated:

| File | `[General]` `fileType` | `fileVersion` | Extra `[General]` keys |
|---|---|---|---|
| `crsdef.ini` (cross-section definitions) | `crossDef` | 3.00 | — |
| `crsloc.ini` (cross-section locations) | `crossLoc` | 3.00 | — |
| `roughness*.ini` (friction) | `roughness` | 3.01 | `frictionValuesFile` (.bc for time-varying friction) |
| `storagenodes.ini` | `storageNodes` | 2.00 (hydrolib) / 2.02 (manual) | — *(this file also has a `[Global]` block; `useStreetStorage` + loss coefficients live there — see §2.4.2)* |
| `structures.ini` | `structure` | 3.00 | — |
| `inifield.ini` (initial & parameter fields) | `iniField` | 2.00 | — |
| `*1d.ini` (1D field) | `1dField` | 2.00 | — |
| `*.ext` (external forcings, new) | `extForce` | 2.01 | — |
| `*.bc` (forcings) | `boundConds` | 1.01 | — |
| `obs.ini` (observation points) | `obsPoints` | 2.00 | — |

#### 2.4.2 The `[Global]` block — present in **three** component files
A `[Global]` block declares **default values** applied wherever no per-item override exists. Among the component files in this report, **three files use one**: the **friction/roughness** file, the **1D field** file, and the **storage node** file. *(Note: the `storagenodes.ini` `[Global]` block is documented in `D-Flow_FM_User_Manual_1D2D.pdf` Table C.48 but is **not** exposed by the `hydrolib-core` typed schema — when automating via Python you may need to handle it outside the model class.)*

**Friction file (`FrictGlobal`, `[Global]`)** — default roughness for a named friction variable, used wherever no `[Branch]` override exists:

| `[Global]` key | Type | Description |
|---|---|---|
| `frictionId` | str | Name of the roughness variable |
| `frictionType` | FrictionType | Default roughness type (Chezy / Manning / …) |
| `frictionValue` | float | Default roughness value |

**1D field file (`OneDFieldGlobal`, `[Global]`)** — a uniform default value for a 1D quantity (e.g. initial water level/depth on the 1D network), used wherever no `[Branch]` override exists:

| `[Global]` key | Type | Description |
|---|---|---|
| `quantity` | str | Name of the quantity (e.g. `waterlevel`, `waterdepth`) |
| `unit` | str | Unit of the quantity |
| `value` | float | Global default value for this quantity |

**Storage node file (`[Global]`, per `D-Flow_FM_User_Manual_1D2D.pdf` Table C.48)** — model-wide **manhole loss coefficients** plus the `useStreetStorage` switch; the loss coefficients *"can be overridden by their counterparts in specific `[StorageNode]` sections"*:

| `[Global]` key | Type | Description |
|---|---|---|
| `useStreetStorage` | logical (default `true`) | Whether above `streetLevel` the `streetStorageArea` is used (`true`) or the regular storage area continues (`false`); only for `useTable = false` nodes |
| `angleCount` | int | Number of values in the angle lookup table |
| `angles` | float[] | Angles in lookup table, monotonically increasing 0–180° [deg] |
| `angleLossCoefficient` | float[] | Angle loss coefficients matching `angles` |
| `entranceLossCoefficient` | float | Entrance loss coefficient |
| `exitLossCoefficient` | float | Exit loss coefficient |
| `expansionLossCoefficient` | float | Expansion loss coefficient |

> All remaining component files (`crsdef`, `crsloc`, `structures`, `inifield`, `.ext`, `.bc`, `obs`) have **no `[Global]` block** — after `[General]` they go straight to their per-item blocks. Each per-component section below notes its block layout.

---

## 3. Group 1 — River, Lake & Canal Network

**Source basis:** `D-Flow_FM_User_Manual_1D2D.pdf` (1D channels, 2D grids, 1D2D coupling); hydrolib-core *net/grid*, *cross-sections*, *friction*, *observation cross-section*.

### 3.1 Modeling method
- **Channels/rivers/canals** → 1D **branches** in `Mesh1d`, discretized into computational nodes.
- **Lakes / floodplains / inundation areas** → `Mesh2d` cells.
- **Channel ↔ floodplain exchange** → `Link1d2d`.
- **Channel conveyance shape** → open cross-section definitions (YZ, XYZ, or ZW) placed by `CrossSection` location.
- **Flow resistance** → `Friction` model (global + per-branch).

### 3.2 Network / grid file (`*_net.nc`)

| Class | Role | Key attributes / arrays |
|---|---|---|
| `Network` | Top container combining 1D, 2D and links; holds projection (Cartesian/spherical) | `mesh1d`, `mesh2d`, `link1d2d` |
| `Mesh1d` | 1D topology | `branches` (Branch dict); `network1d_node_id/x/y`; `mesh1d_node_x/y`; `mesh1d_edge_nodes`; `mesh1d_node_branch_id`, `mesh1d_node_branch_offset` |
| `Mesh2d` | 2D unstructured grid | `mesh2d_node_x/y`; `mesh2d_edge_nodes`; `mesh2d_face_nodes`; `mesh2d_node_z` / `mesh2d_face_z` (bathymetry) |
| `Link1d2d` | 1D–2D coupling | `link1d2d` (index pairs); `link1d2d_contact_type`; `link1d2d_id` |
| `Branch` | A single channel with geometry + discretization | branch geometry, length, discretization points |

> **Grid-generation engine.** In the `hydrolib-core` `Network`, all mesh creation/editing is delegated to the **MeshKernel** library (C++ core with the **`meshkernel` Python** binding). `Network.__init__()` instantiates it with the projection: `mk.MeshKernel(projection=CARTESIAN | SPHERICAL)`. Two generation routes exist: **(a) programmatic** via hydrolib-core / `meshkernel` (below), and **(b) interactive** via the **RGFGRID** GUI, which exports a D-Flow FM grid as UGRID `*_net.nc` (`File → Export → UGRID (D-Flow FM)`).

#### 3.2.1 Mesh1D generation (1D network)
A 1D mesh is built by defining **branch centerlines** and **discretizing** each into computational nodes:

| Step | API (hydrolib-core / meshkernel) | Description |
|---|---|---|
| 1. Define a branch | `Branch(geometry, branch_offsets, mask)` | `geometry` = Nx2 array of (x, y) along the branch centerline |
| 2. Discretize into nodes | `Branch.generate_nodes(mesh1d_edge_length, structure_chainage, max_dist_to_struc)` | Spaces nodes along the branch (`_generate_1d_spacing`), with **structure-aware** anchoring; stores offsets as distances along the centerline |
| 3. Interpolate coordinates | `Branch.interpolate(distance)` | Returns (x, y) at a given chainage (linear interpolation) |
| 4. Add to the network | `Network.mesh1d_add_branch(...)` → `Mesh1d._add_branch(...)` | Builds network topology (edge nodes joining branch ends), creates mesh1d edges, assigns node ids; `force_midpoint` enforces a minimum node count |

This populates: `mesh1d_node_x/y`, `mesh1d_node_branch_id`, `mesh1d_node_branch_offset`, `mesh1d_edge_nodes`.

**Underlying meshkernel layer:** `Mesh1d(node_x, node_y, edge_nodes)` → `mk.mesh1d_set(mesh1d_input)`; read back with `mk.mesh1d_get()`. (See *MeshKernelPy* `02_mesh1d_basics`.)

#### 3.2.2 Mesh2D generation (2D grid for lakes / floodplains / streets)
The `Mesh2d` class offers several generators plus refinement and clipping, all backed by MeshKernel:

| Operation | API (hydrolib-core) | MeshKernel call | Purpose |
|---|---|---|---|
| **Rectilinear** grid | `Mesh2d.create_rectilinear(extent, dx, dy)` | `curvilinear_compute_rectangular_grid()` (+ convert to unstructured) | Structured grid within bbox `(xmin, ymin, xmax, ymax)` |
| **Triangular** grid | `Mesh2d.create_triangular(geometry_list)` / `Network.mesh2d_create_triangular_within_polygon()` | `mesh2d_make_triangular_mesh_from_polygon()` | Unstructured triangular grid inside a polygon |
| **Refine** | `Mesh2d.refine(polygon, level, parameters)` | `mesh2d_refine_based_on_polygon()` / `mesh2d_refine_based_on_samples()` | Adaptive subdivision in a polygon; `MeshRefinementParameters` controls type, smoothing iterations, max-Courant, directional flags |
| **Clip** | `Mesh2d.clip(geometrylist, deletemeshoption, inside)` | `mesh2d_delete()` | Remove cells outside (or inside) a polygon; handles holes via separator values |

Refinement parameters use **`MeshRefinementParameters`**; geometry inputs use **`GeometryList`**. Common urban workflow: rectilinear/triangular base grid → **refine** around streets/channels → **clip** to the catchment/floodplain outline → interpolate DEM bed level (§6.5).

**Interactive (RGFGRID) alternative** — `RGFGRID_User_Manual.pdf`: draw **splines** → *Operations → Change Splines into Grid* (or **Grow Grid from Splines**) → **Refine grid** (incl. Casulli refinement, also for triangular grids) → **Orthogonalise grid** (quality step) → export as UGRID `*_net.nc`. RGFGRID also imports/interpolates `.xyz` DEM samples (§6.4) and saves the grid enclosure `.enc`.

#### 3.2.3 1D2D link generation
After 1D and 2D meshes exist, links (mesh "contacts") are generated:

| Coupling (see §2.1) | API (hydrolib-core) | MeshKernel contacts call |
|---|---|---|
| 1D→2D (single nearest) | `Network.link1d2d_from_1d_to_2d(branchids, polygon)` → `Link1d2d._link_from_1d_to_2d()` | `contacts_compute_single()` / `contacts_compute_multiple(node_mask)` |
| embedded (point-based) | `Link1d2d._link_from_2d_to_1d_embedded()` | `contacts_compute_with_points()` |
| lateral (boundary-based) | `Link1d2d._link_from_2d_to_1d_lateral()` | `contacts_compute_boundary()` |

Output arrays: `link1d2d` (Nx2 node-index pairs), `link1d2d_id`, `link1d2d_contact_type`. Retrieve via `mk.contacts_get()`.

### 3.3 Open-channel cross-section definitions
Definitions live in `crsdef.ini`; their placement on a branch lives in `crsloc.ini`.

> **File layout** — `crsdef.ini`: `[General]` (`fileType=crossDef`) → one `[Definition]` block per cross-section. `crsloc.ini`: `[General]` (`fileType=crossLoc`) → one `[CrossSection]` block per placement. **No `[Global]` block** in either.

**`YZCrsDef`** — natural/irregular open channel (vertical-segmented conveyance):

| Attribute | Type | Description |
|---|---|---|
| `id` | str | Unique definition id |
| `type` | `"yz"` | Must read `yz` |
| `yzCount` | int | Number of YZ-coordinates |
| `yCoordinates` | List[float] | Monotonic-increasing transverse y [m] |
| `zCoordinates` | List[float] | Bed elevations z [m AD] |
| `conveyance` | str | `lumped` or `segmented` (default `segmented`) |
| `sectionCount` | int | Number of roughness sections (default 1) |
| `frictionPositions` | List[float] | Start/end of roughness sections |
| `frictionIds` / `frictionTypes` / `frictionValues` | List | Per-section roughness |
| `thalweg` | float | Transverse alignment of deepest point |

**`XYZCrsDef`** — like YZ but with explicit x,y,z coordinates (georeferenced): adds `xCoordinates`, `yCoordinates`, `zCoordinates`, `xyzCount`, optional `branchId`.

**`ZWCrsDef` / `ZWRiverCrsDef`** — tabulated level–width (good for rivers w/ floodplains):

| Attribute | Type | Description |
|---|---|---|
| `id`, `type` | str, `"zw"`/`"zwRiver"` | Identifier / type |
| `numLevels` | int | Number of table rows |
| `levels` | List[float] | Monotonic heights [m AD] |
| `flowWidths` | List[float] | Conveying width at each level [m] |
| `totalWidths` | List[float] | Total (incl. storage) width [m] |
| `mainWidth`, `fp1Width`, `fp2Width` | float | Main + floodplain-1/2 widths (`zwRiver`) |
| `leveeCrestlevel`, `leveeBaseLevel`, `leveeFlowArea`, `leveeTotalArea` | float | Levee geometry (`zwRiver`) |

**`CrossSection` (location, `crsloc.ini`)**: `id`, `branchId`, `chainage`, `x`, `y`, `shift` (vertical shift of the definition, +up, default 0), `definitionId`.

### 3.4 Friction / roughness (`roughness*.ini`)
`FrictionType` enum: **Chezy, Manning, wallLawNikuradse, WhiteColebrook, StricklerNikuradse, Strickler, deBosBijkerk**.

> **File layout** — one of **three** component files with a `[Global]` block (the others: 1D field §6.6, storage nodes §4.3). Order: `[General]` → `[Global]` (defaults) → `[Branch]` (per-branch overrides). The container class is `FrictionModel` (`general`, `global_` list, `branch` list).

| Block | Class | Key attributes |
|---|---|---|
| **`[General]`** | `FrictGeneral` | `fileVersion` (3.01), `fileType` (`roughness`), `frictionValuesFile` (.bc for time-varying friction) |
| **`[Global]`** | `FrictGlobal` | `frictionId` (variable name), `frictionType`, `frictionValue` — **default used wherever no `[Branch]` override exists** |
| **`[Branch]`** | `FrictBranch` | `branchId`, `frictionType`, `functionType` (`constant`/`timeSeries`/`absDischarge`/`waterLevel`), `numLevels`, `levels`, `numLocations`, `chainage`, `frictionValues` |

### 3.5 Observation cross-sections
Used to **extract total flow (discharge) through a river/canal cross-section** during simulation. Defined by `name` + either (`branchId`, `chainage`) for 1D, or a coordinate polyline (`numCoordinates`, `xCoordinates`, `yCoordinates`) crossing 2D/1D2D. Output goes to the his-file time series.

---

## 4. Group 2 — Urban Drainage System

**Source basis:** `D-Flow_FM_User_Manual_1D2D.pdf` (sewers, outfalls, manholes); hydrolib-core *structure overview*, *structure .ini*, *storagenode*, *cross-section* (closed), *friction*.

### 4.1 Modeling method
- **Sewer/storm pipes** → 1D branches with **closed** cross-sections (`CircleCrsDef`, or `RectangleCrsDef` with `closed=yes`), with wall friction from the `Friction` model.
- **Manholes / inspection chambers** → `StorageNode` on connection nodes (street + chamber storage; surcharge/flooding behaviour).
- **Outfalls** → boundary node (Group 3) or 1D2D link to a 2D receiving water.
- **Hydraulic works** (pumps, weirs, gates, culverts) → `Structure`s on branches.

### 4.2 Closed cross-sections for pipes

| Class | Type | Key attributes |
|---|---|---|
| `CircleCrsDef` | `circle` | `id`, `diameter` [m], `frictionId`/`frictionType`/`frictionValue`, `thalweg` |
| `RectangleCrsDef` | `rectangle` (box culvert/conduit) | `id`, `width` [m], `height` [m], `closed` (`yes`=closed conduit), friction fields, `thalweg` |

### 4.3 Storage Node (manhole) — `storagenodes.ini`

> **File layout** (per `D-Flow_FM_User_Manual_1D2D.pdf` Table C.48) — `[General]` (`fileType=storageNodes`, `fileVersion=2.02`) → **`[Global]`** (model-wide `useStreetStorage` switch + manhole entrance/exit/expansion/angle **loss coefficients**) → one `[StorageNode]` block per manhole. The per-node geometry (`bedLevel`, `area`, …) is in `[StorageNode]`, and a node may **override the Global loss coefficients** locally. See the `[Global]` attribute table in §2.4.2. *(The `hydrolib-core` typed model exposes `[General]`+`[StorageNode]` but not this `[Global]` block.)*

| Attribute | Type | Description |
|---|---|---|
| `id` | str | Unique storage-node id |
| `name` | str | UI long name |
| `manholeid` | str (opt) | Manhole this compartment belongs to |
| `nodetype` | enum (opt) | `inspection` / `soakawayDrain` / `compartment` / `unspecified` |
| `nodeid` | str | Connection node the storage sits on |
| `usetable` | bool | `false`=simple (area), `true`=tabulated storage |
| `bedlevel` | float | Bed level of storage [m AD] |
| `area` | float | Storage area bedLevel→streetLevel [m²] |
| `streetlevel` | float | Street/ground level [m AD] — surcharge threshold |
| `streetstoragearea` | float | Storage area above streetLevel (ponding) [m²] |
| `storagetype` | enum | reservoir / closed |
| `numlevels` | int | Rows in tabulated storage |
| `levels` | List[float] | Levels [m] (tabulated) |
| `storagearea` | List[float] | Areas at levels [m²] (tabulated) |
| `interpolate` | enum | `linear` or `block` |
| `angleCount`, `angles`, `angleLossCoefficient`, `entranceLossCoefficient`, `exitLossCoefficient`, `expansionLossCoefficient` | int/float[]/float | *(optional)* Per-node **override** of the `[Global]` manhole loss coefficients (§2.4.2) |

> Manhole flooding logic: water rising above `streetlevel` enters `streetstoragearea` (street ponding); this is the key coupling point to 2D surface flooding.

### 4.4 Hydraulic structures (`structures.ini`)

> **File layout** — `[General]` (`fileType=structure`, `fileVersion=3.00`) → one `[Structure]` block per structure (each with `id`, `name`, `type` + type-specific fields). **No `[Global]` block.**

**Location (all structures)** — base attributes: either (`branchid`, `chainage`) **or** (`numcoordinates`, `xcoordinates`, `ycoordinates`) **or** `polylinefile`.

#### Pump (pumping station)
| Attribute | Type | Description |
|---|---|---|
| `capacity` | ForcingDataUnion | Discharge capacity [m³/s] (constant or time series) |
| `orientation` | enum | `positive` / `negative` flow direction |
| `controlside` | str | `suctionSide` / `deliverySide` / both |
| `numstages` | int | Number of pump stages |
| `startlevelsuctionside` / `stoplevelsuctionside` | List[float] | Switch-on/off levels (suction) [m AD] |
| `startleveldeliveryside` / `stopleveldeliveryside` | List[float] | Switch-on/off levels (delivery) [m AD] |
| `numreductionlevels`, `head`, `reductionfactor` | int/List | Capacity-reduction curve vs. head |

#### Weir
| Attribute | Type | Description |
|---|---|---|
| `crestlevel` | ForcingDataUnion | Crest elevation [m AD] |
| `crestwidth` | float | Crest width [m] |
| `corrcoeff` | float | Discharge (correction) coefficient |
| `allowedflowdir` | enum | both / positive / negative / none |
| `usevelocityheight` | bool | Include velocity head |

#### Orifice (gated intake/outlet)
| Attribute | Type | Description |
|---|---|---|
| `crestlevel` | ForcingDataUnion | Sill elevation [m AD] |
| `crestwidth` | float | Opening width [m] |
| `gateloweredgelevel` | ForcingDataUnion | Gate lower edge elevation [m AD] (controls opening) |
| `corrcoeff` | float | Discharge coefficient (default 1.0) |
| `usevelocityheight` | bool | Include velocity head (default true) |
| `uselimitflowpos` / `limitflowpos` | bool/float | Cap positive discharge [m³/s] |
| `uselimitflowneg` / `limitflowneg` | bool/float | Cap negative discharge [m³/s] |

#### Culvert (road/embankment crossing)
| Attribute | Type | Description |
|---|---|---|
| `leftlevel` / `rightlevel` | float | Upstream / downstream invert elevation [m AD] |
| `csdefid` | str | Cross-section definition (shape) id |
| `length` | float | Culvert length [m] |
| `inletlosscoeff` / `outletlosscoeff` | float | Entrance / exit loss coefficients |
| `valveonoff` | bool | Valve present |
| `valveopeningheight` | ForcingDataUnion | Valve opening height [m] |
| `numlosscoeff`, `relopening`, `losscoeff` | int/List | Valve loss-vs-opening curve |
| `bedfrictiontype` / `bedfriction` | enum/float | Bed friction inside culvert |
| `subtype` | enum | `culvert` / `invertedSiphon` |
| `bendlosscoeff` | float | Bend loss (inverted siphon) |
| `allowedflowdir` | enum | Flow direction control |

#### LongCulvert (long crossing with profile)
`zcoordinates` (elevation profile [m AD]), `width`, `height`, `frictiontype`, `frictionvalue`, `valverelativeopening`, `csdefid`, `allowedflowdir`.

#### GeneralStructure (universal weir/gate)
Composite geometry for combined weir+gate behaviour: upstream/downstream widths and levels (`upstream1width/level`, `upstream2width/level`, `downstream1width/level`, `downstream2width/level`), `crestwidth`, `crestlevel`, `crestlength`, `gateloweredgelevel`, `gateheight`, `gateopeningwidth`, `gateopeninghorizontaldirection`, and eight directional flow coefficients (`pos/neg` × `free/drown` × `gate/weir`flowcoeff), `usevelocityheight`.

#### Compound
Groups several structures at one location: `numstructures`, `structureids` (list).

> **Bridge** and **Dambreak** also exist (river/embankment-failure use) with attributes such as `csdefid`/`inletlosscoeff` (Bridge) and `crestlevelini`/`breachwidthini`/`t0`/`timetobreachtomaximumdepth`/`ucrit` (Dambreak).

---

## 5. Group 3 — Hydrological Data (Rainfall-Runoff, Time Series)

**Source basis:** `D-Rainfall_Runoff_User_Manual.pdf` (NWRW urban runoff, meteo stations, evaporation); hydrolib-core *RR file models*, *external forcings (.ext)*, *.bc forcing*, *.tim*, *RR meteo (.bui)*, *observation points*.

### 5.1 Modeling method — the NWRW urban concept (per `D-Rainfall_Runoff_User_Manual.pdf` §1.1.18)
- **Urban rainfall–runoff** → D-RR using the **NWRW** concept: a **0D (lumped) rainfall-runoff model** applied to small catchments connected to a sewer system, with typical sewer inflow points **every ~40 m** (Dutch C2100 / NWRW guidelines). It transforms a rainfall time series into a runoff time series used as **inflow into the 1D sewer model**.
- **Processes modelled:** wetting & **surface (depression) storage**, **infiltration** (Horton time-varying formula, on open-paved and unpaved areas), **evaporation**, **runoff delay** (rational-method formula based on distance-to-inflow, slope, geometry), and **dry-weather flow (DWF)** (return flow from households/commerce/industry).
- **Surface schematization:** **4 surface types** (closed paved, open paved, roof, unpaved) × **3 slope classes** (sloped, flat, stretched flat) = **12 area types**; each type carries its own storage and infiltration parameters.
- **2D option:** Delft3D FM 1D2D also supports **rainfall directly on the 2D grid**, with optional per-cell Horton infiltration by land use, and overland flow of runoff to the sewer pipes (or modelling only 1D→street overflow).
- **Rain input** → `.bui` hyetograph per **meteo station** (rain gauge); NWRW nodes reference a meteo station via `ms '<station>'`.
- **Coupling to hydraulics** → RR runoff enters D-Flow FM as **laterals** / **source–sinks** (via DIMR); tidal/river/outfall boundaries enter as **boundary** forcings.

### 5.2 Rainfall event file (`.bui` hyetograph)
| Class | Attribute | Type | Description |
|---|---|---|---|
| `BuiModel` | `number_of_stations` | int | Number of rain gauges |
| | `name_of_stations` | List[str] | Gauge names |
| | `number_of_events` | int | Number of storm events |
| | `seconds_per_timestep` | int | Hyetograph timestep [s] |
| | `precipitation_events` | List[BuiPrecipitationEvent] | The events |
| `BuiPrecipitationEvent` | `start_time` | datetime | Event start |
| | `timeseries_length` | timedelta | Event duration |
| | `precipitation_per_timestep` | List[List[float]] | Depth per station per timestep |

### 5.3 External forcings (`.ext`, new format)

> **File layout** — `[General]` (`fileType=extForce`, `fileVersion=2.01`) → repeated `[Boundary]` / `[Lateral]` / `[SourceSink]` / `[Meteo]` blocks. **No `[Global]` block.**

| Class | Purpose | Key attributes |
|---|---|---|
| `Boundary` | Open boundary (sea level, river inflow, outfall WL) | `quantity`, `nodeid` **or** `locationfile`, `forcingfile` (.bc), `bndwidth1d`, `bndbldepth`, `returntime` |
| `Lateral` | Distributed/point inflow (RR runoff into channel) | `id`, `name`, `locationtype` (`1d`/`2d`/`all`), `nodeid`/`branchid`/`chainage` or `xcoordinates`/`ycoordinates`, `discharge` (ForcingData) |
| `SourceSink` | Point source/sink (e.g. discharge injection) | `id`, `locationfile` or coords, `zsource`/`zsink`, `area`, `discharge`, `salinitydelta`, `temperaturedelta` |
| `Meteo` | Spatial meteorological forcing (rain/evap fields) | `quantity`, `forcingfile`, `forcingfiletype` (bcAscii/uniform/netcdf/arcInfo/spiderweb/polygon…), `interpolationmethod` (nearestNb/linearSpaceTime/constant), `operand`, `extrapolationallowed` |

### 5.4 Time-series forcing files
> **File layout (`.bc`)** — `[General]` (`fileType=boundConds`, `fileVersion=1.01`) → repeated `[Forcing]` blocks. **No `[Global]` block.** (`.tim` is a plain ASCII table with no `[General]`/`[Global]` headers.)

**`.bc` (`ForcingModel`)** — block-based forcing: each `[Forcing]` (`ForcingBase`) has `name`, `function`, `quantityunitpair` (quantity+unit), `datablock`. Subclasses: `TimeSeries` (`timeInterpolation`=linear/block-From/block-To, `offset`, `factor`), `Harmonic`, `Astronomic`, `Constant`, `QHTable` (stage–discharge), `T3D` (vertical profiles).

**`.tim`** — simple ASCII two-column (time, value) series used for discharge, water level and boundary conditions.

### 5.5 Observation points (`obs.ini`)
> **File layout** — `[General]` (`fileType=obsPoints`, `fileVersion=2.00`) → one `[ObservationPoint]` block per point. **No `[Global]` block.**

Output time series at points of interest (typically manholes / pump stations / outfalls):
`name`, `x`/`y` **or** `branchId`+`chainage`, `locationType` (`1d` snap to 1D node / `2d` snap to 2D cell / `all`).

---

## 6. Group 4 — GIS Data (DEM, 2D Maps)

**Source basis:** hydrolib-core *initial & parameter field*, *polyline/polygon*; `RGFGRID_User_Manual.pdf` (.xyz depth points → grid); `D-Flow_FM_User_Manual_1D2D.pdf` / `D-Flow_FM_User_Manual.pdf` (DEM → bed level on 2D grid).

### 6.1 Modeling method
- **DEM → bed level:** interpolate raster/GeoTIFF or `.xyz` sample points onto `Mesh2d` faces/nodes (RGFGRID for `.xyz`; inifield for raster).
- **Spatially varying parameters** (friction, initial depth/level) → parameter/initial fields.
- **Digitizing geometry** (floodplain extents, masks, thin dams, boundaries) → polylines/polygons.

### 6.2 Initial & parameter fields (`inifield.ini`)
> **File layout** — `[General]` (`fileType=iniField`, `fileVersion=2.00`) → repeated `[Initial]` and `[Parameter]` blocks. **No `[Global]` block.**

Container `IniFieldModel` → `general`, `initial` (List[`InitialField`]), `parameter` (List[`ParameterField`]). Both fields share `AbstractSpatialField`:

| Attribute | Type | Description |
|---|---|---|
| `quantity` | str | e.g. `bedlevel`, `frictioncoefficient`, `waterlevel`, `waterdepth` |
| `dataFile` | file | The GIS data source |
| `dataFileType` | enum | `arcinfo` / `GeoTIFF` / `sample` / `1dField` / `polygon` / `netcdf` / `uniform` |
| `interpolationMethod` | enum | `constant` / `triangulation` / `averaging` / `linearSpaceTime` |
| `operand` | enum | How values combine (default `override`) |
| `averagingType` | enum | `mean`/`nearestNb`/`max`/`min`/`invDist`/`minAbs`/`median` |
| `averagingRelSize`, `averagingNumMin`, `averagingPercentile` | num | Cell-averaging controls |
| `locationType` | enum | Target: `1d`/`2d`/`all` (default `all`) |
| `value` | float | Constant value (required when `dataFileType=polygon`) |

### 6.3 Polylines / polygons (`*.pli`, `*.pol`)
`PolyFile` → list of `PolyObject` → header (`name`, `n_rows`, `n_columns`) + `Point`s (`x`, `y`, optional `z`, optional `data`). Used for: floodplain/area digitizing, model boundary lines, thin dams, fixed weirs, DEM clipping masks, observation/cross-section polylines, source/sink/meteo masks.

### 6.4 XYZ depth samples (RGFGRID)
Per `RGFGRID_User_Manual.pdf` (App. A.3): a **`.xyz` sample file** is "a set of disordered x, y, z values given in a sequential list of free-formatted x, y, z values." Workflow notes:
- **Structured (gridded) ArcInfo rasters** can be loaded via *Open Samples (ARC)*; the user gives **row/column refinement factors** that set the resampling block size (a block of samples is averaged into one sample), and can be re-saved as `.xyz`.
- Samples inside a selection **polygon** are the active set for the subsequent interpolation.
- RGFGRID does **not** edit samples; it interpolates them onto grid nodes/faces → `mesh2d_node_z`.
- A **grid enclosure** file (`.enc`) outlines the active computational area.

### 6.5 DEM → bed-level workflow (concrete, from the 1D2D tutorial §18)
`D-Flow_FM_User_Manual_1D2D.pdf` gives an explicit recipe (Magdalena River tutorial):
1. **Add raster samples** of the DEM/DTM (e.g. a **GeoTIFF** `2D_DTM_*.tif`) on the **Bed Level** layer in *Spatial Operations*.
2. **Interpolate** the selected sample set with method **Averaging → SimpleAveraging** (minimum sample points = 1, relative search cell size ≈ 1.01, 2D projection) — *averaging* is chosen because each grid cell contains many DEM samples.
3. **Avoid double-counted storage:** delete the 2D mesh beneath 1D channels (see §2.1 note) and connect with **lateral 1D2D links**.

This corresponds, in the `hydrolib-core`/file API, to an `InitialField`/`ParameterField` with `quantity = bedlevel`, `dataFileType = GeoTIFF` (or `sample`/`arcinfo`), and `interpolationMethod = averaging` (`averagingType = mean`).

### 6.6 1D field file (`*1d.ini`)
While `inifield.ini` (§6.2) maps **2D/raster** spatial data onto the grid, a separate **1D field file** assigns values **along the 1D network** (e.g. initial water level or depth per branch). It is referenced from an `[Initial]`/`[Parameter]` block whose `dataFileType = 1dField`.

> **File layout** — one of the **three** files with a `[Global]` block (the others: friction §3.4, storage nodes §4.3). Order: `[General]` (`fileType=1dField`, `fileVersion=2.00`) → `[Global]` (uniform default) → repeated `[Branch]` blocks (per-branch overrides). Container class `OneDFieldModel`.

| Block | Class | Key attributes |
|---|---|---|
| **`[General]`** | `OneDFieldGeneral` | `fileVersion` (2.00), `fileType` (`1dField`) |
| **`[Global]`** | `OneDFieldGlobal` | `quantity` (e.g. `waterlevel`/`waterdepth`), `unit`, `value` — **uniform default applied where no `[Branch]` override exists** |
| **`[Branch]`** | `OneDFieldBranch` | `branchId`, `numLocations` (0 = uniform on branch), `chainage` (List[float], increasing), `values` (List[float], one per chainage) |

---

## 7. Data Usage Purposes — Hydrology (Objective 3a)

| Data item | Provides | Role in model | Component(s) consuming it |
|---|---|---|---|
| **Hyetograph / rain-gauge station** (`.bui`) | Time-varying rainfall depth per gauge | Meteorological **forcing** that drives D-RR runoff generation (NWRW) | `BuiModel` → D-RR; or `Meteo` block for spatial rain |
| **Evaporation series** | Potential/actual ET | Loss term in RR water balance | D-RR meteo |
| **Time series — discharge** (`.tim`/`.bc`) | Q(t) | Inflow **boundary**/**lateral**/**source** | `Boundary`, `Lateral`, `SourceSink` |
| **Time series — water level** (`.tim`/`.bc`) | h(t) | Downstream/tidal **boundary** (e.g. outfall) | `Boundary` (`waterlevelbnd`) |
| **QH table** (`.bc`) | Rating curve Q–h | Stage-discharge **boundary** | `QHTable` |
| **RR runoff output** | Catchment runoff Q(t) | Coupled **lateral inflow** into the 1D/2D hydraulics via DIMR | `Lateral` |
| **Observation points/cross-sections** | Requested output locations | Define **what/where to record** (levels at manholes, flow through sections) | `ObservationPoint`, observation cross-section |

In short: time series + hyetographs supply **boundary conditions** and **forcing**; RR supplies **internal inflow**; observation definitions supply **output specification**.

---

## 8. Data Usage Purposes — GIS (Objective 3b)

| GIS data item | Provides | Role in model | Component(s) consuming it |
|---|---|---|---|
| **DEM (raster/GeoTIFF/`.xyz`)** | Ground/bed elevation | **Geometry** — bed level on the 2D grid (controls flow paths, storage, flooding) | inifield (`quantity=bedlevel`), RGFGRID `.xyz` → `mesh2d_node_z` |
| **Friction map (raster/polygon)** | Spatial roughness | **Parameter** — friction coefficient per cell/zone | `ParameterField` (`quantity=frictioncoefficient`) |
| **Initial condition map** | Initial WL/depth | **Initial condition** for the solver | `InitialField` (`quantity=waterlevel`/`waterdepth`) |
| **Polygon — floodplain/area extents** | Region boundaries | **Geometry/masking** — define where 2D applies, apply zonal values | `PolyFile`, `Meteo.targetmaskfile`, inifield `polygon` |
| **Polyline — boundaries / thin dams / weirs / cross-sections** | Lines | **Geometry** — boundary placement, flow blocking, output lines | `PolyFile`, boundary `locationfile`, obs cross-section |

In short: DEM → **geometry** (bed level); raster/polygon parameter maps → **spatially distributed parameters**; initial maps → **initial state**; polylines/polygons → **positioning, masking and digitizing** that transfer GIS into the grid.

---

## 9. Master Cross-Reference Table (Objective 4)

| Real-world object | Delft3D concept | hydrolib-core class | File | Most important attributes |
|---|---|---|---|---|
| River / canal reach | 1D branch + open cross-section | `Mesh1d`/`Branch`, `YZCrsDef`/`XYZCrsDef`/`ZWRiverCrsDef`, `CrossSection` | net.nc, crsdef.ini, crsloc.ini | yCoordinates/zCoordinates, levels/flowWidths, definitionId, chainage |
| Lake / floodplain | 2D grid | `Mesh2d` | net.nc | mesh2d_face_nodes, mesh2d_node_z |
| Channel↔floodplain link | 1D2D link | `Link1d2d` | net.nc | link1d2d, link1d2d_contact_type |
| Sewer / storm pipe | Closed 1D cross-section | `CircleCrsDef`/`RectangleCrsDef` | crsdef.ini | diameter / width+height+closed, frictionId |
| Manhole / chamber | Storage node | `StorageNode` | storagenodes.ini | bedlevel, area, streetlevel, streetstoragearea, levels/storagearea |
| Pumping station | Pump structure | `Pump` | structures.ini | capacity, start/stop levels, controlside |
| Weir | Weir structure | `Weir` | structures.ini | crestlevel, crestwidth, corrcoeff |
| Gate / sluice | Orifice | `Orifice` | structures.ini | crestlevel, gateloweredgelevel, crestwidth, limitflow |
| Culvert / siphon | Culvert | `Culvert`/`LongCulvert` | structures.ini | leftlevel/rightlevel, length, csdefid, loss coeffs |
| Combined weir+gate | General structure | `GeneralStructure` | structures.ini | up/down widths+levels, crestlevel, gateloweredgelevel, flow coeffs |
| Multiple works at a point | Compound | `Compound` | structures.ini | numstructures, structureids |
| Flow resistance | Friction model | `FrictGlobal`/`FrictBranch` | roughness.ini | frictiontype, frictionvalue |
| Rainfall (gauge) | Hyetograph / meteo | `BuiModel`, `Meteo` | .bui, .ext | name_of_stations, seconds_per_timestep, precipitation |
| Inflow boundary | Boundary | `Boundary` | .ext + .bc | quantity, nodeid, forcingfile |
| Catchment runoff inflow | Lateral | `Lateral` | .ext | locationtype, nodeid/branchid+chainage, discharge |
| Point source/sink | SourceSink | `SourceSink` | .ext | xcoordinates/ycoordinates, discharge |
| Time series | Forcing | `ForcingModel`/`TimeSeries` | .bc / .tim | function, quantityunitpair, timeInterpolation, datablock |
| Output at manhole/pump | Observation point | `ObservationPoint` | obs.ini | x/y or branchId+chainage, locationType |
| Output of section flow | Observation cross-section | obs cross-section | — | branchId+chainage or polyline coords |
| DEM → bed level | Spatial field (geometry) | `InitialField` (bedlevel) / RGFGRID | inifield.ini / .xyz | quantity, dataFile, dataFileType, interpolationMethod |
| Friction map | Parameter field | `ParameterField` | inifield.ini | quantity, dataFileType, averagingType |
| Floodplain / mask / boundary line | Polyline/polygon | `PolyFile`/`PolyObject`/`Point` | .pol / .pli | x, y, z, name |

---

## 10. Source Map (Traceability)

Both source families were directly consulted: the **hydrolib-core** pages were live-fetched for exact attribute schemas, and the **PDF manuals were text-extracted (`pdftotext`) and mined** for the theory/values cited below (sections/tables noted).

| Topic | PDF source (section mined) | hydrolib-core reference |
|---|---|---|
| 1D2D architecture, 4 coupling concepts, street inlets (0.2 m), DTM-under-channel caveat | D-Flow_FM_User_Manual_1D2D.pdf (§17.7, §18) | — |
| BMI variable table (`s1`,`hs`,`vol1`,`ucx`,`bl`,`bob`,`qlat_1d2d`…) | D-Flow_FM_Developers_Guide.pdf (Table 3.1, §3.4–3.5) | — |
| BMI structure-control fields (pumps→Capacity, gates→GateLowerEdgeLevel…) & obs `water_level` | D-Flow_FM_User_Manual.pdf (§18.3–18.4, Tables 18.1–18.2) | — |
| DIMR coupling, mapping file, shared start-date rule | DIMR_Technical_reference_Manual.pdf (§3–4) | — |
| DIMR sequential/parallel/MPI modes, master-slave, `<coupler>` items, protected extensions | DIMR_User_Manual.pdf (§2.2–2.3) | — |
| .ini backbone | — | base/ini (`INIBasedModel`) |
| Network / grid (structure) | D-Flow_FM_User_Manual_1D2D.pdf | dflowfm/topology-network/net |
| **Mesh1D / Mesh2D / 1D2D-link generation API** | RGFGRID_User_Manual.pdf (splines→grid, refine, orthogonalise; §6.1) | net (Branch/Mesh2d methods) + MeshKernelPy |
| Cross-sections | D-Flow_FM_User_Manual_1D2D.pdf | dflowfm/cross-sections/crosssection |
| Friction | — | dflowfm/cross-sections/friction |
| Storage node (manhole) | D-Flow_FM_User_Manual_1D2D.pdf | dflowfm/topology-network/storagenode |
| Structures | D-Flow_FM_User_Manual_1D2D.pdf | dflowfm/external-forcing/structures/structure(-overview) |
| Rainfall-Runoff / NWRW (12 area types, Horton, DWF, 40 m spacing) | D-Rainfall_Runoff_User_Manual.pdf (§1.1.18 Urban NWRW, §1.2.8 NWRW layer) | rr/rr, rr/meteo |
| External forcings / .bc / .tim | — | dflowfm/external-forcing/ext, /forcing, attribute-files/tim |
| Observation points / cross-sections | — | dflowfm/topology-network/observationpoint(-crosssection) |
| Spatial fields / DEM→bedlevel (GeoTIFF + SimpleAveraging recipe) | D-Flow_FM_User_Manual_1D2D.pdf (§18 tutorial), D-Flow_FM_User_Manual.pdf | dflowfm/external-forcing/inifield |
| `.xyz` samples, ArcInfo resampling, `.enc` enclosure | RGFGRID_User_Manual.pdf (App. A.3, A.7) | — |
| Polylines / polygons | — | dflowfm/attribute-files/polyfile |

> Attribute names and types in the tables above were extracted from the current `hydrolib-core` reference documentation (deltares.github.io/HYDROLIB-core, `latest`). Theory, BMI variable names, NWRW parameters, coupling rules and the DEM workflow were extracted directly from the Deltares PDF manuals (text-mined with `pdftotext`), with sections cited above.

---

## 11. References (URLs)

### 11.1 hydrolib-core documentation
| Topic | Section(s) | URL |
|---|---|---|
| INI format / `INIBasedModel` (`[General]` block) | 2.4 | https://deltares.github.io/HYDROLIB-core/latest/reference/base/ini/ |
| Net / grid file (Mesh1d, Mesh2d, Link1d2d) + generation API | 3.2–3.2.3 | https://deltares.github.io/HYDROLIB-core/latest/reference/dflowfm/topology-network/net/ |
| MeshKernelPy — Mesh1d basics example | 3.2.1 | https://deltares.github.io/MeshKernelPy/examples/02_mesh1d_basics.html |
| MeshKernelPy — library (mesh2d generation/refine/clip, contacts) | 3.2.2–3.2.3 | https://deltares.github.io/MeshKernelPy/ |
| Cross-section files (open & closed) | 3.3, 4.2 | https://deltares.github.io/HYDROLIB-core/latest/reference/dflowfm/cross-sections/crosssection/ |
| Friction / roughness (`[General]`+`[Global]`+`[Branch]`) | 3.4 | https://deltares.github.io/HYDROLIB-core/latest/reference/dflowfm/cross-sections/friction/ |
| Observation cross-section files | 3.5 | https://deltares.github.io/HYDROLIB-core/latest/reference/dflowfm/topology-network/observationcrosssection/ |
| Storage node `.ini` (manholes) | 4.3 | https://deltares.github.io/HYDROLIB-core/latest/reference/dflowfm/topology-network/storagenode/ |
| Structure overview | 4.4 | https://deltares.github.io/HYDROLIB-core/latest/reference/dflowfm/external-forcing/structures/structure-overview/ |
| Structure `.ini` files | 4.4 | https://deltares.github.io/HYDROLIB-core/latest/reference/dflowfm/external-forcing/structures/structure/ |
| RR file models (BuiModel) | 5.1–5.2 | https://deltares.github.io/HYDROLIB-core/latest/reference/rr/rr/ |
| The Rainfall Runoff meteo layer (`.bui`) | 5.2 | https://deltares.github.io/HYDROLIB-core/latest/reference/rr/meteo/ |
| External forcings file (new `.ext`) | 5.3 | https://deltares.github.io/HYDROLIB-core/latest/reference/dflowfm/external-forcing/ext/ |
| Forcings `.bc` file | 5.4 | https://deltares.github.io/HYDROLIB-core/latest/reference/dflowfm/external-forcing/forcing/ |
| Timeseries `.tim` files | 5.4 | https://deltares.github.io/HYDROLIB-core/latest/reference/dflowfm/attribute-files/tim/ |
| Observation point files | 5.5 | https://deltares.github.io/HYDROLIB-core/latest/reference/dflowfm/topology-network/observationpoint/ |
| Initial & parameter field files (DEM, params) | 6.2 | https://deltares.github.io/HYDROLIB-core/latest/reference/dflowfm/external-forcing/inifield/ |
| 1D field INI files (`[General]`+`[Global]`+`[Branch]`) | 6.6 | https://deltares.github.io/HYDROLIB-core/latest/reference/dflowfm/mdu/onedfield/ |
| Polyline / polygon files | 6.3 | https://deltares.github.io/HYDROLIB-core/latest/reference/dflowfm/attribute-files/polyfile/ |

### 11.2 Deltares PDF manuals (local sources)
| Document | Used for |
|---|---|
| `D-Flow_FM_Developers_Guide.pdf` | BMI variable list (Table 3.1) |
| `DIMR_Technical_reference_Manual.pdf` | DIMR coupling mechanics |
| `DIMR_User_Manual.pdf` | DIMR config (sequential/parallel/MPI, couplers, protected extensions) |
| `D-Flow_FM_User_Manual_1D2D.pdf` | 1D2D coupling concepts, sewers/manholes, DEM→bedlevel tutorial |
| `D-Flow_FM_User_Manual.pdf` | BMI structure-control & observation fields (§18.3–18.4); bed-level options |
| `D-Rainfall_Runoff_User_Manual.pdf` | NWRW urban runoff concept, meteo stations, evaporation |
| `RGFGRID_User_Manual.pdf` | `.xyz` depth samples → grid interpolation |
