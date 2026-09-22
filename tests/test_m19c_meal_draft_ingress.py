"""M19c #1 meal-draft ingress — session stickiness + Add-while-open divert."""

from __future__ import annotations

from pathlib import Path

import pytest

from ada.cortex.adapter import CortexTurn, ProposedToolCall
from ada.harness.loop import run_turn
from ada.harness.meal_draft_spine import is_meal_draft_start
from ada.harness.pack_router import route_utterance
from ada.harness.session import ChatSession
from ada.io.paths import get_paths
from ada.logs import meal_draft as draft_mod
from ada.logs.favorites import set_favorite
from ada.logs.food import insert_food
from ada.tools.life_tools import (
    _refuse_empty_macros,
    run_life_meal_draft_start,
    run_life_meal_log,
)


class _ShouldNotRunAdapter:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        raise AssertionError("pack/divert should finish before model generate")


class _DraftStartWrongSidAdapter:
    """Cortex invents session_id=meal_draft_1 (phone f024fb03… failure mode)."""

    model = "fake"
    _n = 0

    def generate(self, *, system, contents, tools=None):
        self._n += 1
        if self._n == 1:
            return CortexTurn(
                text=None,
                tool_calls=[
                    ProposedToolCall(
                        name="life_meal_draft_start",
                        args={"session_id": "meal_draft_1"},
                        call_id="draft-wrong-sid",
                    )
                ],
            )
        return CortexTurn(text="draft open", tool_calls=[])


class _CapturingSink:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def emit(self, event: str, payload: dict) -> None:
        self.events.append((event, payload))


def _isolate_usda(monkeypatch: pytest.MonkeyPatch, data_root: Path) -> None:
    monkeypatch.delenv("USDA_FDC_API_KEY", raising=False)
    secrets = data_root / "secrets"
    secrets.mkdir(exist_ok=True)
    monkeypatch.setenv("ADA_SECRETS_DIR", str(secrets))


def _seed_egg(paths) -> dict:
    return insert_food(
        name="Egg, whole, boiled or poached",
        source="usda_fdc",
        external_id="2707154-m19c",
        nutrients_per_100g={
            "energy_kcal": 155,
            "protein_g": 12.6,
            "fat_g": 10.6,
            "carb_g": 1.1,
        },
        paths=paths,
    )


def _tools(result) -> list[str]:
    return [str(r.get("tool") or "") for r in result.tool_receipts]


