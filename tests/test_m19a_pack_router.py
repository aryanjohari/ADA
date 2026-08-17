"""M19a Slice 6 — pack router and time intent tests."""

from __future__ import annotations

from ada.harness.pack_router import load_pack_config, resolve_chip, resolve_pack, route_utterance
from ada.harness.time_intent import map_time_intent


def test_sleep_intent() -> None:
    m = map_time_intent("going to sleep now")
    assert m["kind"] == "sleep"


def test_deep_work_intent() -> None:
    m = map_time_intent("starting deep work on thesis")
    assert m["kind"] == "focus_deep"


def test_focus_alias_maps_to_time_start() -> None:
    p = resolve_pack("focus_start")
    assert p is not None
    assert p["tool"] == "life_time_start"


def test_chip_meal_prefill() -> None:
    c = resolve_chip("meal")
    assert c is not None
    assert c["tool"] == "life_meal_log"
    assert c["prefill"] == "log meal: "
    assert c["preferred_tools"] == [
        "life_food_search",
        "life_meal_log",
        "life_nutrition_day",
    ]


def test_route_capture_prefix() -> None:
    r = route_utterance("capture: buy oat milk")
    assert r is not None
    assert r["tool"] == "life_capture"
    assert r["args"]["text"] == "buy oat milk"


def test_route_meal_pattern_sets_slot() -> None:
    r = route_utterance("add one banana to breakfast")
    assert r is not None
    assert r["tool"] == "life_meal_log"
    assert r["args"]["utterance"] == "one banana"
    assert r["args"]["meal_slot"] == "breakfast"


def test_route_sleep_pattern() -> None:
    r = route_utterance("going to sleep")
    assert r is not None
    assert r["tool"] == "life_time_start"
    assert r["args"]["kind"] == "sleep"


def test_route_sleep_with_period() -> None:
    r = route_utterance("going to sleep.")
    assert r is not None
    assert r["args"]["kind"] == "sleep"


def test_route_stop_focus() -> None:
    r = route_utterance("stop focus")
    assert r is not None
    assert r["tool"] == "life_time_stop"


def test_route_wake_pattern() -> None:
    r = route_utterance("woke up")
    assert r is not None
    assert r["tool"] == "life_time_start"
    assert r["args"]["kind"] == "wake"


def test_route_lift_nl_pattern() -> None:
    r = route_utterance("flat bench 50kg x6")
    assert r is not None
    assert r["tool"] == "life_lift_log"
    assert r["args"]["utterance"] == "flat bench 50kg x6"


def test_pack_config_loads() -> None:
    cfg = load_pack_config()
    assert "meal_log" in (cfg.get("packs") or {})
    assert "due_add" in (cfg.get("packs") or {})
    assert cfg.get("aliases")


def test_chip_due_binds_due_add() -> None:
    c = resolve_chip("due")
    assert c is not None
    assert c["verb"] == "due_add"
    assert c["tool"] == "memory_open_loops_upsert"
    assert c["prefill"] == "add due: "


def test_route_good_morning_alias() -> None:
    r = route_utterance("good morning")
    assert r is not None
    assert r["verb"] == "time_start"
    assert r["tool"] == "life_time_start"
    assert r["args"]["kind"] == "wake"


def test_route_macros_alias() -> None:
    r = route_utterance("macros")
    assert r is not None
    assert r["verb"] == "nutrition_day"
    assert r["tool"] == "life_nutrition_day"


def test_route_whats_due_alias() -> None:
    r = route_utterance("what's due")
    assert r is not None
    assert r["verb"] == "due_list"
    assert r["tool"] == "memory_open_loops_list"


def test_route_gotta_finish_alias() -> None:
    r = route_utterance("gotta finish thesis by Thursday")
    assert r is not None
    assert r["verb"] == "due_add"
    assert r["tool"] == "memory_open_loops_upsert"


def test_route_remind_me_alias() -> None:
    r = route_utterance("remind me to stretch at 7")
    assert r is not None
    assert r["verb"] == "remind"
    assert r["tool"] == "memory_open_loops_upsert"


def test_route_what_did_i_eat() -> None:
    r = route_utterance("what did i eat")
    assert r is not None
    assert r["verb"] == "nutrition_day"


def test_route_hows_my_day() -> None:
    r = route_utterance("how's my day")
    assert r is not None
    assert r["verb"] == "life_status"
    assert "life_nutrition_day" in r["preferred_tools"]
    assert "memory_open_loops_list" in r["preferred_tools"]


def test_route_gym_status_alias() -> None:
    r = route_utterance("what did i lift")
    assert r is not None
    assert r["verb"] == "gym_status"
    assert r["tool"] == "life_gym_status"


def test_route_add_due_prefix() -> None:
    r = route_utterance("add due: finish thesis by Friday")
    assert r is not None
    assert r["verb"] == "due_add"
    assert r["args"]["utterance"] == "finish thesis by Friday"
