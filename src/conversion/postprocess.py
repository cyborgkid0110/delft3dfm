"""postprocess.py -- thin post-conversion hooks.

The heavy network/net.nc cleanup (node deduplication, 1d2d contact wiring)
is performed inside the mesh stage (``src.conversion.mesh``) at build time,
so there is nothing mandatory to do here.

This module exists as an extension point: the orchestrator may call
``cleanup(network)`` after the mesh is assembled if future passes need to
prune or normalise the network graph.  Keep it minimal and ASCII-only.
"""

from __future__ import annotations


def cleanup(network) -> None:
    """No-op network cleanup hook.

    net.nc cleanup is handled in the mesh stage; this is a placeholder so the
    orchestrator has a stable symbol to call without behaviour changes.
    """
    return None
