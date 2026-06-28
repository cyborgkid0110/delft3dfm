"""
Create, edit, and validate a planning-map GeoPackage (planning_map.gpkg).

The planning-map GPKG stores three layers used by the Delft3D conversion
pipeline: cat_landuses (roughness catalog), ground (2D domain polygons),
and roof (building rooftop polygons). All geometry is in EPSG:4326.

Task 9 contract: roof layer MUST have columns 'surface' (String) and
'slope' (Real) so build_nwrw picks up per-roof overrides.

Implementation note on cat_landuses (non-spatial layer):
  geopandas / pyogrio can write a GeoDataFrame with null/empty geometry
  to GPKG as an attribute-only table. We do this by creating a GeoDataFrame
  with an empty geometry column and no CRS. Some versions of pyogrio require
  the geometry column to be present but it can be all-None. The resulting
  GPKG layer is read back by read_planning_map via gpd.read_file(...,
  layer='cat_landuses'), which tolerates the null-geometry records.

Usage:
    .venv/Scripts/python.exe src/tools/planning_map.py create --gpkg out.gpkg
    .venv/Scripts/python.exe src/tools/planning_map.py add-landuse --gpkg out.gpkg --id STREET --manning 0.017
    .venv/Scripts/python.exe src/tools/planning_map.py add-ground --gpkg out.gpkg --geojson poly.geojson --cellsize 10 --landuse STREET
    .venv/Scripts/python.exe src/tools/planning_map.py add-roof --gpkg out.gpkg --geojson roof.geojson --roughness 0.018 --width 30
    .venv/Scripts/python.exe src/tools/planning_map.py list --gpkg out.gpkg
    .venv/Scripts/python.exe src/tools/planning_map.py validate --gpkg out.gpkg
"""
import argparse
import json
import os
import sys

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ---------------------------------------------------------------------------
# Field schemas (name, pandas dtype)
# ---------------------------------------------------------------------------

# Ground polygon attributes
GROUND_FIELDS = [
    ("code",            "object"),
    ("custom_code",     "object"),
    ("descript",        "object"),
    ("cellsize",        "float64"),
    ("annotation",      "object"),
    ("landuse",         "object"),
    ("custom_roughness","float64"),
    ("scs_cn",          "float64"),
]

# Roof polygon attributes
# Task 9 contract: 'surface' (str) and 'slope' (float) must be present
ROOF_FIELDS = [
    ("code",         "object"),
    ("custom_code",  "object"),
    ("descript",     "object"),
    ("cellsize",     "float64"),
    ("slope",        "float64"),   # per-roof slope override (Task 9)
    ("width",        "float64"),
    ("roughness",    "float64"),
    ("isconnected",  "Int64"),
    ("outlet_code",  "object"),
    ("outlet_vol",   "float64"),
    ("street_vol",   "float64"),
    ("infiltr_vol",  "float64"),
    ("annotation",   "object"),
    ("surface",      "object"),    # per-roof surface override (Task 9)
]

# Landuse catalog attributes (no geometry)
LANDUSE_FIELDS = [
    ("idval",    "object"),
    ("descript", "object"),
    ("manning",  "float64"),
]


# ---------------------------------------------------------------------------
# Geometry parsing
# ---------------------------------------------------------------------------

def _parse_geometry(geojson_arg):
    """Parse geometry from an inline GeoJSON string or a path to a .geojson file."""
    # Try as file path first
    if os.path.isfile(geojson_arg):
        try:
            gdf = gpd.read_file(geojson_arg)
            if len(gdf) > 0:
                return gdf.geometry.iloc[0]
        except Exception:
            pass
        # Fallback: read raw JSON
        with open(geojson_arg, "r", encoding="utf-8") as fh:
            obj = json.load(fh)
    else:
        try:
            obj = json.loads(geojson_arg)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Cannot parse geometry: {exc}") from exc

    # Unwrap Feature/FeatureCollection
    if obj.get("type") == "FeatureCollection":
        obj = obj["features"][0]["geometry"]
    elif obj.get("type") == "Feature":
        obj = obj["geometry"]

    return shape(obj)


