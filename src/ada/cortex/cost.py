"""Approximate USD rate table + estimate helper (not a billing product).

Official pricing: https://ai.google.dev/gemini-api/docs/pricing
Refresh constants when models change. $ figures are labeled estimates only.
"""

from __future__ import annotations

from dataclasses import dataclass

# Approximate USD per 1M tokens (verify official page before trusting $).
RATE_TABLE_USD_PER_1M: dict[str, tuple[float, float]] = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash-lite": (0.10, 0.40),
}


@dataclass(frozen=True)
class CostEstimate:
    model: str
    prompt_tokens: int
    candidates_tokens: int
    usd_estimate: float
    labeled: str = "estimate"


def rate_for(model: str) -> tuple[float, float]:
    """Return (input_per_1m, output_per_1m); fall back to flash rates."""
    return RATE_TABLE_USD_PER_1M.get(model, RATE_TABLE_USD_PER_1M["gemini-2.5-flash"])


def estimate_usd(
    model: str,
    *,
    prompt_tokens: int = 0,
    candidates_tokens: int = 0,
) -> CostEstimate:
    inp, out = rate_for(model)
    usd = (prompt_tokens / 1_000_000) * inp + (candidates_tokens / 1_000_000) * out
    return CostEstimate(
        model=model,
        prompt_tokens=prompt_tokens,
        candidates_tokens=candidates_tokens,
        usd_estimate=round(usd, 6),
    )


def heuristic_token_estimate(text: str) -> int:
    """Rough chars/4 heuristic when count_tokens is unavailable."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def estimate_from_text(model: str, system: str, user: str) -> CostEstimate:
    """Pre-call rough estimate — order-of-magnitude only."""
    prompt_tokens = heuristic_token_estimate(system) + heuristic_token_estimate(user)
    # Assume a short reply for pre-call display.
    return estimate_usd(model, prompt_tokens=prompt_tokens, candidates_tokens=256)
