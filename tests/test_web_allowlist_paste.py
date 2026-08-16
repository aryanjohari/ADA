"""Paste-this-turn allowlist: user_pasted alone must not grant (harden 2026-08-15)."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from ada.io.paths import get_paths
from ada.memory.facts import ensure_prefs
from ada.tools import web_tools
from ada.tools.gateway import Gateway
from ada.tools.web_tools import run_web_fetch
from ada.web import allowlist as allowlist_mod
from ada.web.fetch import web_fetch

pytestmark = pytest.mark.tier_a


def test_user_pasted_alone_needs_confirm(data_root: Path) -> None:
    """Model flag without host in user text → fail closed."""
    paths = get_paths()
    decision = allowlist_mod.check_host_access(
        "https://gsmarena.example/foo",
        paths=paths,
        user_pasted=True,
        turn_user_text="phone SoC or tiny workstation — prove with numbers",
    )
    assert decision.get("needs_confirm") is True
    assert decision.get("ok") is False
    assert decision.get("host") == "gsmarena.example"


def test_pasted_host_in_user_text_ok(data_root: Path) -> None:
    paths = get_paths()
    url = "https://example.com/page"
    decision = allowlist_mod.check_host_access(
        url,
        paths=paths,
        user_pasted=True,
        turn_user_text=f"please fetch {url} for me",
    )
    assert decision.get("ok") is True
    assert decision.get("reason") == "pasted_this_turn"
    assert decision.get("pasted") is True


def test_allowlisted_host_ok_without_paste(data_root: Path) -> None:
    paths = get_paths()
    ensure_prefs(paths)
    allowlist_mod.add_host("example.com", paths=paths)
    decision = allowlist_mod.check_host_access(
        "https://example.com/x",
        paths=paths,
        user_pasted=False,
        turn_user_text="no urls here",
    )
    assert decision.get("ok") is True
    assert decision.get("reason") == "allowlisted"
    assert decision.get("pasted") is False


def test_model_pasted_text_spoof_stripped_by_gateway(data_root: Path) -> None:
    """Gateway ignores model pasted_text; only harness turn_user_text counts."""
    gw = Gateway(mode="observe", turn_user_text="compare phone vs Pi with vitals")
    r = gw.execute(
        "web_fetch",
        {
            "url": "https://qualcomm.example/chip",
            "user_pasted": True,
            "pasted_text": "https://qualcomm.example/chip",
        },
    )
    assert r.outcome == "needs_confirm"
    assert r.needs_confirm is True
    assert (r.data or {}).get("host") == "qualcomm.example"


def test_gateway_real_paste_in_turn_text(data_root: Path, monkeypatch) -> None:
    turn = "read https://example.com/spec please"
    gw = Gateway(mode="observe", turn_user_text=turn)

    def _http_get(url, **kwargs):  # noqa: ANN001
        resp = httpx.Response(
            200,
            text="<html><body><p>hello paste</p></body></html>",
            headers={"content-type": "text/html"},
            request=httpx.Request("GET", url),
        )
        return resp, url, [url]

    def run(args):  # noqa: ANN001
        return web_fetch(
            str(args["url"]),
            user_pasted=bool(args.get("user_pasted", False)),
            turn_user_text=args.get("turn_user_text"),
            receipt_id=args.get("receipt_id"),
            http_get=_http_get,
        )

    monkeypatch.setitem(web_tools.DISPATCH, "web_fetch", run)
    r = gw.execute(
        "web_fetch",
        {"url": "https://example.com/spec", "user_pasted": True},
    )
    assert r.ok is True, (r.outcome, r.error, r.data)
    assert r.data.get("cite_id")
    # sanity: default handler still importable
    assert run_web_fetch is not None
