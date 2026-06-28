"""conversion.py -- end-to-end conversion orchestrator.

Threads every converter / mesh / writer stage into a single base model folder,
mirroring the SWMM Conversion ordering (spec section 4).

Stage order
-----------
build branches -> crosssections -> roughness -> storage -> structures ->
boundaries -> observations -> planning map (read -> 2d domain -> rain mask ->
nwrw) -> mesh1d -> mesh2d -> links -> fields (inifield + DEM node refinement) ->
assemble forcing.ext -> write_model -> write_dimr -> validate.

Cross-task contracts honoured
-----------------------------
* One shared CoordRegistry threads through branches/storage/structures/
  boundaries/observations.  Converters read CRS via
  ``cfg.get('crs') or src.delft3dfm.config.load()['crs']`` -- the orchestrator
  passes the CONVERSION cfg unchanged (no crs injection) so every stage
  reprojects identically and the coordinate-string nodeid linkage holds.
* write_model expects LIVE (possibly empty) model objects for crossdef/
  crossloc/friction/structures/storage/obs/ext -- never None (inifield may be
  None).
* The DEM file is copied into out_dir (shutil.copy) so the inifield basename
  reference resolves.
* forcing.ext is assembled from the boundary list + optional meteo block; the
  meteo targetmaskfile PolyFile already carries filepath 'rain_mask.pol' so it
  serialises alongside.

ASCII-only print/warn strings (Windows cp1258 console safety).
"""

from __future__ import annotations

import os
import shutil

from src.conversion.config import load as load_conversion_cfg
from src.delft3dfm.config import load as load_dfm_cfg

from src.conversion.base import CoordRegistry
from src.conversion.converters.branches import build_branches
from src.conversion.converters.crosssections import build_crosssections
from src.conversion.converters.structures import build_roughness, build_structures
from src.conversion.converters.storage import build_storage
from src.conversion.converters.boundaries import build_boundaries
from src.conversion.converters.observations import build_observations
from src.conversion.converters.domain2d import (
    read_planning_map,
    build_2d_domain,
    build_rain_mask,
)
from src.conversion.converters.nwrw import build_nwrw
from src.conversion.converters.fields import build_inifield, refine_node_levels
from src.conversion.mesh.mesh1d import build_mesh1d
from src.conversion.mesh.mesh2d import build_mesh2d
from src.conversion.mesh.links import build_links
from src.delft3dfm.model_writer import write_model, write_dimr
from src.conversion.validate import validate_model


# Vietnamese dataset subfolder layout (KEEP these names).
_DIR_SEWER = "thoat_nuoc"
_DIR_NETWORK = "mang_luoi_song_ho_kenh_muong"


