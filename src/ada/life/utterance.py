"""Shared utterance hygiene for life pack doors."""

from __future__ import annotations

import re

LEADING_FILLER = re.compile(r"^(?:okay|ok|yeah|yep|sure|please)[,.\s]+", re.I)


def strip_leading_filler(text: str) -> str:
    raw = (text or "").strip()
    return LEADING_FILLER.sub("", raw).strip()
