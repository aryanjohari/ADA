"""`ada triage`: LLM scores unscored knowledge_items for NZ-relevant news value (1–10)."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import ada
from google import genai
from google.genai import types

from ada.config import Settings
from ada.query_engine import TASK_KIND_GOAL, QueryEngine

log = logging.getLogger("ada.triage")

_MAX_EXCERPT_CHARS = 12_000

_TRIAGE_SYSTEM = """You score a short news or article snippet for how useful it is for someone
following New Zealand’s economy, markets, business, and policy.

Use only the title, link line, and excerpt — do not invent facts.

What deserves a HIGHER score (when the excerpt supports it):
- Official or authoritative material: government, regulators, RBNZ, Stats NZ, ministers, agencies,
  courts, listed companies’ announcements, verified economic data or surveys.
- Concrete market or economy signals: prices, rates, indices, forecasts, employment, inflation,
  housing stats, trade figures, budgets, rule changes, dates of effect, dollar amounts, or clear
  “what changed” policy/economy news.
- Credible reporting of those things (not opinion fluff).

What deserves a LOWER score:
- Gossip, lifestyle filler, vague commentary, or items with no real economy/market/policy hook
  in the text you see.

Use the full 1–10 range. Reward real substance; do not inflate scores for thin or off-topic pieces.

Return JSON only with exactly one key:
- impact_score: integer from 1 (little/no value for this lens) to 10 (strong official, data-rich,
  or clearly material NZ economy/market news).

Example: {"impact_score": 6}
No markdown, no other keys, no explanation."""

_TIER1_MACRO_GOAL = """[tier:macro] Perform deep-dive synthesis on high-impact knowledge item ID: {kid}

Contract:
- Treat this as a macro/hard-signal task (score 8-10).
- Ground claims in retrieved evidence from search_knowledge.
- Only use record_market_edge when concrete numeric/policy evidence exists.
- Also write record_synthesis with concise evidence-linked conclusions."""

_TIER2_LEAD_GOAL = """[tier:lead] Perform deep-dive synthesis on high-impact knowledge item ID: {kid}

