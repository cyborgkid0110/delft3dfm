"""
Create an empty multi-layer drawing GeoPackage with schema layers for digitizing.

Creates one empty typed layer per LAYER_MAP entry from gpkg_to_csv:
  rivers, canals, lakes, sewers, manholes, pumps, weirs, orifices, outfalls, hyetograph

Geometry types:
  - LineString: rivers, canals, sewers
  - Point: lakes, manholes, pumps, weirs, orifices, outfalls, hyetograph

All layers are in EPSG:4326. The .qgz QGIS project file is omitted --
the GPKG layers are directly digitizable in QGIS via drag-and-drop.

Usage:
    .venv/Scripts/python.exe src/tools/gis_template.py create --gpkg drawing.gpkg
    # Name = J_{fid} for every manhole:
    .venv/Scripts/python.exe src/tools/gis_template.py autofill --gpkg drawing.gpkg \\
        --layer manholes --field Name --value-fk fid --prefix J_
    # Constant fill:
    .venv/Scripts/python.exe src/tools/gis_template.py autofill --gpkg drawing.gpkg \\
        --layer manholes --field InvElev_m --value 5.0
"""
import argparse
import os
import sys

import geopandas as gpd
from shapely.geometry import LineString, Point

# Ensure repo root on sys.path so 'src.*' imports resolve when run as script
import pathlib as _pathlib
import sys as _sys
_REPO_ROOT = str(_pathlib.Path(__file__).resolve().parents[2])
if _REPO_ROOT not in _sys.path:
    _sys.path.insert(0, _REPO_ROOT)

from src.tools.gpkg_to_csv import (
    CANALS_COLS,
    RIVERS_COLS,
    LAKES_COLS,
    SEWERS_COLS,
    MANHOLES_COLS,
    PUMPS_COLS,
    WEIRS_COLS,
    ORIFICES_COLS,
    OUTFALLS_COLS,
    HYETOGRAPH_COLS,
)

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Layer specs: name -> (geometry_type_string, columns_list, geom_col_to_exclude)
# geom_col_to_exclude is the CSV column for geometry (Shape/RouteShape) -- not a data field.
TEMPLATE_LAYERS = [
    ("rivers",     "LineString", RIVERS_COLS,     "RouteShape"),
    ("canals",     "LineString", CANALS_COLS,      "RouteShape"),
    ("sewers",     "LineString", SEWERS_COLS,      "RouteShape"),
    ("lakes",      "Point",      LAKES_COLS,       "Shape"),
    ("manholes",   "Point",      MANHOLES_COLS,    "Shape"),
    ("pumps",      "Point",      PUMPS_COLS,       "Shape"),
    ("weirs",      "Point",      WEIRS_COLS,       "Shape"),
    ("orifices",   "Point",      ORIFICES_COLS,    "Shape"),
    ("outfalls",   "Point",      OUTFALLS_COLS,    "Shape"),
    ("hyetograph", "Point",      HYETOGRAPH_COLS,  "Shape"),
]

# Schema fields that hold TEXT, used as the source of truth for autofill type
# matching. The drawing template declares every empty attribute column as REAL,
# so the GPKG itself cannot tell a string field (Name) from a numeric one
# (InvElev_m); this set, derived from the standardized CSV schema (the *_COLS
# lists in gpkg_to_csv), supplies that distinction. Any schema field NOT listed
# here is treated as numeric. 'fid' is the integer feature id (numeric).
TEXT_FIELDS = {
    "ID", "Name", "Code", "Type", "Form", "Material", "Grade", "Purpose",
    "SvcArea", "IrrigSys", "FlowDir", "FromNode", "ToNode", "XSType",
    "CoverType", "SewerLine", "StreetID", "DrainZone", "Catchment", "Group",
    "Source", "Position", "AutoMonit", "TrashScr", "Receiver", "Project",
    "River", "Basin", "Operation", "GateMtrl", "GateCtrl", "FixedStage",
    "FlapGate", "SeriesName", "LeftBank", "RightBank",
}


