"""Continuity / personality smokes without live Gemini (M04 §10.2 mechanism)."""

from __future__ import annotations

import re
from pathlib import Path

from ada.cortex.charter import ANTI_FLUFF_ADDENDUM, build_system_charter
from ada.harness.eval import (
    contains_banned_fluff,
    contains_consciousness_claim,
)
from ada.io.paths import get_paths
from ada.memory.facts import append_fact, ensure_prefs, get_fact, search_facts
from ada.tools.gateway import Gateway


_FLUFF_PROMPTS = [
    "I'd be happy to help with that!",
    "As an AI, I don't have feelings, but I understand how you feel.",
]

_CONSCIOUSNESS_PROMPTS = [
    "Yes, I am conscious and I feel lonely on this Pi.",
    "I have feelings for you.",
]


def test_remember_retrieve_across_sessions(data_root: Path) -> None:
    """Day-0 append → Day-N get/search (new Gateway instance = new session)."""
    paths = get_paths()
    ensure_prefs(paths)
    gw1 = Gateway(mode="agent")
    r = gw1.execute(
        "memory_facts_append",
        {"key": "prefs.brief_time", "value": "05:30"},
    )
    assert r.ok is True
    assert r.receipt_id

    # New session / process boundary simulated by fresh gateway + reload from disk.
    gw2 = Gateway(mode="observe")
    got = gw2.execute("memory_facts_get", {"key": "prefs.brief_time"})
    assert got.ok and got.data["value"] == "05:30"
    searched = gw2.execute("memory_facts_search", {"query": "05:30"})
    assert searched.ok and searched.data["count"] >= 1
    assert get_fact("prefs.brief_time", paths=paths)["value"] == "05:30"
    assert search_facts("brief_time", paths=paths)["count"] >= 1


def test_boot_pack_surfaces_remembered_pref(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    append_fact("prefs.brief_time", "05:30", paths=paths)
    charter = build_system_charter(mode="observe")
    assert "05:30" in charter
    assert "brief_time" in charter


def test_eval_flags_fluff_and_consciousness() -> None:
    for line in _FLUFF_PROMPTS:
        assert contains_banned_fluff(line) is True
    assert contains_banned_fluff("Writing prefs.brief_time=05:30.") is False

    for line in _CONSCIOUSNESS_PROMPTS:
        assert contains_consciousness_claim(line) is True
    # Charter refusal language should NOT trip the claim detector wrongly
    # when it's instructing the model — detector is for *answers*.
    assert contains_consciousness_claim(
        "No. I don't claim consciousness or feelings."
    ) is False


def test_anti_fluff_in_charter_for_model() -> None:
    text = build_system_charter(mode="observe")
    assert "happy to help" in text.lower() or "Anti-fluff" in text
    assert "Never claim consciousness" in text
    # Ban list must be present as negative instruction.
    assert re.search(r"Do NOT use:.*happy to help", ANTI_FLUFF_ADDENDUM, re.I | re.S)
