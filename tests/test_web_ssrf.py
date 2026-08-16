"""M07 SSRF denylist falsifiers (F2, F11 helpers)."""

from __future__ import annotations

import pytest

from ada.web.ssrf import SsrfError, check_url, is_blocked_ip, parse_url_strict

pytestmark = pytest.mark.tier_a


def test_web_ssrf_denies_loopback() -> None:
    assert is_blocked_ip("127.0.0.1")
    assert is_blocked_ip("::1")
    with pytest.raises(SsrfError, match="blocked|SSRF"):
        check_url("http://127.0.0.1/", allow_http=True, resolve=True)


def test_web_ssrf_denies_linklocal_metadata() -> None:
    assert is_blocked_ip("169.254.169.254")
    assert is_blocked_ip("169.254.1.1")


def test_web_ssrf_denies_rfc1918() -> None:
    assert is_blocked_ip("192.168.0.1")
    assert is_blocked_ip("10.0.0.1")
    assert is_blocked_ip("172.16.5.5")


def test_web_ssrf_denies_cgnat() -> None:
    assert is_blocked_ip("100.64.0.1")
    assert is_blocked_ip("100.127.255.255")


def test_web_ssrf_rejects_bad_schemes() -> None:
    with pytest.raises(SsrfError, match="scheme"):
        parse_url_strict("file:///etc/passwd")
    with pytest.raises(SsrfError, match="scheme"):
        parse_url_strict("ftp://example.com/")
    with pytest.raises(SsrfError, match="credentials"):
        parse_url_strict("https://user:pass@example.com/")


def test_web_ssrf_rejects_bad_ports() -> None:
    with pytest.raises(SsrfError, match="port"):
        parse_url_strict("https://example.com:22/")
