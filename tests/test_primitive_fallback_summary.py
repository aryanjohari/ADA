"""Operator fallback summaries for run_primitive stream failures."""

from __future__ import annotations

from ada.primitives.handlers import format_run_primitive_operator_summary


def test_recall_memory_summary_lists_excerpts() -> None:
    out = format_run_primitive_operator_summary(
        {
            "ok": True,
            "primitive": "recall_memory",
            "count": 2,
            "items": [
                {"content_excerpt": "SEO report for Ben"},
                {"content_excerpt": "Favorite color is blue"},
            ],
        }
    )
    assert out is not None
    assert "Here's what I remember:" in out
    assert "SEO report for Ben" in out
    assert "Favorite color is blue" in out


def test_recall_memory_empty_is_sanitized() -> None:
    out = format_run_primitive_operator_summary(
        {
            "ok": True,
            "primitive": "recall_memory",
            "count": 0,
            "items": [],
        }
    )
    assert out == "I don't have anything stored about that yet."


def test_recall_memory_strips_control_chars() -> None:
    out = format_run_primitive_operator_summary(
        {
            "ok": True,
            "primitive": "recall_memory",
            "count": 1,
            "items": [{"content_excerpt": "hello\x00world"}],
        }
    )
    assert out is not None
    assert "\x00" not in out
    assert "helloworld" in out
