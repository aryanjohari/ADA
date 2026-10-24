"""Shim — meal draft spine lives in ada.life.food.draft_spine."""

from __future__ import annotations

import sys

from ada.life.food import draft_spine as _impl

sys.modules[__name__] = _impl
