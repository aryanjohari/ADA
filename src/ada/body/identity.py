"""Birth card — identity.yaml written once; born_at is sacred."""

from __future__ import annotations

import platform
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from ada import __version__
from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text, cleanup_orphan_tmps
from ada.io.paths import BodyFault, DataPaths, require_ada_data


class IdentityCard(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: int = 1
    name: str = "ADA"
    pronouns: str = "she/her"
    operator: str = "Aryan"
    born_at: str
    body_hostname: str
    board_model: str
    board_revision: str
    os: str
    kernel: str
    timezone: str
    cortex_primary: str = "gemini"
    voice_charter: str = "witty_full_stage"
    version: str


def _read_os_pretty() -> str:
    data: dict[str, str] = {}
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k] = v.strip().strip('"')
    except OSError:
        return platform.platform()
    return data.get("PRETTY_NAME") or data.get("NAME") or platform.platform()


def _board_info() -> tuple[str, str]:
    model = "unknown"
    revision = "unknown"
    try:
        raw = Path("/proc/device-tree/model").read_bytes().decode("utf-8", errors="replace")
        model = raw.strip("\x00").strip() or model
    except OSError:
        try:
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
                if line.startswith("Model"):
                    model = line.split(":", 1)[1].strip()
        except OSError:
            pass
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("Revision"):
                revision = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    return model, revision


def _timezone_name() -> str:
    try:
        link = Path("/etc/localtime").resolve()
        parts = link.parts
        if "zoneinfo" in parts:
            idx = parts.index("zoneinfo")
            return "/".join(parts[idx + 1 :])
        if Path("/etc/timezone").is_file():
            return Path("/etc/timezone").read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return "UTC"


def build_identity_card(*, born_at: str | None = None) -> IdentityCard:
    import socket

    model, revision = _board_info()
    return IdentityCard(
        born_at=born_at or utc_now_iso(),
        body_hostname=socket.gethostname(),
        board_model=model,
        board_revision=revision,
        os=_read_os_pretty(),
        kernel=platform.release(),
        timezone=_timezone_name(),
        version=__version__,
    )


def identity_exists(paths: DataPaths | None = None) -> bool:
    p = paths or require_ada_data()
    cleanup_orphan_tmps(p.facts, "identity.yaml")
    return p.identity_yaml.is_file()


def load_identity(paths: DataPaths | None = None) -> IdentityCard:
    p = paths or require_ada_data()
    cleanup_orphan_tmps(p.facts, "identity.yaml")
    if not p.identity_yaml.is_file():
        raise BodyFault("identity.yaml missing; run `ada body birth` first", code=2)
    raw = yaml.safe_load(p.identity_yaml.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise BodyFault("identity.yaml is not a mapping", code=2)
    return IdentityCard.model_validate(raw)


def create_identity(
    *,
    paths: DataPaths | None = None,
    append_birth_event: bool = True,
) -> tuple[IdentityCard, bool]:
    """Create birth card once.

    Returns (card, created). Second call keeps born_at and does not rewrite.
    Also applies birth pack seeds (SELF/OPERATOR) and prefs if missing.
    """
    p = paths or require_ada_data()
    cleanup_orphan_tmps(p.facts, "identity.yaml")

    created = False
    if p.identity_yaml.is_file():
        card = load_identity(p)
    else:
        p.facts.mkdir(parents=True, exist_ok=True)
        card = build_identity_card()
        payload = yaml.safe_dump(
            card.model_dump(),
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
        atomic_write_text(p.identity_yaml, payload)
        created = True

        if append_birth_event:
            # Late import avoids circular dependency at module load.
            from ada.body.lifecycle import append_event

            append_event(
                "birth",
                summary=f"ADA born on {card.body_hostname}",
                details={
                    "born_at": card.born_at,
                    "agent_version": card.version,
                    "board_model": card.board_model,
                },
                paths=p,
            )

    # Birth pack + prefs — idempotent; never overwrite operator data.
    try:
        from ada.memory.birth_pack import apply_birth_pack
        from ada.memory.facts import ensure_prefs
        from ada.memory.open_loops import ensure_open_loops

        apply_birth_pack(p)
        ensure_prefs(p)
        ensure_open_loops(p)
    except Exception:  # noqa: BLE001 — birth must not fail closed on optional seeds
        pass

    return card, created
