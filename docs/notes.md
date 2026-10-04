# Shapefile → OSM形式（.osm / .pbf）変換メモ

## OSM形式とは

OpenStreetMapの地図データを保存するための形式。データの中身は共通で、保存の仕方が違う `.osm`（XML）と `.osm.pbf`（バイナリ）の2種類がある。

### データの構造

| 要素 | 意味 | 例 |
|---|---|---|
| **node（ノード）** | 緯度経度を持つ点 | 交差点、コンビニ、信号 |
| **way（ウェイ）** | ノードを順番に並べた線や面 | 道路、川、建物の輪郭 |
| **relation（リレーション）** | 要素どうしの関係をまとめたもの | バス路線、穴あきポリゴン、行政界 |

属性は **タグ**（`key=value`）で表す。

```
highway=primary   ← 幹線道路
name=国道5号
maxspeed=60
```

- Shapefile：点・線・面のファイルを種類ごとに分け、属性は表（DBF）に持つ
- OSM：点（ノード）を共有して線や面を組み立てる、つながり重視の構造
  - そのため、交差点でノードを共有していないと道路がつながらない

### 2つの保存形式

#### `.osm`（XML形式）

```xml
<node id="1" lat="43.0621" lon="141.3544"/>
<node id="2" lat="43.0625" lon="141.3550"/>
<way id="10">
  <nd ref="1"/>
  <nd ref="2"/>
  <tag k="highway" v="residential"/>
  <tag k="name" v="北1条通"/>
</way>
```

- 良い点：テキストエディタで確認でき、デバッグしやすい
- 弱い点：ファイルが大きく、読み込みが遅い

#### `.osm.pbf`（Protocol Buffer Binary Format）

- 良い点：`.osm` よりずっと小さく（数分の1〜十分の1程度）、読み書きが速い
- 弱い点：人間がそのまま読むことはできない

#### 使い分け

- 少量のデータの確認やデバッグ → `.osm`
- 実際の利用 → `.pbf`（OSRM、Valhalla、osm2pgsql、タイル生成ツールなどが前提にしている。Geofabrikの日本全体のデータも `.pbf`）

### `.osm` と `.osm.pbf` は同じもの？

**中身（データ）は同じで、保存の仕方が違うだけ。** 今回の試行でも、2つのファイルのノード数とウェイ数は一致した（下の「試行」を参照）。

| | `.osm` | `.osm.pbf` |
|---|---|---|
| 形式 | XML（テキスト） | Protocol Buffers（バイナリ）を圧縮したもの |
| 中身 | node / way / relation とタグ | 同じ |
| 今回のサイズ | 200MB | 7.3MB |
| 人が読めるか | 読める（エディタで開ける） | 読めない（ツールが必要） |
| 読み書きの速さ | 遅い | 速い |

紙の本と、それを圧縮したZIPファイルのような関係。相互に変換しても、情報は基本的に失われない。

```bash
osmium cat input.osm -o output.osm.pbf   # .osm → .pbf
osmium cat input.osm.pbf -o output.osm   # .pbf → .osm
```

- 正式な拡張子は **`.osm.pbf`**。単に「`.pbf`」と言うと、MVT（ベクトルタイル）と混同しやすい
- `.osm.bz2` のように、XMLの `.osm` をそのまま圧縮した形式もある。中身はXMLなので `.osm.pbf` とは別物

### `.osm.pbf` とベクトルタイル（MVT）は同じ？

**別物。** どちらも同じ「Protocol Buffers」という仕組みでバイナリ化しているので、拡張子に `.pbf` が使われることがあり紛らわしい。データの定義（スキーマ）はまったく違い、互いに読み替えることはできない。

| | OSM PBF（`.osm.pbf`） | MVT（Mapbox Vector Tile、`.mvt` / `.pbf`） |
|---|---|---|
| 目的 | OSMの元データを保存・配布する | 地図を表示するために配信する |
| 中身 | node / way / relation とタグ | レイヤごとの図形（点・線・面）と属性 |
| 座標 | 緯度経度 | タイル内の整数座標（通常 0〜4096） |
| 単位 | 1つのファイルに範囲全体 | ズームレベルとタイルごと（z/x/y）に1ファイル |
| 図形の精度 | 元のまま | ズームに応じて簡略化される |
| 主な使い道 | OSRM、osm2pgsql、タイル生成ツールの入力 | MapLibreなどでの地図表示 |