# ---------------------------------------------------------------------------
# Low-level GPKG read / append helpers
# ---------------------------------------------------------------------------

def _read_layer(gpkg_path, layer_name):
    """Read a layer; return empty GeoDataFrame on error."""
    try:
        return gpd.read_file(gpkg_path, layer=layer_name)
    except Exception:
        return gpd.GeoDataFrame()


def _write_spatial_layer(gpkg_path, layer_name, gdf, mode="w"):
    """Write a GeoDataFrame with real geometry to GPKG."""
    gdf.to_file(gpkg_path, layer=layer_name, driver="GPKG", mode=mode)


def _write_catalog_layer(gpkg_path, layer_name, df):
    """Write a non-spatial catalog table to GPKG.

    Strategy: wrap in a GeoDataFrame with null geometry (no CRS). This works
    with pyogrio/fiona under geopandas 0.14+. The geometry column is all-None
    so the layer reads back as an attribute table. We write in append mode if
    the GPKG already exists (first layer uses 'w', catalog uses 'a').
    """
    gdf = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries([None] * len(df)))
    # Write without CRS (non-spatial)
    gdf.to_file(gpkg_path, layer=layer_name, driver="GPKG", mode="a")


def _append_row_to_spatial_layer(gpkg_path, layer_name, geom, attrs, fields):
    """Append one feature to a spatial layer.

    Reads existing data, appends the new row, rewrites the layer.
    """
    existing = _read_layer(gpkg_path, layer_name)

    # Build new row dict
    row = {name: attrs.get(name) for name, _ in fields}
    row["geometry"] = geom

    new_gdf = gpd.GeoDataFrame([row], crs="EPSG:4326")

    if len(existing) == 0:
        combined = new_gdf
    else:
        if existing.crs is None:
            existing = existing.set_crs("EPSG:4326")
        combined = pd.concat([existing, new_gdf], ignore_index=True)
        combined = gpd.GeoDataFrame(combined, crs="EPSG:4326")

    # Rewrite with mode='a' replacing the layer
    combined.to_file(gpkg_path, layer=layer_name, driver="GPKG", mode="a")


def _append_row_to_catalog(gpkg_path, layer_name, attrs, fields):
    """Append one row to a non-spatial catalog layer."""
    existing = _read_layer(gpkg_path, layer_name)

    row = {name: attrs.get(name) for name, _ in fields}
    new_df = pd.DataFrame([row])

    if len(existing) == 0:
        combined_df = new_df
    else:
        # Drop geometry column from existing if present
        if "geometry" in existing.columns:
            existing = existing.drop(columns=["geometry"])
        combined_df = pd.concat([existing, new_df], ignore_index=True)

    _write_catalog_layer(gpkg_path, layer_name, combined_df)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_create(args):
    path = os.path.abspath(args.gpkg)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    if os.path.exists(path):
        os.remove(path)

    # -- ground layer (Polygon) --
    ground_data = {name: pd.Series(dtype=dtype) for name, dtype in GROUND_FIELDS}
    ground_gdf = gpd.GeoDataFrame(ground_data, geometry=gpd.GeoSeries([], dtype="geometry"), crs="EPSG:4326")
    ground_gdf.to_file(path, layer="ground", driver="GPKG", mode="w")

    # -- roof layer (Polygon) --
    roof_data = {name: pd.Series(dtype=dtype) for name, dtype in ROOF_FIELDS}
    roof_gdf = gpd.GeoDataFrame(roof_data, geometry=gpd.GeoSeries([], dtype="geometry"), crs="EPSG:4326")
    roof_gdf.to_file(path, layer="roof", driver="GPKG", mode="a")

    # -- cat_landuses (non-spatial catalog) --
    lu_data = {name: pd.Series(dtype=dtype) for name, dtype in LANDUSE_FIELDS}
    lu_df = pd.DataFrame(lu_data)
    _write_catalog_layer(path, "cat_landuses", lu_df)

    print(f"Created: {path}")
    print("  Layers: ground, roof, cat_landuses")


def cmd_add_landuse(args):
    path = os.path.abspath(args.gpkg)
    attrs = {
        "idval":   args.id,
        "manning": float(args.manning),
        "descript": args.descript or "",
    }
    _append_row_to_catalog(path, "cat_landuses", attrs, LANDUSE_FIELDS)
    print(f"Added land use: {args.id} (manning={args.manning})")


