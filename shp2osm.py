"""国土数値情報（道路）N13 の Shapefile を OSM 形式（.osm / .osm.pbf）に変換する。

使い方:
    .venv/bin/python shp2osm.py data/N13-24_6441_SHP/N13-24_6441.shp out/N13-24_6441.osm out/N13-24_6441.osm.pbf

- 同じ座標の頂点は1つのノードとして共有する（道路ネットワークの接続性を保つため）
- N13 の属性コードを OSM のタグに変換し、元の値は ksj:* タグとしても残す
- ID は 1 から振る仮の値（OSM 本体へのアップロード用ではない）
"""
import sys

import osmium
import shapefile

# 座標を同一とみなす精度（小数点以下7桁 ≒ 1cm。OSM の座標精度と同じ）
PRECISION = 7

# N13_003 道路分類 → highway
CATEGORY_HIGHWAY = {
    "1": "primary",       # 国道
    "2": "secondary",     # 都道府県道
    "3": "residential",   # 市区町村道等
    "4": "motorway",      # 高速自動車国道等
    "5": "road",          # その他
    "6": "road",          # 不明
}

# N13_006 幅員区分 → ksj:width（元の区分を文字で残す）
WIDTH_CLASS = {
    "1": "<3m",
    "2": "3-5.5m",
    "3": "5.5-13m",
    "4": "13-19.5m",
    "5": ">=19.5m",
    "6": "unknown",
}


def road_tags(rec):
    road_type = rec["N13_002"]   # 種別: 1通常部 2庭園路 3徒歩道 4石段 5不明
    category = rec["N13_003"]    # 道路分類
    state = rec["N13_004"]       # 道路状態: 1通常部 2橋・高架 3トンネル 4雪囲い 5建設中
    level = int(rec["N13_005"] or 0)  # 階層順
    width = rec["N13_006"]       # 幅員区分
    toll = rec["N13_007"]        # 有料区分: 1無料 2有料

    if road_type == "3":
        highway = "footway"
    elif road_type == "4":
        highway = "steps"
    elif road_type == "2":
        highway = "service"
        tags_service = "driveway"
    else:
        highway = CATEGORY_HIGHWAY.get(category, "road")
        # 市区町村道等で幅員3m未満は細街路として service にする
        if highway == "residential" and width == "1":
            highway = "service"

    tags = {}
    if state == "5":
        tags["highway"] = "construction"
        tags["construction"] = highway
    else:
        tags["highway"] = highway
    if road_type == "2":
        tags["service"] = tags_service

    if state == "2":
        tags["bridge"] = "yes"
        tags["layer"] = str(max(level, 1))
    elif state == "3":
        tags["tunnel"] = "yes"
        tags["layer"] = "-1"
    elif state == "4":
        tags["covered"] = "yes"
    elif level > 0:
        tags["layer"] = str(level)

    if toll == "2":
        tags["toll"] = "yes"

    tags["ksj:road_type"] = road_type
    tags["ksj:category"] = category
    tags["ksj:state"] = state
    tags["ksj:width"] = WIDTH_CLASS.get(width, width)
    tags["source"] = "国土数値情報（道路）N13"
    return tags


def main(shp_path, *out_paths):
    reader = shapefile.Reader(shp_path, encoding="utf-8")

    node_ids = {}   # (lon, lat) → node id
    ways = []       # (node id list, tags)
    for sr in reader.iterShapeRecords():
        parts = list(sr.shape.parts) + [len(sr.shape.points)]
        rec = sr.record.as_dict()
        tags = road_tags(rec)
        for start, end in zip(parts[:-1], parts[1:]):
            refs = []
            for lon, lat in sr.shape.points[start:end]:
                key = (round(lon, PRECISION), round(lat, PRECISION))
                nid = node_ids.setdefault(key, len(node_ids) + 1)
                if not refs or refs[-1] != nid:   # 連続する重複点は除く
                    refs.append(nid)
            if len(refs) >= 2:
                ways.append((refs, tags))

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

    print(f"features: {len(reader)}  nodes: {len(node_ids)}  ways: {len(ways)}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], *sys.argv[2:])
