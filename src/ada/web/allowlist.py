"""Web host allowlist — FACTS prefs.web_allowlist + pasted-this-turn (M07)."""

from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

from ada.io.paths import DataPaths, require_ada_data
from ada.memory import facts as facts_mod
from ada.web.ssrf import is_blocked_ip, parse_url_strict

DEFAULT_TTL_SECONDS = 900  # 15 minutes interactive

# Layer 0 named-host complement (M08). SSRF IP denylist stays the runtime backstop.
_WONT_ALLOW_EXACT = frozenset(
    {
        "localhost",
        "ada-pi5",
        "metadata.google.internal",
    }
)
_SHORTENER_HOSTS = frozenset(
    {
        "bit.ly",
        "t.co",
        "tinyurl.com",
        "lnkd.in",
    }
)
_DNS_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def normalize_host(host: str) -> str:
    return host.lower().strip().rstrip(".")


def _normalize_host(host: str) -> str:
    return normalize_host(host)


def _literal_ip(host: str) -> str | None:
    raw = host.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    try:
        ipaddress.ip_address(raw)
        return raw
    except ValueError:
        return None


def wont_allow_reason(host: str) -> str | None:
    """Return a Layer 0 refusal reason, or None if the name may be stored.

    Exact hostname only. Runtime SSRF still denies private IPs even if FACTS
    is later poisoned (F2).
    """
    raw = (host or "").strip()
    if not raw:
        return "won't-allow: empty host"
    if any(sep in raw for sep in ("://", "/", "?", "#", "@", " ")):
        return "won't-allow: host only (no URL, path, or credentials)"
    if "*" in raw:
        return "won't-allow: wildcards are not a pack"
    ip = _literal_ip(raw)
    if ip is not None:
        if is_blocked_ip(ip):
            return f"won't-allow: blocked address {ip}"
        return f"won't-allow: IP literal {ip} (use a hostname)"
    h = _normalize_host(raw)
    if not h:
        return "won't-allow: empty host"
    try:
        h.encode("ascii")
    except UnicodeEncodeError:
        return "won't-allow: ASCII hosts only"
    if h in _WONT_ALLOW_EXACT or h.startswith("localhost.") or h.endswith(".local"):
        return f"won't-allow: loopback/HUD/metadata host {h}"
    for short in _SHORTENER_HOSTS:
        if h == short or h.endswith("." + short):
            return f"won't-allow: shortener {h}"
    if "." not in h:
        return f"won't-allow: single-label hostname {h} (localhost/LAN)"
    labels = h.split(".")
    if any(not lab or not _DNS_LABEL_RE.match(lab) for lab in labels):
        return f"won't-allow: invalid hostname {h}"
    return None


def host_from_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    return _normalize_host(parsed.hostname or "")


def load_allowlist(paths: DataPaths | None = None) -> list[dict[str, Any]]:
    """Return list of {host, ttl_seconds?, note?} from prefs."""
    p = paths or require_ada_data()
    prefs = facts_mod.load_prefs(p) if p.prefs_yaml.is_file() else dict(facts_mod.DEFAULT_PREFS)
    raw = prefs.get("web_allowlist") or []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            h = _normalize_host(item)
            if h:
                out.append({"host": h, "ttl_seconds": DEFAULT_TTL_SECONDS})
        elif isinstance(item, dict) and item.get("host"):
            entry = {
                "host": _normalize_host(str(item["host"])),
                "ttl_seconds": int(item.get("ttl_seconds") or DEFAULT_TTL_SECONDS),
            }
            if item.get("note"):
                entry["note"] = str(item["note"])
            out.append(entry)
    return out


def allowlist_hosts(paths: DataPaths | None = None) -> set[str]:
    return {e["host"] for e in load_allowlist(paths)}


def ttl_for_host(host: str, paths: DataPaths | None = None) -> int:
    h = _normalize_host(host)
    for e in load_allowlist(paths):
        if e["host"] == h:
            return int(e.get("ttl_seconds") or DEFAULT_TTL_SECONDS)
    return DEFAULT_TTL_SECONDS


def is_allowlisted(host: str, paths: DataPaths | None = None) -> bool:
    return _normalize_host(host) in allowlist_hosts(paths)


