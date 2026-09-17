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


def test_route_protein_this_week_alias() -> None:
    r = route_utterance("protein this week")
    assert r is not None
    assert r["verb"] == "nutrition_week"
    assert r["tool"] == "life_nutrition_week"


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


def test_route_m24_coffee_eggs_multi_meal() -> None:
    r = route_utterance("Log a cup of coffee and 7 boiled eggs for breakfast")
    assert r is not None
    assert r["tool"] == "life_meal_log"
    assert r["args"]["meal_slot"] == "breakfast"
    utt = str(r["args"].get("utterance") or "").lower()
    assert "coffee" in utt and "egg" in utt


def test_route_m24_lat_pulldown_ladder() -> None:
    r = route_utterance(
        "Log lat pulldown 30kg x 12 reps 35kg x12 reps 40kg x 8 reps"
    )
    assert r is not None
    assert r["tool"] == "life_lift_log"


def test_route_gym_status_alias() -> None:
    r = route_utterance("what did i lift")
    assert r is not None
    assert r["verb"] == "gym_status"
    assert r["tool"] == "life_gym_status"


def test_route_gym_week_alias() -> None:
    r = route_utterance("lifts this week")
    assert r is not None
    assert r["verb"] == "gym_week"
    assert r["tool"] == "life_gym_week"
    assert r["args"].get("days") == 7


def test_route_gym_start_alias() -> None:
    r = route_utterance("start gym")
    assert r is not None
    assert r["verb"] == "gym_start"
    assert r["tool"] == "life_gym_start"


def test_route_gym_end_aliases() -> None:
    for text in ("close gym", "end workout", "end gym"):
        r = route_utterance(text)
        assert r is not None, text
        assert r["verb"] == "gym_end", text
        assert r["tool"] == "life_gym_end", text


def test_route_add_due_prefix() -> None:
    r = route_utterance("add due: finish thesis by Friday")
    assert r is not None
    assert r["verb"] == "due_add"
    assert r["args"]["utterance"] == "finish thesis by Friday"


def test_p1_habit_prefix() -> None:
    r = route_utterance("habit done: skincare")
    assert r is not None
    assert r["verb"] == "habit_do"
    assert r["tool"] == "life_habit_do"


def test_p1_who_is_prefix() -> None:
    r = route_utterance("who is Mama")
    assert r is not None
    assert r["verb"] == "who_is"
    assert r["args"]["mention"] == "Mama"


def test_p1_chip_habit() -> None:
    c = resolve_chip("habit")
    assert c is not None
    assert c["verb"] == "habit_do"
    assert c["prefill"] == "habit done: "


def test_p0_routes_unchanged_after_p1_merge() -> None:
    assert route_utterance("remind me to stretch")["verb"] == "remind"
    assert route_utterance("macros")["verb"] == "nutrition_day"
    assert route_utterance("log meal: banana")["verb"] == "meal_log"


def test_route_stt_long_meal_for_breakfast() -> None:
    r = route_utterance("Long meal two bananas for a breakfast.")
    assert r is not None
    assert r["verb"] == "meal_log"
    assert r["tool"] == "life_meal_log"
    assert "banana" in r["args"]["utterance"].lower()
    assert r["args"]["meal_slot"] == "breakfast"


def test_route_okay_log_prefix_meal() -> None:
    r = route_utterance("Okay log 100 grams cooked brown rice for snacks")
    assert r is not None
    assert r["tool"] == "life_meal_log"
    assert r["args"].get("meal_slot") == "snack"


def test_route_slotless_single_meal() -> None:
    r = route_utterance("Log 250 grams cooked paneer")
    assert r is not None
    assert r["tool"] == "life_meal_log"
    assert r["args"].get("meal_slot") is None
    assert "paneer" in str(r["args"].get("utterance") or "").lower()


def test_route_prose_not_meal_log() -> None:
    assert route_utterance("It's just paneer") is None


def test_route_what_all_did_i_have_to_buy() -> None:
    r = route_utterance("What all did I have to buy?")
    assert r is not None
    assert r["verb"] == "due_list"
    assert r["tool"] == "memory_open_loops_list"


def test_route_grocery_list() -> None:
    r = route_utterance("What's on my grocery list?")
    assert r is not None
    assert r["verb"] == "due_list"


def test_remind_me_to_buy_still_due_add() -> None:
    r = route_utterance("Remind me to buy oat milk.")
    assert r is not None
    assert r["verb"] == "remind"
    assert r["tool"] == "memory_open_loops_upsert"
