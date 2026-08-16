"""ntfy push actuator — budgeted, quiet/mute aware (M16 Phase 1).

Secrets live under ada-data/secrets/ntfy.env (never git). First enable of
prefs.notify_enabled requires Confirm via memory_facts_append.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text
from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data
from ada.memory.facts import DEFAULT_PREFS, ensure_prefs, load_prefs, save_prefs
from ada.memory.open_loops import notify_due_todos, upsert_loop
from ada.memory.proactivity import proactivity_suppressed
from ada.runs.append import new_receipt_id
from ada.secrets.load import _parse_dotenv, secrets_dir

ENV_NTFY_URL = "NTFY_URL"
ENV_NTFY_TOPIC = "NTFY_TOPIC"
ENV_NTFY_TOKEN = "NTFY_TOKEN"
NTFY_ENV_FILENAME = "ntfy.env"

# Injectable for tests — (url, headers, body_bytes) -> (status, response_text)
HttpPoster = Callable[[str, dict[str, str], bytes], tuple[int, str]]


def _require(paths: DataPaths | None) -> DataPaths:
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault(
            f"ada-data not mounted or missing at {p.root}; refusing notify"
        )
    return p


def load_ntfy_config() -> dict[str, Any]:
    """Load ntfy URL/topic/token from env or secrets/ntfy.env. Never log secrets."""
    url = os.environ.get(ENV_NTFY_URL, "").strip()
    topic = os.environ.get(ENV_NTFY_TOPIC, "").strip()
    token = os.environ.get(ENV_NTFY_TOKEN, "").strip()
    path = secrets_dir() / NTFY_ENV_FILENAME
    if path.is_file():
        try:
            parsed = _parse_dotenv(path.read_text(encoding="utf-8"))
        except OSError:
            parsed = {}
        url = url or (parsed.get(ENV_NTFY_URL) or "").strip()
        topic = topic or (parsed.get(ENV_NTFY_TOPIC) or "").strip()
        token = token or (parsed.get(ENV_NTFY_TOKEN) or "").strip()
    # Allow NTFY_URL to be a full topic URL (https://ntfy.sh/mytopic).
    if url and not topic and "/" in url.rstrip("/").split("://", 1)[-1]:
        return {
            "ok": bool(url),
            "url": url.rstrip("/"),
            "topic": None,
            "token": token or None,
            "configured": bool(url),
        }
    if url and topic:
        base = url.rstrip("/")
        full = f"{base}/{topic.lstrip('/')}"
        return {
            "ok": True,
            "url": full,
            "topic": topic,
            "token": token or None,
            "configured": True,
        }
    return {
        "ok": False,
        "url": None,
        "topic": topic or None,
        "token": None,
        "configured": False,
        "error": f"set {ENV_NTFY_URL}+{ENV_NTFY_TOPIC} or secrets/{NTFY_ENV_FILENAME}",
    }


def _default_http_post(url: str, headers: dict[str, str], body: bytes) -> tuple[int, str]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return int(resp.status), resp.read().decode("utf-8", errors="replace")[:500]
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")[:500] if exc.fp else ""
        return int(exc.code), text
    except urllib.error.URLError as exc:
        return 0, str(exc.reason if hasattr(exc, "reason") else exc)


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    text = ts.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _notify_budget_state(prefs: dict[str, Any], now: datetime) -> dict[str, Any]:
    budget = int(prefs.get("notify_budget_per_day") or DEFAULT_PREFS["notify_budget_per_day"])
    cooldown_m = int(
        prefs.get("notify_cooldown_minutes") or DEFAULT_PREFS["notify_cooldown_minutes"]
    )
    day = now.astimezone(timezone.utc).strftime("%Y-%m-%d")
    meta = prefs.get("_notify_meta") if isinstance(prefs.get("_notify_meta"), dict) else {}
    count = int(meta.get("count") or 0) if meta.get("day") == day else 0
    last = _parse_iso(meta.get("last_at") if isinstance(meta.get("last_at"), str) else None)
    return {
        "budget": budget,
        "cooldown_minutes": cooldown_m,
        "day": day,
        "count": count,
        "last_at": last,
        "meta": dict(meta) if meta.get("day") == day else {"day": day, "count": 0},
    }


def _write_notify_receipt(
    paths: DataPaths,
    *,
    receipt_id: str,
    payload: dict[str, Any],
) -> str | None:
    try:
        day_dir = paths.runs / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        crumb = day_dir / f"notify_{receipt_id[:12]}.json"
        atomic_write_text(
            crumb,
            json.dumps({"receipt_id": receipt_id, **payload}, indent=2, ensure_ascii=False)
            + "\n",
        )
        return str(crumb)
    except OSError:
        return None


def notify_send(
    *,
    title: str | None = None,
    message: str,
    todo_id: str | None = None,
    force: bool = False,
    paths: DataPaths | None = None,
    now: datetime | None = None,
    http_post: HttpPoster | None = None,
) -> dict[str, Any]:
    """Send one ntfy push if policy allows. Always returns a receipt-shaped dict."""
    p = _require(paths)
    ensure_prefs(p)
    prefs = load_prefs(p)
    now = now or datetime.now(timezone.utc)
    receipt_id = new_receipt_id()
    msg = str(message or "").strip()
    if not msg:
        return {
            "ok": False,
            "outcome": "error",
            "error": "message required",
            "receipt_id": receipt_id,
        }

    base_payload = {
        "ts": utc_now_iso(),
        "tool": "notify_send",
        "title": title,
        "message": msg[:500],
        "todo_id": todo_id,
    }

    if not bool(prefs.get("notify_enabled", False)) and not force:
        out = {
            "ok": True,
            "outcome": "skipped",
            "skipped": True,
            "reason": "notify_disabled",
            "receipt_id": receipt_id,
            **base_payload,
        }
        out["receipt_crumb"] = _write_notify_receipt(p, receipt_id=receipt_id, payload=out)
        return out

    suppress = proactivity_suppressed(paths=p, now=now)
    if suppress.get("suppressed") and not force:
        out = {
            "ok": True,
            "outcome": "skipped",
            "skipped": True,
            "reason": "proactivity_suppressed",
            "suppress_reasons": suppress.get("reasons"),
            "receipt_id": receipt_id,
            **base_payload,
        }
        out["receipt_crumb"] = _write_notify_receipt(p, receipt_id=receipt_id, payload=out)
        return out

    budget = _notify_budget_state(prefs, now)
    if budget["count"] >= budget["budget"] and not force:
        out = {
            "ok": True,
            "outcome": "skipped",
            "skipped": True,
            "reason": "budget_exhausted",
            "budget": budget["budget"],
            "count": budget["count"],
            "receipt_id": receipt_id,
            **base_payload,
        }
        out["receipt_crumb"] = _write_notify_receipt(p, receipt_id=receipt_id, payload=out)
        return out

    last = budget["last_at"]
    if last is not None and not force:
        delta = now - last
        if delta < timedelta(minutes=budget["cooldown_minutes"]):
            out = {
                "ok": True,
                "outcome": "skipped",
                "skipped": True,
                "reason": "cooldown",
                "cooldown_minutes": budget["cooldown_minutes"],
                "receipt_id": receipt_id,
                **base_payload,
            }
            out["receipt_crumb"] = _write_notify_receipt(
                p, receipt_id=receipt_id, payload=out
            )
            return out

    channel = str(prefs.get("notify_channel") or "ntfy").strip().lower()
    if channel != "ntfy":
        out = {
            "ok": False,
            "outcome": "error",
            "error": f"unsupported notify_channel={channel!r} (Phase 1: ntfy only)",
            "receipt_id": receipt_id,
            **base_payload,
        }
        out["receipt_crumb"] = _write_notify_receipt(p, receipt_id=receipt_id, payload=out)
        return out

    cfg = load_ntfy_config()
    if not cfg.get("configured"):
        out = {
            "ok": False,
            "outcome": "error",
            "error": cfg.get("error") or "ntfy not configured",
            "receipt_id": receipt_id,
            **base_payload,
        }
        out["receipt_crumb"] = _write_notify_receipt(p, receipt_id=receipt_id, payload=out)
        return out

    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Title": (title or "ADA").strip()[:120],
    }
    if cfg.get("token"):
        headers["Authorization"] = f"Bearer {cfg['token']}"

    poster = http_post or _default_http_post
    status, resp_text = poster(str(cfg["url"]), headers, msg.encode("utf-8"))
    if status < 200 or status >= 300:
        out = {
            "ok": False,
            "outcome": "error",
            "error": f"ntfy HTTP {status}",
            "response": resp_text[:200],
            "receipt_id": receipt_id,
            **base_payload,
        }
        out["receipt_crumb"] = _write_notify_receipt(p, receipt_id=receipt_id, payload=out)
        return out

    # Update budget meta (no secrets).
    meta = budget["meta"]
    meta["day"] = budget["day"]
    meta["count"] = int(meta.get("count") or 0) + 1
    meta["last_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    prefs["_notify_meta"] = meta
    save_prefs(prefs, p)

    if todo_id:
        try:
            upsert_loop(
                loop_id=str(todo_id),
                last_notified_at=meta["last_at"],
                paths=p,
            )
        except Exception:  # noqa: BLE001
            pass

    out = {
        "ok": True,
        "outcome": "ok",
        "skipped": False,
        "channel": "ntfy",
        "http_status": status,
        "receipt_id": receipt_id,
        "budget_count": meta["count"],
        **base_payload,
    }
    out["receipt_crumb"] = _write_notify_receipt(p, receipt_id=receipt_id, payload=out)
    return out


def notify_check_and_send(
    *,
    paths: DataPaths | None = None,
    now: datetime | None = None,
    http_post: HttpPoster | None = None,
    limit: int = 1,
) -> dict[str, Any]:
    """Brief/timer helper: send at most *limit* due/remind pings."""
    p = _require(paths)
    now = now or datetime.now(timezone.utc)
    ready = notify_due_todos(paths=p, now=now, limit=limit)
    results: list[dict[str, Any]] = []
    for item in ready:
        # Per-item cooldown via last_notified_at (in addition to global).
        last = item.get("last_notified_at")
        last_dt = _parse_iso(last if isinstance(last, str) else None)
        prefs = load_prefs(p)
        cooldown_m = int(
            prefs.get("notify_cooldown_minutes")
            or DEFAULT_PREFS["notify_cooldown_minutes"]
        )
        if last_dt is not None and (now - last_dt) < timedelta(minutes=cooldown_m):
            results.append(
                {
                    "ok": True,
                    "skipped": True,
                    "reason": "item_cooldown",
                    "todo_id": item.get("id"),
                }
            )
            continue
        text = str(item.get("title") or item.get("text") or "due").strip()
        results.append(
            notify_send(
                title="ADA due",
                message=text[:400],
                todo_id=str(item.get("id") or "") or None,
                paths=p,
                now=now,
                http_post=http_post,
            )
        )
    return {
        "ok": True,
        "outcome": "ok",
        "checked": len(ready),
        "results": results,
    }
