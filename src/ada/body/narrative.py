"""Ledger → plain sentences. No LLM; never invent outages."""

from __future__ import annotations

from ada.body.lifecycle import LifecycleEvent


def sentence_for(event: LifecycleEvent) -> str:
    """One greppable sentence from a single ledger event."""
    ts = event.ts
    t = event.type
    summary = event.summary.strip() or t
    return f"[{ts}] {t}: {summary}"


def story(events: list[LifecycleEvent], *, n: int | None = None) -> str:
    """Render autobiography from ledger events only.

    If the ledger is empty, say so — do not fabricate childhood.
    """
    if n is not None and n > 0:
        events = events[-n:]
    if not events:
        return "No lifecycle events recorded yet."
    return "\n".join(sentence_for(ev) for ev in events)


def story_uses_only_ledger(text: str, events: list[LifecycleEvent]) -> bool:
    """Return True if every non-empty story line is derived from an event summary/type."""
    if text.strip() == "No lifecycle events recorded yet.":
        return not events
    allowed = {sentence_for(ev) for ev in events}
    for line in text.splitlines():
        if line and line not in allowed:
            return False
    return True
