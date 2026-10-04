"""国土数値情報（道路）N13 の Shapefile を OSM 形式（.osm / .osm.pbf）に変換する。"""

from shp2osm.convert import convert
from shp2osm.tags import road_tags

__all__ = ["convert", "road_tags"]
