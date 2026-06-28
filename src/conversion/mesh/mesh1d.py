"""mesh1d.py — Build the 1D branch network inside a hydrolib Network object.

Mirrors the canonical mesh1d flow from model.py (lines 42-55):
    Branch(geometry=...) → .generate_nodes(...) → network.mesh1d_add_branch(...)
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import numpy as np
from hydrolib.core.dflowfm.net.models import Branch

if TYPE_CHECKING:
    from hydrolib.core.dflowfm.net.models import Network
    from src.conversion.converters.branches import BranchSpec


def build_mesh1d(
    network: "Network",
    branches: list["BranchSpec"],
    cfg: dict,
) -> None:
    """Add all branch centerlines to *network* as 1D mesh branches.

    Parameters
    ----------
    network:
        Hydrolib-core :class:`Network` (mutated in place).
    branches:
        List of :class:`BranchSpec` objects produced by Task 4.
    cfg:
        Conversion config dict (from ``src.conversion.config.load()``).
        Reads ``cfg['mesh']['edge_length_1d']``.
    """
    edge_length: float = float(cfg["mesh"]["edge_length_1d"])

    added = 0
    skipped = 0

    for spec in branches:
        if spec.geometry.shape[0] < 2:
            warnings.warn(
                f"mesh1d: branch '{spec.name}' has fewer than 2 vertices - skipped.",
                stacklevel=2,
            )
            skipped += 1
            continue

        try:
            branch = Branch(geometry=np.array(spec.geometry, dtype=float))
            branch.generate_nodes(mesh1d_edge_length=edge_length)
            network.mesh1d_add_branch(branch, name=spec.name)
            added += 1
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"mesh1d: failed to add branch '{spec.name}': {exc}",
                stacklevel=2,
            )
            skipped += 1

    if skipped:
        print(f"  mesh1d: {skipped} branch(es) skipped (see warnings)")

    node_count: int = int(network._mesh1d.mesh1d_node_x.size)
    print(f"  mesh1d: {added} branches, {node_count} nodes")
