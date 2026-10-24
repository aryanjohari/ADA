"""Shim — gym reflection lives in ada.life.gym.reflection."""

from __future__ import annotations

import sys

from ada.life.gym import reflection as _impl

sys.modules[__name__] = _impl
