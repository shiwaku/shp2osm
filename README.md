# shp2osm

[国土数値情報（道路）N13](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N13-2024.html) の Shapefile を、OpenStreetMap（OSM）形式（`.osm` / `.osm.pbf`）に変換するツールです。

- 道路どうしがつながっている点を共有するので、道路網のつながりが保たれます
- N13 の属性コードを OSM の書き方（タグ）に変換し、元のコードも残します
- GDAL や ogr2osm は使わず、Python（pyshp + pyosmium）だけで動きます

## OSM 形式のしくみ（はじめての人向け）

OSM のデータは、**ノード**・**ウェイ**・**タグ**の3つでできています。

| 用語 | ひとことで | 道路データでは |
|---|---|---|
| **ノード**（node） | 地図上の**点**。緯度と経度を持つ | 道路の曲がり角や交差点 |
| **ウェイ**（way） | ノードを順につないだ**線** | 1本の道路（の区間） |
| **タグ**（tag） | ウェイやノードに付ける**ラベル**。`種類=値` の形 | 「国道」「橋」「有料」などの情報 |

たとえば、交差点 A で2本の道路がぶつかっている場合はこうなります。

```
  ノード1 ──── ノード2(A) ──── ノード3      ← ウェイ①「国道」   highway=primary
                  │
                  │                          ← ウェイ②「市道」   highway=residential
               ノード4
```

- ウェイ①は「ノード1 → 2 → 3」、ウェイ②は「ノード2 → 4」をつないだ線です
- **ノード2を2本のウェイが共有している**ので、「ここで曲がれる」とわかります。経路検索（カーナビのような使い方）では、このつながりが大切です
- Shapefile は線ごとに座標を持つだけなので、このツールでは**同じ座標の点を1つのノードにまとめて**、つながりを作っています

タグは、Shapefile の属性表の「列と値」にあたるものです。OSM では決まった書き方があり、たとえば道路の種類は `highway` で表します。

| タグ | 意味 |
|---|---|
| `highway=primary` | 国道（幹線道路） |
| `highway=secondary` | 都道府県道 |
| `highway=residential` | 市区町村道など |
| `highway=footway` | 歩道 |
| `bridge=yes` | 橋 |
| `tunnel=yes` | トンネル |
| `toll=yes` | 有料道路 |
| `ksj:category=1` など | N13 の元のコード（このツールが独自に残しているもの） |

N13 の属性がどのタグになるかの詳しい対応は [docs/notes.md](docs/notes.md) を見てください。

## 使い方

[uv](https://docs.astral.sh/uv/) を使います。

```bash
uv sync

# 元データを取得（例：1次メッシュ 5339 = 東京周辺）
mkdir -p data out
curl -L -o data/N13-24_5339_SHP.zip https://nlftp.mlit.go.jp/ksj/gml/data/N13/N13-24/N13-24_5339_SHP.zip
unzip data/N13-24_5339_SHP.zip -d data/N13-24_5339_SHP

# 変換（出力ファイルの拡張子で形式が決まる。複数指定できる）
uv run shp2osm data/N13-24_5339_SHP/N13-24_5339.shp out/N13-24_5339.osm out/N13-24_5339.osm.pbf
```

zip の中のフォルダ構成によっては、`.shp` のパスを合わせてください。

### 変換結果を画像で確認する

範囲（西端 東端 南端 北端）を指定すると、道路の種類ごとに色分けした画像を作ります。

```bash
uv run --group preview scripts/preview.py out/N13-24_6441.osm.pbf preview.png 141.32 141.38 43.04 43.08
```

QGIS に `.osm.pbf` をドラッグ＆ドロップして `lines` レイヤを選ぶと、道路をクリックしてタグを確認できます。

## 結果の例

| メッシュ | ノード | ウェイ | `.osm` | `.osm.pbf` | 処理時間 |
|---|---|---|---|---|---|
| 6441（札幌周辺） | 1,232,339 | 311,051 | 200MB | 7.3MB | 約6〜9秒 |
| 5339（東京周辺） | 5,032,828 | 1,943,242 | 1.0GB | 36MB | 約48秒 |

## リポジトリの構成

```
.
├── src/shp2osm/
│   ├── tags.py        # N13 の属性コード → OSM タグの対応付け
│   ├── convert.py     # Shapefile を読み、ノードを共有して OSM 形式に書き出す
│   └── cli.py         # コマンド（uv run shp2osm）
├── tests/             # pytest（タグの対応付け、ノードの共有）
├── scripts/
│   └── preview.py     # 変換結果を画像にして目視確認する
├── docs/
│   └── notes.md       # 調べたこと・試行の記録（OSM 形式の解説、注意点、逆変換、可逆性）
├── .github/workflows/ci.yml   # Ruff と pytest を実行
├── data/              # 元データ（Git 管理外）
└── out/               # 変換結果（Git 管理外）
```

## 開発

```bash
uv run ruff check
uv run ruff format
uv run pytest
```

## 注意

- タグの対応付けは試しに決めたものです。用途に合わせて `src/shp2osm/tags.py` を調整してください
- `oneway`（一方通行）や `maxspeed`（制限速度）は N13 にないため付けていません
- ID は 1 から振る仮の値です。OpenStreetMap 本体へのアップロードには使えません
- 変換したデータを公開・利用する際は、国土数値情報の利用規約に従って出典を表示してください

出典：国土数値情報（道路データ）（国土交通省）