OSM PBF は「元データ」、MVT はそこから表示用に切り出して加工した「成果物」という関係。たとえば `.osm.pbf` を Planetiler などのタイル生成ツールに読み込ませると、MVT のタイル（PMTiles や MBTiles にまとめたもの）ができる。

## 変換方法

ShapefileとOSMはデータモデルが違うため、単純な形式変換ではなく **属性からタグへの対応付け（マッピング）** が必要になる。

### ogr2ogr（GDAL）では OSM 形式に書き出せない

GDALのOSMドライバは**読み込み専用**なので、ogr2ogrでは `.osm` や `.pbf` を書き出せない。前処理（再投影など）には使える。

### 1. ogr2osm で `.osm` に変換（推奨）

```bash
pip install ogr2osm
ogr2osm input.shp -o output.osm
```

属性をOSMタグにするには translation ファイル（Python）を用意する。

```python
# translation.py
def filterTags(attrs):
    if not attrs:
        return
    tags = {}
    if "name" in attrs:
        tags["name"] = attrs["name"]
    if "type" in attrs:
        tags["highway"] = "residential"  # 例
    return tags
```

```bash
ogr2osm input.shp -t translation.py -o output.osm
```

### 2. `.osm` → `.pbf`

```bash
brew install osmium-tool
osmium cat output.osm -o output.osm.pbf
# または
osmconvert output.osm -o=output.pbf
```

おすすめの流れ：まず `.osm` に変換して中身を確認し、問題がなければ `.pbf` にする。

## 注意点・つまずきやすいところ

ツール自体はエラーなく動くことが多いが、**使える結果になるかは別問題**で、一発で完璧にはいかないことが多い。

### すんなりいくところ

- 座標系とエンコーディングが正しければ、`ogr2osm input.shp -o output.osm` は普通に終わる
- `.osm` → `.pbf`（osmium）はほぼ問題ない

### 1. タグがないと使えない

translationファイルなしで変換すると、Shapefileの属性がそのままタグになる。`highway=*` などOSM標準のタグがないと、ルーティングエンジンや地図スタイルに認識されない。**実質的にtranslationの作成は必須**。

### 2. 道路の接続性（ルーティング用途で最大の落とし穴）

- 交差点にノード（頂点）がなく、線が交差しているだけだと、つながっていないとみなされる
- ogr2osmは同じ座標の頂点を共有するが、頂点がなければつながらない
- 事前にQGISの「交点で分割」などで、交差点にノードを作っておく

### 3. 属性名・文字コード

- DBFの属性名は10文字で切れている
- 日本のShapefileはShift_JIS（CP932）が多い。`--encoding cp932` を指定するか、事前にUTF-8に変換する

### 4. 座標系

- OSMはWGS84（EPSG:4326）
- `.prj` があればogr2osmは基本的に自動で再投影するが、事前に再投影しておくほうが確実

```bash
ogr2ogr -t_srs EPSG:4326 input_4326.shp input.shp
```

### 5. ポリゴンと大容量データ

- 穴あきポリゴンは multipolygon リレーションになり、ここでうまくいかないことがある
- 数百MBを超えるデータはメモリを大量に使うため、分割して変換する

### 6. ID

生成されるIDは仮のもの（負の値など）なので、本物のOSMへのアップロードには向かない。インポートする場合はコミュニティのガイドラインに従う。

### 7. ルーティング用途（OSRM / Valhalla / SUMO）

- `highway`、`oneway`、`maxspeed` などのタグを適切に付ける
- ネットワークの接続性（上の2.）を確認する

## 確認方法

```bash
osmium fileinfo -e output.osm.pbf   # 要素の件数などを確認
```

- JOSMやQGISで開いて目視で確認する
- ルーティング用なら、実際にOSRMなどに読み込ませて経路が引けるか試すのが一番確実

## 環境メモ（2026-10-01時点）

- `ogr2ogr`（GDAL）：インストール済み（`/opt/homebrew/bin/ogr2ogr`）だが、`libaws-c-common` 不足で**起動しない**
- `pyshp`、`osmium`（pyosmium）：プロジェクトの `.venv` にインストール済み（今回の変換に使用）
- `ogr2osm`：未インストール → `pip install ogr2osm`（GDAL の Python バインディングが必要）
- `osmium`：未インストール → `brew install osmium-tool`
- `osmconvert`：未インストール

