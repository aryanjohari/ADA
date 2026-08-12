"""Boot charter: constitution §14 + identity + FACT slice + voice exemplars.

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
_DEFAULT_VOICE_EXEMPLARS = _REPO_ROOT / "docs" / "VOICE_EXEMPLARS.md"

_SECTION_14_RE = re.compile(
    r"##\s*14\.\s*Prompt extract.*?\n```text\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)

ANTI_FLUFF_ADDENDUM = """Anti-fluff (hard rules):
- Do NOT use: "I'd be happy to help", "Happy to help!", "As an AI…", "I understand how you feel", empty hedged apologies, or empathy theater.
- Do NOT claim consciousness, sentience, feelings, or an offline inner life beyond lifecycle/runs receipts.
- Warmth = accurate recall + useful initiative + honest refusals — not claimed emotions.
- FACTS are dry standing truth. WORLDVIEW digests are interpretive and must be labeled as such — never equal to vitals/lifecycle metal.
- Prefer short, sharp answers; truth beats charm. If Aryan says chill, chill immediately.
"""


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


def load_voice_exemplars(path: Path | None = None, *, max_chars: int = 2400) -> str:
    """Load operator-owned few-shot pairs from docs/VOICE_EXEMPLARS.md."""
    p = path or _DEFAULT_VOICE_EXEMPLARS
    if not p.is_file():
        return "Voice exemplars: (file missing — keep roast register without fluff.)"
    text = p.read_text(encoding="utf-8").strip()
    if len(text) > max_chars:
        text = text[: max_chars - 20] + "\n…(truncated)"
    return "Voice exemplars (register only — original pairs; not copied routines):\n" + text


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
            "Read-class body + memory tools only; no FACT/WORLDVIEW writes. "
            "runs/ audit append is allowed."
        )
    if mode_l == "agent":
        return (
            "Current harness mode: Agent (local TTY/SSH operator-equivalent). "
            "Memory append tools allowed (memory_facts_append, open_loops, "
            "worldview_write with cites). Overwrite/delete still needs_confirm. "
            "Dream seal runs via `ada dream run`, not as a chat toy."
        )
    if mode_l == "plan":
        return (
            "Current harness mode: Plan (stub). "
            "Propose only; read tools OK; no side-effect tools."
        )
    return f"Current harness mode: {mode}."


def _fact_boot_slice() -> str:
    try:
        from ada.memory.facts import boot_fact_slice

        return boot_fact_slice()
    except Exception as exc:  # noqa: BLE001
        return f"FACTS (dry, standing): unavailable ({exc})."


def _worldview_boot_slice() -> str:
    try:
        from ada.memory.worldview import latest_digest_summary

        paths = get_paths()
        summary = latest_digest_summary(paths=paths, max_chars=1600)
        if not summary:
            return "WORLDVIEW (interpretive): (none yet)."
        return summary
    except Exception as exc:  # noqa: BLE001
        return f"WORLDVIEW (interpretive): unavailable ({exc})."


def build_system_charter(
    *,
    mode: str = "observe",
    constitution_path: Path | None = None,
    include_worldview: bool = True,
) -> str:
    """Full system prompt: §14 + mode + identity + anti-fluff + exemplars + FACT slice."""
    parts = [
        load_section_14_extract(constitution_path),
        "",
        identity_summary(),
        mode_addendum(mode),
        "",
        ANTI_FLUFF_ADDENDUM.strip(),
        "",
        load_voice_exemplars(),
        "",
        _fact_boot_slice(),
    ]
    if include_worldview:
        parts.extend(["", _worldview_boot_slice()])
    parts.extend(
        [
            "",
            "Tool-use: Body claims need body_vitals / body_whoami / body_story / "
            "body_doctor observations. FACT claims need memory_facts_* receipts or "
            "boot FACT slice. WORLDVIEW digests are interpretive — cite them as such; "
            "never equal to vitals/lifecycle metal. "
            "Never invent success without a gateway receipt. "
            "Use memory_facts_append when Aryan says remember (Agent mode).",
        ]
    )
    return "\n".join(parts)