def cmd_add_ground(args):
    path = os.path.abspath(args.gpkg)
    geom = _parse_geometry(args.geojson)
    if geom.geom_type != "Polygon":
        print(f"ERROR: Expected Polygon geometry, got {geom.geom_type}")
        sys.exit(1)

    attrs = {
        "cellsize":        float(args.cellsize),
        "landuse":         args.landuse or "",
        "custom_roughness": float(args.custom_roughness) if args.custom_roughness is not None else None,
        "scs_cn":          float(args.scs_cn) if args.scs_cn is not None else None,
        "code":            args.code or "",
        "descript":        args.descript or "",
        "custom_code":     "",
        "annotation":      "",
    }
    _append_row_to_spatial_layer(path, "ground", geom, attrs, GROUND_FIELDS)
    print(f"Added ground polygon (cellsize={args.cellsize}, landuse={args.landuse})")


def cmd_add_roof(args):
    path = os.path.abspath(args.gpkg)
    geom = _parse_geometry(args.geojson)
    if geom.geom_type != "Polygon":
        print(f"ERROR: Expected Polygon geometry, got {geom.geom_type}")
        sys.exit(1)

    attrs = {
        "roughness":   float(args.roughness),
        "width":       float(args.width),
        "cellsize":    float(args.cellsize) if args.cellsize is not None else 30.0,
        "slope":       float(args.slope) if args.slope is not None else None,
        "surface":     args.surface or "",
        "code":        args.code or "",
        "custom_code": "",
        "descript":    "",
        "isconnected": None,
        "outlet_code": "",
        "outlet_vol":  None,
        "street_vol":  None,
        "infiltr_vol": None,
        "annotation":  "",
    }
    _append_row_to_spatial_layer(path, "roof", geom, attrs, ROOF_FIELDS)
    print(f"Added roof polygon (roughness={args.roughness}, width={args.width})")


def cmd_list(args):
    path = os.path.abspath(args.gpkg)

    lu = _read_layer(path, "cat_landuses")
    print(f"cat_landuses: {len(lu)} entries")
    for _, row in lu.iterrows():
        idval = row.get("idval", "")
        manning = row.get("manning", "")
        descript = row.get("descript", "") or ""
        print(f"  {str(idval):20s}  n={manning}  {descript}")

    ground = _read_layer(path, "ground")
    print(f"\nground: {len(ground)} polygons")
    for _, row in ground.iterrows():
        code = row.get("code") or f"fid={row.name}"
        landuse = row.get("landuse") or ""
        cellsize = row.get("cellsize")
        cr = row.get("custom_roughness")
        roughness_str = f"custom_n={cr}" if (cr is not None and str(cr) != "nan") else f"landuse={landuse}"
        print(f"  {str(code):20s}  cellsize={cellsize}  {roughness_str}")

    roof = _read_layer(path, "roof")
    print(f"\nroof: {len(roof)} polygons")
    for _, row in roof.iterrows():
        code = row.get("code") or f"fid={row.name}"
        roughness = row.get("roughness")
        width = row.get("width")
        slope = row.get("slope")
        surface = row.get("surface") or ""
        print(f"  {str(code):20s}  n={roughness}  w={width}  slope={slope}  surface={surface}")


