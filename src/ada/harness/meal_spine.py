"""Shim — meal spine lives in ada.life.food.spine."""

from __future__ import annotations

import sys

from ada.life.food import spine as _impl

sys.modules[__name__] = _impl
