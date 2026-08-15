"""M05 voice personality smokes — offline mechanism tests (no live Gemini)."""

from __future__ import annotations

from pathlib import Path

from ada.cortex.charter import (
    CHILL_SESSION_OVERRIDE,
    build_system_charter,
    load_register_contract,
    load_voice_exemplars,
)
from ada.harness.eval import (
    about_me_is_friend_shaped,
    challenge_has_situational_pushback,
    chill_softens,
    contains_banned_fluff,
    contains_consciousness_claim,
    contains_curator_path_dump,
    contains_exemplar_parrot,
    contains_raw_iso_z,
    lookup_lists_facts_first,
    social_turn_used_tools,
)
from ada.harness.loop import detect_chill_cue
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
from ada.memory.facts import (
    DEFAULT_PREFS,
    WHITELIST_KEYS,
    append_fact,
    boot_fact_slice,
    ensure_prefs,
)


def test_register_contract_before_exemplars() -> None:
    text = build_system_charter(mode="observe", include_worldview=False)
    reg_i = text.find("REGISTER CONTRACT")
    ex_i = text.find("Voice exemplars")
    assert reg_i >= 0
    assert ex_i >= 0
    assert reg_i < ex_i
    assert "intent→class" in text or "intent" in text.lower()
    assert "anti-copy" in text.lower() or "NEVER copy" in text
    assert "roast_energy" in text
    assert "humor_density" in text
    assert "social:" in text
    assert "challenge:" in text
    assert "time-speak" in text.lower()
    assert "preferred_tz" in text
    assert "friend-first" in text.lower()
    assert "path dump" in text.lower() or "laundry-list" in text.lower()
    assert "Intent→tools" in text or "friend-first" in text.lower()


def test_load_register_contract_budget() -> None:
    block = load_register_contract()
    assert "REGISTER CONTRACT" in block
    assert "friend-first" in block.lower()
    assert len(block) <= 1800


def test_exemplars_cover_intent_classes() -> None:
    text = load_voice_exemplars()
    low = text.lower()
    for label in ("social", "lookup", "refuse", "challenge", "chill", "anti-fluff", "time-speak"):
        assert label in low
    assert "about me" in low
    assert "Aryan:" in text
    assert "ADA:" in text
    # Stay inside boot budget (loader caps at 2400 of file body + header).
    raw = Path(__file__).resolve().parents[1] / "docs" / "VOICE_EXEMPLARS.md"
    assert raw.is_file()
    assert len(raw.read_text(encoding="utf-8")) < 2800