def cmd_validate(args):
    path = os.path.abspath(args.gpkg)
    ok = True

    lu = _read_layer(path, "cat_landuses")
    lu_ids = set()
    for _, row in lu.iterrows():
        idval = row.get("idval")
        manning = row.get("manning")
        if not idval:
            print("  ERROR: cat_landuses entry with empty idval")
            ok = False
        if manning is None or str(manning) == "nan":
            print(f"  ERROR: cat_landuses '{idval}' has NULL manning")
            ok = False
        lu_ids.add(idval)

    ground = _read_layer(path, "ground")
    for _, row in ground.iterrows():
        code = row.get("code") or f"fid={row.name}"
        landuse = row.get("landuse")
        cr = row.get("custom_roughness")
        geom = row.get("geometry")

        if landuse and landuse not in lu_ids:
            print(f"  ERROR: ground '{code}' references unknown landuse '{landuse}'")
            ok = False
        cr_none = cr is None or str(cr) == "nan"
        if not landuse and cr_none:
            print(f"  ERROR: ground '{code}' has neither landuse nor custom_roughness")
            ok = False
        if geom is None or (hasattr(geom, "is_empty") and geom.is_empty):
            print(f"  ERROR: ground '{code}' has NULL geometry")
            ok = False

    roof = _read_layer(path, "roof")
    for _, row in roof.iterrows():
        code = row.get("code") or f"fid={row.name}"
        geom = row.get("geometry")
        roughness = row.get("roughness")
        width = row.get("width")

        if geom is None or (hasattr(geom, "is_empty") and geom.is_empty):
            print(f"  ERROR: roof '{code}' has NULL geometry")
            ok = False
        if roughness is None or str(roughness) == "nan":
            print(f"  ERROR: roof '{code}' has NULL roughness")
            ok = False
        elif float(roughness) <= 0:
            print(f"  ERROR: roof '{code}' has non-positive roughness ({roughness})")
            ok = False
        if width is None or str(width) == "nan":
            print(f"  ERROR: roof '{code}' has NULL width")
            ok = False
        elif float(width) <= 0:
            print(f"  ERROR: roof '{code}' has non-positive width ({width})")
            ok = False

    if ok:
        print("Validation: PASSED")
    else:
        print("Validation: FAILED")
    return ok


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Create, edit, and validate planning-map GeoPackage files"
    )
    sub = parser.add_subparsers(dest="command")
    sub.required = True

    p_create = sub.add_parser("create", help="Create empty planning_map.gpkg")
    p_create.add_argument("--gpkg", required=True)

    p_add_lu = sub.add_parser("add-landuse", help="Add land use catalog entry")
    p_add_lu.add_argument("--gpkg", required=True)
    p_add_lu.add_argument("--id", required=True)
    p_add_lu.add_argument("--manning", required=True, type=float)
    p_add_lu.add_argument("--descript", default=None)

    p_add_gr = sub.add_parser("add-ground", help="Add ground polygon")
    p_add_gr.add_argument("--gpkg", required=True)
    p_add_gr.add_argument("--geojson", required=True)
    p_add_gr.add_argument("--cellsize", required=True, type=float)
    p_add_gr.add_argument("--landuse", default=None)
    p_add_gr.add_argument("--custom_roughness", default=None, type=float)
    p_add_gr.add_argument("--scs_cn", default=None, type=float)
    p_add_gr.add_argument("--code", default=None)
    p_add_gr.add_argument("--descript", default=None)

    p_add_rf = sub.add_parser("add-roof", help="Add roof polygon")
    p_add_rf.add_argument("--gpkg", required=True)
    p_add_rf.add_argument("--geojson", required=True)
    p_add_rf.add_argument("--roughness", required=True, type=float)
    p_add_rf.add_argument("--width", required=True, type=float)
    p_add_rf.add_argument("--cellsize", default=30.0, type=float)
    p_add_rf.add_argument("--slope", default=None, type=float)
    p_add_rf.add_argument("--surface", default=None)
    p_add_rf.add_argument("--code", default=None)

    p_list = sub.add_parser("list", help="List all features")
    p_list.add_argument("--gpkg", required=True)

    p_val = sub.add_parser("validate", help="Check referential integrity")
    p_val.add_argument("--gpkg", required=True)

    args = parser.parse_args()

    handlers = {
        "create":      cmd_create,
        "add-landuse": cmd_add_landuse,
        "add-ground":  cmd_add_ground,
        "add-roof":    cmd_add_roof,
        "list":        cmd_list,
        "validate":    cmd_validate,
    }

    try:
        result = handlers[args.command](args)
        if args.command == "validate" and result is False:
            sys.exit(1)
    except SystemExit:
        raise
    except Exception as exc:
        safe = str(exc).encode("ascii", "replace").decode("ascii")
        print(f"ERROR: {safe}")
        sys.exit(1)


if __name__ == "__main__":
    main()
