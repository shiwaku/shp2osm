"""OSRM・Valhalla・GraphHopper に同じ区間の経路を問い合わせ、結果を比べる。

使い方（scripts/routing/setup.sh で3つのエンジンを起動してから）:
    uv run scripts/routing/compare.py out/routing/routes.geojson

- 各区間の距離・所要時間と、出発地・目的地から道路までの距離（スナップ距離）を表で出す
- 経路の形を GeoJSON に書き出す（QGIS で重ねて見られる）
"""

import json
import sys
import urllib.parse
import urllib.request

OSRM = {"car": "http://localhost:5100", "foot": "http://localhost:5101"}
VALHALLA = "http://localhost:8002"
GRAPHHOPPER = "http://localhost:8989"

# メッシュ 6440（西）と 6441（東）の境界
MESH_BOUNDARY_LON = 141.0

PLACES = {
    "札幌駅": (43.0686, 141.3508),
    "小樽駅": (43.1976, 140.9938),
    "新千歳空港": (42.7876, 141.6800),
    "定山渓": (42.9680, 141.1660),
    "余市駅": (43.1867, 140.7853),
    "大通公園": (43.0610, 141.3565),
    "北大": (43.0716, 141.3445),
    "すすきの": (43.0555, 141.3530),
    "小樽運河": (43.1993, 141.0010),
}

ROUTES = [
    ("car", "札幌駅", "小樽駅"),
    ("car", "札幌駅", "新千歳空港"),
    ("car", "札幌駅", "定山渓"),
    ("car", "小樽駅", "余市駅"),
    ("car", "大通公園", "北大"),
    ("foot", "大通公園", "北大"),
    ("foot", "札幌駅", "すすきの"),
    ("foot", "小樽駅", "小樽運河"),
]


def get_json(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as res:
        return json.load(res)


def osrm(profile, a, b):
    coords = f"{a[1]},{a[0]};{b[1]},{b[0]}"
    r = get_json(f"{OSRM[profile]}/route/v1/{profile}/{coords}?overview=full&geometries=geojson")
    route = r["routes"][0]
    return {
        "distance_km": route["distance"] / 1000,
        "duration_min": route["duration"] / 60,
        "snap_m": max(w["distance"] for w in r["waypoints"]),
        "coords": route["geometry"]["coordinates"],
    }


def decode_polyline6(s):
    coords, lat, lon, i = [], 0, 0, 0
    while i < len(s):
        values = []
        for _ in range(2):
            shift = result = 0
            while True:
                c = ord(s[i]) - 63
                i += 1
                result |= (c & 0x1F) << shift
                shift += 5
                if c < 0x20:
                    break
            values.append(~(result >> 1) if result & 1 else result >> 1)
        lat += values[0]
        lon += values[1]
        coords.append([lon / 1e6, lat / 1e6])
    return coords


def valhalla(profile, a, b):
    costing = {"car": "auto", "foot": "pedestrian"}[profile]
    body = {
        "locations": [{"lat": a[0], "lon": a[1]}, {"lat": b[0], "lon": b[1]}],
        "costing": costing,
        "units": "kilometers",
        "directions_type": "none",
    }
    trip = get_json(f"{VALHALLA}/route", body)["trip"]
    coords = [c for leg in trip["legs"] for c in decode_polyline6(leg["shape"])]
    # Valhalla はスナップ距離を返さないので、出発地・目的地と経路の端の距離で代わりにする
    snap = max(distance_m(a, coords[0][::-1]), distance_m(b, coords[-1][::-1]))
    return {
        "distance_km": trip["summary"]["length"],
        "duration_min": trip["summary"]["time"] / 60,
        "snap_m": snap,
        "coords": coords,
    }


def graphhopper(profile, a, b):
    query = urllib.parse.urlencode(
        [("point", f"{a[0]},{a[1]}"), ("point", f"{b[0]},{b[1]}"), ("profile", profile), ("points_encoded", "false")]
    )
    path = get_json(f"{GRAPHHOPPER}/route?{query}")["paths"][0]
    coords = path["points"]["coordinates"]
    snap = max(
        distance_m(a, path["snapped_waypoints"]["coordinates"][0][::-1]),
        distance_m(b, path["snapped_waypoints"]["coordinates"][-1][::-1]),
    )
    return {
        "distance_km": path["distance"] / 1000,
        "duration_min": path["time"] / 60000,
        "snap_m": snap,
        "coords": coords,
    }


def distance_m(p, q):
    """2点（lat, lon）間の距離（m）。短い距離なので平面近似で十分。"""
    from math import cos, hypot, radians

    dy = (p[0] - q[0]) * 111_320
    dx = (p[1] - q[1]) * 111_320 * cos(radians(p[0]))
    return hypot(dx, dy)


def crosses_boundary(coords):
    lons = [c[0] for c in coords]
    return min(lons) < MESH_BOUNDARY_LON < max(lons)


ENGINES = {"OSRM": osrm, "Valhalla": valhalla, "GraphHopper": graphhopper}


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    features = []
    print("| 手段 | 区間 | エンジン | 距離 km | 時間 分 | スナップ m | 境界をまたぐ |")
    print("|---|---|---|---:|---:|---:|---|")
    for profile, src, dst in ROUTES:
        a, b = PLACES[src], PLACES[dst]
        for name, fn in ENGINES.items():
            try:
                r = fn(profile, a, b)
            except Exception as e:  # エンジンごとの失敗も結果として残す
                print(f"| {profile} | {src}→{dst} | {name} | 失敗: {e} | | | |")
                continue
            cross = "はい" if crosses_boundary(r["coords"]) else "いいえ"
            print(
                f"| {profile} | {src}→{dst} | {name} | {r['distance_km']:.1f} | {r['duration_min']:.0f} "
                f"| {r['snap_m']:.0f} | {cross} |"
            )
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "profile": profile,
                        "route": f"{src}→{dst}",
                        "engine": name,
                        "distance_km": round(r["distance_km"], 3),
                        "duration_min": round(r["duration_min"], 1),
                    },
                    "geometry": {"type": "LineString", "coordinates": r["coords"]},
                }
            )
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False)
        print(f"\n経路の形を {out_path} に書き出しました")


if __name__ == "__main__":
    main()
