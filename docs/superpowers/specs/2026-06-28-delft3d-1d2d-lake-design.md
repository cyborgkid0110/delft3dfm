# 1D2D Lake Component — Design

**Date:** 2026-06-28
**Status:** Approved (pending written-spec review)
**Scope:** Add a combined 1D + 2D lake component to the Delft3D FM conversion submodule.

## 1. Problem & Goal

Today a lake (`mang_luoi_song_ho_kenh_muong/lakes.csv`, a centroid **Point**) is
converted to a single area-form `StorageNode` (`usetable='false'`, `area = Area_ha x 1e4`).
This is a lumped 0-D reservoir with two fidelity problems:

- **Volume is wrong, not just approximate.** `Area_ha` is the *surface* area; using it as a
  constant prism area over-counts storage (lakes have sloped banks). The surveyed `Vol_m3`
  and `BedArea_ha` are discarded (gap G3).
- **No 2D inundation / no 1D2D exchange.** A lumped node cannot spill across a surface or
  exchange laterally with the 2D floodplain.

The authoritative spec (`docs/Delft3D_FM_1D2D.md` §3.1, §3.2.2, §9) models a lake as **2D
`Mesh2d` cells** joined to the 1D network via **`Link1d2d`**. The goal of this design is a
**combined 1D2D lake**: a 1D storage node (correct volume) that exchanges water with the
surrounding 2D mesh through a perimeter ring of 1D2D links, spilling only when the lake
level exceeds the surrounding terrain.

## 2. Workflow (manual-based)

1. **1D storage node** — the lake core is a 1D `StorageNode`; with `useTable=true` it carries
   a `levels`→`storageArea` table so the software interpolates the correct volume.
2. **Avoid double-counting** — the 2D cells inside the lake boundary are removed, so the lake
   volume (and rainfall) is not counted twice (once in 2D, once in the 1D node).
3. **Spillway ring** — the 1D lake node connects to the adjacent 2D cells around the polygon
   perimeter via 1D2D links (flow through links is a weir formulation).
4. **Overflow mechanism** — the lake is a closed reservoir until its level exceeds the
   neighboring terrain, then it spills over the ring onto the 2D surface.

## 3. Data Sources & Lake Identification

- **Hydraulic data:** `lakes.csv` stays **as-is** (centroid Point layer): `Name`, `Area_ha`,
  `BedArea_ha`, `Vol_m3`, `BedElev_m`, `CrestElv`/`BankElev_m`, etc. **No dataset schema change.**
- **Boundary polygon:** taken from the existing planning-map **`ground`** layer — any polygon
  whose `landuse == "lake"`. **No planning-map schema change** (reuses the existing `landuse`
  attribute).
- **Match rule:** each `lakes.csv` row is paired with the lake polygon whose geometry
  **contains the lake centroid**.
- **Unmatched fallback:** a lake row with no containing `landuse=='lake'` polygon falls back to
  the current **area-form 1D StorageNode** (no 2D linkage) and logs a warning. Adding 2D lakes
  never breaks existing point-only lakes.

## 4. Storage Representation — the `useTable` switch

A config flag `cfg['storage']['lake_use_table']` (with optional per-row override) selects which
data source wins. Clean either/or:

### 4.1 `useTable=false` — prism from `Vol_m3` only
- `bedlevel = BedElev_m`
- `streetlevel = CrestElv` -> `BankElev_m` -> `bedlevel + 3.0` (existing precedence)
- `area = Vol_m3 / (streetlevel - bedlevel)` — constant area, vertical walls. Total volume at
  the crest equals `Vol_m3` exactly.
- `BedArea_ha` / `Area_ha` ignored.
- This replaces today's `area = Area_ha x 1e4` (the existing over-count bug).

### 4.2 `useTable=true` — tabulated stage-area from geometry, `Vol_m3` unused
- Two-row table:
  - level `BedElev_m` -> `storageArea = BedArea_ha x 1e4` (bottom)
  - level `CrestElv`/bank -> `storageArea = Area_ha x 1e4` (top)
