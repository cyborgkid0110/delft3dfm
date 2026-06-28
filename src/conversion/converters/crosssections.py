"""Cross-section converter for Delft3D conversion pipeline.

From a list of BranchSpec objects (Task 4), builds:
- crsdef.ini  — cross-section shape definitions (circle / rectangle / YZ trapezoid)
- crsloc.ini  — per-branch cross-section locations (one per branch at mid-chainage)
- frictdefs   — list of (frictionid, 'Manning', value) tuples for Task 7

Datum convention
----------------
YZ profiles use an absolute-elevation datum: z coordinates are referenced to
BedElev_m when it is available in the branch attrs; otherwise 0.0 is used as
datum.  Bank top is then bed_z + h (where h = BankElev_m - BedElev_m, or the
configured default_depth).

Sewer circle default
---------------------
When ``Diam_mm`` is absent or unparseable for a sewer branch the diameter
defaults to **0.5 m** (a conservative DN500 stand-in).
"""

from __future__ import annotations

import math
from typing import List, Tuple

import numpy as np

from hydrolib.core.dflowfm.crosssection.models import (
    CircleCrsDef,
    CrossDefModel,
    CrossLocModel,
    CrossSection,
    RectangleCrsDef,
    YZCrsDef,
)

from src.conversion.converters.branches import BranchSpec

# ---------------------------------------------------------------------------
# Type alias for friction definition tuples returned to Task 7
# ---------------------------------------------------------------------------
FrictDef = Tuple[str, str, float]  # (frictionid, 'Manning', Manning_n)


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


def _friction_id_for(material: str) -> str:
    """Return a stable friction definition id for *material*.

    Task 7 maps ``f_<material>`` back to a Manning n value via cfg['roughness'].
    """
    return f"f_{material}"


def _branch_length(geometry: np.ndarray) -> float:
    """Return the total polyline length (m) of a projected metric geometry."""
    if geometry.shape[0] < 2:
        return 0.0
    diffs = np.diff(geometry, axis=0)
    return float(np.sum(np.sqrt((diffs ** 2).sum(axis=1))))


# ---------------------------------------------------------------------------
# Shape-specific definition builders
# ---------------------------------------------------------------------------

def _circle_def(branch: BranchSpec, cfg: dict) -> CircleCrsDef:
    """Build a CircleCrsDef for a circular sewer branch.

    Diameter source: ``Diam_mm`` attr → /1000 m.
    Default: 0.5 m (DN500 stand-in) when attr is absent or unparseable.
    """
    diam_mm = _safe_float(branch.attrs.get("Diam_mm"), None)
    if diam_mm is None or diam_mm <= 0.0:
        diameter = 0.5  # documented default — see module docstring
    else:
        diameter = diam_mm / 1000.0

    return CircleCrsDef(
        id=f"cd_{branch.name}",
        diameter=diameter,
        frictionid=_friction_id_for(branch.material),
    )


def _parse_size_mm(size_str: str) -> Tuple[float, float]:
    """Parse a ``Size_mm`` string of the form ``WxH``, ``W*H``, or just ``W``.

    Returns (width_mm, height_mm).  If a single number is given, both width
    and height are set to that value.
    """
    s = str(size_str).strip()
    # Try 'x' or '*' separator (case-insensitive)
    for sep in ("x", "X", "*"):
        if sep in s:
            parts = s.split(sep, 1)
            w = _safe_float(parts[0], 0.0)
            h = _safe_float(parts[1], 0.0)
            return (w, h)
    # Single number — treat as square cross-section
    w = _safe_float(s, 0.0)
    return (w, w)


def _rect_def(branch: BranchSpec, cfg: dict) -> RectangleCrsDef:
    """Build a RectangleCrsDef for a rectangular sewer branch.

    Parses ``Size_mm`` in form "WxH" (or "W*H", or just "W") → metres.
    Falls back to ``default_width`` / ``default_depth`` from ``cfg['canal']``
    when the attr is absent or yields non-positive dimensions.
    """
    size_raw = branch.attrs.get("Size_mm", "")
    if size_raw:
        w_mm, h_mm = _parse_size_mm(size_raw)
    else:
        w_mm, h_mm = 0.0, 0.0

    # Fallback to canal defaults (sewers have no dedicated default_width in cfg)
    default_w = float(cfg.get("canal", {}).get("default_width", 1.0))
    default_h = float(cfg.get("canal", {}).get("default_depth", 0.5))

    width = (w_mm / 1000.0) if w_mm > 0.0 else default_w
    height = (h_mm / 1000.0) if h_mm > 0.0 else default_h

    return RectangleCrsDef(
        id=f"cd_{branch.name}",
        width=width,
        height=height,
        closed="yes",
        frictionid=_friction_id_for(branch.material),
    )