class Conversion:
    """Orchestrate a full base-model conversion from a standardized dataset."""

    def __init__(self, dataset_dir, out_dir, dem_path=None, planning_map=None, bbox=None):
        self.dataset_dir = str(dataset_dir)
        self.out_dir = str(out_dir)
        self.dem_path = dem_path
        self.planning_map = planning_map
        self.bbox = bbox

        # Resolve CSV paths (missing files are tolerated by the converters).
        sewer = os.path.join(self.dataset_dir, _DIR_SEWER)
        net = os.path.join(self.dataset_dir, _DIR_NETWORK)

        self.sewers_csv = os.path.join(sewer, "sewers.csv")
        self.manholes_csv = os.path.join(sewer, "manholes.csv")
        self.pumps_csv = os.path.join(sewer, "pumps.csv")
        self.weirs_csv = os.path.join(sewer, "weir.csv")
        self.orifices_csv = os.path.join(sewer, "orifices.csv")
        self.outfalls_csv = os.path.join(sewer, "outfalls.csv")

        self.rivers_csv = os.path.join(net, "rivers.csv")
        self.canals_csv = os.path.join(net, "canals.csv")
        self.lakes_csv = os.path.join(net, "lakes.csv")

        # Config dicts.  Conversion cfg is passed to converters unchanged so the
        # CRS falls back to the delft3dfm global config consistently.
        self.cfg = load_conversion_cfg()
        self.gcfg = load_dfm_cfg()

    # -- internal stage runner -------------------------------------------------
    def _stage(self, idx, total, name, fn):
        print(f"[{idx}/{total}] {name}")
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            # The exception text may carry non-ASCII (Vietnamese dataset paths,
            # hydrolib messages); force ASCII so the failure banner itself never
            # crashes the cp1258 Windows console and hides the real error.
            safe = str(exc).encode("ascii", "replace").decode("ascii")
            print(f"  STAGE FAILED: {name}: {safe}")
            raise

    def run(self) -> str:
        out_dir = self.out_dir
        os.makedirs(out_dir, exist_ok=True)

        cfg = self.cfg
        gcfg = self.gcfg
        total = 13

        # A few-metre tolerance lets branch endpoints and node coordinates that
        # are within survey error share the same registry entry / nodeid.
        registry = CoordRegistry(tol=5.0)

        # [1] branches
        branches = self._stage(
            1, total, "branches",
            lambda: build_branches(
                self.rivers_csv, self.canals_csv, self.sewers_csv, registry, cfg
            ),
        )

        # [2] crosssections
        crossdef, crossloc, frictdefs = self._stage(
            2, total, "crosssections",
            lambda: build_crosssections(branches, cfg),
        )

        # [3] roughness (from frictdefs)
        friction = self._stage(
            3, total, "roughness",
            lambda: build_roughness(frictdefs, cfg),
        )

        # [4] storage
        storage = self._stage(
            4, total, "storage",
            lambda: build_storage(self.manholes_csv, self.lakes_csv, registry, cfg),
        )

        # [5] structures
        structures = self._stage(
            5, total, "structures",
            lambda: build_structures(
                self.pumps_csv, self.weirs_csv, self.orifices_csv,
                branches, registry, cfg,
            ),
        )

        # [6] boundaries
        bnds, bc_forcing = self._stage(
            6, total, "boundaries",
            lambda: build_boundaries(self.outfalls_csv, registry, cfg),
        )

        # [7] observations
        obs = self._stage(
            7, total, "observations",
            lambda: build_observations(
                self.manholes_csv, self.pumps_csv, self.outfalls_csv,
                branches, registry, cfg,
            ),
        )

        # [8] planning map (read -> 2d domain -> rain mask -> nwrw)
        extent = None
        clips = []
        rain_pf = None
        meteo = None
        rr = None

        def _planning():
            nonlocal extent, clips, rain_pf, meteo, rr
            if not self.planning_map:
                print("  planning map: none provided, skipping 2D domain/rain/nwrw")
                return
            ground_gdf, roof_gdf, _cat = read_planning_map(self.planning_map)
            extent, clips = build_2d_domain(ground_gdf, cfg)
            rain_pf, meteo = build_rain_mask(ground_gdf, cfg)
            rr, _roof_recs = build_nwrw(roof_gdf, cfg)

        self._stage(8, total, "planning map", _planning)

        # [9] mesh1d
        from hydrolib.core.dflowfm.net.models import Network
        network = Network()
        self._stage(
            9, total, "mesh1d",
            lambda: build_mesh1d(network, branches, cfg),
        )

        # [10] mesh2d
        self._stage(
            10, total, "mesh2d",
            lambda: build_mesh2d(network, extent, clips, cfg),
        )

        # [11] links
        self._stage(
            11, total, "links",
            lambda: build_links(network, branches, cfg),
        )

        # [12] fields (inifield + DEM node refinement) + DEM copy
        def _fields():
            inifield = build_inifield(self.dem_path, cfg)
            refine_node_levels(self.dem_path, registry, storage, bnds, bc_forcing, cfg)
            # Copy the DEM into out_dir so the inifield's stored basename resolves.
            if self.dem_path and os.path.exists(self.dem_path):
                shutil.copy(self.dem_path, os.path.join(out_dir, os.path.basename(self.dem_path)))
            return inifield

        inifield = self._stage(12, total, "fields", _fields)

        # [13] assemble forcing.ext -> write_model -> write_dimr -> validate
        def _finalize():
            from hydrolib.core.dflowfm.ext.models import ExtModel

            # bc_forcing already carries filepath 'boundaries.bc'; rain_pf already
            # carries 'rain_mask.pol' (set inside their converters).  model_writer
            # sets ext.filepath = 'forcing.ext'.
            ext = ExtModel(boundary=bnds, meteo=[meteo] if meteo else [])

            fm = write_model(
                out_dir, network, crossdef, crossloc, friction, storage,
                structures, obs, ext, inifield, gcfg,
            )
            write_dimr(out_dir, fm, rr_model=rr, gcfg=gcfg)

            problems = validate_model(out_dir)
            return problems

        problems = self._stage(13, total, "write + validate", _finalize)

        print(f"  conversion complete: {len(problems)} problem(s)")
        return out_dir
