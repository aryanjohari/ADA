"""Shim — nutrition date lives in ada.life.food.date."""

from __future__ import annotations

import sys

from ada.life.food import date as _impl

sys.modules[__name__] = _impl
