"""PSEO `page.json` v1 (ISR consumer contract) — Pydantic mirror of docs/pseo-isr-contract.md."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class LeadGenV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    form_fields: list[Any] = Field(default_factory=list)
    form_action_url: str
    call_display_phone: str
    call_tel_link: str


class PageJsonV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    meta_description: str
    og_image: Optional[str] = None
    content: str
    lead_gen: LeadGenV1
    json_ld: dict[str, Any]
