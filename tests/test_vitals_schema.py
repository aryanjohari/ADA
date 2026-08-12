"""Vitals schema + meminfo preference + throttle decode."""

from __future__ import annotations

from pathlib import Path

from ada.body.vitals import (
    VitalsSnapshot,
    collect_vitals,
    memory_from_meminfo,
    parse_meminfo,
    parse_throttled_hex,
)


MEMINFO_FIXTURE = """\
MemTotal:        8255872 kB
MemFree:          200000 kB
MemAvailable:    7403600 kB
SwapTotal:       2097152 kB
SwapFree:        2097152 kB
"""


def test_vitals_schema_roundtrip(data_root: Path) -> None:
    snap = collect_vitals(ada_root=data_root)
    assert isinstance(snap, VitalsSnapshot)
    data = snap.model_dump()
    again = VitalsSnapshot.model_validate(data)
    assert again.schema_version == 1
    # extras accepts arbitrary keys
    again.extras["custom_pi_quirk"] = 42
    assert again.extras["custom_pi_quirk"] == 42


def test_vitals_prefers_mem_available() -> None:
    parsed = parse_meminfo(MEMINFO_FIXTURE)
    mem = memory_from_meminfo(parsed)
    assert mem.mem_total_bytes == 8255872 * 1024
    assert mem.mem_available_bytes == 7403600 * 1024
    # Must not mistake MemFree for available
    assert mem.mem_available_bytes != 200000 * 1024


def test_throttled_parse() -> None:
    clean = parse_throttled_hex("0x0")
    assert clean.under_voltage_now is False
    assert clean.throttled_now is False

    # bit 0 = under_voltage_now; bit 2 = throttled_now
    flags = parse_throttled_hex("0x5")
    assert flags.under_voltage_now is True
    assert flags.throttled_now is True
    assert flags.freq_capped_now is False

    sticky = parse_throttled_hex("throttled=0x50000")
    assert sticky.under_voltage_sticky is True
    assert sticky.throttled_sticky is True
