"""Observation point converter for Delft3D conversion pipeline.

Converts manholes, pumps, and outfalls CSVs (EPSG:4326 Point geometry in the
``Shape`` column) into an :class:`ObservationPointModel`.

Each source location produces one :class:`ObservationPoint`.  Where possible,
points are placed on the nearest branch (branchid + chainage) so the
observation sits on the 1D mesh.  When no branch can be found, the point falls
back to projected (x, y) coordinates.

Unique names are enforced with a numeric suffix on collision.  Missing or
empty CSVs are silently tolerated.
"""

from __future__ import annotations

from typing import Optional

from shapely.geometry import LineString, Point as ShapelyPoint

from hydrolib.core.dflowfm.obs.models import ObservationPoint, ObservationPointModel

from src.conversion.base import (
    CoordRegistry,
    parse_geojson,
    read_csv_rows,
    reproject_geom,
)
from src.conversion.converters.branches import BranchSpec


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _safe_float(val, default: float) -> float:
    """Parse a CSV string to float, tolerant of Vietnamese decimal commas."""
    if val is None:
        return default
    s = str(val).strip()
    if not s:
        return default
    s = s.replace(";", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def _sanitize_name(raw: str) -> str:
    """Return a non-empty, whitespace-stripped name string.

    Replaces spaces with underscores. Falls back to ``'obs'`` if empty.
    """
    s = str(raw).strip().replace(" ", "_")
    return s if s else "obs"


def _unique_name(base: str, seen: set) -> str:
    """Return *base* if not yet in *seen*; otherwise append ``_N`` suffix."""
    if base not in seen:
        return base
    counter = 2
    while True:
        candidate = f"{base}_{counter}"
        if candidate not in seen:
            return candidate
        counter += 1


def _parse_point(shape_str: str, src_epsg: int, dst_epsg: int) -> Optional[tuple]:
    """Parse a GeoJSON Point and reproject.

    Returns ``(lon, lat, x, y)`` or ``None``.
    """
    if not shape_str or not str(shape_str).strip():
        return None
    try:
        geom = parse_geojson(str(shape_str).strip())
    except ValueError:
        return None
    if geom.geom_type != "Point":
        return None
    lon, lat = geom.x, geom.y
    proj_geom = reproject_geom(geom, src_epsg, dst_epsg)
    x, y = proj_geom.x, proj_geom.y
    return (lon, lat, x, y)


def _place_on_branch(
    lon: float,
    lat: float,
    branches: list[BranchSpec],
    src_epsg: int,
    dst_epsg: int,
) -> Optional[tuple]:
    """Find the nearest branch and compute chainage for a given WGS84 point.

    Returns ``(branch_name, chainage)`` or ``None`` if branches is empty.
    """
    if not branches:
        return None

    pt_wgs = ShapelyPoint(lon, lat)
    pt_metric = reproject_geom(pt_wgs, src_epsg, dst_epsg)
    px, py = pt_metric.x, pt_metric.y
    point_m = ShapelyPoint(px, py)

    best_branch = None
    best_dist = float("inf")
    best_chainage = 0.0

    for br in branches:
        coords = [(float(row[0]), float(row[1])) for row in br.geometry]
        if len(coords) < 2:
            continue
        line = LineString(coords)
        dist = line.distance(point_m)
        if dist < best_dist:
            best_dist = dist
            best_branch = br.name
            best_chainage = line.project(point_m)

    if best_branch is None:
        return None

    return (best_branch, best_chainage)


def _rows_to_obs(
    rows: list[dict],
    label: str,
    branches: list[BranchSpec],
    registry: CoordRegistry,
    seen_names: set,
    src_epsg: int,
    dst_epsg: int,
) -> list[ObservationPoint]:
    """Convert CSV rows to :class:`ObservationPoint` objects.

    Args:
        rows:       List of CSV row dicts.
        label:      Source label for logging (e.g. ``'manhole'``).
        branches:   Branch list for placement (may be empty → fallback to xy).
        registry:   Shared coord registry.
        seen_names: Set of names already used (mutated in place).
        src_epsg:   Source CRS (WGS84).
        dst_epsg:   Destination metric CRS.

    Returns:
        List of :class:`ObservationPoint` objects.
    """
    obs: list[ObservationPoint] = []
    skipped = 0

    for row in rows:
        name_raw = str(row.get("Name", row.get("ID", ""))).strip()
        shape_str = row.get("Shape", "")

        coords = _parse_point(shape_str, src_epsg, dst_epsg)
        if coords is None:
            skipped += 1
            continue

        lon, lat, x, y = coords

        base_name = _sanitize_name(name_raw)
        unique = _unique_name(base_name, seen_names)
        seen_names.add(unique)

        registry.get_or_create(x, y, unique, lon=lon, lat=lat)

        # Prefer branch placement; fall back to xy
        placement = _place_on_branch(lon, lat, branches, src_epsg, dst_epsg)
        if placement is not None:
            branchid, chainage = placement
            obs.append(
                ObservationPoint(
                    name=unique,
                    locationtype="1d",
                    branchid=branchid,
                    chainage=chainage,
                )
            )
        else:
            obs.append(
                ObservationPoint(
                    name=unique,
                    locationtype="1d",
                    x=x,
                    y=y,
                )
            )

    if skipped:
        print(f"  observations.py: skipped {skipped} {label} row(s) - no valid Point geometry")

    return obs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_observations(
    manholes_csv,
    pumps_csv,
    outfalls_csv,
    branches: list[BranchSpec],
    registry: CoordRegistry,
    cfg: dict,
) -> ObservationPointModel:
    """Build an :class:`ObservationPointModel` from manholes, pumps, and outfalls.

    Args:
        manholes_csv:  Path to manholes CSV, or ``None``.
        pumps_csv:     Path to pumps CSV, or ``None``.
        outfalls_csv:  Path to outfalls CSV, or ``None``.
        branches:      List of :class:`BranchSpec` objects in metric CRS.
        registry:      Shared :class:`CoordRegistry` (mutated in place).
        cfg:           Conversion config dict.

    Returns:
        An :class:`ObservationPointModel` with one :class:`ObservationPoint`
        per valid source location.  Points that cannot be placed on a branch
        fall back to (x, y) coordinates.  Rows with missing or invalid Point
        geometry are skipped silently.  Names are globally unique via numeric
        suffix.
    """
    from src.delft3dfm.config import load as load_dfm_cfg
    crs_cfg = cfg.get("crs") or load_dfm_cfg()["crs"]
    src_epsg: int = int(crs_cfg.get("in", 4326))
    dst_epsg: int = int(crs_cfg.get("out", 32648))

    seen_names: set = set()
    all_obs: list[ObservationPoint] = []

    manhole_rows = read_csv_rows(manholes_csv)
    pump_rows = read_csv_rows(pumps_csv)
    outfall_rows = read_csv_rows(outfalls_csv)

    all_obs.extend(_rows_to_obs(
        manhole_rows, "manhole", branches, registry, seen_names, src_epsg, dst_epsg
    ))
    all_obs.extend(_rows_to_obs(
        pump_rows, "pump", branches, registry, seen_names, src_epsg, dst_epsg
    ))
    all_obs.extend(_rows_to_obs(
        outfall_rows, "outfall", branches, registry, seen_names, src_epsg, dst_epsg
    ))

    print(
        f"  observations.py: built {len(all_obs)} observation point(s) "
        f"({len(manhole_rows)} manholes, {len(pump_rows)} pumps, "
        f"{len(outfall_rows)} outfalls sources)"
    )

    return ObservationPointModel(observationpoint=all_obs)
