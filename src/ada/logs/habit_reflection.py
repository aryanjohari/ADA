"""Shim — habit reflection lives in ada.life.habits.reflection."""

from __future__ import annotations

import sys

from ada.life.habits import reflection as _impl

sys.modules[__name__] = _impl
