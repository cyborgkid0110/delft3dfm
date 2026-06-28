"""Storage node converter for Delft3D conversion pipeline.

Converts manholes (thoat_nuoc/manholes.csv) and lakes
(mang_luoi_song_ho_kenh_muong/lakes.csv) into a :class:`StorageNodeModel`
(storagenodes.ini).

nodeid contract
---------------
A StorageNode attaches to a 1D mesh node via its ``nodeid`` string.
hydrolib-core names 1D mesh nodes by projected coordinate formatted as
``f"{x:.6f}_{y:.6f}"`` (e.g. ``"1400.000000_200.000000"``).  The helper
:func:`_node_id` produces this format.  This must NOT be confused with the
:class:`~src.conversion.base.CoordRegistry` internal ``node_N`` ids — those
are only used so Task 8 (DEM refinement) can look up elevations by human name.

Lake storage gap
----------------
Lakes are currently converted in area-form (``usetable='false'``) using
Area_ha → m².  Tabulated storage derived from ``Vol_m3`` is a documented gap
(gap_analysis Task 14).  Switching to ``usetable='true'`` with a volume–depth
table is the planned improvement.

streetlevel precedence for lakes
---------------------------------
1. ``CrestElv``  (if present and parseable)
2. ``BankElev_m`` (if present and parseable)
3. ``bedlevel + 3.0`` (fallback default)
"""

from __future__ import annotations

from typing import Optional

from hydrolib.core.dflowfm.storagenode.models import StorageNode, StorageNodeModel

from src.conversion.base import CoordRegistry, parse_geojson, read_csv_rows, reproject_geom


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
    # Remove thousand-separator semicolons (rare but seen in Vietnamese CSVs)
    s = s.replace(";", "")
    # Replace decimal comma with period
    s = s.replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def _node_id(x: float, y: float) -> str:
    """Format projected (x, y) as a 1D mesh node id.

    The format ``f"{x:.6f}_{y:.6f}"`` matches how hydrolib-core names mesh1d
    nodes — e.g. ``"1400.000000_200.000000"``.  Branch endpoints registered by
    Task 12 (orchestrator) will land on the same coordinates so that a storage
    node attached to a branch endpoint is guaranteed to match a real mesh1d node.
    """
    return f"{x:.6f}_{y:.6f}"


def _sanitize_id(raw: str) -> str:
    """Return a non-empty, whitespace-stripped id string.

    Replaces spaces with underscores and strips surrounding whitespace.
    Falls back to ``"node"`` if the result is empty.
    """
    s = str(raw).strip().replace(" ", "_")
    return s if s else "node"


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


