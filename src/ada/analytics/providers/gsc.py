"""GSC provider adapter implementing the analytics provider contract."""

from __future__ import annotations

from collections.abc import Iterable

from ada.analytics.providers.base import AnalyticsProvider, CanonicalAnalyticsRow, ProviderFetchRequest
from ada.config import Settings
from ada.ingest.gsc_client import GSCClient
from ada.ingest.gsc_models import GSCQueryRequest, GSCQueryResponse


class GSCAnalyticsProvider(AnalyticsProvider):
    provider_name = "gsc"
    schema_version = "gsc.v1"

    def __init__(self, settings: Settings) -> None:
        self._client = GSCClient(settings)

    async def fetch_window(self, request: ProviderFetchRequest) -> GSCQueryResponse:
        req = GSCQueryRequest(
            site_url=request.site_url,
            start_date=request.start_date,
            end_date=request.end_date,
            dimensions=request.dimensions,
            row_limit=request.row_limit,
            start_row=request.start_row,
        )
        # Caller owns the time budget and retries for orchestration-level behavior.
        return await self._client.query(req, budget_deadline_monotonic=10**12)

    def normalize(
        self, payload: GSCQueryResponse, dimensions: list[str]
    ) -> Iterable[CanonicalAnalyticsRow]:
        for row in payload.rows:
            d = row.to_dimension_map(dimensions)
            yield CanonicalAnalyticsRow(
                provider=self.provider_name,
                data_date=d.get("date", ""),
                query=d.get("query", ""),
                page=d.get("page", ""),
                country=d.get("country", ""),
                device=d.get("device", ""),
                clicks=float(row.clicks),
                impressions=float(row.impressions),
                ctr=float(row.ctr),
                position=float(row.position),
            )
