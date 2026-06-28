"""Branch centerline converter for Delft3D conversion pipeline.

Reads standardized river/canal/sewer CSVs (EPSG:4326 RouteShape column)
and produces reprojected metric BranchSpec objects with CoordRegistry endpoints.

Material semantics
------------------
`BranchSpec.material` is a label string for roughness look-up.  It is set
from the CSV ``Material`` column when non-empty; otherwise it falls back to
the kind string (``'river'``, ``'canal'``, or ``'sewer'``).  Downstream tasks
(Task 5/7) look this up in ``cfg['roughness']`` (exact match) and fall back to
``cfg['default_roughness']`` when the key is absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from src.conversion.base import (
    CoordRegistry,
    parse_geojson,
    read_csv_rows,
    reproject_geom,
)


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class BranchSpec:
    """One 1-D branch centerline in projected metric coordinates.

    Attributes:
        name:      Unique branch label (sanitised and deduplicated).
        geometry:  (N, 2) float64 array of reprojected (x, y) vertices.
        kind:      ``'river'`` | ``'canal'`` | ``'sewer'``.
        material:  Material label for roughness look-up (see module docstring).
        from_node: Registry node-id of the first vertex.
        to_node:   Registry node-id of the last vertex.
        attrs:     Full original CSV row dict (for Tasks 5 & 7 to read
                   Width_m, BedElev_m, Diam_mm, etc.).
    """

    name: str
    geometry: np.ndarray          # shape (N, 2), projected metric (x, y)
    kind: str                     # 'river' | 'canal' | 'sewer'
    material: str
    from_node: str                # registry node id of first vertex
    to_node: str                  # registry node id of last vertex
    attrs: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sanitize_name(raw: str, kind: str, row_id: str) -> str:
    """Return a non-empty stripped name, falling back to ``kind_ID``."""
    name = raw.strip() if raw else ""
    if not name:
        name = f"{kind}_{row_id}"
    return name


def _rows_to_branches(
    rows: list[dict],
    kind: str,
    registry: CoordRegistry,
    cfg: dict,
    crs: dict,
    used_names: set,
) -> list[BranchSpec]:
    """Convert raw CSV rows into BranchSpec objects.

    Args:
        rows:     Output of :func:`read_csv_rows`.
        kind:     ``'river'``, ``'canal'``, or ``'sewer'``.
        registry: Shared :class:`CoordRegistry` (mutated in place).
        cfg:      Conversion config dict (from ``src.conversion.config.load()``).
        crs:      CRS dict with keys ``'in'`` (4326) and ``'out'`` (metric EPSG).
        used_names: Shared set of branch names already assigned across ALL kinds
                    in this build (mutated in place) so names stay globally
                    unique (a hydrolib-core requirement).

    Returns:
        List of :class:`BranchSpec` objects; skipped rows are not included.
    """
    src_epsg: int = int(crs["in"])
    dst_epsg: int = int(crs["out"])

    branches: list[BranchSpec] = []
    skipped: int = 0

    for row in rows:
        row_id = str(row.get("ID", "")).strip()
        raw_name = str(row.get("Name", "")).strip()

        # --- geometry -------------------------------------------------------
        route_shape = row.get("RouteShape", "")
        try:
            geom_wgs = parse_geojson(route_shape)
        except ValueError:
            skipped += 1
            continue

        # Ensure it is a LineString with >= 2 points
        coords_wgs = list(getattr(geom_wgs, "coords", []))
        if len(coords_wgs) < 2:
            skipped += 1
            continue

        # Reproject to metric CRS
        try:
            geom_proj = reproject_geom(geom_wgs, src_epsg, dst_epsg)
        except Exception:
            skipped += 1
            continue

        coords_proj = list(geom_proj.coords)
        if len(coords_proj) < 2:
            skipped += 1
            continue

        # xy array (N, 2)
        xy = np.array([(c[0], c[1]) for c in coords_proj], dtype=np.float64)

        # --- name (globally unique across all kinds) ------------------------
        base = _sanitize_name(raw_name, kind, row_id)
        name = base
        if name in used_names:
            # First try an ID-based suffix, then fall back to a numeric counter
            # until the derived name is genuinely unused. Guarantees uniqueness
            # even when Name AND ID repeat, or when names collide across kinds.
            candidate = f"{base}_{row_id}" if row_id else base
            n = 2
            while candidate in used_names or candidate == base:
                candidate = f"{base}_{n}"
                n += 1
            name = candidate
        used_names.add(name)

        # --- material -------------------------------------------------------
        raw_mat = str(row.get("Material", "")).strip()
        material = raw_mat if raw_mat else kind

        # --- register endpoints (store WGS84 lon/lat for DEM sampling) ------
        # First vertex
        lon0, lat0 = coords_wgs[0][0], coords_wgs[0][1]
        x0, y0 = float(xy[0, 0]), float(xy[0, 1])
        from_node = registry.get_or_create(
            x0, y0, f"{name}_start", lon=lon0, lat=lat0
        )

        # Last vertex
        lonN, latN = coords_wgs[-1][0], coords_wgs[-1][1]
        xN, yN = float(xy[-1, 0]), float(xy[-1, 1])
        to_node = registry.get_or_create(
            xN, yN, f"{name}_end", lon=lonN, lat=latN
        )

        branches.append(
            BranchSpec(
                name=name,
                geometry=xy,
                kind=kind,
                material=material,
                from_node=from_node,
                to_node=to_node,
                attrs=dict(row),
            )
        )

    if skipped:
        print(f"  {kind}: skipped {skipped} rows (bad/short geometry)")

    return branches


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_branches(
    rivers_csv,
    canals_csv,
    sewers_csv,
    registry: CoordRegistry,
    cfg: dict,
) -> list[BranchSpec]:
    """Build all branch centerlines from river, canal, and sewer CSVs.

    Args:
        rivers_csv:  Path to the rivers standardized CSV, or ``None``.
        canals_csv:  Path to the canals standardized CSV, or ``None``.
        sewers_csv:  Path to the sewers standardized CSV, or ``None``.
        registry:    Shared :class:`CoordRegistry` (mutated in place).
        cfg:         Conversion config (``src.conversion.config.load()``).

    Returns:
        Concatenated list of :class:`BranchSpec`: sewers first, then canals,
        then rivers (mirrors SWMM ordering so sewer junctions register first).
    """
    # Import delft3dfm config here to avoid circular imports at module level.
    from src.delft3dfm.config import load as load_dfm_cfg

    # Resolve CRS via the shared contract: an explicit cfg['crs'] override (if the
    # orchestrator injects one) wins, else fall back to the delft3dfm global crs.
    # Keeps branches aligned with storage/boundaries/observations so every stage
    # reprojects to the SAME metric CRS (required for the coordinate nodeid link).
    crs: dict = cfg.get("crs") or load_dfm_cfg()["crs"]

    sewer_rows = read_csv_rows(sewers_csv)
    canal_rows = read_csv_rows(canals_csv)
    river_rows = read_csv_rows(rivers_csv)

    # Shared across all kinds so branch names are globally unique.
    used_names: set = set()
    sewer_branches = _rows_to_branches(sewer_rows, "sewer", registry, cfg, crs, used_names)
    canal_branches = _rows_to_branches(canal_rows, "canal", registry, cfg, crs, used_names)
    river_branches = _rows_to_branches(river_rows, "river", registry, cfg, crs, used_names)

    ns = len(sewer_branches)
    nc = len(canal_branches)
    nr = len(river_branches)
    print(f"  branches: {ns} sewers, {nc} canals, {nr} rivers")

    return sewer_branches + canal_branches + river_branches
