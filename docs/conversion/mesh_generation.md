# Mesh Generation

Mesh generation is a **stage inside conversion** (stages 9-11 of 13), not a separate pipeline.
It is invoked by `Conversion.run()` and writes all mesh data into the `FlowFM_net.nc` network
file produced by hydrolib-core.

---

## Module Layout

```
src/conversion/mesh/
  __init__.py
  mesh1d.py     -- Build Mesh1d (branch discretization)
  mesh2d.py     -- Build Mesh2d (rectilinear grid, optional refine + clip)
  links.py      -- Build Link1d2d (lateral contacts, into net.nc)
  config.yaml   -- Mesh settings (edge_length_1d, grid_2d, refine, clip, link type)
```

---

## Public API

### `build_mesh1d`
```python
def build_mesh1d(
    network: Network,       # hydrolib-core Network object (mutated in place)
    branches: list[BranchSpec],
    cfg: dict,              # reads cfg['mesh']['edge_length_1d']
) -> None
```
Adds all branch centerlines to `network` as 1D mesh branches.
For each `BranchSpec`:
1. Creates a `Branch(geometry=np.array(spec.geometry))`.
2. Calls `branch.generate_nodes(mesh1d_edge_length=edge_length)`.
3. Calls `network.mesh1d_add_branch(branch, name=spec.name)`.

Branches with fewer than 2 vertices are skipped with a warning.
Any exception during `mesh1d_add_branch` is caught and the branch is skipped (with a warning).
Returns nothing; prints `"{added} branches, {node_count} nodes"`.

### `build_mesh2d`
```python
def build_mesh2d(
    network: Network,
    extent_polygon: BaseGeometry | None,    # unary_union of ground polygons from domain2d.py
    clip_polygons: list[BaseGeometry] | None,  # reserved; clipping uses extent_polygon directly
    cfg: dict,              # reads cfg['mesh']['grid_2d'], cfg['mesh']['refine'], cfg['mesh']['clip']
) -> None
```
Creates a rectilinear 2D surface mesh:

1. **Extent determination:** If `extent_polygon` is provided, uses its bounding box. Otherwise
   falls back to the 1D node bounding box padded by one cell (`dx`, `dy`). If neither is
   available, prints a warning and returns without creating a 2D mesh.
2. **Create:** `network.mesh2d_create_rectilinear_within_extent(extent=bbox, dx=dx, dy=dy)`.
3. **Refine (optional):** If `cfg['mesh']['refine']['enabled']` is true, calls
   `network.mesh2d_refine_mesh(refinement_iterations=levels)`. Wrapped in try/except; failure
   is warned and skipped.
4. **Clip (optional):** If `cfg['mesh']['clip']['to_ground_polygons']` is true AND
   `extent_polygon` is a simple (non-Multi) Polygon AND the ground polygon does not cover
   >= 95% of the mesh bbox area, clips using `meshkernel` (see Clip Semantics below).

Returns nothing; prints `"{node_count} nodes (clip=on/off)"`.

### `build_links`
```python
def build_links(
    network: Network,
    branches: list[BranchSpec],
    cfg: dict,              # reads cfg['mesh']['link']['type']
) -> None
```
Creates 1D2D lateral links from eligible branches to the 2D mesh.

**Coupling strategy (first pass):**
- Branches with `kind != 'sewer'` (i.e. rivers and canals) receive lateral coupling via
  `network.link1d2d_from_1d_to_2d(branchids=lateral_names)`.
- Sewer branches are excluded. Vertical/gully-inlet (street-inlet) coupling for sewers
  requires additional street-inlet parameters and is a documented gap.

The call is wrapped in try/except; branches that lie entirely outside the 2D mesh extent
do not crash the build. Returns nothing; prints `"{n_links} 1d2d contacts"`.

---

## Mesh Config Reference

File: `src/conversion/mesh/config.yaml`

```yaml
edge_length_1d: 100.0    # Computational node spacing along branch centerlines (m)
grid_2d:
  type: rectilinear      # Grid type. Only 'rectilinear' is implemented.
  dx: 100.0              # Cell width (m)
  dy: 100.0              # Cell height (m)
refine:
  enabled: false         # Whether to apply mesh2d refinement after creation
  levels: 1             # Number of refinement iterations
clip:
  to_ground_polygons: true  # Whether to clip 2D mesh to the ground polygon extent
link:
  type: lateral         # 1D2D coupling type for rivers/canals (default: 'lateral')
```