- `usetable='true'`, `numlevels=2`, `levels=[...]`, `storagearea=[...]`. D-Flow FM interpolates
  volume (trapezoidal) between the levels, honoring sloped banks.
- **Guards:**
  - `BedArea_ha` absent/zero -> use `Area_ha` for both rows (degenerates to a prism).
  - crest <= bed -> nudge crest to `bed + epsilon` so levels are strictly increasing
    (hydrolib-core requires monotonic levels).

Both branches set `storagetype='reservoir'` and register the node in the `CoordRegistry`
(so DEM refinement still finds it, per the existing dual-registration rule).

### 4.3 Missing-data warnings

**Existing convention (verified):** converters use `print(f"  <module>: ...")` for skipped
rows; the mesh layer uses `warnings.warn(...)` for exceptions. The current converters log
**row drops** (`SKIP`) but are **silent on field-level fallbacks** — a missing `Area_m2`,
`streetlevel`, etc. quietly uses a default with no message.

**New behavior — warn on every fallback in the lake path**, e.g.:
- `storage.py: lake 'X' missing Vol_m3 - falling back to area-form from Area_ha`
- `storage.py: lake 'X' missing BedArea_ha - useTable bottom area falls back to Area_ha (prism)`
- `storage.py: lake 'X' missing CrestElv/BankElev_m - streetlevel defaulted to bedlevel+3.0`
- `storage.py: lake 'X' no 'landuse==lake' polygon contains centroid - 2D linkage skipped, modeled as 1D point storage`
- `storage.py: lake 'X' crest <= bed - nudged crest to bed+0.01 for monotonic table`

Plus a consolidated summary count: `storage.py: N lake(s) used >=1 fallback`.

**Scope:** lake path only in this design. The broader silent-fallback gap across all
converters (manholes, branches, structures, boundaries) is recorded as a **documented
follow-up**, not expanded here.

## 5. 2D Mesh — Unstructured Triangular (generate-then-clip)

The 2D mesh switches from rectilinear to **unstructured triangular**. Verified in this install
(hydrolib-core 1.0.1 / meshkernel 8.3.0):

| API | Status | Verified behavior |
|---|---|---|
| `Network.mesh2d_create_triangular_within_polygon(GeometryList)` | exists | Triangulates the **polygon outline only** — coarse, no interior fill density |
| `Network.mesh2d_refine_mesh(GeometryList, level, parameters)` | exists | Densifies: level 3 -> 5 to 145 nodes. **Required** after create |
| `Network.mesh2d_clip_mesh(GeometryList, deletemeshoption, inside)` | exists | Removes cells; used to punch lake holes |

### 5.1 Holes-at-generation does NOT work (verified)
Passing `ground.difference(lakes)` (a polygon with interior rings, separator-encoded) to
`create_triangular`/`refine` **does not honor the holes**. The leak **worsens with
refinement**: nodes-inside-lake = 1 (level 1) -> 13 (level 4). The triangulator fills the
region and ignores the interior ring. **This approach is rejected.**

### 5.2 Adopted strategy: generate-then-clip
1. Triangulate the **solid ground** polygon (`create_triangular`). MultiPolygon-safe —
   triangulation handles it natively (fixes the old rectilinear MultiPolygon clip gap).
2. `mesh2d_refine_mesh(ground, level)` to target resolution.
3. For each matched lake: `mesh2d_clip_mesh(lake_polygon, INSIDE_NOT_INTERSECTED, inside=True)`
   to punch the hole. Note `inside=True` (delete-inside) — opposite polarity to the existing
   ground clip (`inside=False`); the lake is a true subset, so the no-op/degenerate case the
   existing code warns about does not apply.
4. **Post-clip ground-only guard:** assert no 2D face center lies inside any lake polygon; warn
   and count if any straddling cell remains (defensive against coarse-mesh-vs-small-lake).

