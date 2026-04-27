"""`ada triage`: LLM scores unscored knowledge_items for NZ-relevant news value (1–10) + taxonomy."""

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
from ada.profile_runtime import enforce_profile_identity
from ada.query_engine import TASK_KIND_GOAL, QueryEngine
from ada.triage.categories import parse_triage_response
from ada.triage.enqueue import tier1_macro_eligible, tier2_lead_eligible

log = logging.getLogger("ada.triage")

_MAX_EXCERPT_CHARS = 12_000

_TRIAGE_SYSTEM = """You classify a short news or article snippet for someone following
New Zealand’s economy, policy, markets, and business — not only sharp price moves.

Use only the title, link line, and excerpt — do not invent facts.

What deserves a HIGHER impact_score (1–10) when the excerpt supports it:
- Official or authoritative material: government, regulators, RBNZ, Stats NZ, ministers,
  agencies, courts, listed companies’ announcements, credible economic data or surveys.
- Policy and rules: laws, consultations, standards, funding programmes, grants, budgets,
  immigration or workforce settings when policy-linked, climate/energy transition when NZ-relevant.
- Ordinary business and sector developments: industry trends, trade, infrastructure projects,
  procurement, company news (listings, M&A, appointments) when substantively about the economy.
- Concrete signals when present: rates, FX, indices, forecasts, employment, inflation, housing,
  trade figures, dollar amounts, dates of effect — but also value surveys, stats releases, and
  project announcements that are not necessarily “market moves.”

What deserves a LOWER score:
- Lifestyle fluff, gossip, or vague commentary with no real economy/policy/business hook
  in the text you see.

Choose exactly one primary_category from the fixed list below, plus 0–2 secondary_categories
(distinct from primary, all from the same list):

policy_regulation — laws, rules, consultations, RMA, standards, regulator guidance
government_fiscal — budget, tax, grants programmes, agency funding envelopes
markets_macro — rates, FX, indices, forecasts, RBNZ, hard economic data
data_surveys_stats — Stats NZ, surveys, statistical releases (not necessarily market moves)
trade_industry — trade deals, tariffs, industry bodies, sector-level trade
sector_business — industry/company operational news, sector trends (qualitative)
infrastructure_projects — major projects, procurement, tenders, capex programmes
climate_energy — climate policy, energy markets, transition (NZ-relevant)
labour_workforce — immigration settings, workforce, wages when policy-linked
company_corporate — listings, M&A, earnings, appointments when excerpt supports
consumer_retail — B2C-facing changes only when clearly economy-relevant (not lifestyle fluff)
international_spillover — offshore events with a clear NZ channel in the text

Return JSON only with exactly these keys:
- impact_score: integer 1–10
- primary_category: one string from the list above
- secondary_categories: array of 0–2 strings from the same list (omit duplicates; do not repeat primary)

Example:
{"impact_score": 6, "primary_category": "data_surveys_stats", "secondary_categories": ["markets_macro"]}

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
    backfill_categories: bool = False,
) -> tuple[TriageStats, int]:
    """
    Score up to ``limit`` knowledge rows (unscored by default, or backfill categories).

    On JSON parse failure or invalid fields from the model: log a warning and **skip**
    that row (leave prior state unchanged; no partial writes).
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
    await enforce_profile_identity(qe, settings)
    stats = TriageStats()
    try:
        if backfill_categories:
            rows = await qe.list_backfill_triage_categories(limit=lim)
        else:
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

            parsed = parse_triage_response(data)
            if parsed is None:
                log.warning(
                    "triage skip knowledge_id=%s: invalid triage fields in %s",
                    kid,
                    data,
                )
                stats.skipped += 1
                continue

            if backfill_categories and item.get("impact_score") is not None:
                score_for_row = int(item["impact_score"])
            else:
                score_for_row = parsed.impact_score

            try:
                await qe.update_triage_result(
                    kid,
                    impact_score=score_for_row,
                    primary_category=parsed.primary_category,
                    secondary_categories=list(parsed.secondary_categories),
                )
            except Exception as e:
                log.warning("triage skip knowledge_id=%s: DB update failed: %s", kid, e)
                stats.skipped += 1
                continue

            stats.scored += 1
            score = score_for_row
            primary = parsed.primary_category

            if tier1_macro_eligible(
                impact_score=score,
                primary_category=primary,
                trigger_min=trigger_min,
            ):
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
                            "primary_category": primary,
                            "secondary_categories": list(parsed.secondary_categories),
                            "contract": "tiered_v1",
                        },
                        ensure_ascii=False,
                    ),
                )
                stats.deep_dives_enqueued += 1
            elif tier2_lead_eligible(
                impact_score=score,
                trigger_min=trigger_min,
            ):
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
                            "primary_category": primary,
                            "secondary_categories": list(parsed.secondary_categories),
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
