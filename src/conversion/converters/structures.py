"""Structure and roughness converters for Delft3D conversion pipeline.

Converts pump, weir, and orifice CSVs (EPSG:4326 Point geometry in the
``Shape`` column) into a :class:`StructureModel` and roughness friction
definitions into a :class:`FrictionModel`.

Culvert conversion is intentionally omitted (deferred to gap-analysis D13).
Structures that cannot be placed on a branch (no branches or distance exceeds
tolerance) are skipped with a printed count.
"""

from __future__ import annotations

import re
from typing import Optional

from shapely.geometry import LineString, Point

from hydrolib.core.dflowfm.friction.models import FrictionModel, FrictGlobal
from hydrolib.core.dflowfm.structure.models import (
    Orifice,
    Pump,
    StructureModel,
    Weir,
)

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
    """Parse a CSV string to float, tolerant of Vietnamese decimal commas.

    Handles: empty string, None, semicolons used as thousand separators,
    comma-as-decimal (e.g. "1,5" → 1.5), surrounding whitespace.
    Falls back to *default* on any parse failure.
    """
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


def _sanitize_id(raw: str) -> str:
    """Return a non-empty, whitespace-stripped id string.

    Replaces spaces with underscores and strips surrounding whitespace.
    Falls back to ``"struct"`` if the result is empty.
    """
    s = str(raw).strip().replace(" ", "_")
    return s if s else "struct"


def _unique_id(base: str, seen: set) -> str:
    """Return *base* if not yet in *seen*; otherwise append ``_N`` suffix."""
    if base not in seen:
        return base
    counter = 2
    while True:
        candidate = f"{base}_{counter}"
        if candidate not in seen:
            return candidate
        counter += 1


def _node_id(x: float, y: float) -> str:
    """Format projected (x, y) as a 1D mesh node id.

    Matches how hydrolib-core names mesh1d nodes.
    """
    return f"{x:.6f}_{y:.6f}"


def _parse_point(shape_str: str, src_epsg: int, dst_epsg: int) -> Optional[tuple]:
    """Parse a GeoJSON Point from *shape_str* and reproject.

    Returns ``(lon, lat, x, y)`` on success, or ``None`` on failure.
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

    Args:
        lon, lat:  WGS84 coordinates of the point.
        branches:  List of :class:`BranchSpec` objects in metric CRS.
        src_epsg:  Source EPSG (typically 4326).
        dst_epsg:  Destination metric EPSG.

    Returns:
        ``(branch_name, chainage)`` tuple, or ``None`` if *branches* is empty.

    The function reprojects the point to metric coordinates, builds a Shapely
    ``LineString`` for each branch's geometry, and picks the branch that
    minimises perpendicular distance.  Chainage is ``line.project(point)``,
    which clamps naturally to ``[0, line.length]``.
    """
    if not branches:
        return None

    from shapely.geometry import Point as ShapelyPoint
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


def _parse_capacity(raw) -> float:
    """Extract the first float from a capacity string like '2.5 m3/s'.

    Strips any non-numeric suffix. Falls back to 0.5 on failure.
    """
    if raw is None:
        return 0.5
    s = str(raw).strip()
    if not s:
        return 0.5
    # Replace comma decimal
    s = s.replace(",", ".")
    # Extract leading number (possibly with decimal point)
    m = re.match(r"[-+]?[0-9]*\.?[0-9]+", s)
    if m:
        try:
            return float(m.group())
        except ValueError:
            pass
    return 0.5


# ---------------------------------------------------------------------------
# Public: build_roughness
# ---------------------------------------------------------------------------

