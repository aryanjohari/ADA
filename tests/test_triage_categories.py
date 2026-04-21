from __future__ import annotations

import pytest

from ada.triage.categories import parse_triage_response


def test_parse_triage_response_valid():
    r = parse_triage_response(
        {
            "impact_score": 7,
            "primary_category": "sector_business",
            "secondary_categories": ["trade_industry"],
        }
    )
    assert r is not None
    assert r.impact_score == 7
    assert r.primary_category == "sector_business"
    assert r.secondary_categories == ("trade_industry",)


def test_parse_rejects_primary_in_secondaries():
    assert (
        parse_triage_response(
            {
                "impact_score": 5,
                "primary_category": "markets_macro",
                "secondary_categories": ["markets_macro"],
            }
        )
        is None
    )


def test_parse_rejects_too_many_secondaries():
    assert (
        parse_triage_response(
            {
                "impact_score": 5,
                "primary_category": "markets_macro",
                "secondary_categories": ["policy_regulation", "government_fiscal", "sector_business"],
            }
        )
        is None
    )


def test_parse_rejects_unknown_category():
    assert (
        parse_triage_response(
            {
                "impact_score": 5,
                "primary_category": "not_a_code",
                "secondary_categories": [],
            }
        )
        is None
    )