| Key | Default | Meaning |
|-----|---------|---------|
| `edge_length_1d` | 100.0 m | Spacing of computational nodes along 1D branch centerlines |
| `grid_2d.dx` | 100.0 m | 2D grid cell width |
| `grid_2d.dy` | 100.0 m | 2D grid cell height |
| `refine.enabled` | false | Enable mesh2d refinement after creation |
| `refine.levels` | 1 | Number of refinement iterations (when enabled) |
| `clip.to_ground_polygons` | true | Clip 2D mesh to the ground polygon footprint |
| `link.type` | lateral | 1D2D link type for river/canal branches |

---

## Clip-to-Ground Semantics

This section documents the **empirically verified** meshkernel behavior (not theoretical).

### What clipping does

When `clip.to_ground_polygons=true` and the ground polygon is a simple Polygon that does not
cover the full mesh extent, the 2D mesh is clipped to keep only cells that fall within the
ground polygon. The underlying meshkernel call is:

```python
network.mesh2d_clip_mesh(
    geometrylist=gl,
    deletemeshoption=mk.DeleteMeshOption.INSIDE_NOT_INTERSECTED,
    inside=False,
)
```

### Verified behavior

`INSIDE_NOT_INTERSECTED + inside=False` deletes cells **outside** the polygon, leaving only
the ground-covered cells. This is the correct clip-to-ground operation.

`INSIDE_NOT_INTERSECTED + inside=True` deletes cells **inside** the polygon (the opposite).
For a full-extent polygon it removes nothing and silently no-ops the clip. This is NOT used.

### Conditions that skip clipping

Three conditions cause clipping to be skipped (with a printed warning), preserving the
full rectilinear mesh:

1. **MultiPolygon ground:** meshkernel has no union-clip. Calling `mesh2d_clip_mesh` with
   `inside=False` on one part of a MultiPolygon would delete cells under sibling parts. Clipping
   is skipped for all MultiPolygon ground domains (documented first-pass gap).

2. **Ground covers full extent:** When the ground polygon area is >= 95% of the mesh bbox area,
   clipping with `inside=False` would only trim the boundary-intersected ring of cells, providing
   no meaningful domain reduction while potentially removing 1D2D link candidates. Clipping is
   skipped in this degenerate case.

3. **Post-clip empty mesh (rollback):** If `mesh2d_clip_mesh` removes all 2D nodes (which can
   happen when no grid cell lies entirely within the ground outline at the configured cellsize),
   the rectilinear mesh is rebuilt from scratch with the same bbox, dx, dy. The invariant
   "clipping never leaves an empty 2D mesh" is guaranteed by this rollback. A warning is printed.

---

## DTM-Under-Channel Caveat

From `docs/Delft3D_FM_1D2D.md` section 2.1 (D-Flow FM 1D2D User Manual, §17 / §18 Magdalena
tutorial note):

In large rivers, including the Digital Terrain Model (DTM) underneath a 1D channel
**double-counts storage**: the channel cross-section already carries all the storage volume for
that channel reach, so having 2D mesh cells overlapping the channel area also contributing
storage is physically incorrect.

**Best practice:** When river width exceeds approximately 2x the DTM raster resolution, delete
the 2D mesh cells beneath the 1D channel and use **lateral 1D2D links** (where the 1D channel
sits adjacent to, not overlapping, the 2D floodplain).

**Current implementation gap:** This module does not automatically detect or remove 2D cells
under 1D channels. The `clip.to_ground_polygons` setting clips the 2D domain to the drawn
ground polygon, but the drawn polygon may still overlap channel banks. Users who need to
eliminate DTM-under-channel double-counting must either:
- Draw the ground polygon to exclude the channel footprint, OR
- Post-process the `FlowFM_net.nc` to manually delete the relevant 2D cells.

This is a documented gap to be addressed when survey-grade channel survey profiles (real YZ
data) and exact channel footprint polygons are available.

---

## meshkernel Integration Notes

- The `meshkernel` library is imported lazily inside `build_mesh2d` to avoid an import-time
  error when only 1D meshes are needed.
- `mk.DeleteMeshOption.INSIDE_NOT_INTERSECTED` is the enum value used; other options
  (`ALL_VERTICES_INSIDE`, `ANY_VERTEX_INSIDE`) are not used.
- The `network.mesh2d_create_rectilinear_within_extent(extent=..., dx=..., dy=...)` call
  takes `extent` as a `(xmin, ymin, xmax, ymax)` tuple in projected metric coordinates.
- All mesh operations happen in the configured output CRS (default EPSG:32648 / UTM 48N).
  The `Network` object is later serialized by hydrolib-core into `FlowFM_net.nc`.
