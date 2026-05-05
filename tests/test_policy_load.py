from __future__ import annotations

import io
from contextlib import redirect_stderr
from pathlib import Path

from ada.policy.load import load_merged_policy


def test_unknown_top_level_policy_key_warns(tmp_path: Path) -> None:
    pol = tmp_path / "policies"
    pol.mkdir(parents=True)
    (pol / "default.yaml").write_text(
        "version: 1\nintent_max_bytes: 65536\nfoo_bar_programme_knob: 99\n",
        encoding="utf-8",
    )
    buf = io.StringIO()
    with redirect_stderr(buf):
        cfg = load_merged_policy(policy_root=pol)
    err = buf.getvalue()
    assert "unknown top-level key" in err
    assert "foo_bar_programme_knob" in err
    assert cfg.intent_max_bytes == 65536
