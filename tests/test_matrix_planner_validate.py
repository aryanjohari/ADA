"""Matrix planner sanitisation helpers."""

from ada.publish.matrix_planner import validate_planner_entity_ids


def test_validate_dedupe_and_cap():
    ok, err = validate_planner_entity_ids(
        body={"entity_ids": [3, 1, 3, 2]},
        allowed_ids={1, 2, 3},
        cap_k=2,
    )
    assert err == ""
    assert ok == [3, 1]


def test_validate_rejects_unknown():
    ok, err = validate_planner_entity_ids(
        body={"entity_ids": [99]},
        allowed_ids={1, 2},
        cap_k=5,
    )
    assert ok is None
    assert "disallowed" in err


def test_validate_rejects_bad_shape():
    ok, err = validate_planner_entity_ids(
        body={"entity_ids": "nope"},
        allowed_ids={1},
        cap_k=2,
    )
    assert ok is None
    assert err == "entity_ids_not_list"


def test_validate_empty_entity_ids():
    ok, err = validate_planner_entity_ids(
        body={"entity_ids": []},
        allowed_ids={1},
        cap_k=2,
    )
    assert ok is None
    assert "empty_entity_ids" in err
