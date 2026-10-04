import pytest

from shp2osm.tags import road_tags


def rec(road_type="1", category="3", state="1", level="0", width="2", toll="1", date="2024-01-01", mesh="644142"):
    return {
        "N13_001": date,
        "N13_002": road_type,
        "N13_003": category,
        "N13_004": state,
        "N13_005": level,
        "N13_006": width,
        "N13_007": toll,
        "N13_008": mesh,
    }


@pytest.mark.parametrize(
    ("category", "highway"),
    [("1", "trunk"), ("2", "secondary"), ("3", "residential"), ("4", "motorway"), ("5", "road"), ("6", "road")],
)
def test_category_to_highway(category, highway):
    assert road_tags(rec(category=category))["highway"] == highway


def test_narrow_residential_stays_residential():
    assert road_tags(rec(category="3", width="1"))["highway"] == "residential"


@pytest.mark.parametrize(("road_type", "highway"), [("2", "path"), ("3", "footway"), ("4", "steps")])
def test_road_type_overrides_category(road_type, highway):
    tags = road_tags(rec(road_type=road_type, category="1"))
    assert tags["highway"] == highway
    assert "service" not in tags


def test_bridge_layer_is_at_least_one():
    assert road_tags(rec(state="2", level="0"))["layer"] == "1"
    assert road_tags(rec(state="2", level="3"))["layer"] == "3"
    assert road_tags(rec(state="2"))["bridge"] == "yes"


def test_tunnel_keeps_original_level():
    tags = road_tags(rec(state="3", level="2"))
    assert tags["tunnel"] == "yes"
    assert tags["layer"] == "-1"
    assert tags["ksj:level"] == "2"


def test_covered_keeps_layer():
    tags = road_tags(rec(state="4", level="1"))
    assert tags["covered"] == "yes"
    assert tags["layer"] == "1"
    assert "layer" not in road_tags(rec(state="4", level="0"))


def test_construction_keeps_original_highway():
    tags = road_tags(rec(state="5", category="1"))
    assert tags["highway"] == "construction"
    assert tags["construction"] == "trunk"


def test_toll():
    assert road_tags(rec(toll="2"))["toll"] == "yes"
    assert "toll" not in road_tags(rec(toll="1"))


def test_all_attributes_are_kept_as_ksj_tags():
    tags = road_tags(rec(road_type="1", category="2", state="2", level="3", width="4", toll="2"))
    assert {k: v for k, v in tags.items() if k.startswith("ksj:")} == {
        "ksj:date": "2024-01-01",
        "ksj:road_type": "1",
        "ksj:category": "2",
        "ksj:state": "2",
        "ksj:level": "3",
        "ksj:width": "13-19.5m",
        "ksj:toll": "2",
        "ksj:mesh": "644142",
    }
