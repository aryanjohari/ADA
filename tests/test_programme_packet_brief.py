"""ProgrammePacket brief_md validation."""

from __future__ import annotations

import pytest

from ada.policy.load import DEFAULT_INTENT_MAX_BYTES
from ada.programme.packet import ProgrammePacket


def test_packet_accepts_brief_md() -> None:
    p = ProgrammePacket(
        mission_slug="brief-m",
        title="T",
        brief_md="Operator intent for NZ ISR.",
    )
    assert p.brief_md == "Operator intent for NZ ISR."


def test_packet_rejects_brief_over_max_bytes() -> None:
    huge = "x" * (DEFAULT_INTENT_MAX_BYTES + 1)
    with pytest.raises(ValueError, match="brief_md exceeds"):
        ProgrammePacket(mission_slug="big", title="T", brief_md=huge)
