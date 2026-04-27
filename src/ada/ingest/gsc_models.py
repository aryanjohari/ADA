"""Typed schemas for Google Search Console ingestion."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GSCQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_url: str
    start_date: date
    end_date: date
    dimensions: list[str] = Field(default_factory=lambda: ["date", "query", "page", "country", "device"])
    row_limit: int = Field(default=25000, ge=1, le=25000)
    start_row: int = Field(default=0, ge=0)

    @field_validator("dimensions")
    @classmethod
    def _validate_dimensions(cls, dims: list[str]) -> list[str]:
        allowed = {"date", "query", "page", "country", "device"}
        out = [str(d).strip().lower() for d in dims if str(d).strip()]
        if not out:
            raise ValueError("dimensions cannot be empty")
        bad = [d for d in out if d not in allowed]
        if bad:
            raise ValueError(f"unsupported dimensions: {bad!r}")
        return out


class GSCResponseRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keys: list[str] = Field(default_factory=list)
    clicks: float = 0.0
    impressions: float = 0.0
    ctr: float = 0.0
    position: float = 0.0

    def to_dimension_map(self, dimensions: list[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for idx, dim in enumerate(dimensions):
            out[dim] = str(self.keys[idx]) if idx < len(self.keys) else ""
        return out


class GSCQueryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rows: list[GSCResponseRow] = Field(default_factory=list)
    response_aggregation_type: Optional[str] = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "GSCQueryResponse":
        rows = payload.get("rows")
        if not isinstance(rows, list):
            rows = []
        return cls(rows=rows, response_aggregation_type=payload.get("responseAggregationType"))
