# shp2osm

[国土数値情報（道路）N13](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N13-2024.html) の Shapefile を、OSM 形式（`.osm` / `.osm.pbf`）に変換するスクリプトです。

- 同じ座標の頂点を1つのノードとして共有するので、道路のつながりが保たれます
- N13 の属性コードを `highway` などの OSM タグに変換し、元のコードも `ksj:*` タグとして残します
- GDAL や ogr2osm は使わず、Python（pyshp + pyosmium）だけで動きます

## 使い方

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 元データを取得（例：1次メッシュ 5339 = 東京周辺）
mkdir -p data out
curl -L -o data/N13-24_5339_SHP.zip https://nlftp.mlit.go.jp/ksj/gml/data/N13/N13-24/N13-24_5339_SHP.zip
unzip data/N13-24_5339_SHP.zip -d data/N13-24_5339_SHP

# 変換（出力ファイルの拡張子で形式が決まる。複数指定できる）
.venv/bin/python shp2osm.py data/N13-24_5339_SHP/N13-24_5339.shp out/N13-24_5339.osm out/N13-24_5339.osm.pbf
```

zip の中のフォルダ構成によっては、`.shp` のパスを合わせてください。

## 結果の例

| メッシュ | ノード | ウェイ | `.osm` | `.osm.pbf` | 処理時間 |
|---|---|---|---|---|---|
| 6441（札幌周辺） | 1,232,339 | 311,051 | 200MB | 7.3MB | 約9秒 |
| 5339（東京周辺） | 5,032,828 | 1,943,242 | 1.0GB | 36MB | 約48秒 |

タグの対応付け、注意点、逆方向（OSM → Shapefile）の変換や可逆性については [NOTES.md](NOTES.md) にまとめています。

## 注意

- タグの対応付けは試しに決めたものです。用途に合わせて `shp2osm.py` の `road_tags()` を調整してください
- `oneway` や `maxspeed` は N13 にないため付けていません
- ID は 1 から振る仮の値です。OpenStreetMap 本体へのアップロードには使えません
- 変換したデータを公開・利用する際は、国土数値情報の利用規約に従って出典を表示してください

出典：国土数値情報（道路データ）（国土交通省）
