"""Boundary condition converter for Delft3D conversion pipeline.

Converts outfall CSVs (EPSG:4326 Point geometry in the ``Shape`` column) into
:class:`Boundary` objects and a shared :class:`ForcingModel` with constant
water-level slots.

Gap note: TIDAL and time-series outfall refinement is not implemented in this
first pass.  All outfall types (FREE/NORMAL/TIDAL/FIXED) are mapped to a
``waterlevelbnd`` quantity with a constant value.  The scenario module is
expected to overwrite the datablock values with actual forcing data.
"""

from __future__ import annotations

from typing import Optional

from hydrolib.core.dflowfm.bc.models import Constant, ForcingModel, QuantityUnitPair
from hydrolib.core.dflowfm.ext.models import Boundary

from src.conversion.base import (
    CoordRegistry,
    parse_geojson,
    read_csv_rows,
    reproject_geom,
)


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


def _node_id(x: float, y: float) -> str:
    """Format projected (x, y) as a 1D mesh node id."""
    return f"{x:.6f}_{y:.6f}"


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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_boundaries(
    outfalls_csv,
    registry: CoordRegistry,
    cfg: dict,
) -> tuple:
    """Build boundary conditions from an outfalls CSV.

    All outfall types (FREE/NORMAL/TIDAL/FIXED) are mapped to ``waterlevelbnd``
    for the first pass.  TIDAL / time-series refinement is a documented gap
    that the scenario module is expected to fill.

    Args:
        outfalls_csv: Path to outfalls CSV, or ``None``.
        registry:     Shared :class:`CoordRegistry` (mutated in place so Task 8
                      can DEM-refine ``Elev_m`` by node name).
        cfg:          Conversion config dict.

    Returns:
        ``(list[Boundary], ForcingModel)`` — one :class:`Boundary` per outfall,
        and a single :class:`ForcingModel` (filepath ``'boundaries.bc'``) with
        one :class:`Constant` slot per outfall.  The constant value is
        ``FixedStage`` if present and parseable, else ``Elev_m``, else ``0.0``.
        Scenario modules should overwrite these placeholder values.
    """
    from src.delft3dfm.config import load as load_dfm_cfg
    crs_cfg = cfg.get("crs") or load_dfm_cfg()["crs"]
    src_epsg: int = int(crs_cfg.get("in", 4326))
    dst_epsg: int = int(crs_cfg.get("out", 32648))

    outfall_rows = read_csv_rows(outfalls_csv)

    # First pass: collect all row data so we can build the shared ForcingModel
    # before constructing Boundary objects (forcingfile is required at init).
    pending: list[dict] = []
    skipped = 0

    for row in outfall_rows:
        name_raw = str(row.get("Name", row.get("ID", ""))).strip()
        shape_str = row.get("Shape", "")

        coords = _parse_point(shape_str, src_epsg, dst_epsg)
        if coords is None:
            skipped += 1
            print(f"  boundaries.py: SKIP outfall (no valid Point): name={name_raw!r}")
            continue

        lon, lat, x, y = coords

        nodeid = _node_id(x, y)

        # Register in CoordRegistry under BOTH the human name AND the coord-string
        # nodeid, so Task 8 DEM refinement can look up the outfall's WGS84 lon/lat
        # whether it iterates by name (SWMM parity) or by the Boundary.nodeid it
        # actually carries.
        registry.get_or_create(x, y, name_raw, lon=lon, lat=lat)
        registry.get_or_create(x, y, nodeid, lon=lon, lat=lat)

        # Determine placeholder water level: FixedStage → Elev_m → 0.0
        fixed_stage = _safe_float(row.get("FixedStage"), None)
        elev_m = _safe_float(row.get("Elev_m"), None)
        if fixed_stage is not None:
            wl_value = fixed_stage
        elif elev_m is not None:
            wl_value = elev_m
        else:
            wl_value = 0.0

        pending.append({"nodeid": nodeid, "wl_value": wl_value})

    if skipped:
        print(f"  boundaries.py: skipped {skipped} outfall row(s)")

    # Build the single shared ForcingModel accumulating all constant slots.
    # All outfall types → waterlevelbnd (scenario module fills real values).
    quantity = "waterlevelbnd"
    forcing_slots = [
        Constant(
            name=item["nodeid"],
            quantityunitpair=[QuantityUnitPair(quantity=quantity, unit="m")],
            datablock=[[item["wl_value"]]],
        )
        for item in pending
    ]
    forcing_model = ForcingModel(forcing=forcing_slots)
    forcing_model.filepath = "boundaries.bc"

    # Build Boundary objects — forcingfile is required at construction time.
    boundaries: list[Boundary] = [
        Boundary(
            quantity=quantity,
            nodeid=item["nodeid"],
            forcingfile=forcing_model,
        )
        for item in pending
    ]

    print(
        f"  boundaries.py: built {len(boundaries)} boundary condition(s) "
        f"({len(outfall_rows) - skipped} outfalls)"
    )

    return (boundaries, forcing_model)