@pytest.fixture
def draft_ingress_root(data_root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _isolate_usda(monkeypatch, data_root)
    return data_root


def test_start_phrases_route_to_draft(draft_ingress_root: Path) -> None:
    for text in (
        "Add a meal",
        "I wanna make a meal",
        "Make a meal",
        "Make a meal smoothie",
        "want to make a meal",
    ):
        assert is_meal_draft_start(text), text
        routed = route_utterance(text)
        assert routed is not None, text
        assert routed.get("verb") == "meal_draft_start", text
        assert routed.get("tool") == "life_meal_draft_start", text


def test_pack_start_uses_chat_session(draft_ingress_root: Path) -> None:
    session = ChatSession(mode="agent")
    result = run_turn(session, "I wanna make a meal", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    assert "life_meal_draft_start" in _tools(result)
    paths = get_paths()
    assert draft_mod.load_draft(session.session_id, paths=paths) is not None
    assert draft_mod.load_draft("meal_draft_1", paths=paths) is None
    assert not draft_mod.draft_path("meal_draft_1", paths=paths).is_file()


def test_cortex_wrong_sid_coerced_to_chat_session(draft_ingress_root: Path) -> None:
    """Model passes session_id=meal_draft_1; metal keys scratch to chat session."""
    session = ChatSession(mode="agent")
    # Avoid pack start so cortex runs (utterance not a draft-start door).
    result = run_turn(
        session, "2 bananas medium please compose", _DraftStartWrongSidAdapter()
    )
    assert "life_meal_draft_start" in _tools(result)
    start = next(
        r for r in result.tool_receipts if r.get("tool") == "life_meal_draft_start"
    )
    assert (start.get("args") or {}).get("session_id") == session.session_id
    paths = get_paths()
    assert draft_mod.load_draft(session.session_id, paths=paths) is not None
    assert draft_mod.load_draft("meal_draft_1", paths=paths) is None
    orphan = paths.scratch / "meal_draft_meal_draft_1.json"
    assert not orphan.is_file()


def test_add_while_draft_open_uses_draft_add(draft_ingress_root: Path) -> None:
    paths = get_paths()
    egg = _seed_egg(paths)
    set_favorite(
        query="eggs",
        ref_id=egg["food_ref_id"],
        label=egg["name"],
        confirmed=True,
        paths=paths,
    )
    session = ChatSession(mode="agent")
    start = run_turn(session, "add a meal", _ShouldNotRunAdapter())
    assert start.stop_reason == "pack_fast_path"
    assert draft_mod.load_draft(session.session_id, paths=paths) is not None

    add = run_turn(session, "Add 5 eggs", _ShouldNotRunAdapter())
    tools = _tools(add)
    assert "life_meal_draft_add" in tools
    assert "life_meal_log" not in tools
    draft = draft_mod.load_draft(session.session_id, paths=paths)
    assert draft is not None
    # Confirm may hold write; either line landed or needs_confirm stash is fine —
    # critical is draft_add not meal_log.
    add_rc = next(
        r for r in add.tool_receipts if r.get("tool") == "life_meal_draft_add"
    )
    data = add_rc.get("data") or {}
    assert data.get("ok") is True or data.get("needs_confirm") is True


def test_open_draft_add_a_meal_does_not_food_resolve(draft_ingress_root: Path) -> None:
    paths = get_paths()
    session = ChatSession(mode="agent")
    run_life_meal_draft_start({"session_id": session.session_id})
    assert draft_mod.load_draft(session.session_id, paths=paths) is not None

    result = run_turn(session, "add a meal", _ShouldNotRunAdapter())
    assert result.stop_reason == "pack_fast_path"
    tools = _tools(result)
    assert "life_meal_draft_add" not in tools
    assert "life_meal_draft_start" not in tools
    draft = draft_mod.load_draft(session.session_id, paths=paths)
    assert draft is not None
    assert draft.get("lines") == []
    assert "already open" in (result.text or "").lower()


def test_null_energy_kcal_refuses_write(draft_ingress_root: Path) -> None:
    """P/F/C without energy must not write kcal 0 (oats path on f024fb03…)."""
    refused = _refuse_empty_macros(
        [
            {
                "display_name": "Oats, rolled",
                "ref_id": "fake-oats-ref",
                "serving_grams": 50,
                "nutrients": {
                    "energy_kcal": None,
                    "protein_g": 6.7,
                    "fat_g": 2.9,
                    "carb_g": 34.3,
                },
            }
        ]
    )
    assert refused is not None
    assert refused.get("reason") == "empty_macros"

    out = run_life_meal_log(
        {
            "lines": [
                {
                    "display_name": "Oats, rolled",
                    "ref_id": "fake-oats-ref",
                    "serving_grams": 50,
                    "nutrients": {
                        "energy_kcal": None,
                        "protein_g": 6.7,
                        "fat_g": 2.9,
                        "carb_g": 34.3,
                    },
                    "snapshot_json": {
                        "schema_version": 1,
                        "nutrients": {
                            "energy_kcal": None,
                            "protein_g": 6.7,
                            "fat_g": 2.9,
                            "carb_g": 34.3,
                        },
                    },
                }
            ],
            "resolve": {
                "bind_authority": "meal_spine",
                "needs_confirm": False,
                "reasons": ["favorite_unique"],
                "rows": [],
            },
            "confirmed": True,
        }
    )
    assert out.get("ok") is False
    assert out.get("reason") == "empty_macros" or out.get("error") == "empty_macros"
