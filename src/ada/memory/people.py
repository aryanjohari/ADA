"""People cards — schema v2 YAML load/write/resolve (M19a P1)."""

from __future__ import annotations

import difflib
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text
from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, get_paths, require_ada_data
from ada.memory.facts import _dump_yaml, _load_yaml, load_prefs

_FUZZY_THRESHOLD = 0.85
_HONORIFICS = re.compile(r"^(?:mr|mrs|ms|dr|prof|auntie|uncle)\.?\s+", re.IGNORECASE)


def _require(paths: DataPaths | None = None) -> DataPaths:
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault("ADA data not mounted", code=2)
    p.ensure_memory_dirs()
    return p


def _normalize_mention(mention: str) -> str:
    text = (mention or "").strip()
    text = _HONORIFICS.sub("", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _person_id_from_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return f"person_{slug or uuid.uuid4().hex[:8]}"


def _safe_person_path(paths: DataPaths, person_id: str) -> Path:
    pid = (person_id or "").strip().removesuffix(".yaml")
    if not pid or ".." in pid or "/" in pid or "\\" in pid:
        raise BodyFault("invalid person_id path", code=2)
    return paths.people / f"{pid}.yaml"


def normalize_person_doc(raw: dict[str, Any], *, path: Path | None = None) -> dict[str, Any]:
    """Normalize v1 stub or v2 doc to canonical in-memory shape (no write)."""
    doc = dict(raw or {})
    version = int(doc.get("schema_version") or 1)
    if version < 2:
        display = str(doc.get("display_name") or doc.get("name") or "").strip()
        if not doc.get("id"):
            stem = path.stem if path else _person_id_from_name(display or "unknown")
            doc["id"] = stem if stem.startswith("person_") else _person_id_from_name(display)
        doc.setdefault("display_name", display)
        doc.setdefault("aliases", [])
        doc.setdefault("kin", {})
        doc.setdefault("interactions", [])
        doc.setdefault("notes", str(doc.get("notes") or ""))
        if doc.get("role") and not doc.get("kin", {}).get("relation_to_operator"):
            doc.setdefault("kin", {})["relation_to_operator"] = str(doc.get("role"))
        doc["schema_version"] = 2
        return doc
    doc.setdefault("id", path.stem if path else "")
    doc.setdefault("display_name", "")
    doc.setdefault("aliases", [])
    doc.setdefault("kin", {})
    doc.setdefault("interactions", [])
    doc.setdefault("notes", "")
    doc.setdefault("remind", {"birthday": {"days_before": [7, 1, 0]}})
    return doc


def list_person_cards(*, paths: DataPaths | None = None) -> list[dict[str, Any]]:
    p = _require(paths)
    cards: list[dict[str, Any]] = []
    if not p.people.is_dir():
        return cards
    for path in sorted(p.people.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        raw = _load_yaml(path)
        if not raw:
            continue
        doc = normalize_person_doc(raw, path=path)
        doc["path"] = str(path.relative_to(p.root))
        cards.append(doc)
    return cards


def load_person(person_id: str, *, paths: DataPaths | None = None) -> dict[str, Any]:
    p = _require(paths)
    path = _safe_person_path(p, person_id)
    if not path.is_file():
        return {"ok": False, "found": False, "person_id": person_id}
    doc = normalize_person_doc(_load_yaml(path), path=path)
    return {"ok": True, "found": True, "person_id": doc["id"], "doc": doc, "path": str(path)}


def write_person_card(
    doc: dict[str, Any],
    *,
    paths: DataPaths | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    p = _require(paths)
    normalized = normalize_person_doc(doc)
    person_id = str(normalized.get("id") or "")
    if not person_id:
        return {"ok": False, "reason": "missing_id"}
    path = _safe_person_path(p, person_id)
    if path.is_file() and not confirmed:
        existing = normalize_person_doc(_load_yaml(path), path=path)
        if existing.get("display_name") != normalized.get("display_name"):
            return {
                "ok": False,
                "needs_confirm": True,
                "outcome": "needs_confirm",
                "reason": "identity_field_conflict",
                "person_id": person_id,
                "existing": existing,
                "proposed": normalized,
            }
    normalized.setdefault("provenance", {})
    normalized["provenance"].update({"source": "operator", "at": utc_now_iso()})
    normalized["schema_version"] = 2
    atomic_write_text(path, _dump_yaml(normalized))
    return {"ok": True, "person_id": person_id, "path": str(path)}


def _alias_surfaces(doc: dict[str, Any]) -> list[tuple[str, str, float, str]]:
    """Return (surface_lower, sense, confidence, person_id) tuples."""
    pid = str(doc.get("id") or "")
    hits: list[tuple[str, str, float, str]] = []
    display = str(doc.get("display_name") or "").strip()
    if display:
        hits.append((_normalize_mention(display), "display_name", 1.0, pid))
    for term in (doc.get("kin") or {}).get("indian_terms") or []:
        hits.append((_normalize_mention(str(term)), "dialect", 0.95, pid))
    for alias in doc.get("aliases") or []:
        if isinstance(alias, str):
            hits.append((_normalize_mention(alias), "alias", 1.0, pid))
            continue
        if isinstance(alias, dict):
            surface = str(alias.get("surface") or "").strip()
            if surface:
                hits.append(
                    (
                        _normalize_mention(surface),
                        str(alias.get("sense") or "alias"),
                        float(alias.get("confidence") or 1.0),
                        pid,
                    )
                )
    return hits


def resolve_mention(
    mention: str,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """0/1/many resolution — never silent pick on many."""
    needle = _normalize_mention(mention)
    if not needle:
        return {"ok": False, "reason": "empty_mention", "candidates": []}
    exact: list[dict[str, Any]] = []
    fuzzy: list[dict[str, Any]] = []
    for doc in list_person_cards(paths=paths):
        pid = str(doc.get("id") or "")
        display = str(doc.get("display_name") or "")
        for surface, sense, confidence, person_id in _alias_surfaces(doc):
            if surface == needle:
                exact.append(
                    {
                        "person_id": person_id,
                        "display_name": display,
                        "confidence": confidence,
                        "reason": f"exact_{sense}",
                    }
                )
        ratio = difflib.SequenceMatcher(None, needle, _normalize_mention(display)).ratio()
        if ratio >= _FUZZY_THRESHOLD:
            fuzzy.append(
                {
                    "person_id": pid,
                    "display_name": display,
                    "confidence": round(ratio, 3),
                    "reason": "fuzzy_display_name",
                }
            )
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in exact + fuzzy:
        pid = item["person_id"]
        if pid in seen:
            continue
        seen.add(pid)
        candidates.append(item)
    if len(candidates) == 1:
        return {"ok": True, "person_id": candidates[0]["person_id"], "candidates": candidates}
    return {
        "ok": False,
        "reason": "ambiguous" if candidates else "not_found",
        "match_count": len(candidates),
        "candidates": candidates,
    }


def parse_capture_utterance(utterance: str) -> dict[str, Any]:
    """Parse 'met X at ...' or 'met X, note'."""
    raw = (utterance or "").strip()
    lower = raw.lower()
    if lower.startswith("met "):
        raw = raw[4:].strip()
    if not raw:
        return {"ok": False, "reason": "empty_capture"}
    name = raw
    note = ""
    for sep in (" at ", " — ", " - ", ", "):
        if sep in raw:
            left, right = raw.split(sep, 1)
            name = left.strip()
            note = right.strip()
            break
    if not name:
        return {"ok": False, "reason": "missing_name"}
    return {"ok": True, "display_name": name, "note": note, "utterance": utterance}


def person_capture(
    *,
    utterance: str | None = None,
    display_name: str | None = None,
    note: str | None = None,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    parsed = (
        parse_capture_utterance(utterance or "")
        if utterance
        else {"ok": True, "display_name": display_name or "", "note": note or ""}
    )
    if not parsed.get("ok"):
        return parsed
    name = str(parsed.get("display_name") or display_name or "").strip()
    interaction_note = str(parsed.get("note") or note or "").strip()
    resolved = resolve_mention(name, paths=paths)
    created = False
    if resolved.get("ok"):
        person_id = str(resolved["person_id"])
        loaded = load_person(person_id, paths=paths)
        doc = loaded.get("doc") or {}
    else:
        person_id = _person_id_from_name(name)
        doc = {
            "id": person_id,
            "display_name": name,
            "schema_version": 2,
            "aliases": [],
            "kin": {},
            "interactions": [],
            "notes": "",
        }
        created = True
    if interaction_note:
        doc.setdefault("interactions", []).append(
            {
                "at": utc_now_iso(),
                "note": interaction_note,
                "source": "person_capture",
            }
        )
        doc["last_contact_at"] = utc_now_iso()
    result = write_person_card(doc, paths=paths, confirmed=created)
    if not result.get("ok"):
        return result
    return {
        "ok": True,
        "person_id": person_id,
        "path": result.get("path"),
        "created": created,
        "interaction_id": len(doc.get("interactions") or []) - 1 if interaction_note else None,
    }


def person_note(
    *,
    person_id: str | None = None,
    mention: str | None = None,
    text: str,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    if not person_id and mention:
        resolved = resolve_mention(mention, paths=paths)
        if not resolved.get("ok"):
            return resolved
        person_id = str(resolved["person_id"])
    if not person_id:
        return {"ok": False, "reason": "missing_person"}
    loaded = load_person(person_id, paths=paths)
    if not loaded.get("found"):
        return {"ok": False, "reason": "not_found", "person_id": person_id}
    doc = loaded["doc"]
    at = utc_now_iso()
    doc.setdefault("interactions", []).append(
        {"at": at, "note": str(text).strip(), "source": "person_note"}
    )
    doc["last_contact_at"] = at
    result = write_person_card(doc, paths=paths, confirmed=True)
    return {
        "ok": True,
        "person_id": person_id,
        "interaction_at": at,
        "note": text,
        **result,
    }


def who_is(*, mention: str, paths: DataPaths | None = None) -> dict[str, Any]:
    resolved = resolve_mention(mention, paths=paths)
    candidates = list(resolved.get("candidates") or [])
    if resolved.get("ok") and len(candidates) == 1:
        pid = str(resolved["person_id"])
        loaded = load_person(pid, paths=paths)
        doc = loaded.get("doc") or {}
        candidates[0]["doc"] = {
            "display_name": doc.get("display_name"),
            "kin": doc.get("kin"),
            "birthday": doc.get("birthday"),
            "last_contact_at": doc.get("last_contact_at"),
        }
    return {
        "ok": True,
        "mention": mention,
        "match_count": len(candidates),
        "candidates": candidates,
        "person_id": resolved.get("person_id") if resolved.get("ok") else None,
    }


def alias_set(
    *,
    alias: str,
    person_id: str | None = None,
    mention: str | None = None,
    sense: str = "alias",
    confirmed: bool = False,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    surface = (alias or mention or "").strip()
    if not surface:
        return {"ok": False, "reason": "missing_alias"}
    if not person_id and mention:
        resolved = resolve_mention(mention, paths=paths)
        if not resolved.get("ok"):
            return {
                "ok": False,
                "needs_confirm": len(resolved.get("candidates") or []) > 1,
                "outcome": "needs_confirm" if len(resolved.get("candidates") or []) > 1 else "error",
                "candidates": resolved.get("candidates") or [],
                "reason": resolved.get("reason"),
            }
        person_id = str(resolved["person_id"])
    if not person_id:
        return {"ok": False, "reason": "missing_person"}
    needle = _normalize_mention(surface)
    clashes: list[dict[str, Any]] = []
    for doc in list_person_cards(paths=paths):
        pid = str(doc.get("id") or "")
        for surf, _, _, _ in _alias_surfaces(doc):
            if surf == needle and pid != person_id:
                clashes.append(
                    {"person_id": pid, "display_name": doc.get("display_name"), "alias": surface}
                )
    if clashes and not confirmed:
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": "alias_clash",
            "alias": surface,
            "person_id": person_id,
            "candidates": clashes,
        }
    loaded = load_person(person_id, paths=paths)
    if not loaded.get("found"):
        return {"ok": False, "reason": "not_found", "person_id": person_id}
    doc = loaded["doc"]
    aliases = list(doc.get("aliases") or [])
    aliases.append({"surface": surface, "sense": sense, "confidence": 1.0, "locale": "en-IN-family"})
    doc["aliases"] = aliases
    result = write_person_card(doc, paths=paths, confirmed=True)
    return {"ok": True, "alias": surface, "person_id": person_id, "sense": sense, **result}


def person_update(
    *,
    person_id: str,
    fields: dict[str, Any] | None = None,
    confirmed: bool = False,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    loaded = load_person(person_id, paths=paths)
    if not loaded.get("found"):
        return {"ok": False, "reason": "not_found", "person_id": person_id}
    doc = loaded["doc"]
    identity_keys = {"display_name", "legal_name", "id"}
    patch = dict(fields or {})
    if any(k in patch for k in identity_keys) and not confirmed:
        return {
            "ok": False,
            "needs_confirm": True,
            "outcome": "needs_confirm",
            "reason": "identity_field_conflict",
            "person_id": person_id,
            "fields": list(patch.keys()),
        }
    for key, val in patch.items():
        if key == "kin" and isinstance(val, dict):
            doc.setdefault("kin", {}).update(val)
        else:
            doc[key] = val
    result = write_person_card(doc, paths=paths, confirmed=confirmed or not patch)
    return {"ok": True, "person_id": person_id, "fields": list(patch.keys()), **result}


def _next_birthday_iso(birthday: str, *, paths: DataPaths | None = None) -> tuple[str, int]:
    """Return (due_at iso UTC, days_until) for next birthday occurrence."""
    prefs = load_prefs(paths)
    tz_name = str(prefs.get("preferred_tz") or "Pacific/Auckland")
    tz = ZoneInfo(tz_name)
    today = datetime.now(tz).date()
    parts = birthday.split("-")
    if len(parts) != 3:
        raise ValueError("birthday must be YYYY-MM-DD")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    try:
        bday = date(today.year, month, day)
    except ValueError:
        # Feb 29 → Feb 28 non-leap
        bday = date(today.year, month, 28)
    if bday < today:
        try:
            bday = date(today.year + 1, month, day)
        except ValueError:
            bday = date(today.year + 1, month, 28)
    due_local = datetime(bday.year, bday.month, bday.day, 9, 0, 0, tzinfo=tz)
    due_utc = due_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    days_until = (bday - today).days
    return due_utc, days_until


def birthday_set(
    *,
    person_id: str | None = None,
    mention: str | None = None,
    birthday: str,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    if not person_id and mention:
        resolved = resolve_mention(mention, paths=paths)
        if not resolved.get("ok"):
            return resolved
        person_id = str(resolved["person_id"])
    if not person_id:
        return {"ok": False, "reason": "missing_person"}
    loaded = load_person(person_id, paths=paths)
    if not loaded.get("found"):
        return {"ok": False, "reason": "not_found", "person_id": person_id}
    doc = loaded["doc"]
    doc["birthday"] = birthday.strip()
    write_person_card(doc, paths=paths, confirmed=True)
    display = str(doc.get("display_name") or person_id)
    due_at, days_until = _next_birthday_iso(birthday, paths=paths)
    remind_days = (
        (doc.get("remind") or {}).get("birthday", {}).get("days_before") or [7, 1, 0]
    )
    first_before = int(remind_days[0]) if remind_days else 7
    prefs = load_prefs(paths)
    tz = ZoneInfo(str(prefs.get("preferred_tz") or "Pacific/Auckland"))
    due_local = datetime.fromisoformat(due_at.replace("Z", "+00:00")).astimezone(tz)
    remind_local = due_local - timedelta(days=first_before)
    remind_at = remind_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    from ada.memory.open_loops import upsert_loop

    loop = upsert_loop(
        kind="todo",
        status="open",
        title=f"Birthday — {display}",
        text=f"Birthday — {display}",
        due_at=due_at,
        remind_at=remind_at,
        people_ids=[person_id],
        notify=True,
        paths=paths,
    )
    return {
        "ok": True,
        "person_id": person_id,
        "birthday": birthday,
        "open_loop_ids": [loop.get("id")] if loop.get("id") else [],
        "due_at": due_at,
        "days_until": days_until,
    }


def people_remind(*, horizon_days: int = 14, paths: DataPaths | None = None) -> dict[str, Any]:
    prefs = load_prefs(paths)
    tz = ZoneInfo(str(prefs.get("preferred_tz") or "Pacific/Auckland"))
    today = datetime.now(tz).date()
    horizon = today + timedelta(days=horizon_days)
    upcoming: list[dict[str, Any]] = []
    birthday_soon: list[dict[str, Any]] = []
    for doc in list_person_cards(paths=paths):
        bday = doc.get("birthday")
        if not bday:
            continue
        try:
            due_at, days_until = _next_birthday_iso(str(bday), paths=paths)
        except ValueError:
            continue
        due_date = datetime.fromisoformat(due_at.replace("Z", "+00:00")).astimezone(tz).date()
        if due_date > horizon:
            continue
        entry = {
            "person_id": doc.get("id"),
            "display_name": doc.get("display_name"),
            "event": "birthday",
            "due_at": due_at,
            "days_until": days_until,
            "reason": "birthday",
        }
        upcoming.append(entry)
        if days_until <= 14:
            birthday_soon.append(entry)
    return {
        "ok": True,
        "horizon_days": horizon_days,
        "upcoming": upcoming,
        "birthday_soon": birthday_soon,
    }


def parse_birthday_utterance(body: str) -> dict[str, Any]:
    """Parse 'Name YYYY-MM-DD' from set birthday prefill body."""
    raw = (body or "").strip()
    match = re.search(r"(\d{4}-\d{2}-\d{2})\s*$", raw)
    if not match:
        return {"ok": False, "reason": "missing_date"}
    birthday = match.group(1)
    mention = raw[: match.start()].strip(" :-,")
    if not mention:
        return {"ok": False, "reason": "missing_person"}
    return {"ok": True, "mention": mention, "birthday": birthday}
