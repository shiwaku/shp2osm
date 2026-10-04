# 属性とタグの対応表

国土数値情報（道路）N13 の Shapefile の属性が、変換後の OSM データでどのタグになるかをまとめる。

- N13 の8属性は、すべて **`ksj:*` タグ**に元の値のまま残す（元の Shapefile の属性を復元できる）
- それとは別に、経路検索や地図表示のソフトが読む **OSM 標準のタグ**（`highway` など）を属性から作る
- コードの意味は国土数値情報の公式コード表による（[N13 の仕様](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N13-2024.html)）
- 変換の処理は `src/shp2osm/tags.py`

## 1. 属性 → タグの一覧

| Shapefile の列 | 属性名 | 残す `ksj:*` タグ | QGIS の列名（※） | 作る OSM 標準タグ |
|---|---|---|---|---|
| N13_001 | データ登録日 | `ksj:date` | `ksj_date` | — |
| N13_002 | 種別 | `ksj:road_type` | `ksj_road_type` | `highway` |
| N13_003 | 道路分類 | `ksj:category` | `ksj_category` | `highway` |
| N13_004 | 道路状態 | `ksj:state` | `ksj_state` | `bridge`、`tunnel`、`covered`、`highway=construction` |
| N13_005 | 階層順 | `ksj:level` | `ksj_level` | `layer` |
| N13_006 | 幅員区分 | `ksj:width` | `ksj_width` | — |
| N13_007 | 有料区分 | `ksj:toll` | `ksj_toll` | `toll` |
| N13_008 | 二次メッシュ番号 | `ksj:mesh` | `ksj_mesh` | — |

※ `config/osmconf.ini` を使って QGIS で開いたときの列名（下の「QGIS で見る」を参照）。GDAL が `:` を `_` に置き換える。

すべてのウェイに `source=国土数値情報（道路）N13` も付ける。

公式の仕様書は図形（場所）を N13_001 と数えるので、仕様書の番号は Shapefile の列番号より1つ大きい（仕様書の N13_002 データ登録日 = Shapefile の N13_001）。

## 2. コードの意味と、作るタグ

### 種別（N13_002 → `ksj:road_type`）

| コード | 意味 | `highway` |
|---|---|---|
| 1 | 通常部 | 道路分類で決める（下の表） |
| 2 | 庭園路（公園の園路・河川敷の道・敷地内の通路など） | `path` |
| 3 | 徒歩道 | `footway` |
| 4 | 石段 | `steps` |
| 5 | 不明 | 道路分類で決める |

### 道路分類（N13_003 → `ksj:category`）

種別が「通常部」か「不明」のときに `highway` を決める。

| コード | 意味 | `highway` |
|---|---|---|
| 1 | 国道 | `trunk` |
| 2 | 都道府県道 | `secondary` |
| 3 | 市区町村道等 | `residential` |
| 4 | 高速自動車国道等 | `motorway` |
| 5 | その他 | `road` |
| 6 | 不明 | `road` |

国道を `trunk` にするのは、[日本の OSM の慣習](https://wiki.openstreetmap.org/wiki/JA:Japan_tagging)に合わせたもの。

### 道路状態（N13_004 → `ksj:state`）

| コード | 意味 | 作るタグ |
|---|---|---|
| 1 | 通常部 | — |
| 2 | 橋・高架 | `bridge=yes`、`layer=<階層順。最低1>` |
| 3 | トンネル | `tunnel=yes`、`layer=-1` |
| 4 | 雪囲い | `covered=yes` |
| 5 | 建設中 | `highway=construction`、`construction=<本来の highway の値>` |
| 6 | その他 | — |
| 7 | 不明 | — |

### 階層順（N13_005 → `ksj:level`）

地上を 0 とする、立体的な上下の位置関係（整数）。

| 条件 | `layer` |
|---|---|
| 橋・高架 | 階層順（0 のときは 1） |
| トンネル | `-1`（階層順にかかわらず） |
| それ以外で階層順が1以上 | 階層順 |
| それ以外で階層順が0 | 付けない |

### 幅員区分（N13_006 → `ksj:width`）

コードではなく、意味がわかる文字で残す。

| コード | 意味 | `ksj:width` |
|---|---|---|
| 1 | 3m未満 | `<3m` |
| 2 | 3m以上5.5m未満 | `3-5.5m` |
| 3 | 5.5m以上13m未満 | `5.5-13m` |
| 4 | 13m以上19.5m未満 | `13-19.5m` |
| 5 | 19.5m以上 | `>=19.5m` |
| 6 | 不明 | `unknown` |

OSM 標準の `width` タグは「4.5」のような実際の幅（メートル）を書くものなので、区分しかない N13 からは作らない。

### 有料区分（N13_007 → `ksj:toll`）

| コード | 意味 | 作るタグ |
|---|---|---|
| 1 | 無料 | — |
| 2 | 有料 | `toll=yes` |

### データ登録日（N13_001 → `ksj:date`）・二次メッシュ番号（N13_008 → `ksj:mesh`）

元の値をそのまま残す。データ登録日は電子国土基本図に地物が登録された日で、道路の供用開始日ではない。

## 3. 読み方の例

QGIS で開いたウェイ（osm_id 110273）のタグは次のとおり。

```
highway=residential
ksj:road_type=1  ksj:category=3  ksj:state=1  ksj:level=0
ksj:width=13-19.5m  ksj:toll=1  ksj:date=2023-11-30  ksj:mesh=644142
```

| タグ | 意味 |
|---|---|
| `ksj:road_type=1` | 種別：通常部 |
| `ksj:category=3` | 道路分類：市区町村道等 → `highway=residential` |
| `ksj:state=1` | 道路状態：通常部（橋でもトンネルでもない） |
| `ksj:level=0` | 階層順：地上 |
| `ksj:width=13-19.5m` | 幅員：13m以上19.5m未満 |
| `ksj:toll=1` | 有料区分：無料 |
| `ksj:date=2023-11-30` | データ登録日 |
| `ksj:mesh=644142` | 二次メッシュ番号 |

→ 幅13〜19.5m の、地上にある無料の市区町村道。

## 4. QGIS で見る

QGIS（GDAL）は、初期設定では `name` や `highway` などの決まったタグだけを列にし、それ以外のタグを `other_tags` という1つの列に `"ksj:category"=>"3",...` の形でまとめる。`config/osmconf.ini` を使うと、`ksj:*` タグと `bridge`・`tunnel`・`layer` などが1つずつ別の列になる。

### QGIS の設定

1. 「QGIS」メニュー →「環境設定」（Windows / Linux は「設定」→「オプション」）→「システム」→「環境」
2. 「カスタム変数を使う」にチェックを入れ、変数を追加する
   - 適用：`Overwrite`
   - 変数：`OSM_CONFIG_FILE`
   - 値：`config/osmconf.ini` の絶対パス（例：`/Users/xxx/GitHub/shp2osm/config/osmconf.ini`）
3. QGIS を再起動し、`.osm.pbf` を開いて `lines` レイヤを選ぶ

この設定は QGIS で開くすべての OSM データに効く。ほかの OSM データを開くときに困る場合は、設定を外すか、下のように GeoPackage に書き出して使う。

### GeoPackage に書き出す

列を固定したファイルにしておくと、設定なしで QGIS に読み込める。QGIS に同梱されている `ogr2ogr` を使う（macOS の場合）。

```bash
/Applications/QGIS.app/Contents/MacOS/ogr2ogr --config OSM_CONFIG_FILE config/osmconf.ini \
  -f GPKG out/N13-24_6441.gpkg out/N13-24_6441.osm.pbf lines
```
