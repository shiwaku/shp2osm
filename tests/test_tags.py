import pytest

from shp2osm.tags import road_tags


def rec(road_type="1", category="3", state="1", level="0", width="2", toll="1"):
    return {
        "N13_002": road_type,
        "N13_003": category,
        "N13_004": state,
        "N13_005": level,
        "N13_006": width,
        "N13_007": toll,
    }


@pytest.mark.parametrize(
    ("category", "highway"),
    [("1", "primary"), ("2", "secondary"), ("3", "residential"), ("4", "motorway"), ("5", "road"), ("6", "road")],
)
def test_category_to_highway(category, highway):
    assert road_tags(rec(category=category))["highway"] == highway


def test_narrow_residential_is_service():
    assert road_tags(rec(category="3", width="1"))["highway"] == "service"


@pytest.mark.parametrize(("road_type", "highway"), [("3", "footway"), ("4", "steps")])
def test_road_type_overrides_category(road_type, highway):
    assert road_tags(rec(road_type=road_type, category="1"))["highway"] == highway


def test_garden_path_is_driveway():
    tags = road_tags(rec(road_type="2"))
    assert tags["highway"] == "service"
    assert tags["service"] == "driveway"


def test_bridge_layer_is_at_least_one():
    assert road_tags(rec(state="2", level="0"))["layer"] == "1"
    assert road_tags(rec(state="2", level="3"))["layer"] == "3"
    assert road_tags(rec(state="2"))["bridge"] == "yes"


def test_tunnel():
    tags = road_tags(rec(state="3", level="2"))
    assert tags["tunnel"] == "yes"
    assert tags["layer"] == "-1"


def test_construction_keeps_original_highway():
    tags = road_tags(rec(state="5", category="1"))
    assert tags["highway"] == "construction"
    assert tags["construction"] == "primary"


def test_toll_and_ksj_tags():
    tags = road_tags(rec(toll="2", width="4"))
    assert tags["toll"] == "yes"
    assert tags["ksj:width"] == "13-19.5m"
    assert tags["ksj:category"] == "3"
    assert "toll" not in road_tags(rec(toll="1"))