def _parse_point(shape_str: str, src_epsg: int, dst_epsg: int) -> Optional[tuple]:
    """Parse a GeoJSON Point from *shape_str* and reproject.

    Returns ``(lon, lat, x, y)`` on success (lon/lat are WGS84, x/y projected),
    or ``None`` if the input is missing or not a Point geometry.
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


# ---------------------------------------------------------------------------
# Manhole conversion
# ---------------------------------------------------------------------------

def _manhole_to_storage_node(
    row: dict,
    registry: CoordRegistry,
    cfg: dict,
    seen_ids: set,
    src_epsg: int,
    dst_epsg: int,
) -> Optional[StorageNode]:
    """Convert one manhole CSV row to a :class:`StorageNode`.

    Returns ``None`` (and prints a warning) when the Shape column is absent
    or does not contain a valid Point geometry.
    """
    name_raw = row.get("Name", row.get("ID", ""))
    shape_str = row.get("Shape", "")

    coords = _parse_point(shape_str, src_epsg, dst_epsg)
    if coords is None:
        print(f"  SKIP manhole (no valid Point): name={name_raw!r} shape={str(shape_str)[:60]!r}")
        return None

    lon, lat, x, y = coords

    # Numeric fields
    storage_cfg = cfg.get("storage", {})
    factor = float(storage_cfg.get("street_storage_factor", 1.0))
    stype = str(storage_cfg.get("storage_type", "reservoir"))

    bedlevel = _safe_float(row.get("InvElev_m"), 0.0)
    area = _safe_float(row.get("Area_m2"), 1.0)
    if area <= 0.0:
        area = 1.0

    street_raw = _safe_float(row.get("RimElev_m"), None)
    if street_raw is None or street_raw < bedlevel:
        streetlevel = bedlevel + 3.0  # keep street above bed
    else:
        streetlevel = street_raw

    streetstoragearea = factor * area

    # Unique sanitized id
    base_id = _sanitize_id(name_raw)
    node_id_str = _unique_id(base_id, seen_ids)
    seen_ids.add(node_id_str)

    # Register in CoordRegistry under BOTH the raw CSV name AND the final
    # StorageNode id. Task 8 DEM refinement looks up by StorageNode.name (which
    # is node_id_str, possibly sanitized/de-duplicated from name_raw), so it must
    # be registered under that exact id or refinement silently skips this node.
    registry.get_or_create(x, y, name_raw, lon=lon, lat=lat)
    registry.get_or_create(x, y, node_id_str, lon=lon, lat=lat)

    return StorageNode(
        id=node_id_str,
        name=node_id_str,
        nodeid=_node_id(x, y),
        usetable="false",
        bedlevel=bedlevel,
        area=area,
        streetlevel=streetlevel,
        streetstoragearea=streetstoragearea,
        storagetype=stype,
    )


# ---------------------------------------------------------------------------
# Lake conversion
# ---------------------------------------------------------------------------

def _lake_to_storage_node(
    row: dict,
    registry: CoordRegistry,
    cfg: dict,
    seen_ids: set,
    src_epsg: int,
    dst_epsg: int,
) -> Optional[StorageNode]:
    """Convert one lake CSV row to a :class:`StorageNode` (area-form).

    streetlevel precedence:
    1. CrestElv — if present and parseable
    2. BankElev_m — if present and parseable
    3. bedlevel + 3.0 — fallback default

    Note: tabulated storage from Vol_m3 (usetable='true') is a documented gap
    (gap_analysis Task 14).  This converter uses area-form as the first pass.
    """
    name_raw = row.get("Name", "")
    shape_str = row.get("Shape", "")

    coords = _parse_point(shape_str, src_epsg, dst_epsg)
    if coords is None:
        print(f"  SKIP lake (no valid Point): name={name_raw!r} shape={str(shape_str)[:60]!r}")
        return None

    lon, lat, x, y = coords

    storage_cfg = cfg.get("storage", {})
    factor = float(storage_cfg.get("street_storage_factor", 1.0))
    stype = str(storage_cfg.get("storage_type", "reservoir"))

    # Area: Area_ha → m²
    area_ha = _safe_float(row.get("Area_ha"), 1.0)
    if area_ha <= 0.0:
        area_ha = 1.0
    area = area_ha * 1e4  # ha → m²

    bedlevel = _safe_float(row.get("BedElev_m"), 0.0)

    # streetlevel precedence: CrestElv → BankElev_m → bedlevel+3.0
    crestelv = _safe_float(row.get("CrestElv"), None)
    bankelev = _safe_float(row.get("BankElev_m"), None)
    if crestelv is not None and crestelv >= bedlevel:
        streetlevel = crestelv
    elif bankelev is not None and bankelev >= bedlevel:
        streetlevel = bankelev
    else:
        streetlevel = bedlevel + 3.0

    streetstoragearea = factor * area

    base_id = _sanitize_id(name_raw)
    node_id_str = _unique_id(base_id, seen_ids)
    seen_ids.add(node_id_str)

    # Register under BOTH raw name and the final node id (see manhole note):
    # DEM refinement (Task 8) looks up by StorageNode.name == node_id_str.
    registry.get_or_create(x, y, name_raw, lon=lon, lat=lat)
    registry.get_or_create(x, y, node_id_str, lon=lon, lat=lat)

    return StorageNode(
        id=node_id_str,
        name=node_id_str,
        nodeid=_node_id(x, y),
        usetable="false",
        bedlevel=bedlevel,
        area=area,
        streetlevel=streetlevel,
        streetstoragearea=streetstoragearea,
        storagetype=stype,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_storage(
    manholes_csv,
    lakes_csv,
    registry: CoordRegistry,
    cfg: dict,
) -> StorageNodeModel:
    """Build a :class:`StorageNodeModel` from manholes and lakes CSVs.

    Args:
        manholes_csv: Path to ``thoat_nuoc/manholes.csv``, or ``None``.
        lakes_csv:    Path to ``mang_luoi_song_ho_kenh_muong/lakes.csv``, or ``None``.
        registry:     :class:`~src.conversion.base.CoordRegistry` instance;
                      each storage location is registered so Task 8 can look it
                      up by name for DEM-based elevation refinement.
        cfg:          Conversion config dict from ``src.conversion.config.load()``.
                      Reads ``cfg['storage']``. CRS comes from the delft3dfm
                      global config (same source as branches.py) so every
                      converter reprojects to the same metric CRS — a hard
                      requirement for the coordinate-based ``nodeid`` linkage.

    Returns:
        A populated :class:`StorageNodeModel`.  Rows with missing or non-Point
        geometries are skipped (count is printed to stdout).
    """
    # CRS resolution — input is always WGS84; output from the delft3dfm global
    # config (matches branches.py). An explicit cfg['crs'] override, if the
    # orchestrator injected one, takes precedence so all stages stay aligned.
    from src.delft3dfm.config import load as load_dfm_cfg
    crs_cfg = cfg.get("crs") or load_dfm_cfg()["crs"]
    src_epsg: int = int(crs_cfg.get("in", 4326))
    dst_epsg: int = int(crs_cfg.get("out", 32648))

    nodes: list = []
    seen_ids: set = set()
    skipped_manholes = 0
    skipped_lakes = 0

    # --- Manholes ---
    manhole_rows = read_csv_rows(manholes_csv)
    for row in manhole_rows:
        sn = _manhole_to_storage_node(row, registry, cfg, seen_ids, src_epsg, dst_epsg)
        if sn is None:
            skipped_manholes += 1
        else:
            nodes.append(sn)

    # --- Lakes ---
    lake_rows = read_csv_rows(lakes_csv)
    for row in lake_rows:
        sn = _lake_to_storage_node(row, registry, cfg, seen_ids, src_epsg, dst_epsg)
        if sn is None:
            skipped_lakes += 1
        else:
            nodes.append(sn)

    if skipped_manholes:
        print(f"  storage.py: skipped {skipped_manholes} manhole row(s) - no valid Point geometry")
    if skipped_lakes:
        print(f"  storage.py: skipped {skipped_lakes} lake row(s) - no valid Point geometry")

    print(f"  storage.py: built {len(nodes)} StorageNode(s) "
          f"({len(manhole_rows) - skipped_manholes} manholes, "
          f"{len(lake_rows) - skipped_lakes} lakes)")

    return StorageNodeModel(storagenode=nodes)
