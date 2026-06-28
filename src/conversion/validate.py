"""validate.py -- round-trip validator for a produced base model folder.

``validate_model(out_dir)`` re-reads each produced file with hydrolib-core and
returns a list of problem strings (empty list == OK).

Meteo round-trip bug (hydrolib-core 1.0.1)
------------------------------------------
A ``forcing.ext`` that carries a meteo ``targetmaskfile`` SAVES fine but does
NOT re-parse via ``ExtModel(filepath=...)`` -- the targetmaskfile is re-read as
a plain string and raises.  ``FMModel(filepath=...)`` recursively parses the
ext, so it hits the same bug whenever a rain mask is present.

To stay correct we try ``FMModel(filepath=...)`` first; if it fails AND a
``rain_mask.pol`` is present (i.e. the meteo path), we fall back to validating
the model piece-by-piece (crsdef/crsloc/roughness/structures/storage/obs via
their own models, the net via NetworkModel, the .pol via PolyFile) and we do
NOT count the meteo-parse failure as a problem.  If FMModel fails with no rain
mask present, that is a genuine problem and is reported.

ASCII-only strings (Windows cp1258 console safety).
"""

from __future__ import annotations

import os


# Files that must always be present in a produced base model.
_REQUIRED = [
    "FlowFM.mdu",
    "FlowFM_net.nc",
    "crsdef.ini",
    "crsloc.ini",
    "roughness.ini",
    "structures.ini",
    "obs.ini",
    "forcing.ext",
    "dimr_config.xml",
]


def _crossloc_definition_ids(crsdef_model) -> set:
    ids = set()
    for d in getattr(crsdef_model, "definition", []) or []:
        did = getattr(d, "id", None)
        if did is not None:
            ids.add(str(did))
    return ids


def _validate_pieces(out_dir, problems) -> None:
    """Parse each sub-file directly; append a problem string per failure.

    Also runs the best-effort reference checks.  Used both as the meteo-bug
    fallback and to perform the dangling-reference checks regardless.
    """
    from hydrolib.core.dflowfm.crosssection.models import CrossDefModel, CrossLocModel
    from hydrolib.core.dflowfm.friction.models import FrictionModel
    from hydrolib.core.dflowfm.structure.models import StructureModel
    from hydrolib.core.dflowfm.obs.models import ObservationPointModel
    from hydrolib.core.dflowfm.net.models import NetworkModel

    crsdef_model = None
    crsloc_model = None
    friction_model = None

    def _p(path):
        return os.path.join(out_dir, path)

    # crsdef
    try:
        crsdef_model = CrossDefModel(filepath=_p("crsdef.ini"))
    except Exception as exc:  # noqa: BLE001
        problems.append(f"crsdef.ini parse failed: {exc}")

    # crsloc
    try:
        crsloc_model = CrossLocModel(filepath=_p("crsloc.ini"))
    except Exception as exc:  # noqa: BLE001
        problems.append(f"crsloc.ini parse failed: {exc}")

    # roughness
    try:
        friction_model = FrictionModel(filepath=_p("roughness.ini"))
    except Exception as exc:  # noqa: BLE001
        problems.append(f"roughness.ini parse failed: {exc}")

    # structures
    try:
        StructureModel(filepath=_p("structures.ini"))
    except Exception as exc:  # noqa: BLE001
        problems.append(f"structures.ini parse failed: {exc}")

    # obs
    try:
        ObservationPointModel(filepath=_p("obs.ini"))
    except Exception as exc:  # noqa: BLE001
        problems.append(f"obs.ini parse failed: {exc}")

    # storage (conditional)
    if os.path.exists(_p("storagenodes.ini")):
        try:
            from hydrolib.core.dflowfm.storagenode.models import StorageNodeModel
            StorageNodeModel(filepath=_p("storagenodes.ini"))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"storagenodes.ini parse failed: {exc}")

    # inifield (conditional)
    if os.path.exists(_p("inifield.ini")):
        try:
            from hydrolib.core.dflowfm.inifield.models import IniFieldModel
            IniFieldModel(filepath=_p("inifield.ini"))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"inifield.ini parse failed: {exc}")

    # net
    branch_ids = None
    try:
        netmodel = NetworkModel(filepath=_p("FlowFM_net.nc"))
        try:
            mesh1d = netmodel.network._mesh1d
            ids = list(getattr(mesh1d, "branch_names", None) or [])
            if ids:
                branch_ids = set(str(b) for b in ids)
        except Exception:  # noqa: BLE001
            branch_ids = None
    except Exception as exc:  # noqa: BLE001
        problems.append(f"FlowFM_net.nc parse failed: {exc}")

    # rain_mask.pol (conditional -- validates the meteo targetmaskfile)
    if os.path.exists(_p("rain_mask.pol")):
        try:
            from hydrolib.core.dflowfm.polyfile.models import PolyFile
            PolyFile(filepath=_p("rain_mask.pol"))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"rain_mask.pol parse failed: {exc}")

    # --- reference checks (best-effort) ---
    if crsdef_model is not None and crsloc_model is not None:
        def_ids = _crossloc_definition_ids(crsdef_model)
        for loc in getattr(crsloc_model, "crosssection", []) or []:
            did = getattr(loc, "definitionid", None)
            if did is not None and str(did) not in def_ids:
                problems.append(
                    f"crossloc definitionid '{did}' missing from crsdef"
                )
            bid = getattr(loc, "branchid", None)
            if bid is not None and branch_ids is not None:
                if str(bid) not in branch_ids:
                    problems.append(
                        f"crossloc branchid '{bid}' missing from mesh1d branches"
                    )

    # friction ids referenced by crossdef must exist in roughness
    if crsdef_model is not None and friction_model is not None:
        frict_ids = set()
        for g in getattr(friction_model, "global_", []) or []:
            fid = getattr(g, "frictionid", None)
            if fid is not None:
                frict_ids.add(str(fid))
        for d in getattr(crsdef_model, "definition", []) or []:
            fid = getattr(d, "frictionid", None)
            if fid is not None and str(fid) not in frict_ids:
                problems.append(
                    f"crossdef frictionid '{fid}' missing from roughness"
                )


