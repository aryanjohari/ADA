"""FACTS organ — strict standing prefs / YAML docs (M04).

Append free; overwrite/delete → needs_confirm. Crash-safe via ada.io.atomic.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text, cleanup_orphan_tmps
from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data

# Body §5.3 / constitution — Dream auto-merge whitelist only.
WHITELIST_KEYS: frozenset[str] = frozenset(
    {
        "brief_time",
        "quiet_hours_start",
        "quiet_hours_end",
        "mute_proactivity",
        "tease_ok",
        "preferred_tz",
        "brief_enabled",
        "roast_energy",
        "humor_density",
        "chill_immediate",
        "humor_banned_topics",
    }
)

# Identity fields Dream must never touch.
SACRED_IDENTITY_KEYS: frozenset[str] = frozenset(
    {
        "born_at",
        "operator",
        "pronouns",
        "name",
        "body_hostname",
        "board_model",
        "board_revision",
    }
)

DEFAULT_PREFS: dict[str, Any] = {
    "schema_version": 1,
    "brief_time": "05:30",
    "quiet_hours_start": "23:00",
    "quiet_hours_end": "05:30",
    "mute_proactivity": False,
    "tease_ok": True,
    "preferred_tz": "Pacific/Auckland",
    "brief_enabled": True,
    # M05 voice register dials (standing overrides; contract has same defaults).
    "roast_energy": 0.65,
    "humor_density": 0.15,
    "chill_immediate": True,
    "humor_banned_topics": [],
    # M07 web egress — list of {host, ttl_seconds?, note?} or bare host strings.
    "web_allowlist": [],
    # M16 Phase 1 notify (ntfy). First enable → Confirm.
    "notify_enabled": False,
    "notify_channel": "ntfy",
    "notify_budget_per_day": 5,
    "notify_cooldown_minutes": 60,
}

_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _require_mounted(paths: DataPaths) -> DataPaths:
    if not ada_data_mounted(paths.root):
        raise BodyFault(
            f"ada-data not mounted or missing at {paths.root}; refusing durable writes"
        )
    return paths


def _dump_yaml(obj: dict[str, Any]) -> str:
    return yaml.safe_dump(
        obj,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise BodyFault(f"{path.name} is not a YAML mapping", code=2)
    return raw


def ensure_prefs(paths: DataPaths | None = None) -> dict[str, Any]:
    """Create prefs.yaml with lab defaults if missing; return current prefs."""
    p = _require_mounted(paths or require_ada_data())
    p.ensure_memory_dirs()
    cleanup_orphan_tmps(p.facts, "prefs.yaml")
    if not p.prefs_yaml.is_file():
        atomic_write_text(p.prefs_yaml, _dump_yaml(dict(DEFAULT_PREFS)))
    # Thin people stub (optional; never auto-merged by Dream).
    if not p.aryan_yaml.is_file():
        stub = {
            "schema_version": 1,
            "name": "Aryan",
            "role": "operator",
            "notes": "sovereign; prefs live in facts/prefs.yaml",
        }
        atomic_write_text(p.aryan_yaml, _dump_yaml(stub))
    return load_prefs(p)


def load_prefs(paths: DataPaths | None = None) -> dict[str, Any]:
    p = paths or require_ada_data()
    cleanup_orphan_tmps(p.facts, "prefs.yaml")
    if not p.prefs_yaml.is_file():
        return dict(DEFAULT_PREFS)
    data = _load_yaml(p.prefs_yaml)
    merged = dict(DEFAULT_PREFS)
    merged.update(data)
    return merged


def save_prefs(prefs: dict[str, Any], paths: DataPaths | None = None) -> dict[str, Any]:
    p = _require_mounted(paths or require_ada_data())
    p.ensure_memory_dirs()
    cleanup_orphan_tmps(p.facts, "prefs.yaml")
    out = dict(prefs)
    out.setdefault("schema_version", 1)
    atomic_write_text(p.prefs_yaml, _dump_yaml(out))
    return out


def _parse_key(key: str) -> tuple[str, str | None]:
    """Return (doc, field). 'prefs.brief_time' → ('prefs', 'brief_time')."""
    key = key.strip().lstrip("/")
    if not key:
        raise ValueError("empty fact key")
    if "." in key:
        doc, field = key.split(".", 1)
        return doc, field
    if key.endswith(".yaml"):
        return key[: -len(".yaml")], None
    return key, None


def _doc_path(paths: DataPaths, doc: str) -> Path:
    doc = doc.strip().removesuffix(".yaml")
    if doc == "identity":
        return paths.identity_yaml
    if doc == "prefs":
        return paths.prefs_yaml
    if doc == "open_loops":
        return paths.open_loops_yaml
    if doc.startswith("people/"):
        return paths.facts / f"{doc}.yaml"
    if doc in {"aryan"} or doc.startswith("people"):
        name = doc.removeprefix("people/")
        return paths.people / f"{name}.yaml"
    return paths.facts / f"{doc}.yaml"


def get_fact(key: str, *, paths: DataPaths | None = None) -> dict[str, Any]:
    """Lookup by key (`prefs.brief_time`) or doc name (`prefs`)."""
    p = paths or require_ada_data()
    doc, field = _parse_key(key)
    if doc == "prefs" and not p.prefs_yaml.is_file():
        ensure_prefs(p)
    path = _doc_path(p, doc)
    if not path.is_file():
        return {"found": False, "key": key, "doc": doc, "value": None}
    data = _load_yaml(path)
    if field is None:
        return {"found": True, "key": key, "doc": doc, "path": str(path), "value": data}
    if field not in data:
        return {"found": False, "key": key, "doc": doc, "field": field, "value": None}
    return {
        "found": True,
        "key": key,
        "doc": doc,
        "field": field,
        "path": str(path),
        "value": data[field],
    }


def _coerce_pref_value(field: str, value: Any) -> Any:
    if field in {
        "mute_proactivity",
        "tease_ok",
        "brief_enabled",
        "chill_immediate",
        "notify_enabled",
    }:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            low = value.strip().lower()
            if low in {"true", "1", "yes", "on"}:
                return True
            if low in {"false", "0", "no", "off"}:
                return False
        raise ValueError(f"{field} must be bool, got {value!r}")
    if field in {"roast_energy", "humor_density"}:
        try:
            f = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be float 0..1, got {value!r}") from exc
        if not 0.0 <= f <= 1.0:
            raise ValueError(f"{field} must be in [0, 1], got {f}")
        return f
    if field == "humor_banned_topics":
        if value is None:
            return []
        if isinstance(value, str):
            parts = [p.strip() for p in value.split(",") if p.strip()]
            return parts
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        raise ValueError(f"{field} must be list or comma-string, got {value!r}")
    if field in {"brief_time", "quiet_hours_start", "quiet_hours_end"}:
        s = str(value).strip()
        if not _HHMM_RE.match(s):
            raise ValueError(f"{field} must be HH:MM, got {value!r}")
        return s
    if field == "preferred_tz":
        return str(value).strip()
    if field == "web_allowlist":
        if value is None:
            return []
        if isinstance(value, list):
            return value
        raise ValueError(f"{field} must be a list, got {value!r}")
    if field == "notify_channel":
        ch = str(value).strip().lower()
        if ch != "ntfy":
            raise ValueError("notify_channel Phase 1 supports only 'ntfy'")
        return ch
    if field in {"notify_budget_per_day", "notify_cooldown_minutes"}:
        try:
            n = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be int, got {value!r}") from exc
        if n < 0:
            raise ValueError(f"{field} must be >= 0")
        return n
    return value


def append_fact(
    key: str,
    value: Any,
    *,
    paths: DataPaths | None = None,
    note: str | None = None,
    allow_prefs_update: bool = True,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Append/set a FACT field.

    Whitelist prefs may be updated freely when *allow_prefs_update* (operator
    ``remember`` / Agent tool). Pass allow_prefs_update=False for Dream merge
    so conflicting values surface as needs_confirm → stage.
    Non-prefs fields: overwrite of a different existing value → needs_confirm.
    Enabling ``prefs.notify_enabled`` always needs Confirm on first enable.
    """
    p = _require_mounted(paths or require_ada_data())
    p.ensure_memory_dirs()
    doc, field = _parse_key(key)
    if field is None:
        raise ValueError("append requires dotted key like prefs.brief_time")

    if doc == "identity" or field in SACRED_IDENTITY_KEYS:
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": f"identity/sacred field '{field}' cannot be appended this way",
            "key": key,
        }

    if doc == "prefs":
        ensure_prefs(p)
        prefs = load_prefs(p)
        coerced = _coerce_pref_value(field, value)
        existing = prefs.get(field)
        # M16: first enable of push notify requires Confirm.
        if (
            field == "notify_enabled"
            and coerced is True
            and not bool(existing)
            and not confirmed
        ):
            return {
                "ok": False,
                "needs_confirm": True,
                "outcome": "needs_confirm",
                "reason": (
                    "enabling prefs.notify_enabled requires Confirm "
                    "(ntfy secrets under secrets/ntfy.env; budget/quiet/mute apply)"
                ),
                "key": key,
                "existing": existing,
                "proposed": coerced,
            }
        if (
            not allow_prefs_update
            and field in prefs
            and existing is not None
            and existing != coerced
        ):
            return {
                "ok": False,
                "needs_confirm": True,
                "outcome": "needs_confirm",
                "reason": f"prefs.{field} already set to {existing!r}; confirm overwrite",
                "key": key,
                "existing": existing,
                "proposed": coerced,
            }
        prefs[field] = coerced
        if note:
            prefs.setdefault("_notes", [])
            if isinstance(prefs["_notes"], list):
                prefs["_notes"].append({"ts": utc_now_iso(), "note": note, "field": field})
        save_prefs(prefs, p)
        return {
            "ok": True,
            "outcome": "ok",
            "key": key,
            "value": coerced,
            "path": str(p.prefs_yaml),
            "ts": utc_now_iso(),
            "updated": existing != coerced if existing is not None else False,
        }

    # Generic FACT doc field append (create file if needed).
    path = _doc_path(p, doc)
    cleanup_orphan_tmps(path.parent, path.name)
    data = _load_yaml(path) if path.is_file() else {"schema_version": 1}
    if field in data and data[field] != value and not confirmed:
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": f"{doc}.{field} already set; confirm overwrite",
            "key": key,
            "existing": data[field],
            "proposed": value,
        }
    data[field] = value
    if note:
        data.setdefault("_notes", [])
        if isinstance(data["_notes"], list):
            data["_notes"].append({"ts": utc_now_iso(), "note": note, "field": field})
    atomic_write_text(path, _dump_yaml(data))
    return {
        "ok": True,
        "outcome": "ok",
        "key": key,
        "value": value,
        "path": str(path),
        "ts": utc_now_iso(),
    }


