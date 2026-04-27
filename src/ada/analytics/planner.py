"""Deterministic GSC opportunity planning helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from ada.query_engine import QueryEngine


@dataclass(frozen=True)
class GSCPlanningWindow:
    site: str
    start_date: str
    end_date: str
    limit: int


def ranking_gap(avg_position: float) -> float:
    """Gap to top-5 rankings, clamped to [0, 14]."""
    p = max(1.0, float(avg_position))
    return max(0.0, min(14.0, p - 5.0))


def ctr_gap(ctr: float) -> float:
    """Gap to 12% CTR baseline, clamped to [0, 1]."""
    c = max(0.0, min(1.0, float(ctr)))
    return max(0.0, 0.12 - c)


def opportunity_score(*, impressions: float, avg_position: float, ctr: float) -> float:
    return float(impressions) * ranking_gap(avg_position) * ctr_gap(ctr)


def default_window(*, site: str, lookback_days: int, limit: int) -> GSCPlanningWindow:
    if lookback_days < 1:
        raise ValueError("lookback_days must be >= 1")
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=lookback_days - 1)
    return GSCPlanningWindow(
        site=site.strip(),
        start_date=start.isoformat(),
        end_date=today.isoformat(),
        limit=limit,
    )


def _dedupe_keep_order(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        s = str(v).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


async def build_gsc_campaign_plan_payload(
    qe: QueryEngine,
    *,
    campaign_goal: str,
    window: GSCPlanningWindow,
    max_items: int,
) -> dict[str, Any]:
    if not window.site:
        raise ValueError("site is required")
    if max_items < 1 or max_items > 200:
        raise ValueError("max_items must be between 1 and 200")
    top_queries = await qe.list_gsc_top_queries(
        site=window.site,
        start_date=window.start_date,
        end_date=window.end_date,
        limit=max_items,
    )
    quick_wins = await qe.list_gsc_quick_wins(
        site=window.site,
        start_date=window.start_date,
        end_date=window.end_date,
        limit=max_items,
    )
    content_gaps = await qe.list_gsc_content_gaps(
        site=window.site,
        start_date=window.start_date,
        end_date=window.end_date,
        limit=max_items,
    )
    page_fixes = await qe.list_gsc_page_fixes(
        site=window.site,
        start_date=window.start_date,
        end_date=window.end_date,
        limit=max_items,
    )

    opportunities: list[dict[str, Any]] = []
    for row in quick_wins:
        score = opportunity_score(
            impressions=float(row.get("impressions") or 0.0),
            avg_position=float(row.get("avg_position") or 0.0),
            ctr=float(row.get("ctr") or 0.0),
        )
        opportunities.append(
            {
                "query": str(row.get("query") or ""),
                "page": str(row.get("page") or ""),
                "issue": "quick_win_low_ctr_mid_rank",
                "suggested_action": "refresh title/meta and align content to search intent",
                "score": round(score, 6),
            }
        )
    for row in content_gaps:
        impressions = float(row.get("total_impressions") or 0.0)
        score = opportunity_score(impressions=impressions, avg_position=20.0, ctr=0.0)
        opportunities.append(
            {
                "query": str(row.get("query") or ""),
                "page": str(row.get("top_page") or ""),
                "issue": "content_gap_weak_page_match",
                "suggested_action": "create or split dedicated landing page for this query cluster",
                "score": round(score, 6),
            }
        )
    for row in page_fixes:
        score = opportunity_score(
            impressions=float(row.get("impressions") or 0.0),
            avg_position=float(row.get("avg_position") or 0.0),
            ctr=float(row.get("ctr") or 0.0),
        )
        opportunities.append(
            {
                "query": "",
                "page": str(row.get("page") or ""),
                "issue": "page_fix_high_impressions_low_ctr",
                "suggested_action": "rewrite SERP snippet elements and strengthen above-the-fold relevance",
                "score": round(score, 6),
            }
        )
    opportunities.sort(
        key=lambda x: (
            -float(x.get("score") or 0.0),
            str(x.get("query") or ""),
            str(x.get("page") or ""),
            str(x.get("issue") or ""),
        )
    )
    top_opportunities = opportunities[:max_items]
    proposed_pages = _dedupe_keep_order(
        [
            str(r.get("query") or "")
            for r in content_gaps[:max_items]
            if str(r.get("query") or "").strip()
        ]
    )
    proposed_updates = _dedupe_keep_order(
        [str(r.get("page") or "") for r in page_fixes[:max_items]]
        + [str(r.get("page") or "") for r in quick_wins[:max_items]]
    )
    priority_order = [
        f"{str(o.get('query') or '').strip()}::{str(o.get('page') or '').strip()}::{str(o.get('issue') or '').strip()}"
        for o in top_opportunities
    ]
    return {
        "campaign_goal": campaign_goal,
        "top_opportunities": top_opportunities,
        "proposed_pages": proposed_pages,
        "proposed_updates": proposed_updates,
        "priority_order": priority_order,
        "approval_status": "pending",
        "window": {
            "site": window.site,
            "start_date": window.start_date,
            "end_date": window.end_date,
            "max_items": max_items,
            "top_query_count": len(top_queries),
            "quick_win_count": len(quick_wins),
            "content_gap_count": len(content_gaps),
            "page_fix_count": len(page_fixes),
        },
    }