2026-10-05 にリポジトリの構成を整理した（uv・Python 3.14、`shp2osm.py` を `src/shp2osm/` のパッケージに分割）。以下の試行の記録に出てくる `.venv/bin/python shp2osm.py ...` は、今は `uv run shp2osm ...` で同じことができる。変換結果（ノード数・ウェイ数）は整理前と同じであることを確認した。

## 試行：国土数値情報（道路）N13 を1メッシュ変換（2026-10-01）

### 使ったデータ

- [国土数値情報（道路）N13 令和6年度](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N13-2024.html)
- 1次メッシュ **6441**（北緯42.67〜43.33度、東経141〜142度。札幌市を含む）
- `data/N13-24_6441_SHP/N13-24_6441.shp`：ライン 311,054 本
- 文字コードは UTF-8（`.cpg` あり）、座標系は JGD2011 経緯度（WGS84 とほぼ同じなので再投影なし）

### 属性（コードリスト）

| shp属性 | 内容 | コード |
|---|---|---|
| N13_001 | データ登録日 | 日付（供用開始日ではない） |
| N13_002 | 種別 | 1通常部 2庭園路 3徒歩道 4石段 5不明 |
| N13_003 | 道路分類 | 1国道 2都道府県道 3市区町村道等 4高速自動車国道等 5その他 6不明 |
| N13_004 | 道路状態 | 1通常部 2橋・高架 3トンネル 4雪囲い 5建設中 6その他 7不明 |
| N13_005 | 階層順 | 整数（地上からの立体的な位置関係） |
| N13_006 | 幅員区分 | 1:3m未満 2:3-5.5m 3:5.5-13m 4:13-19.5m 5:19.5m以上 6不明 |
| N13_007 | 有料区分 | 1無料 2有料 |
| N13_008 | 二次メッシュ番号 | |

### タグの対応付け（`src/shp2osm/tags.py`）