def propose_edit(
    key: str,
    value: Any,
    *,
    paths: DataPaths | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Overwrite FACT field — requires confirmed=True unless value is new."""
    p = _require_mounted(paths or require_ada_data())
    doc, field = _parse_key(key)
    if field is None:
        raise ValueError("propose_edit requires dotted key")

    if doc == "identity" or field == "born_at":
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": "born_at / identity sacred — refuse Dream and casual overwrite",
            "key": key,
        }

    if not confirmed:
        hit = get_fact(key, paths=p)
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": "overwrite requires confirmation",
            "key": key,
            "existing": hit.get("value") if hit.get("found") else None,
            "proposed": value,
        }

    if doc == "prefs":
        ensure_prefs(p)
        prefs = load_prefs(p)
        prefs[field] = _coerce_pref_value(field, value)
        save_prefs(prefs, p)
        return {
            "ok": True,
            "outcome": "ok",
            "key": key,
            "value": prefs[field],
            "path": str(p.prefs_yaml),
            "confirmed": True,
        }

    path = _doc_path(p, doc)
    data = _load_yaml(path) if path.is_file() else {"schema_version": 1}
    data[field] = value
    atomic_write_text(path, _dump_yaml(data))
    return {
        "ok": True,
        "outcome": "ok",
        "key": key,
        "value": value,
        "path": str(path),
        "confirmed": True,
    }


def search_facts(
    query: str,
    *,
    paths: DataPaths | None = None,
    max_hits: int = 20,
) -> dict[str, Any]:
    """Key lookup + content grep across facts/*.yaml (Tier A — no embeddings)."""
    p = paths or require_ada_data()
    q = (query or "").strip()
    hits: list[dict[str, Any]] = []
    if not q:
        return {"query": q, "hits": hits, "count": 0}

    # Exact / dotted key first.
    try:
        keyed = get_fact(q, paths=p)
        if keyed.get("found"):
            hits.append(
                {
                    "kind": "key",
                    "key": q,
                    "path": keyed.get("path"),
                    "value": keyed.get("value"),
                }
            )
    except ValueError:
        pass

    # Also try prefs.<query> for bare whitelist key names.
    if q in WHITELIST_KEYS:
        keyed = get_fact(f"prefs.{q}", paths=p)
        if keyed.get("found") and not any(h.get("key") == f"prefs.{q}" for h in hits):
            hits.append(
                {
                    "kind": "key",
                    "key": f"prefs.{q}",
                    "path": keyed.get("path"),
                    "value": keyed.get("value"),
                }
            )

    q_low = q.lower()
    if p.facts.is_dir():
        for path in sorted(p.facts.rglob("*.yaml")):
            if len(hits) >= max_hits:
                break
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if q_low not in text.lower():
                continue
            rel = str(path.relative_to(p.facts))
            # Avoid duplicate if already key-hit on same file with exact key.
            if any(h.get("path") == str(path) and h.get("kind") == "key" for h in hits):
                # Still add a grep snippet context if query isn't the key itself.
                if q.startswith("prefs.") or q in WHITELIST_KEYS:
                    continue
            snippet_lines = [
                ln.strip() for ln in text.splitlines() if q_low in ln.lower()
            ][:3]
            hits.append(
                {
                    "kind": "grep",
                    "path": str(path),
                    "rel": rel,
                    "snippets": snippet_lines,
                }
            )
            if len(hits) >= max_hits:
                break

    return {"query": q, "hits": hits[:max_hits], "count": len(hits[:max_hits])}


def boot_fact_slice(*, paths: DataPaths | None = None, max_chars: int = 3200) -> str:
    """Budgeted dry FACT block for the system charter."""
    p = paths or get_paths_soft()
    if p is None:
        return "FACTS (dry, standing): unavailable (no data root)."

    lines = ["FACTS (dry, standing):"]
    try:
        mounted = ada_data_mounted(p.root)
        if mounted and not p.prefs_yaml.is_file():
            ensure_prefs(p)
        if p.prefs_yaml.is_file():
            prefs = load_prefs(p)
        elif mounted:
            prefs = dict(DEFAULT_PREFS)
        else:
            prefs = dict(DEFAULT_PREFS)
        for k in sorted(WHITELIST_KEYS):
            if k in prefs:
                lines.append(f"- {k}: {prefs[k]!r}")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"- (prefs unavailable: {exc})")

    try:
        from ada.memory.open_loops import (
            K_CAMPAIGN_HEADS,
            K_DUE_PER_WAKE,
            K_TODO_HEADS,
            campaign_heads,
            due_todos,
            format_campaign_head,
            format_todo_head,
            list_loops,
        )

        heads = campaign_heads(paths=p, limit=K_CAMPAIGN_HEADS)
        if heads:
            lines.append("- campaigns:")
            for camp in heads:
                lines.append(f"  - {format_campaign_head(camp)}")
        else:
            lines.append("- campaigns: (none)")

        dues = due_todos(paths=p, limit=K_DUE_PER_WAKE)
        if dues:
            lines.append("- due_todos:")
            for todo in dues:
                lines.append(f"  - {format_todo_head(todo)}")
        else:
            lines.append("- due_todos: (none)")

        todos = list_loops(paths=p, status="open", kind="todo", limit=K_TODO_HEADS)
        if todos:
            lines.append("- open_loops:")
            for loop in todos:
                lines.append(f"  - [{loop.get('id', '?')}] {loop.get('text', '')[:120]}")
        else:
            lines.append("- open_loops: (none)")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"- campaigns/open_loops: unavailable ({exc})")

    text = "\n".join(lines)
    if len(text) > max_chars:
        return text[: max_chars - 20] + "\n…(truncated)"
    return text


def get_paths_soft() -> DataPaths | None:
    """Return paths without raising when substrate missing."""
    from ada.io.paths import get_paths

    try:
        return get_paths()
    except Exception:
        return None
