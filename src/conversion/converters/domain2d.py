"""domain2d.py — 2-D domain converter for Delft3D conversion pipeline.

Reads the planning-map GPKG produced by Task 13 (planning_map.py) and builds:
  - extent / clip polygons for the 2-D mesh domain (D10 prep)
  - rain-mask PolyFile + Meteo block for spatially distributed rainfall (D10)

CRS rule
--------
``crs_cfg = cfg.get('crs') or src.delft3dfm.config.load()['crs']``
Input is EPSG:4326; output is the configured metric CRS (default 32648 UTM 48N).
Never hard-code 32648 alone.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union

from hydrolib.core.dflowfm.polyfile.models import (
    Metadata,
    PolyFile,
    PolyObject,
)
from hydrolib.core.dflowfm.polyfile.models import Point as PolyPoint
from hydrolib.core.dflowfm.ext.models import Meteo
from hydrolib.core.dflowfm.bc.models import ForcingModel


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


def _polygon_to_polyobject(polygon, name: str) -> PolyObject:
    """Convert a shapely Polygon exterior ring to a PolyFile PolyObject.

    The ring is closed (first == last point) as required by hydrolib-core.
    """
    coords = list(polygon.exterior.coords)
    # Ensure ring is closed (first == last)
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    points = [PolyPoint(x=float(x), y=float(y), z=None, data=[]) for x, y in coords]
    meta = Metadata(name=name, n_rows=len(points), n_columns=2)
    return PolyObject(metadata=meta, points=points)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_planning_map(gpkg_path: str) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, dict]:
    """Read planning-map GPKG layers produced by Task 13.

    Returns:
        ground_gdf:      GeoDataFrame for the ``ground`` layer (may be empty).
        roof_gdf:        GeoDataFrame for the ``roof`` layer (may be empty).
        landuse_catalog: dict mapping ``idval`` → ``manning`` from ``cat_landuses``
                         (empty dict if layer is absent or malformed).

    Notes:
        Tolerant of a missing file or missing individual layers — each is
        wrapped in its own try/except so one absent layer does not prevent
        reading the others.
    """
    empty_gdf = gpd.GeoDataFrame()

    # --- ground layer -------------------------------------------------------
    try:
        ground_gdf = gpd.read_file(gpkg_path, layer="ground")
    except Exception:
        ground_gdf = empty_gdf

    # --- roof layer ---------------------------------------------------------
    try:
        roof_gdf = gpd.read_file(gpkg_path, layer="roof")
    except Exception:
        roof_gdf = empty_gdf

    # --- landuse catalog (no geometry table) --------------------------------
    landuse_catalog: dict = {}
    try:
        lu = gpd.read_file(gpkg_path, layer="cat_landuses")
        if "idval" in lu.columns and "manning" in lu.columns:
            landuse_catalog = dict(zip(lu["idval"], lu["manning"].astype(float)))
    except Exception:
        landuse_catalog = {}

    return ground_gdf, roof_gdf, landuse_catalog


def build_2d_domain(
    ground_gdf: gpd.GeoDataFrame,
    cfg: dict,
) -> tuple:
    """Build 2-D domain extent and per-zone clip polygons from ground polygons.

    Args:
        ground_gdf: GeoDataFrame with ground polygons (EPSG:4326 by default).
        cfg:        Conversion config dict.

    Returns:
        extent_polygon: Shapely (multi)polygon — unary_union of all reprojected
                        ground geometries.  ``None`` if ground_gdf is empty.
        clip_polygons:  List of individual reprojected shapely polygons.
                        Each entry is the polygon itself; downstream tasks
                        (Task 10) may also read ``cellsize``/roughness from the
                        original GeoDataFrame row.  Empty list if ground_gdf
                        is empty.
    """
    if ground_gdf is None or len(ground_gdf) == 0:
        return (None, [])

    out_epsg = _out_epsg(cfg)
    gdf = _ensure_crs(ground_gdf)
    gdf_proj = gdf.to_crs(epsg=out_epsg)

    polys = list(gdf_proj.geometry)
    if not polys:
        return (None, [])

    extent = unary_union(polys)
    return (extent, polys)


def build_rain_mask(
    ground_gdf: gpd.GeoDataFrame,
    cfg: dict,
) -> tuple:
    """Build a rain-mask PolyFile and matching Meteo block from ground polygons.

    Each ground polygon exterior ring becomes one ``PolyObject`` (named
    ``ground_1``, ``ground_2``, …).  The ``Meteo`` object references the
    PolyFile as ``targetmaskfile`` (must be a PolyFile object, not a path) and
    uses an empty ``ForcingModel(filepath='rainfall.bc')`` as the scenario-
    agnostic forcing slot.

    Known hydrolib-core 1.0.1 limitation
    -------------------------------------
    Saving a ``forcing.ext`` containing this Meteo works fine, but re-loading
    it via ``ExtModel(filepath=...)`` fails (``targetmaskfile`` is re-parsed
    as a plain string and raises).  Task 12 validates the ``.pol`` file
    separately instead of round-tripping the ext.

    Args:
        ground_gdf: GeoDataFrame with ground polygons (EPSG:4326 by default).
        cfg:        Conversion config dict.

    Returns:
        (polyfile, meteo) — both ``None`` if ground_gdf is empty.
    """
    if ground_gdf is None or len(ground_gdf) == 0:
        return (None, None)

    out_epsg = _out_epsg(cfg)
    gdf = _ensure_crs(ground_gdf)
    gdf_proj = gdf.to_crs(epsg=out_epsg)

    poly_objects = []
    for i, geom in enumerate(gdf_proj.geometry, start=1):
        obj = _polygon_to_polyobject(geom, name=f"ground_{i}")
        poly_objects.append(obj)

    if not poly_objects:
        return (None, None)

    polyfile = PolyFile(objects=poly_objects)
    polyfile.filepath = "rain_mask.pol"

    forcing_model = ForcingModel()
    forcing_model.filepath = "rainfall.bc"

    meteo = Meteo(
        quantity="rainfall",
        forcingfile=forcing_model,
        forcingfiletype="bcAscii",
        targetmaskfile=polyfile,
        interpolationmethod="constant",
    )

    return (polyfile, meteo)
