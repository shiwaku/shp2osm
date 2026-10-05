#!/usr/bin/env bash
# OSRM・Valhalla・GraphHopper に .osm.pbf を読み込ませて起動する。
#   scripts/routing/setup.sh out/N13-24_6440-6441.osm.pbf
# 必要なもの: Docker、Java 21 以上。作業ファイルは out/routing/ に置く。
# 止めるとき: docker rm -f osrm-car osrm-foot valhalla; kill $(cat out/routing/graphhopper/server.pid)
set -euo pipefail

PBF=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
WORK=$ROOT/out/routing
GH_VERSION=11.1
OSRM_IMAGE=ghcr.io/project-osrm/osrm-backend:latest
VALHALLA_IMAGE=ghcr.io/valhalla/valhalla-scripted:latest

mkdir -p "$WORK"
docker rm -f osrm-car osrm-foot valhalla >/dev/null 2>&1 || true

# OSRM: プロファイル（car / foot）ごとにデータを作る。ポート 5000 は macOS の AirPlay と重なるので 5100 / 5101
port=5100
for profile in car foot; do
  dir=$WORK/osrm/$profile
  rm -rf "$dir" && mkdir -p "$dir" && cp "$PBF" "$dir/map.osm.pbf"
  docker run --rm -v "$dir:/data" $OSRM_IMAGE osrm-extract -p /opt/$profile.lua /data/map.osm.pbf
  docker run --rm -v "$dir:/data" $OSRM_IMAGE osrm-partition /data/map.osrm
  docker run --rm -v "$dir:/data" $OSRM_IMAGE osrm-customize /data/map.osrm
  docker run -d --name osrm-$profile -p $port:5000 -v "$dir:/data" $OSRM_IMAGE osrm-routed --algorithm mld /data/map.osrm
  port=$((port + 1))
done

# Valhalla: custom_files に置いた .osm.pbf から、起動時にタイルを作る（行政界・タイムゾーン・標高は使わない）
rm -rf "$WORK/valhalla" && mkdir -p "$WORK/valhalla" && cp "$PBF" "$WORK/valhalla/"
docker run -d --name valhalla -p 8002:8002 -v "$WORK/valhalla:/custom_files" \
  -e build_admins=False -e build_time_zones=False -e build_elevation=False $VALHALLA_IMAGE

# GraphHopper: jar を Maven Central から取得し、取り込み（import）してからサーバーを起動する
GH=$WORK/graphhopper
mkdir -p "$GH"
jar=$GH/graphhopper-web-$GH_VERSION.jar
[ -f "$jar" ] || curl -sfL -o "$jar" \
  https://repo1.maven.org/maven2/com/graphhopper/graphhopper-web/$GH_VERSION/graphhopper-web-$GH_VERSION.jar
cd "$GH" && rm -rf graph-cache
java -Xmx4g -Ddw.graphhopper.datareader.file="$PBF" -jar "$jar" import "$ROOT/scripts/routing/graphhopper.yml"
nohup java -Xmx2g -Ddw.graphhopper.datareader.file="$PBF" -jar "$jar" server "$ROOT/scripts/routing/graphhopper.yml" \
  >server.log 2>&1 &
echo $! >server.pid

echo "起動待ち..."
until curl -sf localhost:8989/health >/dev/null && curl -sf localhost:8002/status >/dev/null; do sleep 5; done
echo "OSRM: localhost:5100 (car) / 5101 (foot)  Valhalla: localhost:8002  GraphHopper: localhost:8989"