**Verified end-to-end:** solid-ground (refined, 545 nodes) -> clip lake -> 532 nodes, 988 faces,
**0 face centers inside the lake**, **0 faces outside ground-minus-lake**. The ring cells are
guaranteed ground-only.

### 5.3 Config
- `cfg['mesh']['grid_2d']['type']: triangular` (default). Rectilinear kept as a fallback behind
  the same `type` switch — existing behavior is not lost.
- `cfg['mesh']['refine']['levels']` calibrated so triangular cell size approximates the old
  `dx`/`dy`. `dx`/`dy` retained for the rectilinear path.

## 6. Lake 1D Node + Spillway Ring

**Constraint:** a `StorageNode` attaches to a 1D mesh node by coordinate
(`nodeid = f"{x:.6f}_{y:.6f}"`), but mesh1d nodes only exist where a **branch** passes, and the
link generator only links **branches** (`link1d2d_from_1d_to_2d(branchids=...)`).

**Adopted: internal lake branch.** For each matched lake, generate a tiny 2-point branch at the
lake centroid (length ~ one `edge_length_1d`, fully inside the polygon), added via the existing
`mesh1d_add_branch`. The lake `StorageNode.nodeid` is set to this branch's mesh node coordinate
(reusing the existing `nodeid` contract). Branch name `lake_<Name>`. The branch is a modeling
artifact (very short, internal) — accepted as the path that stays inside the existing
branch+link machinery.

**Link ring:** `network.link1d2d_from_1d_to_2d(branchids=["lake_<Name>"])`, bounded by the lake
polygon so contacts attach to the ground cells bordering the clipped hole — forming the
connection ring. (The exact bounding-polygon parameter is verified during implementation; a
post-filter on contacts is the fallback if needed.) Because §5.2 guarantees no faces remain
inside the lake, the ring cells are ground-only.

**Edge cases:**
- Lake polygon smaller than one cell -> clip removes nothing / ring empty: warn, keep lake as 1D
  storage (still valid).
- Lake with no matched polygon -> §3 unmatched fallback (1D-only).

New module `src/conversion/mesh/lake_links.py` owns lake↔polygon matching, internal-branch
generation, and ring linking (keeps `links.py` focused on branch lateral linking).

## 7. Overflow Mechanism — default 2D-bed crest (no link file)

**No `1D2DLinkFile` / `oned2dlinkfile` is authored.** Verified: hydrolib-core 1.0.1 exposes
`oned2dlinkfile` only as an opaque `DiskOnlyFileModel` (no typed crest model), and `Link1d2d`
has no per-link crest attribute. Rather than hand-write an unvalidated file format, the design
relies on Delft3D's **default** behavior:

- The 1D2D link's effective overflow level is automatically the **adjacent 2D cell's bed
  elevation** (from the DEM) — equivalent to the bank/weir crest. No artificial levee; water
  flows either direction once the level exceeds the neighboring terrain.

Three invariants make this behave as intended (all use data already in the pipeline):
1. **Lake `bedlevel` below the ring's 2D bed** — lake fills before spilling. **Post-build check:**
   sample DEM at ring cells; warn if `bedlevel >= ring_min_dem`.
2. **Lake interior clipped from 2D** (§5.2) — so "neighboring 2D cell" means the bank ring.
3. **Ring cells carry real DEM bed levels** — the existing `inifield.ini` `bedlevel` from the
   DEM. Makes the DEM a **functional requirement** for lake overflow; warn if a lake exists with
   no DEM provided (ring falls back to flat `bedlevuni`).

The lake's spill behavior emerges from **(clipped hole) + (DEM bed on ring) + (lake bedlevel
below ring)** — no new file, no hydrolib gap.

## 8. Orchestrator Wiring, Files & Verification

### 8.1 New / changed files