def _yz_trapezoid(branch: BranchSpec, cfg: dict) -> YZCrsDef:
    """Build a symmetric 5-point trapezoidal YZCrsDef.

    Geometry
    --------
    With bottom width ``b``, depth ``h``, side slope ``m`` (H:V), the 5 y-points
    span the full section top-to-top::

        y = [0,  m*h,  m*h + b/2,  m*h + b,  2*m*h + b]
        z = [bank_z, bed_z, bed_z, bed_z, bank_z]

    z is referenced to ``BedElev_m`` when available; otherwise 0.0 (module
    docstring explains the datum choice).

    frictionpositions span the full y-range [y[0], y[-1]] with a single
    friction section (sectioncount=1, frictionids=[id]).
    """
    kind = branch.kind  # 'river' or 'canal'
    kind_cfg = cfg.get(kind, cfg.get("river", {}))

    b = _safe_float(branch.attrs.get("Width_m"), float(kind_cfg.get("default_width", 5.0)))
    if b <= 0.0:
        b = float(kind_cfg.get("default_width", 5.0))

    bed_raw = branch.attrs.get("BedElev_m", "")
    bank_raw = branch.attrs.get("BankElev_m", "")
    bed_z = _safe_float(bed_raw, None)
    bank_z_raw = _safe_float(bank_raw, None)

    if bed_z is not None and bank_z_raw is not None and (bank_z_raw - bed_z) > 0.0:
        h = bank_z_raw - bed_z
    else:
        h = float(kind_cfg.get("default_depth", 2.0))
        bed_z = bed_z if bed_z is not None else 0.0

    m = _safe_float(branch.attrs.get("SlopCoef", ""), float(kind_cfg.get("side_slope", 1.0)))
    if m < 0.0:
        m = float(kind_cfg.get("side_slope", 1.0))

    # Absolute z values
    z_bed = bed_z if bed_z is not None else 0.0
    z_bank = z_bed + h

    # 5 symmetric y-coordinates (left top → left toe → centre → right toe → right top)
    y0 = 0.0
    y1 = m * h
    y2 = m * h + b / 2.0
    y3 = m * h + b
    y4 = 2.0 * m * h + b

    ycoords = [y0, y1, y2, y3, y4]
    zcoords = [z_bank, z_bed, z_bed, z_bed, z_bank]

    fric_id = _friction_id_for(branch.material)

    return YZCrsDef(
        id=f"cd_{branch.name}",
        yzcount=5,
        ycoordinates=ycoords,
        zcoordinates=zcoords,
        sectioncount=1,
        frictionpositions=[y0, y4],
        frictionids=[fric_id],
    )


# ---------------------------------------------------------------------------
# Sewer-type dispatch helper
# ---------------------------------------------------------------------------

def _is_rectangular(attrs: dict) -> bool:
    """Return True when attrs suggest a rectangular sewer cross-section.

    Criteria (either is sufficient):
    - ``XSType`` value contains 'RECT' (case-insensitive).
    - ``Size_mm`` contains 'x', 'X', or '*' (WxH notation).
    """
    xs_type = str(attrs.get("XSType", "")).upper()
    if "RECT" in xs_type:
        return True
    size_mm = str(attrs.get("Size_mm", ""))
    for sep in ("x", "X", "*"):
        if sep in size_mm:
            return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_crosssections(
    branches: List[BranchSpec],
    cfg: dict,
) -> Tuple[CrossDefModel, CrossLocModel, List[FrictDef]]:
    """Build crsdef + crsloc models and collect friction definitions.

    For each branch:
    - sewer  → circle by default; rectangle when XSType contains 'RECT' or
               Size_mm is in WxH notation.
    - river / canal → symmetric 5-point YZ trapezoid.

    One ``CrossSection`` is placed at the midpoint chainage of each branch.

    Args:
        branches:  List of :class:`~src.conversion.converters.branches.BranchSpec`.
        cfg:       Conversion config dict (from ``src.conversion.config.load()``).

    Returns:
        A 3-tuple ``(CrossDefModel, CrossLocModel, frictdefs)`` where
        *frictdefs* is a list of ``(frictionid, 'Manning', Manning_n)`` tuples
        (one per distinct frictionid) for Task 7 to consume.
    """
    roughness_table: dict = cfg.get("roughness", {})
    default_roughness: float = float(cfg.get("default_roughness", 0.013))

    defs: list = []
    locs: list = []
    seen_def_ids: set = set()

    # Collect unique friction ids as an ordered mapping frictionid → Manning n
    frictid_to_n: dict = {}

    for branch in branches:
        # 1. Build shape definition
        kind = branch.kind
        if kind == "sewer":
            if _is_rectangular(branch.attrs):
                crs_def = _rect_def(branch, cfg)
            else:
                crs_def = _circle_def(branch, cfg)
        else:
            # 'river' or 'canal'
            crs_def = _yz_trapezoid(branch, cfg)

        # Guard against accidental duplicate definition ids (branch names are
        # unique from Task 4, so cd_{name} should also be unique; this is a
        # safety net).
        if crs_def.id not in seen_def_ids:
            defs.append(crs_def)
            seen_def_ids.add(crs_def.id)

        # 2. Mid-chainage location
        length = _branch_length(branch.geometry)
        chainage = length / 2.0

        loc = CrossSection(
            id=f"cs_{branch.name}",
            branchid=branch.name,
            chainage=chainage,
            definitionid=crs_def.id,
        )
        locs.append(loc)

        # 3. Collect friction definition
        fric_id = _friction_id_for(branch.material)
        if fric_id not in frictid_to_n:
            n_val = roughness_table.get(branch.material, default_roughness)
            frictid_to_n[fric_id] = float(n_val)

    frictdefs: List[FrictDef] = [
        (fid, "Manning", n_val) for fid, n_val in frictid_to_n.items()
    ]

    crossdef_model = CrossDefModel(definition=defs)
    crossloc_model = CrossLocModel(crosssection=locs)

    return (crossdef_model, crossloc_model, frictdefs)
