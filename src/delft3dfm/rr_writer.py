"""rr_writer.py -- Write D-RR (RainfallRunoffModel) files into out_dir/rr/.

Public API
----------
write_rr(out_dir, rr_model) -> str | None
    Save the RainfallRunoffModel (and its NodeFile) into ``out_dir/rr/``.
    Returns the inputFile name (relative to the ``rr/`` subdirectory) that
    the DIMR RRComponent should reference -- currently always
    ``'Sobek_3b.fnm'``.
    Returns None when rr_model is None (FM-only mode) or if the save fails
    (degraded FM-only fallback).

Scope / documented gaps
-----------------------
The first-pass RR model produced by nwrw.build_nwrw() contains only topology
nodes (rrtop.NodeFile).  Full NWRW area records (.3b_nod), rainfall .bui
wiring, and DWA table files are filled in by the scenario module (decoupled
from this writer) so this writer only guarantees that the minimum set of files
required for a valid DIMR RR entry are written.
"""

from __future__ import annotations

import pathlib
import warnings


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RR_CONTROL_FILENAME = "Sobek_3b.fnm"
_RR_NODE_FILENAME = "3b_nod.tp"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_rr(out_dir, rr_model) -> "str | None":
    """Write RainfallRunoffModel files into ``out_dir/rr/``.

    Parameters
    ----------
    out_dir:
        Root output directory (``pathlib.Path`` or str).  The files are
        written into the ``rr/`` sub-directory which is created if absent.
    rr_model:
        A ``hydrolib.core.rr.models.RainfallRunoffModel`` instance (or None).
        When None the function returns None immediately (FM-only mode).

    Returns
    -------
    str or None
        The inputFile name *relative to the rr/ subdirectory* for the DIMR
        RRComponent (e.g. ``'Sobek_3b.fnm'``), or None on failure / absent
        model.

    Notes
    -----
    - On any save failure a warning is printed (ASCII-safe) and None is
      returned so the caller can fall back to FM-only DIMR assembly.
    - ``recurse=False`` is used on the RR model save; the NodeFile is saved
      explicitly separately so we control its output path.
    """
    if rr_model is None:
        return None

    out_dir = pathlib.Path(out_dir)
    rr_dir = out_dir / "rr"

    try:
        rr_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        warnings.warn(
            f"[rr_writer] Cannot create rr/ directory: {exc} -- skipping RR, using FM-only.",
            stacklevel=2,
        )
        return None

    # --- save NodeFile (topology nodes) if present ---
    node_data = getattr(rr_model, "node_data", None)
    if node_data is not None:
        try:
            node_data.filepath = rr_dir / _RR_NODE_FILENAME
            node_data.save()
        except Exception as exc:  # noqa: BLE001
            # Non-fatal: DIMR can still reference the .fnm even without nodes
            print(
                f"[rr_writer] WARNING: NodeFile save failed ({type(exc).__name__}: {exc}) -- continuing."
            )

    # --- save the RainfallRunoffModel control file (.fnm) ---
    try:
        rr_model.filepath = rr_dir / _RR_CONTROL_FILENAME
        rr_model.save(recurse=False)
    except Exception as exc:  # noqa: BLE001
        print(
            f"[rr_writer] WARNING: RainfallRunoffModel save failed "
            f"({type(exc).__name__}: {exc}) -- falling back to FM-only DIMR."
        )
        return None

    return _RR_CONTROL_FILENAME