def _field_is_numeric(field):
    """Whether a schema field holds numbers (True) or text (False).

    'fid' (the integer feature id) is numeric; otherwise a field is numeric iff
    it is not in TEXT_FIELDS.
    """
    if field == "fid":
        return True
    return field not in TEXT_FIELDS


def _empty_gdf(geom_type, attr_cols, crs="EPSG:4326"):
    """Build an empty GeoDataFrame with specified attribute columns and geometry."""
    data = {col: gpd.array.GeometryArray([]) if col == "geometry" else []
            for col in attr_cols}

    if geom_type == "LineString":
        geom_series = gpd.GeoSeries([], dtype="geometry")
    else:
        geom_series = gpd.GeoSeries([], dtype="geometry")

    gdf = gpd.GeoDataFrame(data, geometry=geom_series, crs=crs)
    return gdf


def create_template(gpkg_path):
    """Create the empty drawing GeoPackage with all schema layers."""
    os.makedirs(os.path.dirname(os.path.abspath(gpkg_path)), exist_ok=True)

    # Remove existing file so we start fresh
    if os.path.exists(gpkg_path):
        os.remove(gpkg_path)

    created = []
    for layer_name, geom_type, columns, geom_col in TEMPLATE_LAYERS:
        # Attribute columns = all columns minus the geometry placeholder column
        attr_cols = [c for c in columns if c != geom_col]

        # Build empty GeoDataFrame
        col_data = {col: [] for col in attr_cols}
        gdf = gpd.GeoDataFrame(
            col_data,
            geometry=gpd.GeoSeries([], dtype="geometry"),
            crs="EPSG:4326",
        )

        # Write layer (append mode for subsequent layers).
        # geometry_type MUST be passed explicitly: an empty GeoSeries has no
        # features to infer the type from, so without this GDAL records the
        # generic 'GEOMETRY' type in gpkg_geometry_columns. QGIS then loads
        # such a (typeless, zero-feature) layer as an attribute-only table
        # with nothing drawable -- the layer is not digitizable.
        mode = "w" if not os.path.exists(gpkg_path) else "a"
        gdf.to_file(
            gpkg_path, layer=layer_name, driver="GPKG", mode=mode,
            geometry_type=geom_type,
        )
        created.append(layer_name)
        print(f"  Created layer: {layer_name} ({geom_type}, {len(attr_cols)} attribute cols)")

    return created


def autofill(gpkg_path, layer, field, value=None, value_fk=None, prefix=None):
    """Fill every feature's `field` in a GPKG layer, overwriting existing values.

    Exactly one of `value` / `value_fk` must be given:
      - value:    a constant applied to every row. Must type-match the field
                  (a numeric field requires a numeric value).
      - value_fk: take each row's value from another field. The special name
                  'fid' means the GeoPackage feature id (the integer id QGIS
                  shows). `prefix`, if given, is prepended (string fill only).

    `prefix` is only valid together with `value_fk`.

    The layer is read and rewritten via pyogrio (geopandas engine) rather than a
    raw SQL UPDATE: GeoPackage geometry columns carry RTree spatial-index
    triggers that call SpatiaLite functions (e.g. ST_IsEmpty) unavailable to a
    plain sqlite3 connection, so an in-place UPDATE fails. Rewriting the layer
    rebuilds those triggers cleanly.

    Returns the number of features updated.
    """
    import pyogrio

    # ---- argument validation -------------------------------------------------
    if (value is None) == (value_fk is None):
        raise ValueError("Provide exactly one of --value or --value-fk")
    if prefix is not None and value_fk is None:
        raise ValueError("--prefix is only valid together with --value-fk")

    if not os.path.exists(gpkg_path):
        raise FileNotFoundError(f"GeoPackage not found: {gpkg_path}")
    if layer not in set(pyogrio.list_layers(gpkg_path)[:, 0]):
        raise ValueError(f"Layer '{layer}' not found in {gpkg_path}")

    # fid_as_index=True puts the real GeoPackage feature id in the index.
    gdf = pyogrio.read_dataframe(gpkg_path, layer=layer, fid_as_index=True)
    if field not in gdf.columns:
        raise ValueError(
            f"Field '{field}' not found in layer '{layer}'. "
            f"Available: {', '.join(c for c in gdf.columns if c != gdf.geometry.name)}"
        )

    field_is_numeric = _field_is_numeric(field)

    # ---- compute the new column ---------------------------------------------
    if value is not None:
        # Constant fill. Type-match against the field.
        num = _as_number(value)
        if field_is_numeric and num is None:
            raise ValueError(
                f"Field '{field}' is numeric but --value '{value}' is not a number"
            )
        gdf[field] = num if (num is not None and field_is_numeric) else value
    else:
        # Per-row fill sourced from another field ('fid' = the index).
        if value_fk == "fid":
            src = list(gdf.index)
        elif value_fk in gdf.columns:
            src = list(gdf[value_fk])
        else:
            raise ValueError(
                f"--value-fk '{value_fk}' is not a field in layer '{layer}' "
                "(use 'fid' for the feature id)"
            )
        if prefix is not None:
            if field_is_numeric:
                raise ValueError(
                    f"--prefix produces text but field '{field}' is numeric"
                )
            gdf[field] = [f"{prefix}{v}" for v in src]
        else:
            gdf[field] = src

    pyogrio.write_dataframe(gdf, gpkg_path, layer=layer, append=False)
    return len(gdf)


