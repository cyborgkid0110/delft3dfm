"""links.py — Generate 1D2D lateral links inside a hydrolib Network.

Mirrors the canonical link call from model.py (line 78):
    network.link1d2d_from_1d_to_2d(branchids=["Channel_up", "Tributary"])

First-pass coupling strategy:
    ALL branches with kind != 'sewer' receive lateral coupling
    (rivers and canals exchange water laterally with the 2D surface mesh).
    Sewer branches are excluded here — vertical/gully-inlet coupling for
    sewers requires additional street-inlet parameters that are a documented
    gap for a future pass.

The ``cfg['mesh']['link']['type']`` key is 'lateral' by default; a different
value is logged but not acted upon in this pass (extend here if needed).

Linking is DEFENSIVE: wrapped in try/except so a branch that lies entirely
outside the 2D mesh extent does not crash the build.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hydrolib.core.dflowfm.net.models import Network
    from src.conversion.converters.branches import BranchSpec


def _link_count(network: "Network") -> int:
    """Return the number of 1d2d contacts, guarding against empty arrays."""
    try:
        arr = network._link1d2d.link1d2d
        return int(arr.shape[0]) if arr.size else 0
    except Exception:  # noqa: BLE001
        return 0


def build_links(
    network: "Network",
    branches: list["BranchSpec"],
    cfg: dict,
) -> None:
    """Create 1D2D lateral links from eligible 1D branches to the 2D mesh.

    Parameters
    ----------
    network:
        Hydrolib-core :class:`Network` (mutated in place).
    branches:
        List of :class:`BranchSpec` objects produced by Task 4.
    cfg:
        Conversion config dict (from ``src.conversion.config.load()``).
        Reads ``cfg['mesh']['link']['type']``.

    Notes
    -----
    Sewer branches (``kind == 'sewer'``) are intentionally skipped in this
    first pass.  Vertical / street-inlet coupling requires additional gully
    parameters and is a documented gap.

    The contacts themselves are written into *net.nc* by the network object;
    no separate ``1d2d_links.ini`` is produced in this pass (its physical
    parameters are optional and can be added when needed).
    """
    link_type: str = cfg["mesh"]["link"].get("type", "lateral")
    if link_type != "lateral":
        print(
            f"  links: WARNING - link type '{link_type}' is not 'lateral'; "
            f"only lateral coupling is implemented in this pass."
        )

    # Determine which branch names are eligible for lateral linking
    lateral_names = [
        spec.name for spec in branches if spec.kind != "sewer"
    ]

    if not lateral_names:
        print(
            "  links: WARNING - no lateral-eligible branches found "
            "(all branches are sewers or branch list is empty); skipping linking."
        )
        print(f"  links: {_link_count(network)} 1d2d contacts")
        return

    # Log sewer exclusions so the user is aware
    sewer_names = [spec.name for spec in branches if spec.kind == "sewer"]
    if sewer_names:
        print(
            f"  links: {len(sewer_names)} sewer branch(es) excluded from lateral "
            f"linking (vertical/gully coupling is a documented gap)."
        )

    # Attempt linking
    try:
        network.link1d2d_from_1d_to_2d(branchids=lateral_names)
    except Exception as exc:  # noqa: BLE001
        warnings.warn(
            f"links: link1d2d_from_1d_to_2d failed: {exc} - "
            f"some or all branches may lie outside the 2D mesh extent.",
            stacklevel=2,
        )

    n_links = _link_count(network)
    print(f"  links: {n_links} 1d2d contacts")
