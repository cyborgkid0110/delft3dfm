"""model_writer.py -- Assemble FM model (MDU + net.nc) and DIMR config.

Public API
----------
write_model(out_dir, network, crossdef, crossloc, friction, storage,
            structures, obs, ext, inifield, gcfg) -> FMModel
    Wire all converter outputs into an FMModel and save to *out_dir*.

write_dimr(out_dir, fm, rr_model=None, gcfg=None) -> None
    Build and save a dimr_config.xml in *out_dir*.  Supports both FM-only
    (no rr_model) and RR-coupled (rr_model present) modes.

Notes
-----
ASCII-only strings are used throughout (Windows cp1258 console safety).
"""

from __future__ import annotations

import pathlib
import warnings


# ---------------------------------------------------------------------------
# write_model
# ---------------------------------------------------------------------------


def write_model(
    out_dir,
    network,
    crossdef,
    crossloc,
    friction,
    storage,
    structures,
    obs,
    ext,
    inifield,
    gcfg: dict,
):
    """Wire converter outputs into an FMModel and save to *out_dir*.

    Parameters
    ----------
    out_dir:
        Destination directory (``pathlib.Path`` or str).  Created if absent.
    network:
        ``hydrolib.core.dflowfm.net.models.Network`` (raw mesh graph).
        Wrapped in a ``NetworkModel`` internally.
    crossdef:
        ``CrossDefModel`` -- channel cross-section definitions.
    crossloc:
        ``CrossLocModel`` -- cross-section locations along branches.
    friction:
        ``FrictionModel`` -- global roughness definition.
    storage:
        ``StorageNodeModel`` -- storage nodes (may be empty / None).
    structures:
        ``StructureModel`` -- hydraulic structures (may be empty / None).
    obs:
        ``ObservationPointModel`` -- output observation points.
    ext:
        ``ExtModel`` -- assembled external forcing (boundaries + meteo).
    inifield:
        ``IniFieldModel`` or None.  When None the ``inifieldfile`` key is
        not set on the MDU so Delft3D uses internal defaults.
    gcfg:
        Config dict from ``src.delft3dfm.config.load()``.  The sub-dict
        ``gcfg['model']`` must contain: refdate, tstart, tstop, dtuser,
        bedlevuni, waterlevini, allowbndatbifurcation.

    Returns
    -------
    FMModel
        The assembled and saved FMModel (filepath already set).

    Notes
    -----
    - ``.filepath`` is set on every sub-model *before* ``fm.save(recurse=True)``
      so hydrolib-core writes each file with the intended name.
    - The ext / meteo targetmaskfile round-trip bug in hydrolib-core 1.0.1 only
      affects *re-parsing* the ext, not *saving* -- so saving is safe.
    """
    from hydrolib.core.dflowfm.mdu.models import FMModel
    from hydrolib.core.dflowfm.net.models import NetworkModel

    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mcfg = gcfg["model"]

    # --- wrap raw Network in a NetworkModel ---
    netfile = NetworkModel(network=network)
    netfile.filepath = pathlib.Path("FlowFM_net.nc")

    # --- set target filepaths on all sub-models ---
    crossdef.filepath = pathlib.Path("crsdef.ini")
    crossloc.filepath = pathlib.Path("crsloc.ini")
    friction.filepath = pathlib.Path("roughness.ini")
    structures.filepath = pathlib.Path("structures.ini")
    obs.filepath = pathlib.Path("obs.ini")
    ext.filepath = pathlib.Path("forcing.ext")

    if storage is not None:
        storage.filepath = pathlib.Path("storagenodes.ini")

    if inifield is not None:
        inifield.filepath = pathlib.Path("inifield.ini")

    # --- build FMModel and wire sub-models ---
    fm = FMModel()

    fm.geometry.netfile = netfile
    fm.geometry.crossdeffile = crossdef
    fm.geometry.crosslocfile = crossloc
    fm.geometry.frictfile = [friction]
    fm.geometry.structurefile = [structures]
    fm.geometry.bedlevuni = mcfg["bedlevuni"]
    fm.geometry.waterlevini = mcfg["waterlevini"]
    fm.geometry.allowbndatbifurcation = mcfg["allowbndatbifurcation"]

    if storage is not None:
        fm.geometry.storagenodefile = storage

    if inifield is not None:
        fm.geometry.inifieldfile = inifield

    fm.output.obsfile = [obs]
    fm.external_forcing.extforcefilenew = ext

    # --- time settings ---
    fm.time.refdate = int(mcfg["refdate"])
    fm.time.tstart = float(mcfg["tstart"])
    fm.time.tstop = float(mcfg["tstop"])
    fm.time.dtuser = float(mcfg["dtuser"])

    fm.filepath = out_dir / "FlowFM.mdu"
    fm.save(recurse=True)

    return fm


