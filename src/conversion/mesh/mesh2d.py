"""mesh2d.py — Build the 2D rectilinear surface mesh inside a hydrolib Network.

Mirrors the canonical mesh2d flow from model.py (lines 70-72):
    network.mesh2d_create_rectilinear_within_extent(extent=..., dx=..., dy=...)

Clipping (D10) trims the rectilinear 2D mesh DOWN TO the ground domain: it
keeps cells covered by ``extent_polygon`` (the ground union) and deletes the
rest. It is DEFENSIVE: if the clip removes all 2D nodes, a warning is printed
but the (empty) mesh is left as-is — the caller/user must inspect their polygons.

CLIP SEMANTICS (empirically verified in this meshkernel version, using a
*partial* ground polygon smaller than the mesh extent):
    INSIDE_NOT_INTERSECTED + inside=False → deletes cells OUTSIDE the polygon,
        leaving only the ground-covered cells. This is the correct
        clip-to-ground and is what we use.
    INSIDE_NOT_INTERSECTED + inside=True  → deletes cells INSIDE the polygon
        (the opposite). For a full-extent polygon it removes nothing and so
        silently NO-OPS the clip — NOT used.

A MultiPolygon ground cannot be clipped part-by-part with inside=False without
deleting cells under sibling parts (meshkernel has no union-clip), so a true
MultiPolygon ground skips clipping with a warning — a documented first-pass gap.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from hydrolib.core.dflowfm.net.models import Network
    from shapely.geometry.base import BaseGeometry


def _shapely_to_geometrylist(poly):
    """Convert a shapely Polygon to a meshkernel GeometryList."""
    import meshkernel as mk

    xs, ys = poly.exterior.coords.xy
    return mk.GeometryList(
        x_coordinates=np.array(xs, dtype=float),
        y_coordinates=np.array(ys, dtype=float),
    )


def build_mesh2d(
    network: "Network",
    extent_polygon: "BaseGeometry | None",
    clip_polygons: "list[BaseGeometry] | None",
    cfg: dict,
) -> None:
    """Create a rectilinear 2D surface mesh clipped to *extent_polygon*.

    Parameters
    ----------
    network:
        Hydrolib-core :class:`Network` (mutated in place).
    extent_polygon:
        Shapely geometry that defines the spatial footprint of the 2D mesh.
        Used for both the bbox extent and (optionally) clipping.
        May be ``None``, in which case the extent falls back to the 1D node
        bounding box (padded by one cell).
    clip_polygons:
        List of shapely polygons used for clipping (currently unused as a
        separate argument — clipping uses ``extent_polygon`` directly).
        Reserved for future per-polygon clipping. May be ``None``.
    cfg:
        Conversion config dict (from ``src.conversion.config.load()``).
        Reads ``cfg['mesh']['grid_2d']``, ``cfg['mesh']['refine']``,
        ``cfg['mesh']['clip']``.
    """
    import meshkernel as mk

    mesh_cfg = cfg["mesh"]
    dx: float = float(mesh_cfg["grid_2d"]["dx"])
    dy: float = float(mesh_cfg["grid_2d"]["dy"])
    refine_enabled: bool = bool(mesh_cfg["refine"]["enabled"])
    clip_enabled: bool = bool(mesh_cfg["clip"]["to_ground_polygons"])

    # ------------------------------------------------------------------
    # 1. Determine the bounding box (extent)
    # ------------------------------------------------------------------
    bbox: tuple[float, float, float, float] | None = None

    if extent_polygon is not None:
        xmin, ymin, xmax, ymax = extent_polygon.bounds
        bbox = (xmin, ymin, xmax, ymax)
    else:
        # Fall back to 1D node bounding box padded by one cell
        try:
            x_nodes = network._mesh1d.mesh1d_node_x
            y_nodes = network._mesh1d.mesh1d_node_y
            if x_nodes.size > 0:
                bbox = (
                    float(x_nodes.min()) - dx,
                    float(y_nodes.min()) - dy,
                    float(x_nodes.max()) + dx,
                    float(y_nodes.max()) + dy,
                )
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"mesh2d: could not derive extent from 1D nodes: {exc}",
                stacklevel=2,
            )

    if bbox is None:
        print(
            "  mesh2d: WARNING - no extent_polygon and no 1D nodes available; "
            "skipping 2D mesh creation."
        )
        return

    # ------------------------------------------------------------------
    # 2. Create rectilinear mesh within bbox extent
    # ------------------------------------------------------------------
    network.mesh2d_create_rectilinear_within_extent(
        extent=bbox, dx=dx, dy=dy
    )

    # ------------------------------------------------------------------
    # 3. Optional refinement (best-effort; meshkernel API varies by version)
    # ------------------------------------------------------------------
    if refine_enabled:
        levels: int = int(mesh_cfg["refine"].get("levels", 1))
        try:
            network.mesh2d_refine_mesh(refinement_iterations=levels)
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"mesh2d: refinement failed (skipped): {exc}",
                stacklevel=2,
            )

    # ------------------------------------------------------------------
    # 4. Optional clipping to extent_polygon
    # ------------------------------------------------------------------
    clipped = False

    if clip_enabled and extent_polygon is not None:
        # Clip the 2D mesh DOWN TO the ground domain (D10): keep only cells that
        # fall within the ground polygon, delete the rest.
        #
        # Verified meshkernel semantics for a *partial* ground polygon (smaller
        # than the mesh extent):
        #   INSIDE_NOT_INTERSECTED + inside=False  → deletes cells OUTSIDE the
        #       polygon, leaving the ground-covered cells (true clip-to-ground).
        #   INSIDE_NOT_INTERSECTED + inside=True   → deletes cells inside the
        #       polygon (the opposite); for a full-extent polygon it removes
        #       nothing, i.e. it silently NO-OPS the clip. Do not use it here.
        #
        # A MultiPolygon ground cannot be clipped part-by-part with inside=False
        # (the first part would delete cells under the other parts). meshkernel
        # has no union-clip, so for a true MultiPolygon we skip the clip with a
        # warning rather than corrupt the mesh — documented first-pass gap.
        is_multi = hasattr(extent_polygon, "geoms")
        # Only clip when the ground polygon is a MEANINGFUL SUBSET of the mesh
        # bbox. When ground ≈ the full extent, INSIDE_NOT_INTERSECTED+inside=False
        # deletes the boundary-intersected ring of cells for no benefit and can
        # zero out the 1D2D links — so we skip clipping in that degenerate case.
        try:
            ext_bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            ground_area = float(getattr(extent_polygon, "area", 0.0))
            covers_full = ext_bbox_area > 0 and (ground_area / ext_bbox_area) >= 0.95
        except Exception:  # noqa: BLE001
            covers_full = False

        if is_multi:
            print(
                "  mesh2d: WARNING - ground domain is a MultiPolygon; "
                "clip-to-ground skipped (single-polygon clip only in this "
                "first pass). The full rectilinear extent is kept."
            )
        elif covers_full:
            print(
                "  mesh2d: ground polygon ~= full mesh extent; clip-to-ground "
                "skipped (nothing to trim)."
            )
        else:
            try:
                pre_count = int(network._mesh2d.mesh2d_node_x.size)
                gl = _shapely_to_geometrylist(extent_polygon)
                network.mesh2d_clip_mesh(
                    geometrylist=gl,
                    deletemeshoption=mk.DeleteMeshOption.INSIDE_NOT_INTERSECTED,
                    inside=False,
                )
                post_count = int(network._mesh2d.mesh2d_node_x.size)
                if post_count == 0:
                    # meshkernel's clip can wipe the whole mesh when no grid cell
                    # lies entirely within the ground polygon (e.g. an irregular
                    # ground outline vs. a coarse grid). A zero-cell 2D mesh is
                    # unusable, so ROLL BACK to the unclipped rectilinear mesh
                    # rather than ship an empty domain.
                    print(
                        f"  mesh2d: WARNING - clip-to-ground removed ALL 2D "
                        f"cells (pre={pre_count}, post=0); rolling back to the "
                        f"unclipped rectilinear mesh. (Ground outline likely "
                        f"does not contain whole grid cells at this cellsize.)"
                    )
                    network.mesh2d_create_rectilinear_within_extent(
                        extent=bbox, dx=dx, dy=dy
                    )
                    clipped = False
                else:
                    clipped = True
            except Exception as exc:  # noqa: BLE001
                warnings.warn(
                    f"mesh2d: clipping failed (skipped): {exc}",
                    stacklevel=2,
                )
                # The clip may have raised mid-mutation and left the 2D mesh
                # empty/corrupt. Guarantee the invariant "clipping never leaves
                # an empty mesh" by rebuilding the rectilinear mesh if no 2D
                # nodes remain.
                try:
                    if int(network._mesh2d.mesh2d_node_x.size) == 0:
                        network.mesh2d_create_rectilinear_within_extent(
                            extent=bbox, dx=dx, dy=dy
                        )
                except Exception:  # noqa: BLE001
                    pass
                clipped = False

    node_count: int = int(network._mesh2d.mesh2d_node_x.size)
    print(
        f"  mesh2d: {node_count} nodes "
        f"(clip={'on' if clipped else 'off'})"
    )
