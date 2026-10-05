"""使い方:
shp2osm INPUT.shp [INPUT.shp ...] OUTPUT.osm [OUTPUT.osm.pbf ...]

入力（.shp）を複数指定すると、1つのデータにまとめて変換する（隣り合うメッシュをつなげるときに使う）。
"""

import sys

from shp2osm.convert import convert


def main() -> None:
    args = sys.argv[1:]
    shp_paths = [a for a in args if a.lower().endswith(".shp")]
    out_paths = [a for a in args if not a.lower().endswith(".shp")]
    if not shp_paths or not out_paths:
        sys.exit(__doc__)
    stats = convert(shp_paths, out_paths)
    print("  ".join(f"{k}: {v}" for k, v in stats.items()))


if __name__ == "__main__":
    main()
