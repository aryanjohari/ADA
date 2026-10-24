"""People card store — re-export ada.memory.people."""

from __future__ import annotations

from ada.memory.people import *  # noqa: F403
import ada.memory.people as store

__all__ = [name for name in dir(store) if not name.startswith("__")]
