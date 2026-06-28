"""
CLI entry point for the Delft3D FM conversion pipeline.

Constructs a Conversion object from the given dataset directory and output
directory, then calls .run() to produce a scenario-agnostic Delft3D FM
base model.

Usage:
    .venv/Scripts/python.exe src/tools/run_conversion.py \\
        --dataset dataset/ \\
        --out output/base_model/ \\
        [--dem dem.tif] \\
        [--planning-map planning_map.gpkg] \\
        [--bbox min_lon min_lat max_lon max_lat]

Relative paths are resolved against the repository root (two levels above
this file).
"""
import argparse
import os
import sys

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Ensure repo root is on sys.path so 'src.*' imports work when the script is
# run directly (not via python -m).
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)


def _resolve(path):
    """Resolve a path against REPO_DIR if it is relative."""
    if path is None:
        return None
    return os.path.join(REPO_DIR, path) if not os.path.isabs(path) else path


def main():
    parser = argparse.ArgumentParser(
        description="Run the Delft3D FM conversion pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Minimal (1D-only, no DEM, no planning map)
  run_conversion.py --dataset hanoi/dataset --out hanoi/model

  # Full (DEM + planning map + bbox clip)
  run_conversion.py --dataset hanoi/dataset --out hanoi/model \\
      --dem hanoi/dem.tif \\
      --planning-map hanoi/planning_map.gpkg \\
      --bbox 105.7 20.9 106.0 21.1
""",
    )
    parser.add_argument(
        "--dataset", required=True,
        help="Path to standardized CSV dataset directory",
    )
    parser.add_argument(
        "--out", required=True,
        help="Output directory for the Delft3D FM base model",
    )
    parser.add_argument(
        "--dem", default=None,
        help="Path to DEM raster (.tif/.asc) for bed-level initialisation",
    )
    parser.add_argument(
        "--planning-map", default=None, dest="planning_map",
        help="Path to planning-map GeoPackage (ground/roof/cat_landuses layers)",
    )
    parser.add_argument(
        "--bbox", nargs=4, type=float,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        default=None,
        help="Bounding-box clip: min_lon min_lat max_lon max_lat (EPSG:4326)",
    )
    args = parser.parse_args()

    dataset_dir  = _resolve(args.dataset)
    out_dir      = _resolve(args.out)
    dem_path     = _resolve(args.dem)
    planning_map = _resolve(args.planning_map)
    bbox         = tuple(args.bbox) if args.bbox else None

    from src.conversion.conversion import Conversion

    conv = Conversion(
        dataset_dir,
        out_dir,
        dem_path=dem_path,
        planning_map=planning_map,
        bbox=bbox,
    )
    result = conv.run()
    print(f"Output: {result}")


if __name__ == "__main__":
    main()