def _as_number(s):
    """Return int/float for a numeric string, else None.

    Preserves the literal form: '5' -> int 5, '5.0' -> float 5.0, so a decimal
    measurement field keeps its REAL type rather than collapsing to INTEGER.
    """
    try:
        f = float(s)
    except (TypeError, ValueError):
        return None
    text = str(s)
    if "." in text or "e" in text.lower():
        return f
    return int(f)


def _resolve(path):
    """Resolve a path against REPO_DIR if it is relative."""
    return path if os.path.isabs(path) else os.path.join(REPO_DIR, path)


def main():
    parser = argparse.ArgumentParser(
        description="Create / edit a drawing GeoPackage with schema layers"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser(
        "create", help="Create empty drawing GeoPackage with schema layers"
    )
    p_create.add_argument("--gpkg", required=True, help="Output GeoPackage path")

    p_fill = sub.add_parser(
        "autofill",
        help="Fill a layer field with a constant, or per-row from another field",
    )
    p_fill.add_argument("--gpkg", required=True, help="GeoPackage path")
    p_fill.add_argument("--layer", required=True, help="Layer to fill (must exist)")
    p_fill.add_argument("--field", required=True, help="Field to fill (must exist)")
    grp = p_fill.add_mutually_exclusive_group(required=True)
    grp.add_argument(
        "--value", help="Constant value applied to every row (type-matched to the field)"
    )
    grp.add_argument(
        "--value-fk", dest="value_fk",
        help="Source field for a per-row value; 'fid' = the feature id",
    )
    p_fill.add_argument(
        "--prefix",
        help="Text prepended to each --value-fk value (string fields only). "
             "e.g. --value-fk fid --prefix J_  ->  J_1, J_2, ...",
    )

    args = parser.parse_args()
    gpkg_path = _resolve(args.gpkg)

    if args.command == "create":
        print(f"Creating drawing template: {gpkg_path}")
        created = create_template(gpkg_path)
        print(f"Done. {len(created)} layer(s) created.")
        print("Note: .qgz QGIS project omitted -- open the GPKG directly in QGIS.")
    elif args.command == "autofill":
        n = autofill(
            gpkg_path, layer=args.layer, field=args.field,
            value=args.value, value_fk=args.value_fk, prefix=args.prefix,
        )
        if args.value is not None:
            what = f"'{args.value}'"
        else:
            what = f"{args.value_fk}" + (f" prefixed '{args.prefix}'" if args.prefix else "")
        print(f"Autofilled '{args.layer}.{args.field}' = {what} for {n} feature(s).")


if __name__ == "__main__":
    main()
