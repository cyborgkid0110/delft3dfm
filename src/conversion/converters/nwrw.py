"""nwrw.py — NWRW (roof) converter for Delft3D conversion pipeline.

Converts roof polygons from the planning-map GPKG into D-RR topology Nodes
and a companion list of roof records for Task 11 (rr_writer.py).

hydrolib-core 1.0.1 note
-------------------------
There is no typed NWRW catchment class in 1.0.1.  Roof polygons are therefore
emitted as ``rrtop.Node`` objects with ``modelnodetype=2`` and
``netternodetype=44`` — the validated NWRW combo.  Any other type combination
raises.  The ``roof_records`` list carries the per-roof area / surface type /
slope type that Task 11 uses when writing the actual D-RR model (NWRW area
records and coupling).

CRS rule
--------
``crs_cfg = cfg.get('crs') or src.delft3dfm.config.load()['crs']``
Input is EPSG:4326; output is the configured metric CRS (default 32648 UTM 48N).
Never hard-code 32648 alone.
"""

from __future__ import annotations

import geopandas as gpd

import hydrolib.core.rr.topology.models as rrtop
from hydrolib.core.rr.models import RainfallRunoffModel


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _out_epsg(cfg: dict) -> int:
    """Return the output (metric) EPSG from cfg, falling back to delft3dfm cfg."""
    crs_cfg = cfg.get("crs")
    if not crs_cfg:
        from src.delft3dfm.config import load as load_dfm
        crs_cfg = load_dfm()["crs"]
    return int(crs_cfg["out"])


def _ensure_crs(gdf: gpd.GeoDataFrame, assume_epsg: int = 4326) -> gpd.GeoDataFrame:
    """Return gdf with a CRS set; if it has none, assume *assume_epsg*."""
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=assume_epsg)
    return gdf


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_nwrw(
    roof_gdf: gpd.GeoDataFrame,
    cfg: dict,
) -> tuple:
    """Build NWRW topology nodes and roof records from reprojected roof polygons.

    hydrolib-core 1.0.1 has no typed NWRW catchment class, so roofs are
    emitted as ``rrtop.Node`` objects with ``modelnodetype=2`` /
    ``netternodetype=44`` (the validated NWRW combo — any other raises).
    The companion ``roof_records`` list carries per-roof area / surface type /
    slope type, which Task 11 (rr_writer.py) uses to write the actual D-RR
    model NWRW area records and the 1-D/2-D coupling.

    Surface type / slope type fallback (documented gap)
    ----------------------------------------------------
    If the ``roof_gdf`` has a ``surface`` column, its value is used per row;
    otherwise ``cfg['nwrw']['roof_surface_type']`` (default ``'closed_paved'``)
    applies.  Similarly for ``slope`` → ``cfg['nwrw']['roof_slope_type']``
    (default ``'sloped'``).  This allows per-roof type overrides in the
    planning map while keeping a sensible config-level default.

    Args:
        roof_gdf: GeoDataFrame with roof polygons (EPSG:4326 by default).
        cfg:      Conversion config dict; expected keys under ``cfg['nwrw']``:
                  ``roof_surface_type`` and ``roof_slope_type``.

    Returns:
        rr:           ``RainfallRunoffModel`` with ``node_data`` set to a
                      ``NodeFile`` containing one Node per roof polygon.
                      ``None`` if roof_gdf is empty.
        roof_records: List of dicts — one per roof — with keys:
                      ``id``, ``x``, ``y``, ``area_m2``,
                      ``surface_type``, ``slope_type``.
                      Empty list if roof_gdf is empty.
    """
    if roof_gdf is None or len(roof_gdf) == 0:
        return (None, [])

    out_epsg = _out_epsg(cfg)
    gdf = _ensure_crs(roof_gdf)
    gdf_proj = gdf.to_crs(epsg=out_epsg)

    # --- config-level defaults for surface/slope type ----------------------
    nwrw_cfg = cfg.get("nwrw", {})
    default_surface = nwrw_cfg.get("roof_surface_type", "closed_paved")
    default_slope = nwrw_cfg.get("roof_slope_type", "sloped")

    nodes: list[rrtop.Node] = []
    roof_records: list[dict] = []

    for i, (_, row) in enumerate(gdf_proj.iterrows(), start=1):
        geom = row.geometry
        centroid = geom.centroid
        x = float(centroid.x)
        y = float(centroid.y)
        area_m2 = float(geom.area)

        node_id = f"nwrw_{i}"

        # Per-row overrides; fall back to config defaults
        surface_type = (
            str(row["surface"]) if "surface" in row and row["surface"] is not None and str(row["surface"]) not in ("", "None", "<NA>")
            else default_surface
        )
        slope_type = (
            str(row["slope"]) if "slope" in row and row["slope"] is not None and str(row["slope"]) not in ("", "None", "<NA>")
            else default_slope
        )

        node = rrtop.Node(
            id=node_id,
            name=node_id,
            branchid=0,
            modelnodetype=2,
            netternodetype=44,
            objectid=node_id,
            xposition=x,
            yposition=y,
        )
        nodes.append(node)

        roof_records.append(
            {
                "id": node_id,
                "x": x,
                "y": y,
                "area_m2": area_m2,
                "surface_type": surface_type,
                "slope_type": slope_type,
            }
        )

    node_file = rrtop.NodeFile(node=nodes)
    rr = RainfallRunoffModel()
    rr.node_data = node_file

    return (rr, roof_records)
