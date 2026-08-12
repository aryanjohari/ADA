"""Boot charter: constitution §14 prompt extract + identity summary.

No SOUL.md. Agent must not rewrite this charter (M02 §4.8 / §15).
CLI default mode is Observe (M02 lock) even though §14 text mentions Agent
as the normal chat mode — harness flag wins; gateway enforces tool set.
"""

from __future__ import annotations

import re
from pathlib import Path

from ada.io.paths import BodyFault, get_paths

# Repo-relative default when running from installed package next to docs/.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CONSTITUTION = _REPO_ROOT / "docs" / "02_CONSTITUTION.md"

_SECTION_14_RE = re.compile(
    r"##\s*14\.\s*Prompt extract.*?\n```text\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


class CharterError(Exception):
    """Constitution extract could not be loaded."""


def load_section_14_extract(constitution_path: Path | None = None) -> str:
    """Parse the fenced ```text block under §14 from the constitution."""
    path = constitution_path or _DEFAULT_CONSTITUTION
    if not path.is_file():
        raise CharterError(f"constitution not found at {path}")
    text = path.read_text(encoding="utf-8")
    match = _SECTION_14_RE.search(text)
    if not match:
        raise CharterError(f"§14 prompt extract not found in {path}")
    extract = match.group(1).strip()
    if "not conscious" not in extract.lower() and "not conscious" not in extract:
        # Soft check — constitution must refuse consciousness claims.
        if "Never claim consciousness" not in extract:
            raise CharterError("§14 extract missing consciousness refusal cue")
    return extract


def identity_summary() -> str:
    """One-line identity boot context; empty if not born / mount missing."""
    try:
        from ada.body.identity import identity_exists, load_identity

        paths = get_paths()
        if not identity_exists(paths):
            return "Identity: not born yet (no identity.yaml)."
        card = load_identity(paths)
        return (
            f"Identity: {card.name} ({card.pronouns}); born_at={card.born_at}; "
            f"host={card.body_hostname}; operator={card.operator}."
        )
    except BodyFault as exc:
        return f"Identity: unavailable ({exc.message})."
    except Exception as exc:  # noqa: BLE001 — boot must not crash charter
        return f"Identity: unavailable ({exc})."


def mode_addendum(mode: str) -> str:
    """Harness mode override note — flag wins over §14 prose defaults."""
    mode_l = mode.lower().strip()
    if mode_l == "observe":
        return (
            "Current harness mode: Observe (CLI default). "
            "Read-class body tools only; no organ writes. "
            "runs/ audit append is allowed."
        )
    if mode_l == "agent":
        return (
            "Current harness mode: Agent (local TTY/SSH operator-equivalent). "
            "M02 tools remain the four body reads; write tools not yet admitted."
        )
    if mode_l == "plan":
        return (
            "Current harness mode: Plan (stub). "
            "Propose only; read tools OK; no side-effect tools."
        )
    return f"Current harness mode: {mode}."


def build_system_charter(
    *,
    mode: str = "observe",
    constitution_path: Path | None = None,
) -> str:
    """Full system prompt: §14 + identity + mode addendum."""
    parts = [
        load_section_14_extract(constitution_path),
        "",
        identity_summary(),
        mode_addendum(mode),
        "",
        "Body claims require tool observations in this session. "
        "Use body_vitals / body_whoami / body_story / body_doctor as needed. "
        "Never invent success without a gateway receipt.",
    ]
    return "\n".join(parts)
