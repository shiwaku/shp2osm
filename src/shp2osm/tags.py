"""N13 の属性コードを OSM のタグに変換する。"""

# N13_003 道路分類 → highway
CATEGORY_HIGHWAY = {
    "1": "primary",  # 国道
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
    road_type = rec["N13_002"]  # 種別: 1通常部 2庭園路 3徒歩道 4石段 5不明
    category = rec["N13_003"]  # 道路分類
    state = rec["N13_004"]  # 道路状態: 1通常部 2橋・高架 3トンネル 4雪囲い 5建設中
    level = int(rec["N13_005"] or 0)  # 階層順
    width = rec["N13_006"]  # 幅員区分
    toll = rec["N13_007"]  # 有料区分: 1無料 2有料

    if road_type == "3":
        highway = "footway"
    elif road_type == "4":
        highway = "steps"
    elif road_type == "2":
        highway = "service"
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
        tags["service"] = "driveway"

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
    tags["source"] = SOURCE
    return tags
