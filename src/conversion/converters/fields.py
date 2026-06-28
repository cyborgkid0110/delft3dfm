"""DEM bedlevel inifield builder and SWMM-parity node elevation refinement (D12).

Two public functions:
  - build_inifield: wraps a GeoTIFF DEM into a hydrolib-core IniFieldModel.
  - refine_node_levels: refines storage-node and outfall elevations from DEM
    surface samples, matching SWMM postprocess.py::refine_elevations exactly.

Gap analysis
------------
- Depth fallback: when a storage node has no usable prior depth
  (streetlevel - bedlevel <= 0 or unparseable), the refinement falls back to a
  depth of 0.0 m (invert == surface), exactly mirroring SWMM
  refine_elevations' `invert = dem_elev - (max_depth or 0.0)`. This preserves
  D12 parity rather than inventing a synthetic depth.
- The orchestrator (Task 12) is responsible for copying the DEM file into the
  model output folder.  build_inifield stores only the DEM basename so the
  reference resolves relative to that folder.
"""

from __future__ import annotations

import os
from typing import Optional

from hydrolib.core.dflowfm.inifield.models import IniFieldModel, InitialField

from src.conversion.base import CoordRegistry, DEMSampler


def build_inifield(dem_path, cfg) -> Optional[IniFieldModel]:
    """Return an IniFieldModel for *dem_path*, or None if no DEM is available.

    Args:
        dem_path: Absolute path to a GeoTIFF DEM file, or falsy.
        cfg:      Conversion config dict (currently unused; reserved for future
                  interpolation-method overrides).

    Returns:
        IniFieldModel with a single bedlevel InitialField, or None when
        dem_path is falsy or the file does not exist on disk.

    Note:
        Only the DEM basename is stored in ``datafile``.  Task 12 /
        orchestrator is responsible for copying the DEM into the model output
        folder and updating the reference to a relative basename if required.
    """
    if not dem_path or not os.path.exists(dem_path):
        return None

    field = InitialField(
        quantity="bedlevel",
        datafile=os.path.basename(dem_path),
        datafiletype="GeoTIFF",
        interpolationmethod="averaging",
        averagingtype="mean",
    )
    return IniFieldModel(initial=[field])


def refine_node_levels(
    dem_path,
    registry: CoordRegistry,
    storage_model,
    outfall_boundaries: list,
    forcing_model,
    cfg,
) -> int:
    """Refine storage-node and outfall elevations from DEM surface samples.

    Matches SWMM postprocess.py::refine_elevations exactly (D12 parity):
    - Storage nodes: streetlevel = DEM_surface; bedlevel = DEM_surface - depth
      where depth = prior (streetlevel - bedlevel) if > 0, else 0.0 (matching
      SWMM's `invert = dem_elev - (max_depth or 0.0)`; no synthetic depth).
    - Outfalls:      level = DEM_surface (no depth subtraction).
    - Rounds all results to 3 decimal places.
    - Skips nodes not in the registry or where DEM returns None (nodata/OOB).
    - Prints per-table refined/total counts and a grand total.

    Args:
        dem_path:           Path to GeoTIFF DEM, or falsy/missing.
        registry:           CoordRegistry with WGS84 coords keyed by name.
        storage_model:      StorageNodeModel from Task 6.
        outfall_boundaries: list[Boundary] from Task 7.
        forcing_model:      ForcingModel whose Constant entries hold outfall
                            water levels (matched by Constant.name == nodeid).
        cfg:                Conversion config dict (reserved; depth fallback is
                            0.0 for exact SWMM parity - see module docstring).

    Returns:
        Total number of nodes whose elevation was updated.
    """
    # ---- explicit DEM availability check (so the message is accurate) ----
    if not dem_path or not os.path.exists(dem_path):
        print("  DEM refinement: no DEM available, skipping")
        return 0

    dem = DEMSampler(dem_path)
    if dem._band is None:
        print("  DEM refinement: no DEM available, skipping")
        return 0

    total = 0

    # ---- Storage nodes -------------------------------------------------------
    storage_nodes = storage_model.storagenode if storage_model else []
    sn_refined = 0
    for sn in storage_nodes:
        lonlat = registry.wgs84_of(sn.name)
        if lonlat is None:
            continue
        lon, lat = lonlat
        surface = dem.sample(lon, lat)
        if surface is None:
            continue

        # Depth = the node's prior (streetlevel - bedlevel), exactly mirroring
        # SWMM refine_elevations' `invert = dem_elev - (max_depth or 0.0)`:
        # when the prior depth is not a usable positive value, SWMM falls back
        # to 0.0 (invert == surface), NOT a synthetic depth. Keep that parity.
        try:
            prior_depth = float(sn.streetlevel) - float(sn.bedlevel)
        except (TypeError, ValueError, AttributeError):
            prior_depth = 0.0

        depth = prior_depth if prior_depth > 0.0 else 0.0

        sn.streetlevel = round(surface, 3)
        sn.bedlevel = round(surface - depth, 3)
        sn_refined += 1

    print(f"  storage: {sn_refined}/{len(storage_nodes)} refined")
    total += sn_refined

    # ---- Outfalls ------------------------------------------------------------
    outfall_refined = 0
    for bnd in (outfall_boundaries or []):
        lonlat = registry.wgs84_of(bnd.nodeid)
        if lonlat is None:
            continue
        lon, lat = lonlat
        surface = dem.sample(lon, lat)
        if surface is None:
            continue

        # Update the matching Constant in the ForcingModel
        if forcing_model is not None:
            for constant in forcing_model.forcing:
                if constant.name == bnd.nodeid:
                    constant.datablock = [[round(surface, 3)]]
                    break

        outfall_refined += 1

    print(f"  outfalls: {outfall_refined}/{len(outfall_boundaries or [])} refined")
    total += outfall_refined

    print(f"  Total: {total} nodes refined from DEM")
    return total
