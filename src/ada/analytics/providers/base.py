"""Provider abstraction for analytics ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Protocol


@dataclass(frozen=True)
class CanonicalAnalyticsRow:
    provider: str
    data_date: str
    query: str
    page: str
    country: str
    device: str
    clicks: float
    impressions: float
    ctr: float
    position: float


@dataclass(frozen=True)
class ProviderFetchRequest:
    site_url: str
    start_date: date
    end_date: date
    dimensions: list[str]
    row_limit: int
    start_row: int = 0


class AnalyticsProvider(Protocol):
    provider_name: str
    schema_version: str

    async def fetch_window(self, request: ProviderFetchRequest) -> object:
        ...

    def normalize(self, payload: object, dimensions: list[str]) -> Iterable[CanonicalAnalyticsRow]:
        ...