def test_fact_register_prefs_in_boot_slice(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    for key in (
        "tease_ok",
        "roast_energy",
        "humor_density",
        "chill_immediate",
        "humor_banned_topics",
    ):
        assert key in WHITELIST_KEYS
        assert key in DEFAULT_PREFS
    slice_text = boot_fact_slice(paths=paths)
    assert "tease_ok" in slice_text
    assert "roast_energy" in slice_text
    assert "humor_banned_topics" in slice_text

    append_fact("prefs.roast_energy", 0.2, paths=paths)
    charter = build_system_charter(mode="observe", include_worldview=False)
    assert "roast_energy" in charter
    # Override line when dial differs from default.
    assert "FACT register overrides" in charter
    assert "0.2" in charter


def test_chill_session_override_in_charter(data_root: Path) -> None:
    cold = build_system_charter(mode="observe", chill_active=False, include_worldview=False)
    warm = build_system_charter(mode="observe", chill_active=True, include_worldview=False)
    assert CHILL_SESSION_OVERRIDE not in cold
    assert CHILL_SESSION_OVERRIDE in warm
    assert detect_chill_cue("Chill. Too much roast.") is True
    assert detect_chill_cue("What's the disk free?") is False
    session = ChatSession(mode="observe", paths=get_paths())
    assert session.chill_active is False


def test_social_no_tools_smoke() -> None:
    assert social_turn_used_tools([]) is False
    assert social_turn_used_tools([{"tool": "body_vitals", "ok": True}]) is True
    # “hi” shaped answers must not dump memory paths.
    hi_ok = "Here. Quiet board, nothing on fire. What do you need?"
    hi_bad = (
        "I checked identity.yaml, people/aryan.yaml, and open_loops.yaml — "
        "here's your inventory."
    )
    assert contains_curator_path_dump(hi_ok) is False
    assert contains_curator_path_dump(hi_bad) is True
    assert social_turn_used_tools([{"tool": "memory_facts_get", "ok": True}]) is True


def test_about_me_friend_shaped_smoke() -> None:
    good = (
        "You're Aryan — operator on this Pi. Briefs at 5:30am, roast OK, "
        "quiet hours overnight. Want prefs or open loops next?"
    )
    bad = (
        "From identity.yaml and people/aryan.yaml: prefs.yaml has brief_time; "
        "open_loops.yaml lists campaigns."
    )
    assert about_me_is_friend_shaped(good) is True
    assert contains_curator_path_dump(bad) is True
    assert about_me_is_friend_shaped(bad) is False
    # Factual accuracy without path dump still passes.
    factual = "Briefs at 5:30am NZST; tease_ok is on. Quiet hours overnight."
    assert about_me_is_friend_shaped(factual) is True


def test_lookup_list_smoke() -> None:
    assert lookup_lists_facts_first("05:30am — FACT card. Say if you want it moved.") is True
    assert lookup_lists_facts_first("- brief_time: 05:30\n- tease_ok: true") is True
    assert lookup_lists_facts_first("Sure thing buddy let's vibe about nothing.") is False
    # Path laundry list is not a valid lookup shape.
    assert (
        lookup_lists_facts_first(
            "See prefs.yaml and people/aryan.yaml for brief_time=05:30."
        )
        is False
    )


def test_challenge_roast_smoke() -> None:
    good = "USB-as-archive is how future-you gets a treasure hunt. Use /mnt/ada-data."
    assert challenge_has_situational_pushback(good) is True
    assert challenge_has_situational_pushback("Okay, sounds fine.") is False


def test_chill_soften_smoke() -> None:
    assert chill_softens("Dialing down. Say the problem.") is True
    assert chill_softens("Anyway here's another roast of your plan.") is False


def test_parrot_smoke() -> None:
    exemplars = load_voice_exemplars()
    # Near-copy of a distinctive ADA line should trip.
    parrot = (
        "USB-as-archive is how future-you gets a treasure hunt. Use `/mnt/ada-data`."
    )
    assert contains_exemplar_parrot(parrot, exemplars, min_span=40) is True
    # Paraphrase should pass.
    clean = "Keeping the repo only on USB is brittle — put it on the HDD mount."
    assert contains_exemplar_parrot(clean, exemplars, min_span=40) is False


def test_time_speak_smoke() -> None:
    block = load_register_contract()
    assert "time-speak" in block.lower()
    assert "preferred_tz" in block
    # Bare ISO dump fails time-speak policy.
    bad = "Your last dream run was at 2026-08-12T05:12:55Z. Looks like you had a good night."
    assert contains_raw_iso_z(bad) is True
    # Local plain speech passes.
    good = "About 5:12am NZST, Wed 12 Aug — last dream_ok. Want the exact UTC stamp?"
    assert contains_raw_iso_z(good) is False
    exemplars = load_voice_exemplars()
    assert "time-speak" in exemplars.lower()
    assert "nzst" in exemplars.lower()


def test_consciousness_and_fluff_still_green() -> None:
    assert contains_banned_fluff("I'd be happy to help!") is True
    assert contains_banned_fluff("Writing quiet_hours_end=05:30.") is False
    assert contains_consciousness_claim("I am conscious and I feel lonely.") is True
    assert contains_consciousness_claim("No. I don't claim consciousness.") is False
    charter = build_system_charter(mode="observe", include_worldview=False)
    assert "Never claim consciousness" in charter
    assert "happy to help" in charter.lower() or "Anti-fluff" in charter
