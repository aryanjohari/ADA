"""ProgrammePacket schema (closed fields)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ada.policy.load import DEFAULT_INTENT_MAX_BYTES


class KnowledgeSourceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    kind: str = "rss"


class CronLineEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comment: str = ""
    line: str


class ProgrammePacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mission_slug: str
    title: str
    defaults_json: dict[str, Any] = Field(default_factory=dict)
    schedule_hint_json: Optional[dict[str, Any]] = None
    knowledge_sources: list[KnowledgeSourceEntry] = Field(default_factory=list)
    recommended_cron: list[CronLineEntry] = Field(default_factory=list)
    skills_enabled: list[str] = Field(default_factory=list)
    risk_summary: str = ""
    brief_md: str = ""

    @field_validator("mission_slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("mission_slug required")
        return s

    @field_validator("brief_md")
    @classmethod
    def _brief_md(cls, v: str) -> str:
        text = v if isinstance(v, str) else ""
        if len(text.encode("utf-8")) > DEFAULT_INTENT_MAX_BYTES:
            raise ValueError(
                f"brief_md exceeds {DEFAULT_INTENT_MAX_BYTES} bytes (UTF-8)"
            )
        return text


def validate_packet_dict(data: dict[str, Any]) -> ProgrammePacket:
    return ProgrammePacket.model_validate(data)
