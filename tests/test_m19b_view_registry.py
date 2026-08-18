"""M19b v1.6.1 shipped slice — nutrition_day payload + markdown contract."""

from __future__ import annotations

from pathlib import Path

from ada.tools.gateway import Gateway


def test_nutrition_day_payload_has_honest_meal_rows(data_root: Path) -> None:
    gw = Gateway(mode="agent")
    gw.execute(
        "life_meal_log",
        {
            "lines": [
                {
                    "display_name": "eggs",
                    "provenance": "manual",
                    "nutrients": {"energy_kcal": 140, "protein_g": 12},
                },
                {
                    "display_name": "toast",
                    "provenance": "manual",
                    "nutrients": {"energy_kcal": 80, "protein_g": 3},
                },
            ],
            "meal_slot": "breakfast",
        },
    )
    obs = gw.execute("life_nutrition_day", {})
    assert obs.ok
    data = obs.data or {}
    assert data.get("date")
    assert data.get("totals", {}).get("energy_kcal") == 220
    assert data.get("totals", {}).get("protein_g") == 15
    meals = data.get("meals") or []
    assert len(meals) == 1
    assert meals[0]["meal_slot"] == "breakfast"
    assert meals[0]["foods"] == ["eggs", "toast"]
    assert meals[0]["kcal"] == 220.0
    assert meals[0]["protein_g"] == 15.0


def test_nutrition_day_empty_fails_closed(data_root: Path) -> None:
    obs = Gateway(mode="observe").execute("life_nutrition_day", {})
    assert obs.ok
    data = obs.data or {}
    assert data.get("totals") == {}
    assert data.get("meals") == []


def test_stream_markdown_uses_light_allowlist() -> None:
    root = Path(__file__).resolve().parents[1]
    markdown_js = (root / "src/ada/hud/static/js/markdown.js").read_text(
        encoding="utf-8"
    )
    stream_js = (root / "src/ada/hud/static/js/stream.js").read_text(
        encoding="utf-8"
    )
    assert "renderMarkdownSafe(raw, { headings: false })" in stream_js
    assert ".replace(/`([^`]+)`/g" in markdown_js
    assert '.replace(/\\*\\*([^*]+)\\*\\*/g' in markdown_js
    assert 'listItems' in markdown_js and '"<ul>" +' in markdown_js
    assert '"<pre><code>" + esc(codeBuf.join("\\n")) + "</code></pre>"' in markdown_js
    assert "innerHTML = renderMarkdownSafe" in stream_js
    assert "<script" not in markdown_js


def test_boot_path_js_stays_syntax_conservative() -> None:
    root = Path(__file__).resolve().parents[1]
    for rel in (
        "src/ada/hud/static/js/markdown.js",
        "src/ada/hud/static/js/stream.js",
        "src/ada/hud/static/js/today.js",
    ):
        text = (root / rel).read_text(encoding="utf-8")
        assert "??" not in text
        assert "?." not in text
    markdown_js = (root / "src/ada/hud/static/js/markdown.js").read_text(
        encoding="utf-8"
    )
    assert "...opts" not in markdown_js
