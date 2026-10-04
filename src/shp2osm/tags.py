"""N13 の属性コードを OSM のタグに変換する。

highway の値は日本の慣習（https://wiki.openstreetmap.org/wiki/JA:Japan_tagging）に合わせる。
N13 の属性はすべて ksj:* タグとしても残し、元の Shapefile の属性を復元できるようにする。
"""

# N13_003 道路分類 → highway
CATEGORY_HIGHWAY = {
    "1": "trunk",  # 国道
    "2": "secondary",  # 都道府県道
    "3": "residential",  # 市区町村道等
    "4": "motorway",  # 高速自動車国道等
    "5": "road",  # その他
    "6": "road",  # 不明
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

SOURCE = "国土数値情報（道路）N13"


def road_tags(rec: dict) -> dict[str, str]:
    date = rec["N13_001"]  # データ登録日
    road_type = rec["N13_002"]  # 種別: 1通常部 2庭園路 3徒歩道 4石段 5不明
    category = rec["N13_003"]  # 道路分類
    state = rec["N13_004"]  # 道路状態: 1通常部 2橋・高架 3トンネル 4雪囲い 5建設中
    level = int(rec["N13_005"] or 0)  # 階層順
    width = rec["N13_006"]  # 幅員区分
    toll = rec["N13_007"]  # 有料区分: 1無料 2有料
    mesh = rec["N13_008"]  # 二次メッシュ番号

    if road_type == "3":
        highway = "footway"
    elif road_type == "4":
        highway = "steps"
    elif road_type == "2":
        # 庭園路は公園の園路・河川敷の道・敷地内の通路など。車道とは限らないので path にする
        highway = "path"
    else:
        highway = CATEGORY_HIGHWAY.get(category, "road")

    tags = {}
    if state == "5":
        tags["highway"] = "construction"
        tags["construction"] = highway
    else:
        tags["highway"] = highway

    # 階層順は地上を 0 とする上下の位置関係。トンネルは地下なので layer=-1 とし、元の値は ksj:level に残す
    if state == "2":
        tags["bridge"] = "yes"
        tags["layer"] = str(max(level, 1))
    elif state == "3":
        tags["tunnel"] = "yes"
        tags["layer"] = "-1"
    elif level > 0:
        tags["layer"] = str(level)
    if state == "4":
        tags["covered"] = "yes"

    if toll == "2":
        tags["toll"] = "yes"

    tags["ksj:road_type"] = road_type
    tags["ksj:category"] = category
    tags["ksj:state"] = state
    tags["ksj:level"] = str(level)
    tags["ksj:width"] = WIDTH_CLASS.get(width, width)
    tags["ksj:toll"] = toll
    tags["ksj:date"] = str(date)
    tags["ksj:mesh"] = mesh
    tags["source"] = SOURCE
    return tags
