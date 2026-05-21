"""HTTP client for Google Search Console Search Analytics API."""

from __future__ import annotations

import asyncio
import json
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone

UTC = timezone.utc
from typing import Any
from urllib.parse import quote

import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

from ada.config import Settings
from ada.ingest.gsc_errors import (
    GSCAuthError,
    GSCQuotaError,
    GSCTransientHttpError,
    GSCValidationError,
    GSCTimeBudgetExceeded,
)
from ada.ingest.gsc_models import GSCQueryRequest, GSCQueryResponse

GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


@dataclass
class RetryDecision:
    retry: bool
    reason: str


def _classify_retry(status_code: int) -> RetryDecision:
    if status_code == 429:
        return RetryDecision(retry=True, reason="rate_limited")
    if 500 <= status_code < 600:
        return RetryDecision(retry=True, reason="server_error")
    return RetryDecision(retry=False, reason="non_retryable_status")


def _build_backoff_delay_ms(*, attempt: int, base_ms: int, max_ms: int) -> float:
    base = min(max_ms, base_ms * (2 ** max(0, attempt - 1)))
    jitter = random.uniform(0.5, 1.5)
    return base * jitter


class GSCClient:
    def __init__(self, settings: Settings, *, http_client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._http_client = http_client
        self._token: str = ""
        self._token_expiry_epoch: float = 0.0

    def _load_service_account_info(self) -> dict[str, Any]:
        if self._settings.gsc_service_account_json:
            try:
                raw = json.loads(self._settings.gsc_service_account_json)
            except json.JSONDecodeError as e:
                raise GSCValidationError(f"GSC_SERVICE_ACCOUNT_JSON invalid JSON: {e}") from e
            if not isinstance(raw, dict):
                raise GSCValidationError("GSC_SERVICE_ACCOUNT_JSON must decode to a JSON object")
            return raw
        if self._settings.gsc_service_account_file:
            try:
                return json.loads(
                    open(self._settings.gsc_service_account_file, "r", encoding="utf-8").read()
                )
            except Exception as e:
                raise GSCValidationError(f"cannot load GSC_SERVICE_ACCOUNT_FILE: {e}") from e
        raise GSCValidationError(
            "GSC auth requires GSC_SERVICE_ACCOUNT_JSON or GSC_SERVICE_ACCOUNT_FILE"
        )

    async def _get_access_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expiry_epoch - 60:
            return self._token
        info = self._load_service_account_info()
        try:
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=[GSC_SCOPE]
            )
            await asyncio.to_thread(creds.refresh, GoogleAuthRequest())
        except Exception as e:
            raise GSCAuthError(f"unable to mint GSC access token: {e}") from e
        if not creds.token:
            raise GSCAuthError("GSC auth token is empty")
        self._token = creds.token
        exp = getattr(creds, "expiry", None)
        if isinstance(exp, datetime):
            self._token_expiry_epoch = exp.replace(tzinfo=UTC).timestamp()
        else:
            self._token_expiry_epoch = now + 300
        return self._token

    async def query(self, request: GSCQueryRequest, *, budget_deadline_monotonic: float) -> GSCQueryResponse:
        token = await self._get_access_token()
        own_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=self._settings.gsc_timeout_connect_sec,
                read=self._settings.gsc_timeout_read_sec,
                write=self._settings.gsc_timeout_read_sec,
                pool=self._settings.gsc_timeout_read_sec,
            )
        )
        site_path = quote(request.site_url, safe="")
        url = f"{self._settings.gsc_api_base_url.rstrip('/')}/sites/{site_path}/searchAnalytics/query"
        body = {
            "startDate": request.start_date.isoformat(),
            "endDate": request.end_date.isoformat(),
            "dimensions": request.dimensions,
            "rowLimit": request.row_limit,
            "startRow": request.start_row,
        }
        try:
            for attempt in range(1, self._settings.gsc_retry_max_attempts + 1):
                if time.monotonic() > budget_deadline_monotonic:
                    raise GSCTimeBudgetExceeded(
                        "GSC query exceeded ADA_GSC_TIMEOUT_TOTAL_SEC budget"
                    )
                try:
                    resp = await client.post(
                        url,
                        json=body,
                        headers={"Authorization": f"Bearer {token}"},
                    )
                except httpx.TimeoutException as e:
                    if attempt == self._settings.gsc_retry_max_attempts:
                        raise GSCTransientHttpError(f"GSC timeout after retries: {e}") from e
                    delay_ms = _build_backoff_delay_ms(
                        attempt=attempt,
                        base_ms=self._settings.gsc_retry_base_ms,
                        max_ms=self._settings.gsc_retry_max_ms,
                    )
                    await asyncio.sleep(delay_ms / 1000.0)
                    continue
                if resp.status_code in (401, 403):
                    raise GSCAuthError(f"GSC auth/permission failed ({resp.status_code})")
                if resp.status_code == 429:
                    if attempt == self._settings.gsc_retry_max_attempts:
                        raise GSCQuotaError("GSC quota/rate limit after retry budget")
                decision = _classify_retry(resp.status_code)
                if decision.retry:
                    if attempt == self._settings.gsc_retry_max_attempts:
                        raise GSCTransientHttpError(
                            f"GSC transient HTTP {resp.status_code} after retries"
                        )
                    retry_after = resp.headers.get("Retry-After", "").strip()
                    if retry_after.isdigit():
                        delay_ms = max(50, int(retry_after) * 1000)
                    else:
                        delay_ms = _build_backoff_delay_ms(
                            attempt=attempt,
                            base_ms=self._settings.gsc_retry_base_ms,
                            max_ms=self._settings.gsc_retry_max_ms,
                        )
                    await asyncio.sleep(delay_ms / 1000.0)
                    continue
                if resp.status_code >= 400:
                    raise GSCValidationError(f"GSC API rejected request ({resp.status_code}): {resp.text[:400]}")
                try:
                    payload = resp.json()
                except ValueError as e:
                    raise GSCValidationError(f"GSC response is not valid JSON: {e}") from e
                if not isinstance(payload, dict):
                    raise GSCValidationError("GSC response payload must be an object")
                return GSCQueryResponse.from_payload(payload)
            raise GSCTransientHttpError("GSC query exhausted retry loop")
        finally:
            if own_client:
                await client.aclose()
