"""Base converter utilities for Delft3D conversion pipeline.

Shared utility layer: CSV reading, GeoJSON parsing, CRS reprojection,
coordinate registry, and DEM sampling.

Pure-Python + geopandas/shapely/rasterio/pyproj — NO osgeo/GDAL dependency.
"""

import csv
import json
import math
import os

import rasterio
from pyproj import CRS, Transformer
from shapely import geometry as shp_geometry
from shapely.ops import transform as shp_transform


# ---------------------------------------------------------------------------
# Module-level transformer cache: (src_epsg, dst_epsg) -> Transformer
# ---------------------------------------------------------------------------
_TRANSFORMER_CACHE: dict = {}


# ===========================================================================
# 1. CSV reading
# ===========================================================================

def read_csv_rows(path) -> list[dict]:
    """Read a UTF-8-BOM CSV and return a list of dicts.

    Returns [] if the file is missing or empty (tolerant — never raises).
    """
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        return rows
    except Exception:
        return []


# ===========================================================================
# 2. GeoJSON parsing → shapely geometry
# ===========================================================================

def parse_geojson(s) -> shp_geometry.base.BaseGeometry:
    """Parse a GeoJSON string and return a shapely geometry object.

    Supports Point, LineString, Polygon (and Multipart variants).
    Raises ValueError with offending snippet on empty/malformed input.
    """
    if not s or not s.strip():
        raise ValueError(f"Empty GeoJSON input: {repr(s[:100])}")
    try:
        obj = json.loads(s)
        return shp_geometry.shape(obj)
    except Exception as exc:
        snippet = str(s)[:100]
        raise ValueError(f"Malformed GeoJSON ({snippet!r}): {exc}") from exc


# ===========================================================================
# 3. Reprojection
# ===========================================================================

def reproject_geom(geom, src_epsg: int, dst_epsg: int):
    """Reproject a shapely geometry from src_epsg to dst_epsg.

    Transformers are cached per (src, dst) pair.
    If src_epsg == dst_epsg, returns geom unchanged.
    """
    if src_epsg == dst_epsg:
        return geom

    key = (int(src_epsg), int(dst_epsg))
    if key not in _TRANSFORMER_CACHE:
        _TRANSFORMER_CACHE[key] = Transformer.from_crs(
            f"EPSG:{src_epsg}", f"EPSG:{dst_epsg}", always_xy=True
        )
    transformer = _TRANSFORMER_CACHE[key]
    return shp_transform(transformer.transform, geom)


# ===========================================================================
# 4. Coordinate registry
# ===========================================================================

class CoordRegistry:
    """Deduplicated node registry in projected metric coordinates.

    Nodes are snapped together when they fall within *tol* metres of each
    other (euclidean distance in the projected CRS).
    """

    def __init__(self, tol: float = 1.0):
        """
        Args:
            tol: Snap tolerance in projected metres. Two points closer than
                 this are treated as the same node.
        """
        self.tol = tol
        self._nodes: dict = {}   # node_id -> record dict
        self._name_index: dict = {}  # human name -> node_id
        self._counter: int = 0

    # ---- public property ---------------------------------------------------

    @property
    def nodes(self) -> dict:
        """Return the underlying node dict (id -> record).

        Each record has keys: x, y, lon, lat, name, attrs.
        """
        return self._nodes

    # ---- core method -------------------------------------------------------

    def get_or_create(self, x: float, y: float, name: str, **attrs) -> str:
        """Get an existing node id (if within tol) or create a new one.

        Args:
            x, y: Projected metric coordinates.
            name: Human-readable label stored with the node.
            **attrs: Extra attributes, e.g. lon=…, lat=… for WGS84 storage.

        Returns:
            node_id string, e.g. "node_1".
        """
        # Linear scan for nearest node within tolerance
        best_id = None
        best_dist = float("inf")
        for node_id, rec in self._nodes.items():
            d = math.sqrt((x - rec["x"]) ** 2 + (y - rec["y"]) ** 2)
            if d < best_dist:
                best_dist = d
                best_id = node_id

        if best_id is not None and best_dist <= self.tol:
            self._name_index.setdefault(name, best_id)
            # Optionally fill in lon/lat if the snapped node has none yet
            if attrs.get("lon") is not None and self._nodes[best_id]["lon"] is None:
                self._nodes[best_id]["lon"] = attrs["lon"]
            if attrs.get("lat") is not None and self._nodes[best_id]["lat"] is None:
                self._nodes[best_id]["lat"] = attrs["lat"]
            return best_id

        # Create new node
        self._counter += 1
        node_id = f"node_{self._counter}"
        self._nodes[node_id] = {
            "x": x,
            "y": y,
            "lon": attrs.pop("lon", None),
            "lat": attrs.pop("lat", None),
            "name": name,
            "attrs": attrs,
        }
        self._name_index[name] = node_id
        return node_id

    # ---- lookup by human name ----------------------------------------------

    def wgs84_of(self, name: str):
        """Return (lon, lat) for the node registered under *name*, or None.

        Lookup key is the human `name` argument passed to get_or_create.
        Returns None if no node has that name or if lon/lat were not recorded.
        """
        node_id = self._name_index.get(name)
        if node_id is None:
            return None
        rec = self._nodes[node_id]
        lon, lat = rec.get("lon"), rec.get("lat")
        if lon is None or lat is None:
            return None
        return (lon, lat)


