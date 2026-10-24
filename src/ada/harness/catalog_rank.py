"""Shim — catalog rank lives in ada.life.food.rank."""

from __future__ import annotations

import sys

from ada.life.food import rank as _impl

sys.modules[__name__] = _impl