2026-10-05 に見直した対応付け（[日本のタグ付けの慣習](https://wiki.openstreetmap.org/wiki/JA:Japan_tagging)に合わせた）。

- 道路分類：国道 → `highway=trunk`、都道府県道 → `secondary`、市区町村道等 → `residential`、高速 → `motorway`、その他・不明 → `road`
- 種別：庭園路 → `path`、徒歩道 → `footway`、石段 → `steps`（道路分類より優先）
- 道路状態：橋・高架 → `bridge=yes` + `layer`（最低1）、トンネル → `tunnel=yes` + `layer=-1`、雪囲い → `covered=yes`、建設中 → `highway=construction` + `construction=<本来の値>`
- 階層順：橋・トンネル以外で1以上なら `layer`
- 有料 → `toll=yes`
- N13 の8属性はすべて `ksj:date`、`ksj:road_type`、`ksj:category`、`ksj:state`、`ksj:level`、`ksj:width`、`ksj:toll`、`ksj:mesh` として残し、`source=国土数値情報（道路）N13` を付ける

#### 見直しの内容と理由

| 変更 | 前 | 後 | 理由 |
|---|---|---|---|
| 国道 | `primary` | `trunk` | 日本の OSM では国道を `trunk` にするのが慣習 |
| 庭園路 | `service` + `service=driveway` | `path` | 地図で確認すると、公園の園路・河川敷の道・敷地内の通路だった。`driveway` は家の車庫への私道の意味なので合わない |
| 幅3m未満の市区町村道 | `service` | `residential` | `service` は敷地への出入り用の道。一般の細い道は `residential` が自然 |
| 雪囲い | `layer` なし | 階層順が1以上なら `layer` | 階層順の情報を落とさないため |
| 失われていた属性 | なし | `ksj:date`、`ksj:level`、`ksj:toll`、`ksj:mesh` | 元の属性をすべて復元できるようにするため |

#### 変換が正しいかの確認（2026-10-05）

- 属性コードの意味を、国土数値情報の公式コード表（種別・道路分類・道路状態・幅員区分・有料区分）で確認した。仕様書は図形（場所）を N13_001 と数えるので、Shapefile の列番号とは1つずれる（Shapefile の N13_001 がデータ登録日）
- 元の Shapefile の全レコードと `.osm.pbf` の全ウェイを順に突き合わせ、タグから8属性すべてを復元できること（6441：311,051本、5339：1,943,242本、不一致0）、座標のずれが最大約5mm（小数点以下7桁への丸め）であることを確認した

### 手順

GDAL（Homebrew）が `libaws-c-common` 不足で起動しなかったため、ogr2osm は使わずに Python（pyshp + pyosmium）で変換した。同じ座標（小数点以下7桁）の頂点は1つのノードとして共有する。

```bash
python3 -m venv .venv
.venv/bin/pip install pyshp osmium
.venv/bin/python shp2osm.py data/N13-24_6441_SHP/N13-24_6441.shp out/N13-24_6441.osm out/N13-24_6441.osm.pbf
```

pyosmium は出力ファイルの拡張子を見て形式を決めるので、`.osm` と `.osm.pbf` を1回で書き出せる。

### 結果

| | |
|---|---|
| 処理時間 | 約9秒 |
| ノード | 1,232,339 |
| ウェイ | 311,051（長さ0の3本は除外） |
| `.osm` | 200MB |
| `.osm.pbf` | **7.3MB**（`.osm` の約1/27。元の SHP の zip は19MB） |

- `.osm` と `.osm.pbf` を pyosmium で読み直し、ノード数・ウェイ数がどちらも上の値と一致することを確認した

- 複数のウェイが共有するノード（交差点・接続点）：191,392
- 行き止まりの端点：37,089 / 622,102（約6%。本当の行き止まりとメッシュ境界の端を含む）
- highway の内訳（見直し後）：residential 233,439 / path 52,701 / secondary 11,754 / footway 6,173 / trunk 5,883 / motorway 886 / steps 173 / road 42
- 道路の端点が頂点として共有されていて、**交点で分割する前処理なしでもネットワークはおおむねつながっている**

### 残っている課題

- `oneway` や `maxspeed` はN13にないため付けていない。ルーティングすると一方通行が無視される
- メッシュ境界で道路が切れるため、複数メッシュを使う場合は結合して変換する
- 実際に OSRM などに読み込ませて、経路が引けるかはまだ試していない
- 修復するなら `brew reinstall gdal` など（Homebrew の依存関係の問題）

## 試行：メッシュ 5339（東京周辺）を変換（2026-10-01）

メッシュ 6441 と同じ `shp2osm.py` で、東京23区を含む1次メッシュ **5339**（北緯35.33〜36.0度、東経139〜140度）を変換した。

```bash
.venv/bin/python shp2osm.py data/N13-24_5339_SHP/N13-24_5339.shp out/N13-24_5339.osm out/N13-24_5339.osm.pbf
```

| | 6441（札幌周辺） | **5339（東京周辺）** |
|---|---|---|
| 入力ライン | 311,054 | 1,943,251 |
| SHP（.shp本体） | — | 228MB（zip 96MB） |
| ノード | 1,232,339 | 5,032,828 |
| ウェイ | 311,051 | 1,943,242（長さ0の9本は除外） |
| `.osm` | 200MB | **1.0GB** |
| `.osm.pbf` | 7.3MB | **36MB** |
| 処理時間 | 約9秒 | 約48秒 |
| 最大メモリ | — | 約2.3GB |
| 共有ノード（交差点・接続点） | 191,392 | 1,177,860 |
| 行き止まりの端点 | 37,089 / 622,102（約6%） | 251,401 / 3,886,484（約6%） |

- highway の内訳（5339、見直し後）：residential 1,600,546 / path 208,322 / secondary 84,182 / trunk 19,857 / footway 19,274 / motorway 6,671 / steps 4,368 / road 22
- 見直し後は `ksj:*` タグが増えたため、`.osm` は 6441 で250MB、5339 で1.3GB、`.osm.pbf` は 6441 で7.4MB、5339 で38MBになった
- `.osm.pbf` を読み直してノード数・ウェイ数を確認し、`.osm` のウェイ数とも一致した
- 都市部でも1メッシュなら問題なく変換できる。ただし `shp2osm.py` は全ノードをメモリに持つので、複数メッシュをまとめるとメモリ使用量が増える

## 逆方向：`.osm` / `.osm.pbf` → Shapefile

**できる。** GDALのOSMドライバは書き出しには対応していないが、読み込みには対応しているため、ogr2ogrで直接変換できる。

```bash
ogr2ogr -f "ESRI Shapefile" roads.shp N13-24_5339.osm.pbf lines \
  -lco ENCODING=UTF-8
```

GDALはOSMデータを、図形の種類ごとに次の5つのレイヤに分けて読み込む。

| レイヤ | 中身 |
|---|---|
| `points` | タグを持つノード（POIなど） |
| `lines` | 線のウェイ（道路など。今回の道路はここに入る） |
| `multilinestrings` | 線のリレーション（路線など） |
| `multipolygons` | 面（閉じたウェイや multipolygon リレーション） |
| `other_relations` | それ以外のリレーション |

### 注意点

- **タグの扱い**：初期設定では `name` や `highway` などよく使われるタグだけが列になる。それ以外のタグは `other_tags` という1つの列に `"key"=>"value",...` の形でまとめて入る。`ksj:category` などを列として出したい場合は、`osmconf.ini` で列に加えるタグを指定する
- **Shapefileの制限**：列名は10文字まで、文字列は254バイトまで、ファイルは1つ2GBまで。大きいデータや長いタグを扱うなら GeoPackage（`-f GPKG`）のほうが安全
- **つながりの情報は消える**：ノードを共有しているという情報はなくなり、ただの線になる
- このMacの Homebrew の GDAL は起動しない状態だが、QGIS に同梱されている GDAL（`/Applications/QGIS.app/Contents/MacOS/ogr2ogr`）で変換できる。QGISで `.osm.pbf` を開いて「エクスポート」から保存する方法もある

#### 試した結果（2026-10-05）

QGIS 同梱の GDAL 3.12 で、`out/N13-24_6441.osm.pbf` の `lines` レイヤを GeoPackage に書き出した。311,051本すべてが出力され、約1秒で終わった。`config/osmconf.ini` を使うと、`ksj:*` タグが `ksj_category` などの別々の列になる（使い方と属性の対応は [attributes.md](attributes.md)）。

```bash
/Applications/QGIS.app/Contents/MacOS/ogr2ogr --config OSM_CONFIG_FILE config/osmconf.ini \
  -f GPKG out/N13-24_6441.gpkg out/N13-24_6441.osm.pbf lines
```

### 可逆か？

**完全な可逆ではない。** 形式としては相互に変換できるが、元のShapefileにそのまま戻るわけではない。

Shapefileは「線と属性の表」、OSMは「ノードを共有するネットワークとタグ」で、データモデルが違うため、行って戻ると何かしら変わるのが普通。

- Shapefile → OSM：属性をタグに変換する方法次第で、情報が落ちる
- OSM → Shapefile：ノードの共有（つながり）の情報は消える。タグは `other_tags` にまとめられる

#### 今回の変換で戻せるもの（2026-10-05 の見直し後）

| 元の属性 | 戻し方 |
|---|---|
| N13_001 データ登録日 | `ksj:date` |
| N13_002 種別 | `ksj:road_type` に元のコードが残っている |
| N13_003 道路分類 | `ksj:category` に元のコードが残っている |
| N13_004 道路状態 | `ksj:state` に元のコードが残っている |
| N13_005 階層順 | `ksj:level` |
| N13_006 幅員区分 | `ksj:width` に `<3m` などの文字で残っている（コード表で元の番号に戻せる） |
| N13_007 有料区分 | `ksj:toll` |
| N13_008 二次メッシュ番号 | `ksj:mesh` |
| 線の形 | 戻せる（座標は小数点以下7桁、約1cm単位に丸められている） |

#### 失われるもの

| 項目 | 理由 |
|---|---|
| 長さ0の線（6441で3本、5339で9本） | 変換時に除外した |
| 1つの地物が複数のパーツからなる線 | パーツごとに別のウェイに分かれる |
| 地物の順番やID | 変換時に振り直している |

#### 可逆に近づけるには

2026-10-05 の見直しで、属性はすべて `ksj:*` タグから戻せるようになった。それでも座標の丸め、マルチパートの分割、IDの振り直しは残るので、**「ほぼ可逆」が限界**。
