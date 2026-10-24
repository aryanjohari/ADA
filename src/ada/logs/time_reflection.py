"""Shim — time reflection lives in ada.life.time.reflection."""

from __future__ import annotations

import sys

from ada.life.time import reflection as _impl

sys.modules[__name__] = _impl
