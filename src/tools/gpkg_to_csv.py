"""
Convert GeoPackage layers to standardized CSV datasets.

Reads vector layers from a .gpkg file and writes standardized CSVs
with the full schema from dataset.md. Attribute fields present in both
the GPKG layer and the CSV schema are copied; fields defined in the schema
but absent in the GPKG are written as empty strings. Geometry is
reprojected to WGS84 GeoJSON (Shape/RouteShape).

Output folder structure:
    <dst>/
      mang_luoi_song_ho_kenh_muong/canals.csv
      mang_luoi_song_ho_kenh_muong/rivers.csv
      mang_luoi_song_ho_kenh_muong/lakes.csv
      thoat_nuoc/sewers.csv
      thoat_nuoc/manholes.csv
      thoat_nuoc/pumps.csv
      thoat_nuoc/weir.csv
      thoat_nuoc/orifices.csv
      thoat_nuoc/outfalls.csv
      thuy_van/hyetographs.csv

Usage:
    .venv/Scripts/python.exe src/tools/gpkg_to_csv.py --gpkg drawing.gpkg --dst dataset/
"""
import argparse
import csv
import json
import os
import sys

import geopandas as gpd
from shapely.geometry import mapping

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


# ===========================================================================
# Standardized CSV column schemas (ported verbatim from SWMM gpkg_to_csv.py)
# ===========================================================================

CANALS_COLS = [
    "ID", "Name", "Type", "Length_m", "Width_m", "BedElev_m", "LeftBank",
    "RightBank", "SlopCoef", "Material", "Grade", "Purpose", "SvcArea",
    "IrrigSys", "FlowDir", "FromNode", "ToNode", "RouteShape", "XSType",
    "WtrLevel", "XSArea",
]

RIVERS_COLS = [
    "ID", "Name", "Code", "Strahler", "Length_m", "Width_m", "BedElev_m",
    "BankElev_m", "FlowDir", "FromNode", "ToNode", "RouteShape", "XSType",
    "Material", "Basin", "IrrigSys",
]

LAKES_COLS = [
    "ID", "Name", "Group", "Area_ha", "BedArea_ha", "Vol_m3", "BedElev_m",
    "CrestElv", "BankElev_m", "NatWtrLvl", "WetLvl_m", "DryLvl_m",
    "NumInlets", "Perim_m", "IrrigSys", "Shape",
]

SEWERS_COLS = [
    "ID", "Name", "Type", "Diam_mm", "Size_mm", "Length_m", "Material",
    "XSArea", "FlowDir", "FromNode", "ToNode", "RouteShape", "XSType",
    "StreetID", "DrainZone", "Catchment",
]

MANHOLES_COLS = [
    "ID", "Name", "Type", "Area_m2", "Size_m", "CoverType", "InvElev_m",
    "RimElev_m", "SewerLine", "StreetID", "DrainZone", "Catchment",
    "Width", "Length", "InletDepth", "InletEffic", "Shape",
]

PUMPS_COLS = [
    "ID", "Name", "Source", "SewerLine", "Type", "Grade", "NumPumps",
    "Cap_m3s", "InElev_m", "OutElev_m", "AutoMonit", "TrashScr", "Purpose",
    "SvcArea", "IrrigSys", "StreetID", "Shape",
]

WEIRS_COLS = [
    "ID", "Name", "Type", "Form", "Chainage", "River", "Basin", "Length_m",
    "Width_m", "Height_m", "Diam_m", "Openings", "InvElev_m", "CrestElv",
    "Grade", "Operation", "Purpose", "Receiver", "Project", "SvcArea",
    "IrrigSys", "Shape",
]

ORIFICES_COLS = [
    "ID", "Name", "Source", "Position", "Type", "Form", "Length_m",
    "Width_m", "Height_m", "Openings", "InvElev_m", "CrestElv", "DischCoef",
    "ClearSpan", "SillElev", "GateMtrl", "GateCtrl", "Purpose", "Receiver",
    "SvcArea", "Grade", "Shape",
]

OUTFALLS_COLS = [
    "ID", "Name", "Type", "Elev_m", "FixedStage", "FlapGate", "Receiver",
    "SewerLine", "Shape",
]

HYETOGRAPH_COLS = ["ID", "Name", "SeriesName", "Shape"]