def validate_model(out_dir) -> list:
    """Round-trip validate a produced base model folder.

    Returns a list of problem strings (empty == OK).
    """
    out_dir = str(out_dir)
    problems: list = []

    # --- required files present ---
    for name in _REQUIRED:
        if not os.path.exists(os.path.join(out_dir, name)):
            problems.append(f"missing required file: {name}")

    has_rain_mask = os.path.exists(os.path.join(out_dir, "rain_mask.pol"))

    # --- FMModel round-trip (may hit the meteo bug) ---
    from hydrolib.core.dflowfm.mdu.models import FMModel

    mdu_path = os.path.join(out_dir, "FlowFM.mdu")
    if os.path.exists(mdu_path):
        try:
            FMModel(filepath=mdu_path)
        except Exception as exc:  # noqa: BLE001
            # Only the KNOWN meteo targetmaskfile round-trip bug is tolerated,
            # and only when a rain mask is actually present. We discriminate on
            # the exception text (it names targetmaskfile / PolyFile) so that any
            # OTHER FMModel failure -- corrupt MDU header, bad field value, etc.
            # -- is still reported as a real problem rather than silently hidden.
            msg = str(exc)
            is_meteo_bug = has_rain_mask and (
                "targetmaskfile" in msg or "PolyFile" in msg
            )
            if is_meteo_bug:
                print(
                    "  validate: FMModel parse skipped (known meteo "
                    "targetmaskfile round-trip bug); validating pieces "
                    "individually"
                )
            else:
                problems.append(f"FMModel parse failed: {exc}")

    # Always run piece-wise checks (also provides reference checks even when the
    # full FMModel parse succeeded).
    _validate_pieces(out_dir, problems)

    # --- DIMR round-trip ---
    dimr_path = os.path.join(out_dir, "dimr_config.xml")
    if os.path.exists(dimr_path):
        try:
            from hydrolib.core.dimr.models import DIMR
            DIMR(filepath=dimr_path)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"dimr_config.xml parse failed: {exc}")

    # --- summary ---
    print(f"  validate: {len(problems)} problem(s)")
    for p in problems:
        print(f"    - {p}")

    return problems