def build_roughness(frictdefs: list, cfg: dict) -> FrictionModel:
    """Build a :class:`FrictionModel` from a list of friction definitions.

    Args:
        frictdefs: List of ``(frictionid, frictiontype, value)`` tuples,
                   typically produced by Task 5.  Duplicate ids are deduplicated
                   (first occurrence wins).
        cfg:       Conversion config dict (from ``src.conversion.config.load()``).
                   Reads ``cfg['default_roughness']`` for the fallback entry.

    Returns:
        A :class:`FrictionModel` with at least one :class:`FrictGlobal` entry.
        If *frictdefs* is empty, a single global default ``(f_default, Manning,
        cfg['default_roughness'])`` is emitted so ``roughness.ini`` is non-empty.
    """
    default_n = float(cfg.get("default_roughness", 0.013))

    if not frictdefs:
        return FrictionModel(
            global_=[
                FrictGlobal(
                    frictionid="f_default",
                    frictiontype="Manning",
                    frictionvalue=default_n,
                )
            ]
        )

    seen_ids: set = set()
    globals_: list = []
    for entry in frictdefs:
        fid, ftype, val = entry[0], entry[1], entry[2]
        fid_s = str(fid).strip() if fid else "f_default"
        if fid_s in seen_ids:
            continue
        seen_ids.add(fid_s)
        ftype_s = str(ftype).strip() if ftype else "Manning"
        fval = float(val) if val is not None else default_n
        globals_.append(
            FrictGlobal(
                frictionid=fid_s,
                frictiontype=ftype_s,
                frictionvalue=fval,
            )
        )

    return FrictionModel(global_=globals_)


# ---------------------------------------------------------------------------
# Public: build_structures
# ---------------------------------------------------------------------------