# ===========================================================================
# 5. DEM sampler
# ===========================================================================

class DEMSampler:
    """Rasterio-based DEM elevation sampler.

    Uses ``_band is None`` sentinel when DEM is absent or unreadable;
    callers can safely call ``.sample()`` — it returns None without crashing.
    """

    def __init__(self, path):
        self._band = None       # sentinel: None → DEM unavailable
        self._dataset = None
        self._nodata = None
        self._transformer = None  # WGS84 → raster CRS transformer, if needed

        if not path or not os.path.exists(path):
            return

        try:
            ds = rasterio.open(path)
        except Exception as exc:
            print(f"  WARNING: cannot open DEM {path}: {exc}")
            return

        self._dataset = ds
        self._nodata = ds.nodata

        # Build CRS transformer if raster is not in WGS84
        try:
            raster_crs = ds.crs
            if raster_crs is not None:
                # Use proper CRS equality rather than a coordinate-transform heuristic
                is_wgs84 = CRS.from_epsg(4326).equals(CRS.from_user_input(raster_crs))
                if not is_wgs84:
                    self._transformer = Transformer.from_crs(
                        "EPSG:4326", raster_crs, always_xy=True
                    )
        except Exception:
            pass  # No reprojection if CRS unresolvable

        # Set the band sentinel to non-None so .sample() proceeds
        self._band = True  # truthy flag; we always read via dataset.sample()

    def sample(self, lon: float, lat: float):
        """Return ground-surface elevation (m) at WGS84 (lon, lat), or None.

        Returns None when:
        - DEM is absent (_band sentinel is None)
        - Coordinates are outside raster extent
        - Value equals nodata or is NaN
        """
        if self._band is None:
            return None

        x, y = lon, lat
        if self._transformer is not None:
            x, y = self._transformer.transform(lon, lat)

        try:
            # Explicit bounds check: rasterio.sample() does NOT raise for OOB
            row, col = self._dataset.index(x, y)
            if not (0 <= row < self._dataset.height and 0 <= col < self._dataset.width):
                return None
            # rasterio.DatasetReader.sample() returns an iterator of arrays
            result = list(self._dataset.sample([(x, y)]))[0]
        except Exception:
            return None

        if result is None or len(result) == 0:
            return None

        val = float(result[0])

        # Check NaN first (order matters: NaN == nodata would be False anyway,
        # but an explicit NaN check first is the correct, order-independent pattern)
        if math.isnan(val):
            return None

        if self._nodata is not None:
            try:
                if not math.isnan(self._nodata) and val == self._nodata:
                    return None
            except (TypeError, ValueError):
                pass

        return val
