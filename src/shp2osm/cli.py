"""使い方:
shp2osm INPUT.shp OUTPUT.osm [OUTPUT.osm.pbf ...]
"""

import sys

from shp2osm.convert import convert


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    stats = convert(sys.argv[1], *sys.argv[2:])
    print("  ".join(f"{k}: {v}" for k, v in stats.items()))


if __name__ == "__main__":
    main()
