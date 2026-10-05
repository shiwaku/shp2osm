import osmium
import shapefile

from shp2osm.convert import convert

FIELDS = ["N13_001", "N13_002", "N13_003", "N13_004", "N13_005", "N13_006", "N13_007", "N13_008"]


def write_shp(path, lines, mesh="644142"):
    with shapefile.Writer(path, shapeType=shapefile.POLYLINE, encoding="utf-8") as w:
        for name in FIELDS:
            w.field(name, "C", size=10)
        for points in lines:
            w.line([points])
            w.record("2024-01-01", "1", "3", "1", "0", "2", "1", mesh)


def read_back(path):
    nodes, ways = 0, []
    for obj in osmium.FileProcessor(str(path)):
        if obj.is_node():
            nodes += 1
        elif obj.is_way():
            ways.append([n.ref for n in obj.nodes])
    return nodes, ways


def test_shared_vertex_becomes_shared_node(tmp_path):
    # 2本の線が (141.1, 43.0) で接する
    write_shp(tmp_path / "roads", [[(141.0, 43.0), (141.1, 43.0)], [(141.1, 43.0), (141.1, 43.1)]])
    stats = convert([str(tmp_path / "roads.shp")], [str(tmp_path / "out.osm"), str(tmp_path / "out.osm.pbf")])

    assert stats == {"features": 2, "nodes": 3, "ways": 2}
    for out in ("out.osm", "out.osm.pbf"):
        nodes, ways = read_back(tmp_path / out)
        assert nodes == 3
        assert ways[0][-1] == ways[1][0]


def test_zero_length_line_is_skipped(tmp_path):
    write_shp(tmp_path / "roads", [[(141.0, 43.0), (141.0, 43.0)], [(141.0, 43.0), (141.1, 43.0)]])
    stats = convert([str(tmp_path / "roads.shp")], [str(tmp_path / "out.osm")])
    assert stats["ways"] == 1


def test_meshes_are_joined_at_boundary(tmp_path):
    # 東経141度の境界で2つのメッシュの道路が接する
    write_shp(tmp_path / "west", [[(140.9, 43.0), (141.0, 43.0)]], mesh="644077")
    write_shp(tmp_path / "east", [[(141.0, 43.0), (141.1, 43.0)]], mesh="644170")
    stats = convert([str(tmp_path / "west.shp"), str(tmp_path / "east.shp")], [str(tmp_path / "out.osm.pbf")])

    assert stats == {"features": 2, "nodes": 3, "ways": 2}
    _, ways = read_back(tmp_path / "out.osm.pbf")
    assert ways[0][-1] == ways[1][0]