| File | Change |
|---|---|
| `src/conversion/converters/storage.py` | Rework `_lake_to_storage_node`: `useTable` switch (§4), fallback warnings (§4.3), accept matched polygon + ring node coordinate |
| `src/conversion/converters/domain2d.py` | `read_planning_map` returns lake polygons (`landuse=='lake'`); `build_2d_domain` excludes lakes from the solid-ground extent and exposes them separately |
| `src/conversion/mesh/mesh2d.py` | Triangular path: `create_triangular(ground)` -> `refine(level)` -> per-lake `clip(inside=True)`; post-clip ground-only assertion. Rectilinear kept as fallback |
| `src/conversion/mesh/lake_links.py` *(new)* | Lake↔polygon match (centroid containment); internal lake branch; ring links from bordering ground cells |
| `src/conversion/converters/fields.py` | Lake overflow check: warn if lake `bedlevel >= ring DEM min`, or lake exists with no DEM |
| `src/conversion/conversion.py` | Thread lake polygons through stages (§8.2) |
| `src/conversion/config.yaml` + `mesh/config.yaml` | `storage.lake_use_table` flag; `grid_2d.type: triangular` default + `refine.levels` calibration |
| `docs/conversion/gap_analysis.md` | Close G3 (lake now `useTable`); update G11/G12 for lake ring; note the silent-fallback follow-up and the default-crest (no `1D2DLinkFile`) decision |
| `docs/conversion/mesh_generation.md` | Document triangular generate-then-clip, the holes-leak finding, the lake ring |

### 8.2 Stage order (`conversion.py`)
Lakes need polygon + mesh before storage finalizes its `nodeid`:

planning-map read -> branches / crosssections / roughness / structures / boundaries /
observations (unchanged) -> **lake match** -> mesh1d (+ internal lake branches) -> mesh2d
(triangular, clip lakes) -> links (branches) + **lake ring links** -> storage (table switch,
attach to lake branch node) -> fields (DEM + overflow check) -> assemble -> validate.

### 8.3 Verification (project convention — no pytest, no binary)
- **Round-trip:** `FMModel(filepath=...)` re-reads `storagenodes.ini` with `useTable=true` lakes;
  `net.nc` reloads with the triangular mesh + lake contacts.
- **Inline smoke tests:** tabulated volume ≈ trapezoidal `(BedArea, Area, depth)`; **0** 2D faces
  inside any lake; ring links ≥ 1 per lake; fallback warnings fire on missing fields.
- **End-to-end** on `sample/` with a `landuse=='lake'` ground polygon + matching `lakes.csv` row
  + DEM.

## 9. Out of Scope / Documented Gaps

- **Fallback warnings for non-lake converters** (manholes, branches, structures, boundaries) —
  follow-up, not this design.
- **Explicit per-link crest** (`1D2DLinkFile`) — intentionally not authored; default 2D-bed crest
  used instead (§7). Revisit if a typed hydrolib API appears or a hand-writer is prioritized.
- **Per-zone 2D roughness / cellsize** (existing G11) — unchanged.
- **Sewer vertical coupling** (existing G12) — unchanged.
- **Behavioral (simulated) verification** — no Delft3D binary in this environment; verification is
  round-trip parse + geometric assertions only.

## 10. Verification Evidence (recorded from this session)

- `mesh2d_create_triangular_within_polygon` and `mesh2d_refine_mesh` exist; both take
  `mk.GeometryList`. `refine` level 3: 5 -> 145 nodes.
- Holes-at-generation leaks and worsens with refinement (1 -> 13 nodes inside lake at level 4).
  **Rejected.**
- Generate-solid-then-clip: 545 -> 532 nodes, 988 faces, **0** nodes/faces inside the lake,
  **0** faces outside ground-minus-lake. **Adopted.**
- No typed 1D2D link-parameter class in hydrolib-core 1.0.1; `oned2dlinkfile` is a
  `DiskOnlyFileModel`; `Link1d2d` has only `meshkernel`. -> default-crest design (§7).
