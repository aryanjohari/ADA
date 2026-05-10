"""Parse ops/schedule.md and runbooks for cron + ada commands (schedules audit)."""

from __future__ import annotations

import re
from dataclasses import dataclass


_HEADING_RE = re.compile(r"^(#{2,6})\s+(.+)$")
_FENCE_OPEN = re.compile(r"^\s*(```cron|```bash)\s*$", re.I)
_FENCE_CLOSE = re.compile(r"^\s*```\s*$")
_ADA_CMD = re.compile(r"\bada\s+([a-z0-9\-]+)", re.I)
_SCRIPT_SH = re.compile(r"([^\s]+\.sh)\b")


@dataclass
class ScheduleRow:
    section: str
    cron_schedule: str | None
    line_raw: str
    ada_subcommands: tuple[str, ...]
    scripts: tuple[str, ...]


def parse_markdown_schedules(text: str) -> list[ScheduleRow]:
    """Extract schedule rows from ```cron and ```bash fenced blocks only."""
    lines = text.splitlines()
    current_section = "(preamble)"
    in_fence: bool = False
    rows: list[ScheduleRow] = []

    for line in lines:
        hm = _HEADING_RE.match(line)
        if hm and not in_fence:
            current_section = hm.group(2).strip()
            continue

        if in_fence:
            if _FENCE_CLOSE.match(line):
                in_fence = False
                continue
            row = _parse_schedule_line(current_section, line)
            if row:
                rows.append(row)
            continue

        if _FENCE_OPEN.match(line):
            in_fence = True
            continue

    return rows


def _parse_schedule_line(section: str, line: str) -> ScheduleRow | None:
    raw = line.rstrip()
    s = raw.strip()
    if not s or s.startswith("#"):
        return None

    cron_part: str | None = None
    rest = s

    m5 = re.search(
        r"((?:[\d\*\/\-,]+\s+){5})(.+)$",
        s,
    )
    if m5:
        cron_part = m5.group(1).strip()
        rest = m5.group(2).strip()

    ada_cmds = tuple(sorted(set(m.group(1).lower() for m in _ADA_CMD.finditer(rest))))
    scripts = tuple(sorted(set(_SCRIPT_SH.findall(rest))))

    if not ada_cmds and not scripts and not cron_part:
        return None

    return ScheduleRow(
        section=section,
        cron_schedule=cron_part,
        line_raw=raw[:500],
        ada_subcommands=ada_cmds,
        scripts=scripts,
    )


def overlap_heuristic(rows: list[ScheduleRow]) -> list[tuple[str, str, str]]:
    """Return (message, key_a, key_b) for possible duplicate cadence."""
    from collections import defaultdict

    by_key: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        for sub in r.ada_subcommands:
            key = f"{sub}|{r.cron_schedule or ''}"
            by_key[key].append(i)

    out: list[tuple[str, str, str]] = []
    for key, idxs in by_key.items():
        if len(idxs) < 2:
            continue
        parts = key.split("|", 1)
        sub, sched = parts[0], parts[1] if len(parts) > 1 else ""
        msg = f"Same ada subcommand `{sub}` and schedule `{sched or 'n/a'}` — review for duplicate ingest."
        out.append((msg, rows[idxs[0]].line_raw[:120], rows[idxs[1]].line_raw[:120]))
    return out


def normalize_crontab_lines(text: str) -> list[str]:
    return [ln.rstrip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def crontab_ada_commands(text: str) -> set[str]:
    out: set[str] = set()
    for ln in normalize_crontab_lines(text):
        for m in _ADA_CMD.finditer(ln):
            out.add(m.group(1).lower())
    return out
