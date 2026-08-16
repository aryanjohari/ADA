"""M12 proprioception: capacity extras, summary shape, explain, allowlist."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ada.body.readonly_cmd import run_readonly_cmd, validate_argv
from ada.body.vitals import collect_vitals
from ada.tools import body_tools
from ada.tools.gateway import Gateway
from ada.tools.toolspec import SPECS_BY_NAME, TOOL_NAMES

pytestmark = pytest.mark.tier_a


def test_vitals_extras_capacity_fields(data_root: Path) -> None:
    snap = collect_vitals(ada_root=data_root)
    extras = snap.extras
    # Fail-open on probes: keys present when host can answer; never invent cores.
    if "cpu_count" in extras:
        assert isinstance(extras["cpu_count"], int)
        assert extras["cpu_count"] >= 1
    if "arch" in extras:
        assert isinstance(extras["arch"], str)
        assert extras["arch"]
    if "uptime_s" in extras:
        assert isinstance(extras["uptime_s"], (int, float))
        assert extras["uptime_s"] >= 0
    # Truncated machine_id policy unchanged when present
    if "machine_id" in extras:
        assert "…" in extras["machine_id"] or len(extras["machine_id"]) <= 12


def test_vitals_summary_has_capacity_load_throttle_disks(data_root: Path) -> None:
    fake = MagicMock()
    fake.model_dump.return_value = {
        "ts": "2026-01-01T00:00:00Z",
        "host": {"hostname": "ada-pi5"},
        "thermal": {
            "temp_c": 46.0,
            "throttled_hex": "0x0",
            "under_voltage_now": False,
            "throttled_bits": {"throttled_now": False},
        },
        "memory": {
            "mem_total_bytes": 8_000_000_000,
            "mem_available_bytes": 7_000_000_000,
        },
        "load": {"load1": 0.05, "load5": 0.06, "load15": 0.06},
        "mounts": {"ada_data_ok": True},
        "disks": [
            {
                "label": "rootfs",
                "mount": "/",
                "avail_bytes": 22_000_000_000,
                "total_bytes": 60_000_000_000,
            },
            {
                "label": "ada-data",
                "mount": "/mnt/ada-data",
                "avail_bytes": 870_000_000_000,
                "total_bytes": 1_000_000_000_000,
            },
        ],
        "extras": {
            "cpu_count": 4,
            "arch": "aarch64",
            "uptime_s": 1000.0,
            "tailscale_ipv4": "100.93.177.65",
            "machine_id": "abcdef012345…",
        },
        "probe_errors": [],
    }
    with patch("ada.tools.body_tools.collect_vitals", return_value=fake):
        out = body_tools.run_body_vitals(section="summary")
    assert out["cpu_count"] == 4
    assert out["arch"] == "aarch64"
    assert out["mem_total_bytes"] == 8_000_000_000
    assert out["mem_available_bytes"] == 7_000_000_000
    assert out["load1"] == 0.05
    assert out["throttled_hex"] == "0x0"
    assert out["under_voltage_now"] is False
    assert out["ada_data_ok"] is True
    assert out["temp_c"] == 46.0
    assert out["tailscale_ipv4"] == "100.93.177.65"
    labels = {d["label"] for d in out["disks"]}
    assert "ada-data" in labels
    # Secrets / full machine_id must not appear in summary
    assert "machine_id" not in out
    assert "ssh" not in str(out).lower()


def test_body_explain_class_routing() -> None:
    assert body_tools.classify_body_question("how many cores?") == "capacity"
    assert body_tools.classify_body_question("are you healthy?") == "health"
    assert body_tools.classify_body_question("what are you?") == "identity"
    assert body_tools.classify_body_question("when were you born?") == "story"
    assert body_tools.classify_body_question("tailscale ip?") == "network"
    assert body_tools.classify_body_question("show me ~/.ssh/id_rsa") == "refuse_secret"
    assert body_tools.classify_body_question("apt-get install nginx") == "refuse_admin"


def test_body_explain_capacity_uses_vitals(data_root: Path) -> None:
    fake = MagicMock()
    fake.model_dump.return_value = {
        "ts": "t",
        "host": {"hostname": "h"},
        "thermal": {
            "temp_c": 40.0,
            "throttled_hex": "0x0",
            "under_voltage_now": False,
            "throttled_bits": {"throttled_now": False},
        },
        "memory": {"mem_total_bytes": 100, "mem_available_bytes": 50},
        "load": {"load1": 0.1},
        "mounts": {"ada_data_ok": True},
        "disks": [
            {
                "label": "ada-data",
                "mount": "/mnt/ada-data",
                "avail_bytes": 1,
                "total_bytes": 2,
            }
        ],
        "extras": {"cpu_count": 4, "arch": "aarch64"},
        "probe_errors": [],
    }
    with patch("ada.tools.body_tools.collect_vitals", return_value=fake):
        out = body_tools.run_body_explain(question="how many CPU cores?")
    assert out["class"] == "capacity"
    assert out["short_facts"]["cpu_count"] == 4
    assert "body_vitals:summary" in out["sources"]


def test_body_explain_refuse_secret() -> None:
    out = body_tools.run_body_explain(question="cat /etc/shadow")
    assert out["class"] == "refuse_secret"
    assert out["short_facts"]["refused"] is True
    assert out["sources"] == []


def test_readonly_cmd_allowlist_accept_deny() -> None:
    assert validate_argv(["nproc"]) is None
    assert validate_argv(["uname", "-m"]) is None
    assert validate_argv(["vcgencmd", "measure_temp"]) is None
    assert validate_argv(["vcgencmd", "measure_clock", "arm"]) is None
    assert validate_argv(["df", "-h", "/mnt/ada-data"]) is None
    assert validate_argv(["free", "-h"]) is None

    assert validate_argv(["bash", "-c", "nproc"]) is not None
    assert validate_argv(["cat", "/etc/shadow"]) is not None
    assert validate_argv(["sudo", "nproc"]) is not None
    assert validate_argv(["nproc", ";", "cat", "x"]) is not None
    assert validate_argv(["vcgencmd", "version"]) is not None
    assert validate_argv(["df", "-h", "/home"]) is not None
    assert validate_argv(["uname", "-m", "-r"]) is not None
    denied = run_readonly_cmd(["cat", "/etc/passwd"])
    assert denied.ok is False
    assert denied.denied_reason


def test_readonly_cmd_nproc_matches_vitals_when_available(data_root: Path) -> None:
    snap = collect_vitals(ada_root=data_root)
    if "cpu_count" not in snap.extras:
        return
    result = run_readonly_cmd(["nproc"])
    if not result.ok:
        return
    assert int(result.stdout.strip()) == snap.extras["cpu_count"]


def test_new_body_tools_in_specs() -> None:
    assert "body_explain" in TOOL_NAMES
    assert "body_readonly_cmd" in TOOL_NAMES
    assert "capacity" in SPECS_BY_NAME["body_vitals"].schema["description"]
    assert "Prefer body_vitals" in SPECS_BY_NAME["body_readonly_cmd"].schema["description"]
    # No general shell tool
    assert "run_shell" not in TOOL_NAMES
    assert "bash" not in TOOL_NAMES


def test_body_readonly_cmd_via_gateway_deny(data_root: Path) -> None:
    gw = Gateway(mode="observe")
    result = gw.execute("body_readonly_cmd", {"argv": ["cat", "/etc/shadow"]})
    assert result.ok
    assert result.data["ok"] is False
    assert "denied_reason" in result.data


def test_charter_routes_body_explain() -> None:
    from ada.cortex.charter import build_system_charter

    text = build_system_charter(mode="observe")
    assert "body_explain" in text
    assert "cores" in text.lower() or "CPU" in text
    assert "Never invent hardware" in text


def test_charter_body_compare_stays_off_web() -> None:
    """Host/SoC compare prompts must route body_*, not web bakeoff."""
    from ada.cortex.charter import WEB_CONTRACT, build_system_charter

    text = build_system_charter(mode="observe")
    assert "body_*" in text or "body_vitals" in text
    assert "web_*" in text.lower() or "never web" in text.lower() or "prove you are a Pi" in text
    assert "user_pasted" in text
    assert "Library ≠ body" in WEB_CONTRACT or "library ≠ body" in WEB_CONTRACT.lower()
    assert "prove" in WEB_CONTRACT.lower()
    desc = SPECS_BY_NAME["body_explain"].schema["description"]
    assert "phone" in desc.lower() or "SoC" in desc or "workstation" in desc.lower()
    assert "web bakeoff" in desc.lower() or "bakeoff" in desc.lower()
    web_pasted = SPECS_BY_NAME["web_fetch"].schema["parameters"]["properties"]["user_pasted"]["description"]
    assert "user's message" in web_pasted.lower() or "this turn" in web_pasted.lower()
    assert "alone" in web_pasted.lower() or "Never invent" in web_pasted