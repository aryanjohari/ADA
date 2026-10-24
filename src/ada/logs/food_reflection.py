"""Shim — food reflection lives in ada.life.food.reflection."""

from __future__ import annotations

import sys

from ada.life.food import reflection as _impl

sys.modules[__name__] = _impl