# Mapping: gpkg_layer_name -> (csv_relative_path, column_list, geom_col_name)
LAYER_MAP = {
    "canals":     ("mang_luoi_song_ho_kenh_muong/canals.csv", CANALS_COLS, "RouteShape"),
    "rivers":     ("mang_luoi_song_ho_kenh_muong/rivers.csv", RIVERS_COLS, "RouteShape"),
    "lakes":      ("mang_luoi_song_ho_kenh_muong/lakes.csv", LAKES_COLS, "Shape"),
    "sewers":     ("thoat_nuoc/sewers.csv", SEWERS_COLS, "RouteShape"),
    "manholes":   ("thoat_nuoc/manholes.csv", MANHOLES_COLS, "Shape"),
    "pumps":      ("thoat_nuoc/pumps.csv", PUMPS_COLS, "Shape"),
    "weirs":      ("thoat_nuoc/weir.csv", WEIRS_COLS, "Shape"),
    "orifices":   ("thoat_nuoc/orifices.csv", ORIFICES_COLS, "Shape"),
    "outfalls":   ("thoat_nuoc/outfalls.csv", OUTFALLS_COLS, "Shape"),
    "hyetograph": ("thuy_van/hyetographs.csv", HYETOGRAPH_COLS, "Shape"),
}


# ===========================================================================
# Required-field validation (ported from SWMM gpkg_to_csv.py)
# ===========================================================================

BREAKING_FIELDS = {
    "hyetograph": ["SeriesName"],
}

ADVISORY_FIELDS = {
    "canals":     ["Name", "Length_m", "FromNode", "ToNode"],
    "rivers":     ["Strahler", "Length_m", "FromNode", "ToNode"],
    "lakes":      ["Name", "Area_ha", "Vol_m3", "BedElev_m"],
    "sewers":     ["Name", "Diam_mm", "Length_m", "FromNode", "ToNode"],
    "manholes":   ["Name", "InvElev_m", "RimElev_m"],
    "pumps":      ["Name", "Cap_m3s"],
    "weirs":      ["Name", "InvElev_m"],
    "orifices":   ["Name", "Openings", "InvElev_m"],
    "outfalls":   ["Name"],
    "hyetograph": ["Name"],
}


def _is_empty(val):
    if val is None:
        return True
    s = str(val).strip()
    return s == "" or s.lower() in ("null", "none", "nan")


# ===========================================================================
# Geometry helpers (geopandas/shapely, no GDAL)
# ===========================================================================

def _geom_to_geojson(geom):
    """Convert a shapely geometry to a compact GeoJSON string (WGS84 coords)."""
    if geom is None or geom.is_empty:
        return ""
    d = mapping(geom)
    # Round coordinates to 8 decimal places
    d = _round_mapping(d)
    return json.dumps(d, separators=(",", ":"))


def _round_mapping(d):
    """Recursively round all coordinate values in a GeoJSON-like mapping."""
    gtype = d["type"]
    coords = d["coordinates"]
    return {"type": gtype, "coordinates": _round_coords(coords)}


def _round_coords(coords):
    """Recursively round a nested coordinate structure."""
    if not coords:
        return coords
    first = coords[0]
    if isinstance(first, (int, float)):
        # It's a single point: [x, y, ...]
        return [round(v, 8) for v in coords]
    return [_round_coords(c) for c in coords]


# ===========================================================================
# Converter
# ===========================================================================

def _list_gpkg_layers(gpkg_path):
    """Return list of layer names in a GPKG (via pyogrio or fiona fallback)."""
    try:
        import pyogrio
        layers_arr = pyogrio.list_layers(gpkg_path)
        return [row[0] for row in layers_arr]
    except Exception:
        pass
    try:
        import fiona
        return fiona.listlayers(gpkg_path)
    except Exception:
        return []


def convert_layer(gpkg_path, layer_name, csv_path, columns, geom_col):
    """Convert one GPKG layer to a standardized CSV using geopandas.

    Returns (n_written, rows) or (-1, []) if layer not found.
    """
    try:
        gdf = gpd.read_file(gpkg_path, layer=layer_name)
    except Exception:
        return -1, []

    # Reproject to WGS84 if needed
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    gpkg_cols = set(gdf.columns)
    written = []

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for idx, row_s in gdf.iterrows():
            row = {col: "" for col in columns}

            for col in columns:
                if col == geom_col:
                    continue
                if col in gpkg_cols:
                    val = row_s[col]
                    if val is None or (hasattr(val, "__class__") and
                                       val.__class__.__name__ in ("float",) and
                                       str(val) == "nan"):
                        row[col] = ""
                    else:
                        import math
                        try:
                            if isinstance(val, float) and math.isnan(val):
                                row[col] = ""
                            else:
                                row[col] = "" if val is None else val
                        except Exception:
                            row[col] = val if val is not None else ""

            if "ID" in columns and _is_empty(row.get("ID")):
                row["ID"] = idx

            geom = row_s.geometry if hasattr(row_s, "geometry") else None
            row[geom_col] = _geom_to_geojson(geom)

            writer.writerow(row)
            written.append(row)

    return len(written), written


