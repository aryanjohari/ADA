"""Body tool wrappers call M00 organs — no second probe stack."""

from unittest.mock import MagicMock, patch

from ada.tools import body_tools
from ada.tools.gateway import Gateway


def test_body_vitals_tool_calls_collect_vitals(data_root):
    fake = MagicMock()
    fake.model_dump.return_value = {
        "ts": "2026-01-01T00:00:00Z",
        "host": {"hostname": "test"},
        "thermal": {"temp_c": 40.0, "throttled_hex": "0x0"},
        "memory": {"mem_available_bytes": 1_000_000},
        "mounts": {"ada_data_ok": True},
        "disks": [],
        "probe_errors": [],
    }
    with patch("ada.tools.body_tools.collect_vitals", return_value=fake) as spy:
        out = body_tools.run_body_vitals(section="summary")
        spy.assert_called_once()
        assert out["hostname"] == "test"
        assert out["temp_c"] == 40.0


def test_body_tools_via_gateway(data_root):
    with patch("ada.tools.body_tools.collect_vitals") as spy:
        snap = MagicMock()
        snap.model_dump.return_value = {
            "ts": "t",
            "host": {"hostname": "h"},
            "thermal": {"temp_c": 1.0, "throttled_hex": "0x0"},
            "memory": {"mem_available_bytes": 1},
            "mounts": {"ada_data_ok": True},
            "disks": [],
            "probe_errors": [],
        }
        spy.return_value = snap
        gw = Gateway(mode="observe")
        result = gw.execute("body_vitals", {"section": "summary"})
        assert result.ok
        spy.assert_called_once()