# ---------------------------------------------------------------------------
# write_dimr
# ---------------------------------------------------------------------------


def write_dimr(out_dir, fm, rr_model=None, gcfg=None) -> None:
    """Build and save a DIMR config (dimr_config.xml) in *out_dir*.

    Parameters
    ----------
    out_dir:
        Model root directory (same as the one passed to ``write_model``).
    fm:
        The ``FMModel`` returned by ``write_model`` (already saved).
    rr_model:
        Optional ``RainfallRunoffModel``.  When provided (and successfully
        saved) a fully RR-coupled DIMR is produced.  On any RR save failure
        the function falls back to FM-only mode and prints an ASCII warning.
    gcfg:
        Config dict from ``src.delft3dfm.config.load()``.  Required when
        *rr_model* is not None to derive the StartGroup time string
        (``'tstart dtuser tstop'``).

    DIMR structure
    --------------
    FM-only:
        <component name="dflowfm"> + <control><start name="dflowfm"/>

    RR-coupled:
        Two components (dflowfm + rr), one coupler (rr2flow), and a
        Parallel/StartGroup control block.  The StartGroup.time is a STRING
        derived from gcfg (format: ``'<tstart> <dtuser> <tstop>'``).

    Notes
    -----
    - ``rr_writer.write_rr`` is called first so the RR files exist under
      ``out_dir/rr/`` before the DIMR xml is written (critical ordering).
    - ``dimr.save(recurse=False)`` is used so the dimr serialiser does not
      attempt to re-read/re-parse any component input files.
    """
    from hydrolib.core.dimr.models import (
        DIMR,
        FMComponent,
        RRComponent,
        Start,
        StartGroup,
        Parallel,
        ComponentOrCouplerRef,
        Coupler,
        CoupledItem,
    )
    from src.delft3dfm import rr_writer  # local import avoids circular at module level

    out_dir = pathlib.Path(out_dir)

    # --- optionally write RR files first ---
    rr_input: str | None = None
    if rr_model is not None:
        rr_input = rr_writer.write_rr(out_dir, rr_model)
        if rr_input is None:
            print(
                "[model_writer] WARNING: RR writer returned None -- "
                "building FM-only DIMR."
            )

    # --- build DIMR ---
    dimr = DIMR()

    dimr.component.append(
        FMComponent(
            name="dflowfm",
            workingDir=".",
            inputFile="FlowFM.mdu",
            library="dflowfm",
            model=fm,
        )
    )

    if rr_input is not None:
        # RR-coupled mode
        dimr.component.append(
            RRComponent(
                name="rr",
                workingDir="rr",
                inputFile=rr_input,
                library="rr_dll",
            )
        )

        dimr.coupler.append(
            Coupler(
                name="rr2flow",
                sourceComponent="rr",
                targetComponent="dflowfm",
                item=[
                    CoupledItem(
                        sourceName="catchments/runoff",
                        targetName="laterals/discharge",
                    )
                ],
            )
        )

        # Derive time string from gcfg; fall back to '0 60 3600' if gcfg absent
        if gcfg is not None:
            mcfg = gcfg["model"]
            time_str = (
                f"{int(mcfg['tstart'])} "
                f"{int(mcfg['dtuser'])} "
                f"{int(mcfg['tstop'])}"
            )
        else:
            time_str = "0 60 3600"
            warnings.warn(
                "[model_writer] gcfg not provided; using default StartGroup.time '0 60 3600'.",
                stacklevel=2,
            )

        dimr.control.append(
            Parallel(
                startGroup=StartGroup(
                    time=time_str,
                    start=ComponentOrCouplerRef(name="dflowfm"),
                    coupler=[ComponentOrCouplerRef(name="rr2flow")],
                ),
                start=ComponentOrCouplerRef(name="rr"),
            )
        )
    else:
        # FM-only mode
        dimr.control.append(Start(name="dflowfm"))

    dimr.filepath = out_dir / "dimr_config.xml"
    dimr.save(recurse=False)
