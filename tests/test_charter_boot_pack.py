"""Boot pack includes FACT slice, voice exemplars, anti-fluff (M04/M05)."""

from __future__ import annotations

from pathlib import Path

from ada.cortex.charter import (
    ANTI_FLUFF_ADDENDUM,
    build_system_charter,
    load_register_contract,
    load_voice_exemplars,
)
from ada.io.paths import get_paths
from ada.memory.facts import append_fact, ensure_prefs


def test_voice_exemplars_file_has_pairs() -> None:
    text = load_voice_exemplars()
    assert "Aryan:" in text
    assert "ADA:" in text
    assert "conscious" in text.lower()


def test_charter_includes_anti_fluff_and_facts(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    append_fact("prefs.brief_time", "05:30", paths=paths)
    from ada.memory.open_loops import upsert_loop

    upsert_loop(
        text="Boot camp",
        kind="campaign",
        status="active",
        stages=[{"id": "s1", "state": "active"}],
        current_stage="s1",
        paths=paths,
    )
    text = build_system_charter(mode="agent")
    assert "Never claim consciousness" in text
    assert "I'd be happy to help" in ANTI_FLUFF_ADDENDUM or "happy to help" in text.lower()
    assert "FACTS (dry" in text
    assert "brief_time" in text
    assert "campaigns:" in text
    assert "Boot camp" in text
    assert "Voice exemplars" in text
    assert "WORLDVIEW" in text
    assert "memory_facts_append" in text
    assert "REGISTER CONTRACT" in text
    assert text.find("REGISTER CONTRACT") < text.find("Voice exemplars")


def test_register_contract_loads() -> None:
    block = load_register_contract()
    assert "roast_energy" in block
    assert "tease_ok" in block


def test_fluff_ban_list_present() -> None:
    assert "I'd be happy to help" in ANTI_FLUFF_ADDENDUM or "happy to help" in ANTI_FLUFF_ADDENDUM.lower()
    assert "As an AI" in ANTI_FLUFF_ADDENDUM
    assert "consciousness" in ANTI_FLUFF_ADDENDUM.lower()
