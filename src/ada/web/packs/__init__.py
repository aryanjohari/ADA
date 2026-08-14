"""Named web allowlist packs — catalog loader + operator seed (M08).

YAML catalog is canonical. This module loads, validates, and merges packs
into prefs.web_allowlist. No silent seed on import, Dream, or chat.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ada.io.paths import DataPaths, require_ada_data
from ada.web import allowlist as allowlist_mod

CATALOG_FILENAME = "catalog.yaml"
CATALOG_PATH = Path(__file__).resolve().parent / CATALOG_FILENAME

# Operator-locked first rooms for this host (M08 implement slice). Not §7.2.
FIRST_ROOMS: tuple[str, ...] = (
    "lab.papers",
    "lab.code",
    "lab.standards",
    "lab.encyclopedia",
    "lab.cortex-docs",
    "nz.law",
    "nz.civic",
    "nz.economy",
    "nz.data",
    "nz.place",
    "nz.news",
)

DAY_ONE_HOST_BUDGET = 50


@dataclass(frozen=True)
class PackHost:
    host: str
    ttl_seconds: int
    ttl: str
    pack_id: str

    @property
    def note(self) -> str:
        return f"pack:{self.pack_id}"


@dataclass(frozen=True)
class Pack:
    id: str
    title: str
    day_one: bool
    hosts: tuple[PackHost, ...]
    inherits: tuple[str, ...]
    redirect_pairs: tuple[tuple[str, str], ...]


def catalog_path() -> Path:
    return CATALOG_PATH


def _load_raw() -> dict[str, Any]:
    path = catalog_path()
    if not path.is_file():
        raise FileNotFoundError(f"pack catalog missing: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("pack catalog must be a YAML mapping")
    return raw


def _ttl_vibes(raw: dict[str, Any]) -> dict[str, int]:
    vibes = raw.get("ttl_vibes") or {}
    if not isinstance(vibes, dict) or not vibes:
        raise ValueError("pack catalog missing ttl_vibes")
    out: dict[str, int] = {}
    for name, seconds in vibes.items():
        out[str(name)] = int(seconds)
    return out


def _as_pair(item: Any) -> tuple[str, str]:
    if not isinstance(item, (list, tuple)) or len(item) != 2:
        raise ValueError(f"redirect_pairs entries must be [host, host], got {item!r}")
    a = allowlist_mod.normalize_host(str(item[0]))
    b = allowlist_mod.normalize_host(str(item[1]))
    if not a or not b:
        raise ValueError(f"redirect pair has empty host: {item!r}")
    return a, b


def _parse_pack(pack_id: str, body: dict[str, Any], vibes: dict[str, int]) -> Pack:
    if not isinstance(body, dict):
        raise ValueError(f"pack {pack_id!r} must be a mapping")
    title = str(body.get("title") or pack_id)
    day_one = bool(body.get("day_one", False))
    inherits_raw = body.get("inherits") or []
    if not isinstance(inherits_raw, list):
        raise ValueError(f"pack {pack_id!r} inherits must be a list")
    inherits = tuple(str(x) for x in inherits_raw)

    hosts_raw = body.get("hosts") or []
    if not isinstance(hosts_raw, list):
        raise ValueError(f"pack {pack_id!r} hosts must be a list")
    seen: set[str] = set()
    hosts: list[PackHost] = []
    for item in hosts_raw:
        if not isinstance(item, dict) or not item.get("host"):
            raise ValueError(f"pack {pack_id!r} host entries need host+ttl, got {item!r}")
        host = allowlist_mod.normalize_host(str(item["host"]))
        refused = allowlist_mod.wont_allow_reason(host)
        if refused:
            raise ValueError(f"pack {pack_id!r} host {host!r}: {refused}")
        if host in seen:
            raise ValueError(f"pack {pack_id!r} duplicates host {host}")
        seen.add(host)
        vibe = str(item.get("ttl") or "")
        if vibe not in vibes:
            raise ValueError(f"pack {pack_id!r} host {host}: unknown ttl vibe {vibe!r}")
        hosts.append(
            PackHost(
                host=host,
                ttl_seconds=int(vibes[vibe]),
                ttl=vibe,
                pack_id=pack_id,
            )
        )

    pairs_raw = body.get("redirect_pairs") or []
    if not isinstance(pairs_raw, list):
        raise ValueError(f"pack {pack_id!r} redirect_pairs must be a list")
    pairs: list[tuple[str, str]] = []
    for item in pairs_raw:
        a, b = _as_pair(item)
        if a not in seen or b not in seen:
            raise ValueError(
                f"pack {pack_id!r} redirect pair {a}/{b} must both be listed hosts"
            )
        pairs.append((a, b))

    return Pack(
        id=pack_id,
        title=title,
        day_one=day_one,
        hosts=tuple(hosts),
        inherits=inherits,
        redirect_pairs=tuple(pairs),
    )


def load_catalog() -> dict[str, Pack]:
    """Load and validate the git-tracked catalog. Raises on corrupt data."""
    raw = _load_raw()
    vibes = _ttl_vibes(raw)
    packs_raw = raw.get("packs")
    if not isinstance(packs_raw, dict) or not packs_raw:
        raise ValueError("pack catalog missing packs mapping")
    packs: dict[str, Pack] = {}
    for pack_id, body in packs_raw.items():
        pid = str(pack_id)
        packs[pid] = _parse_pack(pid, body if isinstance(body, dict) else {}, vibes)
    for pack in packs.values():
        for inherited in pack.inherits:
            if inherited not in packs:
                raise ValueError(f"pack {pack.id!r} inherits unknown {inherited!r}")
    return packs


def list_pack_summaries() -> list[dict[str, Any]]:
    """Catalog pack ids + host counts (own hosts, not inherited)."""
    packs = load_catalog()
    rows: list[dict[str, Any]] = []
    for pid, pack in packs.items():
        rows.append(
            {
                "id": pid,
                "title": pack.title,
                "day_one": pack.day_one,
                "host_count": len(pack.hosts),
                "inherits": list(pack.inherits),
            }
        )
    return rows


def get_pack(pack_id: str) -> Pack:
    pid = (pack_id or "").strip()
    packs = load_catalog()
    if pid not in packs:
        known = ", ".join(sorted(packs))
        raise KeyError(f"unknown pack {pid!r}; known: {known}")
    return packs[pid]


def expand_pack_ref(pack_ref: str) -> list[str]:
    """Resolve a pack id or alias (`lab` → all day-one `lab.*` packs)."""
    ref = (pack_ref or "").strip()
    if not ref:
        raise KeyError("empty pack id")
    packs = load_catalog()
    if ref == "lab":
        ids = sorted(
            pid for pid, pack in packs.items() if pid.startswith("lab.") and pack.day_one
        )
        if not ids:
            raise KeyError("no day-one lab.* packs in catalog")
        return ids
    if ref not in packs:
        known = ", ".join(sorted(packs))
        raise KeyError(f"unknown pack {ref!r}; known: {known} (alias: lab)")
    return [ref]


def day_one_hosts() -> dict[str, PackHost]:
    """Unique day-one hosts (first pack wins on overlap). Excludes inherit-only."""
    packs = load_catalog()
    out: dict[str, PackHost] = {}
    for pack in packs.values():
        if not pack.day_one:
            continue
        for item in pack.hosts:
            out.setdefault(item.host, item)
    return out


def seed_pack(
    pack_ref: str,
    *,
    paths: DataPaths | None = None,
    update_existing: bool = True,
) -> dict[str, Any]:
    """Merge catalog pack(s) into prefs.web_allowlist. Idempotent; no wipe."""
    try:
        pack_ids = expand_pack_ref(pack_ref)
    except KeyError as exc:
        return {
            "ok": False,
            "outcome": "error",
            "error": str(exc),
            "denied_reason": str(exc),
        }
    p = paths or require_ada_data()
    catalog = load_catalog()
    added: list[str] = []
    already: list[str] = []
    updated: list[str] = []
    errors: list[str] = []
    for pid in pack_ids:
        pack = catalog[pid]
        for item in pack.hosts:
            result = allowlist_mod.add_host(
                item.host,
                paths=p,
                ttl_seconds=item.ttl_seconds,
                note=item.note,
                update_existing=update_existing,
            )
            if not result.get("ok"):
                errors.append(str(result.get("error") or item.host))
                continue
            if result.get("already"):
                already.append(item.host)
                if result.get("updated"):
                    updated.append(item.host)
            else:
                added.append(item.host)
    entries = allowlist_mod.load_allowlist(p)
    ok = not errors
    return {
        "ok": ok,
        "outcome": "ok" if ok else "error",
        "pack_ref": pack_ref,
        "pack_ids": pack_ids,
        "added": added,
        "already": already,
        "updated": updated,
        "errors": errors,
        "allowlist": entries,
        "count": len(entries),
        **({"error": "; ".join(errors)} if errors else {}),
    }
