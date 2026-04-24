"""Pydantic PageJsonV1 vs golden fixture."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ada.publish.page_schema_v1 import PageJsonV1


def test_pseo_golden_roundtrip():
    p = Path(__file__).resolve().parent / "fixtures" / "pseo_page.json"
    raw = p.read_text(encoding="utf-8")
    page = PageJsonV1.model_validate_json(raw)
    assert page.slug == "acme-corp-compliance"
    assert page.lead_gen.form_action_url.startswith("https://")
    out = page.model_dump_json()
    again = PageJsonV1.model_validate_json(out)
    assert again.slug == page.slug


def test_page_rejects_trash():
    with pytest.raises(Exception):
        PageJsonV1.model_validate(
            {
                "slug": "x",
                "title": "t",
                "meta_description": "m",
                "content": "c",
            }
        )