def add_host(
    host: str,
    *,
    paths: DataPaths | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    note: str | None = None,
    update_existing: bool = False,
) -> dict[str, Any]:
    """Append host to prefs.web_allowlist (idempotent). Layer 0 won't-allow applies."""
    refused = wont_allow_reason(host)
    if refused:
        return {"ok": False, "outcome": "error", "error": refused, "denied_reason": refused}
    p = paths or require_ada_data()
    facts_mod.ensure_prefs(p)
    prefs = facts_mod.load_prefs(p)
    h = _normalize_host(host)
    entries = load_allowlist(p)
    for e in entries:
        if e["host"] == h:
            if not update_existing:
                return {
                    "ok": True,
                    "outcome": "ok",
                    "host": h,
                    "already": True,
                    "updated": False,
                    "allowlist": entries,
                }
            new_ttl = int(ttl_seconds)
            changed = int(e.get("ttl_seconds") or DEFAULT_TTL_SECONDS) != new_ttl
            if note and e.get("note") != note:
                changed = True
            if changed:
                e["ttl_seconds"] = new_ttl
                if note:
                    e["note"] = note
                prefs["web_allowlist"] = entries
                facts_mod.save_prefs(prefs, p)
            return {
                "ok": True,
                "outcome": "ok",
                "host": h,
                "already": True,
                "updated": changed,
                "allowlist": entries,
            }
    entry: dict[str, Any] = {"host": h, "ttl_seconds": int(ttl_seconds)}
    if note:
        entry["note"] = note
    entries.append(entry)
    prefs["web_allowlist"] = entries
    facts_mod.save_prefs(prefs, p)
    return {
        "ok": True,
        "outcome": "ok",
        "host": h,
        "already": False,
        "updated": False,
        "allowlist": entries,
    }


def pasted_hosts_from_text(text: str | None) -> set[str]:
    """Extract http(s) hosts mentioned in operator text (pasted-this-turn)."""
    if not text:
        return set()
    hosts: set[str] = set()
    for token in text.replace("\n", " ").split():
        t = token.strip(".,;:)'\"<>[]()")
        if "://" not in t and not t.startswith("www."):
            continue
        candidate = t if "://" in t else f"https://{t}"
        try:
            _scheme, host, _port, _path = parse_url_strict(
                candidate if "://" in candidate else f"https://{candidate}",
                allow_http=True,
            )
            # parse_url_strict may reject http without allow — already allow_http
            hosts.add(host)
        except Exception:
            parsed = urlparse(candidate)
            if parsed.hostname:
                hosts.add(_normalize_host(parsed.hostname))
    return hosts


def check_host_access(
    url: str,
    *,
    paths: DataPaths | None = None,
    user_pasted: bool = False,
    pasted_text: str | None = None,
    confirm_host: bool = False,
) -> dict[str, Any]:
    """Return policy decision for a URL host.

    Outcomes:
      ok — host allowlisted or pasted-this-turn
      needs_confirm — new host (Consent Integrity)
      error — unparseable
    """
    try:
        # Peek host with lenient http for policy (scheme enforced later in fetch)
        parsed = urlparse(url.strip())
        host = _normalize_host(parsed.hostname or "")
        if not host:
            return {
                "ok": False,
                "outcome": "error",
                "error": "missing host",
                "denied_reason": "missing host",
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "outcome": "error",
            "error": str(exc),
            "denied_reason": str(exc),
        }

    if is_allowlisted(host, paths):
        return {
            "ok": True,
            "outcome": "ok",
            "host": host,
            "reason": "allowlisted",
            "pasted": False,
        }

    pasted = set()
    if user_pasted:
        pasted.add(host)
    pasted |= pasted_hosts_from_text(pasted_text)
    if host in pasted:
        return {
            "ok": True,
            "outcome": "ok",
            "host": host,
            "reason": "pasted_this_turn",
            "pasted": True,
        }

    if confirm_host:
        added = add_host(host, paths=paths, note="confirmed via web_fetch")
        if not added.get("ok"):
            return {
                "ok": False,
                "outcome": "error",
                "error": added.get("error"),
                "denied_reason": added.get("denied_reason") or added.get("error"),
                "host": host,
            }
        return {
            "ok": True,
            "outcome": "ok",
            "host": host,
            "reason": "confirmed_and_allowlisted",
            "pasted": False,
        }

    return {
        "ok": False,
        "needs_confirm": True,
        "outcome": "needs_confirm",
        "host": host,
        "reason": (
            f"host '{host}' not on prefs.web_allowlist; "
            "confirm_host=true to allowlist, or set user_pasted=true"
        ),
        "denied_reason": f"new host requires confirm: {host}",
    }