def build_structures(
    pumps_csv,
    weirs_csv,
    orifices_csv,
    branches: list[BranchSpec],
    registry: CoordRegistry,
    cfg: dict,
) -> StructureModel:
    """Build a :class:`StructureModel` from pump, weir, and orifice CSVs.

    Culvert conversion is intentionally omitted (deferred to gap-analysis D13).

    Args:
        pumps_csv:    Path to pumps CSV, or ``None``.
        weirs_csv:    Path to weirs CSV, or ``None``.
        orifices_csv: Path to orifices CSV, or ``None``.
        branches:     List of :class:`BranchSpec` objects (metric CRS).
        registry:     Shared :class:`CoordRegistry` (mutated in place).
        cfg:          Conversion config dict.

    Returns:
        A populated :class:`StructureModel`.  Rows with missing required fields
        or that cannot be placed on a branch are skipped (count printed).
    """
    from src.delft3dfm.config import load as load_dfm_cfg
    crs_cfg = cfg.get("crs") or load_dfm_cfg()["crs"]
    src_epsg: int = int(crs_cfg.get("in", 4326))
    dst_epsg: int = int(crs_cfg.get("out", 32648))

    struct_cfg = cfg.get("structure", {})
    weir_corrcoeff = float(struct_cfg.get("weir_corrcoeff", 1.0))
    orifice_corrcoeff = float(struct_cfg.get("orifice_corrcoeff", 0.63))

    structures: list = []
    seen_ids: set = set()

    # ----- Pumps -------------------------------------------------------------
    skipped_pumps = 0
    pump_rows = read_csv_rows(pumps_csv)
    for row in pump_rows:
        name_raw = str(row.get("Name", row.get("ID", ""))).strip()
        shape_str = row.get("Shape", "")
        coords = _parse_point(shape_str, src_epsg, dst_epsg)
        if coords is None:
            skipped_pumps += 1
            continue
        lon, lat, x, y = coords

        placement = _place_on_branch(lon, lat, branches, src_epsg, dst_epsg)
        if placement is None:
            skipped_pumps += 1
            continue
        branchid, chainage = placement

        capacity = _parse_capacity(row.get("Cap_m3s"))

        base_id = _sanitize_id(name_raw)
        uid = _unique_id(base_id, seen_ids)
        seen_ids.add(uid)

        registry.get_or_create(x, y, uid, lon=lon, lat=lat)

        pump = Pump(
            id=uid,
            name=uid,
            branchid=branchid,
            chainage=chainage,
            capacity=capacity,
            orientation="positive",
            controlside="suctionSide",
            numstages=0,
        )

        # Note: startlevelsuctionside / stoplevelsuctionside are List[float]
        # with length == numstages.  Since numstages=0, these must remain None.
        # When numstages > 0, pass them as constructor kwargs sized to numstages.

        structures.append(pump)

    # ----- Weirs -------------------------------------------------------------
    skipped_weirs = 0
    weir_rows = read_csv_rows(weirs_csv)
    for row in weir_rows:
        name_raw = str(row.get("Name", row.get("ID", ""))).strip()
        shape_str = row.get("Shape", "")
        coords = _parse_point(shape_str, src_epsg, dst_epsg)
        if coords is None:
            skipped_weirs += 1
            continue
        lon, lat, x, y = coords

        # crestlevel is required
        crestlevel = _safe_float(row.get("CrestElv"), None)
        if crestlevel is None:
            skipped_weirs += 1
            continue

        placement = _place_on_branch(lon, lat, branches, src_epsg, dst_epsg)
        if placement is None:
            skipped_weirs += 1
            continue
        branchid, chainage = placement

        crestwidth = _safe_float(row.get("Width_m"), 1.0)

        base_id = _sanitize_id(name_raw)
        uid = _unique_id(base_id, seen_ids)
        seen_ids.add(uid)

        registry.get_or_create(x, y, uid, lon=lon, lat=lat)

        structures.append(
            Weir(
                id=uid,
                name=uid,
                branchid=branchid,
                chainage=chainage,
                crestlevel=crestlevel,
                crestwidth=crestwidth,
                corrcoeff=weir_corrcoeff,
            )
        )

    # ----- Orifices ----------------------------------------------------------
    # Note: Culverts (D13) are intentionally excluded from this converter.
    skipped_orifices = 0
    ori_rows = read_csv_rows(orifices_csv)
    for row in ori_rows:
        name_raw = str(row.get("Name", row.get("ID", ""))).strip()
        shape_str = row.get("Shape", "")
        coords = _parse_point(shape_str, src_epsg, dst_epsg)
        if coords is None:
            skipped_orifices += 1
            continue
        lon, lat, x, y = coords

        # crestlevel (InvElev_m) is required
        crestlevel = _safe_float(row.get("InvElev_m"), None)
        if crestlevel is None:
            skipped_orifices += 1
            continue

        height_m = _safe_float(row.get("Height_m"), None)
        gateloweredgelevel = (
            crestlevel + height_m if height_m is not None else crestlevel + 1.0
        )

        placement = _place_on_branch(lon, lat, branches, src_epsg, dst_epsg)
        if placement is None:
            skipped_orifices += 1
            continue
        branchid, chainage = placement

        crestwidth = _safe_float(row.get("Width_m"), 1.0)

        base_id = _sanitize_id(name_raw)
        uid = _unique_id(base_id, seen_ids)
        seen_ids.add(uid)

        registry.get_or_create(x, y, uid, lon=lon, lat=lat)

        structures.append(
            Orifice(
                id=uid,
                name=uid,
                branchid=branchid,
                chainage=chainage,
                crestlevel=crestlevel,
                gateloweredgelevel=gateloweredgelevel,
                corrcoeff=orifice_corrcoeff,
                crestwidth=crestwidth,
            )
        )

    if skipped_pumps:
        print(f"  structures.py: skipped {skipped_pumps} pump(s) - missing geometry/branch")
    if skipped_weirs:
        print(f"  structures.py: skipped {skipped_weirs} weir(s) - missing geometry/crestlevel/branch")
    if skipped_orifices:
        print(f"  structures.py: skipped {skipped_orifices} orifice(s) - missing geometry/crestlevel/branch")

    print(
        f"  structures.py: built {len(structures)} structure(s) "
        f"({len(pump_rows) - skipped_pumps} pumps, "
        f"{len(weir_rows) - skipped_weirs} weirs, "
        f"{len(ori_rows) - skipped_orifices} orifices)"
    )

    return StructureModel(structure=structures)
