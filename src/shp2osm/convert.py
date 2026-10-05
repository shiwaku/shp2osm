"""Shapefile を読み、ノードを共有したウェイとして OSM 形式に書き出す。

- 同じ座標の頂点は1つのノードとして共有する（道路ネットワークの接続性を保つため）
- 複数の Shapefile を渡すと1つにまとめる。N13 はメッシュ境界で端点の座標が一致するので、境界でもノードを共有する
- ID は 1 から振る仮の値（OSM 本体へのアップロード用ではない）
"""

from collections.abc import Sequence
from itertools import pairwise

import osmium
import shapefile

from shp2osm.tags import road_tags

# 座標を同一とみなす精度（小数点以下7桁 ≒ 1cm。OSM の座標精度と同じ）
PRECISION = 7


def build(
    shp_paths: Sequence[str],
) -> tuple[dict[tuple[float, float], int], list[tuple[list[int], dict[str, str]]], int]:
    """Shapefile（複数可）からノードとウェイを組み立てる。(ノード, ウェイ, 地物数) を返す。"""
    node_ids = {}  # (lon, lat) → node id
    ways = []  # (node id list, tags)
    features = 0
    for shp_path in shp_paths:
        reader = shapefile.Reader(shp_path, encoding="utf-8")
        features += len(reader)
        for sr in reader.iterShapeRecords():
            parts = [*sr.shape.parts, len(sr.shape.points)]
            tags = road_tags(sr.record.as_dict())
            for start, end in pairwise(parts):
                refs = []
                for lon, lat in sr.shape.points[start:end]:
                    key = (round(lon, PRECISION), round(lat, PRECISION))
                    nid = node_ids.setdefault(key, len(node_ids) + 1)
                    if not refs or refs[-1] != nid:  # 連続する重複点は除く
                        refs.append(nid)
                if len(refs) >= 2:
                    ways.append((refs, tags))
    return node_ids, ways, features


def convert(shp_paths: Sequence[str], out_paths: Sequence[str]) -> dict[str, int]:
    """Shapefile（複数可）を変換して out_paths に書き出す。形式は拡張子（.osm / .osm.pbf）で決まる。"""
    node_ids, ways, features = build(shp_paths)

    writers = [osmium.SimpleWriter(p, overwrite=True) for p in out_paths]
    try:
        for (lon, lat), nid in node_ids.items():
            node = osmium.osm.mutable.Node(id=nid, version=1, location=(lon, lat))
            for w in writers:
                w.add_node(node)
        for wid, (refs, tags) in enumerate(ways, start=1):
            way = osmium.osm.mutable.Way(id=wid, version=1, nodes=refs, tags=tags)
            for w in writers:
                w.add_way(way)
    finally:
        for w in writers:
            w.close()

    return {"features": features, "nodes": len(node_ids), "ways": len(ways)}