Contract:
- Treat this as a qualitative lead task (score 6-7).
- Prioritize sector trends, supply/demand gaps, and business pain points.
- Default to record_synthesis.
- Do NOT use record_market_edge unless concrete numeric evidence is present in retrieved sources."""


def _build_user_block(item: dict[str, Any]) -> str:
    iid = int(item["id"])
    payload = item.get("payload")
    title = ""
    link = ""
    if isinstance(payload, dict):
        title = str(payload.get("title") or "").strip()
        link = str(payload.get("link") or "").strip()
    excerpt = str(item.get("content_excerpt") or "")
    if len(excerpt) > _MAX_EXCERPT_CHARS:
        excerpt = excerpt[:_MAX_EXCERPT_CHARS] + "…"
    lines = [f"knowledge_id: {iid}"]
    if title:
        lines.append(f"title: {title}")
    if link:
        lines.append(f"link: {link}")
    lines.append("")
    lines.append("excerpt:")
    lines.append(excerpt)
    return "\n".join(lines).strip()


def _parse_impact_score(data: dict[str, Any]) -> int | None:
    """Return validated 1–10 score or None."""
    v = data.get("impact_score")
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if 1 <= v <= 10 else None
    if isinstance(v, float):
        if v.is_integer():
            iv = int(v)
            return iv if 1 <= iv <= 10 else None
        return None
    if isinstance(v, str):
        try:
            iv = int(v.strip())
            return iv if 1 <= iv <= 10 else None
        except ValueError:
            return None
    return None


@dataclass
class TriageStats:
    processed: int = 0
    scored: int = 0
    skipped: int = 0
    deep_dives_enqueued: int = 0


def _today_key_local(prefix: str) -> str:
    return f"{prefix}.{datetime.now().date().isoformat()}"


async def run_triage_cli(
    settings: Settings,
    *,
    limit: int,
    client_cls: type = genai.Client,
) -> tuple[TriageStats, int]:
    """
    Score up to ``limit`` unscored knowledge rows. Returns (stats, exit_code).

    On JSON parse failure or invalid impact_score from the model: log a warning and **skip**
    that row (leave impact_score NULL; do not write partial state).
    """
    if not settings.gemini_api_key.strip():
        print("triage: GEMINI_API_KEY not set", file=sys.stderr)
        return TriageStats(), 2

    lim = max(1, min(limit, 500))
    settings.ensure_data_dir()
    schema_path = Path(ada.__path__[0]) / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    stats = TriageStats()
    try:
        rows = await qe.list_unscored_knowledge(limit=lim)
        stats.processed = len(rows)
        if not rows:
            return stats, 0

        client = client_cls(api_key=settings.gemini_api_key)
        model = settings.triage_model
        lead_cap = max(0, int(settings.triage_lead_daily_cap))
        trigger_min = max(1, min(10, int(settings.triage_deep_dive_min_score)))
        lead_day_key = _today_key_local("triage.lead_enqueued")
        raw_lead_count = await qe.state_get(lead_day_key)
        try:
            lead_count_today = int(raw_lead_count) if raw_lead_count is not None else 0
        except ValueError:
            lead_count_today = 0

        for item in rows:
            kid = int(item["id"])
            user_block = _build_user_block(item)
            try:
                resp = await client.aio.models.generate_content(
                    model=model,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=user_block)],
                        )
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=_TRIAGE_SYSTEM,
                        response_mime_type="application/json",
                        temperature=0.2,
                    ),
                )
                raw = (getattr(resp, "text", None) or "").strip()
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError("model JSON is not an object")
            except json.JSONDecodeError as e:
                # Skip: keep row unscored; do not call update_impact_score.
                log.warning(
                    "triage skip knowledge_id=%s: invalid JSON from model: %s",
                    kid,
                    e,
                )
                stats.skipped += 1
                continue
            except Exception as e:
                log.warning("triage skip knowledge_id=%s: %s", kid, e)
                stats.skipped += 1
                continue

            score = _parse_impact_score(data)
            if score is None:
                log.warning(
                    "triage skip knowledge_id=%s: missing or invalid impact_score in %s",
                    kid,
                    data,
                )
                stats.skipped += 1
                continue

            try:
                await qe.update_impact_score(kid, score)
            except Exception as e:
                log.warning("triage skip knowledge_id=%s: DB update failed: %s", kid, e)
                stats.skipped += 1
                continue

            stats.scored += 1
            if score >= 8 and score >= trigger_min:
                goal = _TIER1_MACRO_GOAL.format(kid=kid)
                task_id = await qe.insert_task(
                    goal, status="pending", task_kind=TASK_KIND_GOAL
                )
                await qe.set_task_plan_json(
                    task_id,
                    json.dumps(
                        {
                            "tier": "macro",
                            "knowledge_id": kid,
                            "impact_score": score,
                            "contract": "tiered_v1",
                        },
                        ensure_ascii=False,
                    ),
                )
                stats.deep_dives_enqueued += 1
            elif score >= 6 and score >= trigger_min:
                if lead_cap == 0 or lead_count_today >= lead_cap:
                    continue
                goal = _TIER2_LEAD_GOAL.format(kid=kid)
                task_id = await qe.insert_task(
                    goal, status="pending", task_kind=TASK_KIND_GOAL
                )
                await qe.set_task_plan_json(
                    task_id,
                    json.dumps(
                        {
                            "tier": "lead",
                            "knowledge_id": kid,
                            "impact_score": score,
                            "contract": "tiered_v1",
                        },
                        ensure_ascii=False,
                    ),
                )
                lead_count_today += 1
                await qe.state_set(lead_day_key, str(lead_count_today))
                stats.deep_dives_enqueued += 1

        return stats, 0
    finally:
        await qe.close()
