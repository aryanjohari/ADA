"""Cost estimate uses rate table constants."""

from ada.cortex.cost import RATE_TABLE_USD_PER_1M, estimate_usd


def test_cost_estimate_uses_rate_table():
    assert "gemini-2.5-flash" in RATE_TABLE_USD_PER_1M
    est = estimate_usd("gemini-2.5-flash", prompt_tokens=1_000_000, candidates_tokens=1_000_000)
    inp, out = RATE_TABLE_USD_PER_1M["gemini-2.5-flash"]
    assert est.usd_estimate == round(inp + out, 6)
    assert est.labeled == "estimate"