def _row_label(layer_name, row, idx):
    name = row.get("Name")
    if not _is_empty(name):
        return f"{layer_name} '{str(name).strip()}'"
    return f"{layer_name} row {idx} (ID={row.get('ID', '?')})"


def validate_layer_rows(layer_name, rows):
    errors, warnings = [], []
    breaking = BREAKING_FIELDS.get(layer_name, [])
    advisory = ADVISORY_FIELDS.get(layer_name, [])

    advisory_counts = {f: 0 for f in advisory}
    for idx, row in enumerate(rows, start=1):
        label = _row_label(layer_name, row, idx)
        for field in breaking:
            if _is_empty(row.get(field)):
                errors.append(f"ERROR: {label}: required field '{field}' is empty")
        for field in advisory:
            if _is_empty(row.get(field)):
                advisory_counts[field] += 1

    for field, n in advisory_counts.items():
        if n:
            warnings.append(
                f"WARN:  {layer_name}.{field}: empty in {n}/{len(rows)} "
                f"feature(s) (conversion will substitute a default)"
            )
    return errors, warnings


def validate_network_structure(layer_rows):
    errors = []
    n_manholes = len(layer_rows.get("manholes", []))
    n_sewers = len(layer_rows.get("sewers", []))
    n_outfalls = len(layer_rows.get("outfalls", []))

    has_1d_network = n_manholes > 0 or n_sewers > 0
    if has_1d_network and n_outfalls == 0:
        errors.append(
            f"ERROR: 1D network present "
            f"({n_manholes} manhole(s), {n_sewers} sewer(s)) but 0 outfalls. "
            "Draw at least one outfall and connect a sewer's downstream end "
            "(ToNode) to it."
        )
    return errors


def gpkg_to_csv(gpkg, out_dir):
    """Convert all layers found in LAYER_MAP from gpkg to CSV files under out_dir."""
    print(f"GPKG -> CSV: {gpkg} -> {out_dir}")
    print("=" * 60)

    available_layers = set(_list_gpkg_layers(gpkg))

    total = 0
    layer_rows = {}
    for layer_name, (csv_rel, columns, geom_col) in LAYER_MAP.items():
        if layer_name not in available_layers:
            print(f"  SKIP (layer not found): {layer_name}")
            continue
        csv_path = os.path.join(out_dir, csv_rel)
        n, rows = convert_layer(gpkg, layer_name, csv_path, columns, geom_col)
        if n < 0:
            print(f"  SKIP (read error): {layer_name}")
        else:
            print(f"  {layer_name}: {n} features -> {csv_rel}")
            layer_rows[layer_name] = rows
            total += n

    print("=" * 60)
    print(f"Total: {total} features exported to CSV")
    return layer_rows


def main():
    parser = argparse.ArgumentParser(
        description="Convert GeoPackage layers to standardized CSV datasets"
    )
    parser.add_argument("--gpkg", required=True, help="Source GeoPackage file path")
    parser.add_argument("--dst", required=True, help="Destination directory for CSV files")
    parser.add_argument(
        "--no-validate", action="store_true",
        help="Skip required-field validation after export"
    )
    args = parser.parse_args()

    gpkg_path = (
        os.path.join(REPO_DIR, args.gpkg)
        if not os.path.isabs(args.gpkg)
        else args.gpkg
    )
    dst_dir = (
        os.path.join(REPO_DIR, args.dst)
        if not os.path.isabs(args.dst)
        else args.dst
    )

    if not os.path.exists(gpkg_path):
        print(f"ERROR: Cannot open {gpkg_path}")
        sys.exit(1)

    layer_rows = gpkg_to_csv(gpkg_path, dst_dir)

    if args.no_validate:
        return

    errors, warnings = [], []
    for layer_name, rows in layer_rows.items():
        e, w = validate_layer_rows(layer_name, rows)
        errors.extend(e)
        warnings.extend(w)
    errors.extend(validate_network_structure(layer_rows))

    print("\nField validation")
    print("=" * 60)
    for w in warnings:
        print(f"  {w}")
    for e in errors:
        print(f"  {e}")
    if not errors and not warnings:
        print("  All required fields present.")
    print("=" * 60)
    print(
        f"  Validation: {'FAILED' if errors else 'PASSED'} "
        f"({len(errors)} error(s), {len(warnings)} warning(s))"
    )

    if errors:
        print("\nFix the ERROR fields in the drawing GPKG, re-export, and re-run. "
              "(Use --no-validate to bypass.)")
        sys.exit(1)


if __name__ == "__main__":
    main()
