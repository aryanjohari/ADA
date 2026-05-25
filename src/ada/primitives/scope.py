"""Resolve base_ops / ada_ops hat ids from MissionKernel."""

from __future__ import annotations

from ada.boot import MissionKernel, get_kernel, warm_kernel_cache
from ada.config import Settings
from ada.query_engine import QueryEngine


async def resolve_kernel(
    qe: QueryEngine,
    settings: Settings,
    *,
    kernel: MissionKernel | None = None,
) -> MissionKernel:
    """Return process kernel cache; optional pre-booted kernel for same-connection tests."""
    if kernel is not None:
        warm_kernel_cache(kernel)
        return kernel
    return await get_kernel(settings)


async def base_ops_id(settings: Settings, *, kernel: MissionKernel | None = None) -> int:
    k = kernel if kernel is not None else await get_kernel(settings)
    return k.base_ops_id


async def ada_ops_id(settings: Settings, *, kernel: MissionKernel | None = None) -> int:
    k = kernel if kernel is not None else await get_kernel(settings)
    return k.ada_ops_id


async def memory_source_id(
    settings: Settings, *, kernel: MissionKernel | None = None
) -> int:
    k = kernel if kernel is not None else await get_kernel(settings)
    return k.memory_source_id
