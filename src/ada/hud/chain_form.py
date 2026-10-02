"""HUD control for one portfolio chain campaign.

Publish one page reads the whole business file, chooses the next unpublished
card in the card folders, opens up to three notes that teach that page,
stores the passages, and writes the search title from those passages. It
does not take a typed source list and it does not read a YAML question.
Repair and publish wakes the current campaign. It does not call the planner
and does not ask for a new title. The portfolio config is not created here.
Delete stays on the blog form.
"""

from __future__ import annotations

from typing import Any

from ada.io.paths import DataPaths, require_ada_data
from ada.memory.chain_plan import (
    _rewrite_stages,
    current_item,
    is_chain_loop,
    load_plan,
    open_chain_campaign,
    plan_one_page,
    plan_source_questions,
    read_published_pages,
    record_published_page,
    run_chain_wake,
    save_plan,
)
from ada.memory.chain_receipt import latest_receipt
from ada.memory.open_loops import get_loop, list_loops
from ada.memory.portfolio_chain import read_portfolio_chain

PAGE_STAGES = (
    "external-fetch",
    "gather",
    "gate",
    "draft",
    "librarian",
    "diagram",
    "critic",
    "deliver",
    "push",
)
_PREP = ("bind-site", "understand-aim")


def _deny(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "outcome": "denied",
        "denied_reason": reason,
        "error": reason,
        "result_line": reason,
    }


def _reason(result: dict[str, Any], receipt: dict[str, Any] | None) -> str:
    checks = result.get("checks") or (receipt or {}).get("checks") or []
    if checks:
        return ", ".join(str(item) for item in checks)
    return str(
        result.get("denied_reason")
        or result.get("error")
        or result.get("reason")
        or ""
    )


def _stage_state(loop: dict[str, Any], stage: str) -> str:
    for raw in loop.get("stages") or []:
        if str(raw.get("id") or "") == stage:
            return str(raw.get("state") or "")
    return ""


def _source_rows(sources: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in sources or []:
        if not isinstance(raw, dict):
            continue
        source = str(raw.get("source") or "").strip()
        fill = str(raw.get("fill") or "").strip()
        keyword = str(raw.get("keyword") or "").strip()
        if not source and not fill and not keyword:
            continue
        rows.append({"source": source, "fill": fill, "keyword": keyword})
    return rows


def _pushed_slugs(campaign_id: str, paths: DataPaths) -> set[str]:
    found: set[str] = set()
    receipt = latest_receipt(campaign_id, "push", outcome="ok", paths=paths)
    slug = str((receipt or {}).get("slug") or "")
    if slug:
        found.add(slug)
    return found


def _draft_path(
    campaign_id: str,
    paths: DataPaths,
    receipt: dict[str, Any] | None = None,
) -> str:
    if receipt and receipt.get("paths"):
        for item in receipt["paths"]:
            if str(item).endswith(".md"):
                return str(item)
    plan = load_plan(campaign_id, paths=paths)
    item = current_item(plan) if plan else None
    if item and item.get("draft_path"):
        return str(item["draft_path"])
    stored = latest_receipt(campaign_id, "draft", outcome="ok", paths=paths)
    if stored and stored.get("paths"):
        return str(stored["paths"][0])
    return ""


def _title_row(item: dict[str, Any], *, state: str) -> dict[str, str]:
    return {
        "question": str(item.get("question") or ""),
        "source": str(item.get("source") or ""),
        "fill": str(item.get("fill") or ""),
        "state": state,
    }


def _queue_rows(
    campaign_id: str,
    paths: DataPaths,
    *,
    started: bool,
) -> list[dict[str, str]]:
    plan = load_plan(campaign_id, paths=paths)
    queue = plan.get("queue") if isinstance(plan, dict) else None
    if not isinstance(queue, list):
        return []
    pushed = _pushed_slugs(campaign_id, paths)
    rows: list[dict[str, str]] = []
    for index, item in enumerate(queue):
        if not isinstance(item, dict):
            continue
        slug = str(item.get("slug") or "")
        if slug and slug in pushed:
            state = "published"
        elif started and index == 0:
            state = "stopped"
        else:
            state = "waiting"
        rows.append(_title_row(item, state=state))
    return rows


def _refusals(campaign_id: str, paths: DataPaths) -> list[dict[str, str]]:
    plan = load_plan(campaign_id, paths=paths)
    raw = plan.get("refusals") if isinstance(plan, dict) else None
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "question": str(item.get("question") or ""),
                "source": str(item.get("source") or ""),
                "reason": str(item.get("reason") or ""),
            }
        )
    return rows


def _view(
    campaign_id: str | None,
    *,
    paths: DataPaths,
    ok: bool,
    result_line: str,
    stages: list[dict[str, str]] | None = None,
    draft_path: str = "",
    published: list[dict[str, str]] | None = None,
    started: bool = False,
    outcome: str = "",
) -> dict[str, Any]:
    cid = campaign_id or ""
    body: dict[str, Any] = {
        "ok": ok,
        "outcome": outcome or ("ok" if ok else "denied"),
        "campaign_id": cid or None,
        "result_line": result_line,
        "draft_path": draft_path,
        "stages": stages or [],
        "queue": _queue_rows(cid, paths, started=started) if cid else [],
        "published": published or [],
        "refusals": _refusals(cid, paths) if cid else [],
    }
    if not ok:
        body["denied_reason"] = result_line
        body["error"] = result_line
    return body


def describe_chain(
    campaign_id: str | None = None,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Read the queue. Do not wake and do not create the config."""
    p = paths or require_ada_data()
    cid = (campaign_id or "").strip()
    if not cid:
        return _view(None, paths=p, ok=True, result_line="", outcome="ok")
    loop = get_loop(cid, paths=p)
    if not is_chain_loop(loop):
        return _deny("not a chain campaign")
    draft = _draft_path(cid, p)
    return _view(
        cid,
        paths=p,
        ok=True,
        result_line="",
        draft_path=draft,
        outcome="ok",
    )


def _require_config(paths: DataPaths) -> dict[str, Any] | None:
    config = read_portfolio_chain(paths=paths)
    if not config.get("ok"):
        return config
    aims = list(config["config"].get("aims") or [])
    if len(aims) != 1:
        return _deny("the config aim is not a single copied aim")
    return None


def _merge_refusals(
    campaign_id: str,
    extra: list[dict[str, str]],
    paths: DataPaths,
) -> None:
    if not extra:
        return
    plan = load_plan(campaign_id, paths=paths)
    if not isinstance(plan, dict):
        return
    current = [row for row in (plan.get("refusals") or []) if isinstance(row, dict)]
    plan["refusals"] = current + extra
    save_plan(plan, paths=paths)


def queue_chain_sources(
    sources: list[dict[str, Any]] | None,
    *,
    paths: DataPaths | None = None,
    model: Any | None = None,
) -> dict[str, Any]:
    """Bind, understand the aim, and plan one reader question per source."""
    p = paths or require_ada_data()
    blocked = _require_config(p)
    if blocked:
        blocked = dict(blocked)
        blocked["result_line"] = str(
            blocked.get("denied_reason") or blocked.get("error") or "Refused."
        )
        blocked.setdefault("queue", [])
        blocked.setdefault("refusals", [])
        blocked.setdefault("stages", [])
        blocked.setdefault("published", [])
        blocked.setdefault("draft_path", "")
        return blocked
    config = read_portfolio_chain(paths=p)
    cfg = config["config"]
    planned = plan_source_questions(
        _source_rows(sources),
        audience=str(cfg.get("audience") or ""),
        aim=str((cfg.get("aims") or [""])[0]),
        model=model,
    )
    opened = open_chain_campaign(paths=p)
    if not opened.get("ok"):
        return opened
    cid = str(opened.get("id") or "")
    stages: list[dict[str, str]] = []
    for stage in _PREP:
        result = run_chain_wake(cid, paths=p)
        receipt = latest_receipt(cid, stage, paths=p)
        outcome = str((receipt or {}).get("outcome") or result.get("outcome") or "")
        reason = "" if result.get("ok") else _reason(result, receipt)
        stages.append({"stage": stage, "outcome": outcome, "draft_path": "", "reason": reason})
        if not result.get("ok") or outcome in {"denied", "fail"}:
            line = f"{stage} {outcome}. {reason}".strip()
            return _view(cid, paths=p, ok=False, result_line=line, stages=stages, outcome=outcome)
    result = run_chain_wake(
        cid,
        items=list(planned.get("items") or []),
        suggestions=list(planned.get("suggestions") or []),
        paths=p,
    )
    _merge_refusals(cid, list(planned.get("refusals") or []), p)
    receipt = latest_receipt(cid, "plan", paths=p)
    outcome = str((receipt or {}).get("outcome") or result.get("outcome") or "")
    reason = "" if result.get("ok") else _reason(result, receipt)
    stages.append({"stage": "plan", "outcome": outcome, "draft_path": "", "reason": reason})
    if not result.get("ok") or outcome in {"denied", "fail"}:
        line = f"plan {outcome}. {reason}".strip()
        return _view(cid, paths=p, ok=False, result_line=line, stages=stages, outcome=outcome)
    queued = _queue_rows(cid, paths=p, started=False)
    if queued:
        line = f"Queued {len(queued)} sources."
    else:
        line = "No queued source."
    return _view(cid, paths=p, ok=True, result_line=line, stages=stages, outcome="ok")


def _current_chain_id(paths: DataPaths) -> str:
    """The latest chain campaign that is still running. Does not open one."""
    loops = list_loops(paths=paths, kind="campaign")
    chains = [
        loop
        for loop in loops
        if is_chain_loop(loop) and loop.get("status") not in {"done", "failed"}
    ]
    chains.sort(key=lambda loop: str(loop.get("updated_at") or ""), reverse=True)
    if not chains:
        return ""
    return str(chains[0].get("id") or "")


def repair_and_publish(
    campaign_id: str | None = None,
    *,
    paths: DataPaths | None = None,
) -> dict[str, Any]:
    """Wake this campaign from its current stage through push.

    Does not open a campaign, does not call the planner, and does not ask
    for a new title.
    """
    p = paths or require_ada_data()
    cid = (campaign_id or "").strip() or _current_chain_id(p)
    if not cid:
        return _deny("campaign_id required")
    return make_one_chain_page(cid, paths=p, model=None)


def publish_one_page(
    *,
    paths: DataPaths | None = None,
    model: Any | None = None,
    draft_model: Any | None = None,
) -> dict[str, Any]:
    """Choose the next unpublished card, publish that page, then stop.

    The plan lists the markdown cards in the card folders, skips a card
    already recorded, and chooses one remaining card that has a passage.
    ``model`` picks up to three notes that teach it and writes the title
    after those passages are stored. With no model, the title is one
    sentence already in the passages. A YAML question is not read. The
    draft model writes the page. Sends no source list, does not append a
    fact, and does not edit the operator file. One page.
    """
    p = paths or require_ada_data()
    blocked = _require_config(p)
    if blocked:
        blocked = dict(blocked)
        blocked["result_line"] = str(
            blocked.get("denied_reason") or blocked.get("error") or "Refused."
        )
        blocked.setdefault("queue", [])
        blocked.setdefault("refusals", [])
        blocked.setdefault("stages", [])
        blocked.setdefault("published", [])
        blocked.setdefault("draft_path", "")
        return blocked
    config = read_portfolio_chain(paths=p)
    opened = open_chain_campaign(paths=p)
    if not opened.get("ok"):
        return opened
    cid = str(opened.get("id") or "")
    stages: list[dict[str, str]] = []
    for stage in _PREP:
        result = run_chain_wake(cid, paths=p)
        receipt = latest_receipt(cid, stage, paths=p)
        outcome = str((receipt or {}).get("outcome") or result.get("outcome") or "")
        reason = "" if result.get("ok") else _reason(result, receipt)
        stages.append({"stage": stage, "outcome": outcome, "draft_path": "", "reason": reason})
        if not result.get("ok") or outcome in {"denied", "fail"}:
            line = f"{stage} {outcome}. {reason}".strip()
            return _view(cid, paths=p, ok=False, result_line=line, stages=stages, outcome=outcome)
    cfg = config["config"]
    prepared = plan_one_page(
        cfg,
        model=model,
        published=read_published_pages(paths=p),
    )
    _merge_refusals(cid, list(prepared.get("refusals") or []), p)
    if not prepared.get("ok") or not prepared.get("items"):
        line = str(prepared.get("deny") or "No card.")
        return _view(cid, paths=p, ok=False, result_line=line, stages=stages, outcome="denied")
    result = run_chain_wake(cid, items=list(prepared.get("items") or []), paths=p)
    receipt = latest_receipt(cid, "plan", paths=p)
    outcome = str((receipt or {}).get("outcome") or result.get("outcome") or "")
    reason = "" if result.get("ok") else _reason(result, receipt)
    stages.append({"stage": "plan", "outcome": outcome, "draft_path": "", "reason": reason})
    if not result.get("ok") or outcome in {"denied", "fail"}:
        line = f"plan {outcome}. {reason}".strip()
        return _view(cid, paths=p, ok=False, result_line=line, stages=stages, outcome=outcome)
    queued = _queue_rows(cid, paths=p, started=False)
    if not queued:
        return _view(
            cid,
            paths=p,
            ok=True,
            result_line="No card.",
            stages=stages,
            outcome="ok",
        )
    made = make_one_chain_page(cid, paths=p, model=draft_model if draft_model is not None else model)
    made["stages"] = stages + list(made.get("stages") or [])
    if made.get("queue") is None:
        made["queue"] = []
    return made


def _release_next(campaign_id: str, paths: DataPaths) -> dict[str, str] | None:
    """Drop the published title off the queue. Do not wake the next one."""
    plan = load_plan(campaign_id, paths=paths)
    if not isinstance(plan, dict):
        return None
    queue = plan.get("queue")
    if not isinstance(queue, list) or not queue or not isinstance(queue[0], dict):
        return None
    finished = _title_row(queue[0], state="published")
    record_published_page(
        str(queue[0].get("card") or queue[0].get("source") or ""),
        paths=paths,
    )
    if len(queue) == 1:
        return finished
    plan["queue"] = queue[1:]
    save_plan(plan, paths=paths)
    _rewrite_stages(
        campaign_id,
        paths=paths,
        current="external-fetch",
        done={"bind-site", "understand-aim", "plan"},
        pending=set(PAGE_STAGES),
        active="external-fetch",
        status="active",
    )
    return finished


def make_one_chain_page(
    campaign_id: str | None,
    *,
    paths: DataPaths | None = None,
    model: Any | None = None,
) -> dict[str, Any]:
    """Run the next queued title through push, then stop."""
    p = paths or require_ada_data()
    cid = (campaign_id or "").strip()
    if not cid:
        return _deny("campaign_id required")
    loop = get_loop(cid, paths=p)
    if not is_chain_loop(loop):
        return _deny("not a chain campaign")
    stages: list[dict[str, str]] = []
    draft_path = ""
    for _ in PAGE_STAGES:
        loop = get_loop(cid, paths=p) or {}
        stage = str(loop.get("current_stage") or "")
        if stage not in PAGE_STAGES:
            return _view(
                cid,
                paths=p,
                ok=False,
                result_line="Save the list before making a page.",
                stages=stages,
                draft_path=draft_path,
                started=bool(stages),
            )
        if _stage_state(loop, stage) == "done":
            waiting = [
                row
                for row in _queue_rows(cid, p, started=False)
                if row["state"] == "waiting"
            ]
            line = (
                "The next title is still waiting."
                if waiting
                else "No queued title."
            )
            return _view(
                cid,
                paths=p,
                ok=True,
                result_line=line,
                stages=stages,
                draft_path=draft_path,
                outcome="ok",
            )
        before = stage
        result = run_chain_wake(cid, paths=p, model=model)
        receipt = latest_receipt(cid, before, paths=p)
        outcome = str((receipt or {}).get("outcome") or result.get("outcome") or "")
        if before == "draft" or (receipt and receipt.get("paths")):
            found = _draft_path(cid, p, receipt if before == "draft" else None)
            if found:
                draft_path = found
        reason = "" if result.get("ok") and outcome not in {"denied", "fail"} else _reason(result, receipt)
        stages.append(
            {
                "stage": before,
                "outcome": outcome,
                "draft_path": draft_path if before == "draft" else "",
                "reason": reason,
            }
        )
        if not result.get("ok") or outcome in {"denied", "fail"}:
            line = f"{before} {outcome}. {reason}".strip()
            return _view(
                cid,
                paths=p,
                ok=False,
                result_line=line,
                stages=stages,
                draft_path=draft_path,
                started=True,
                outcome=outcome or "denied",
            )
        if before == "push":
            finished = _release_next(cid, p)
            published = [finished] if finished else []
            if draft_path:
                line = f"Published one page. Draft is {draft_path}."
            else:
                line = "Published one page."
            loop_after = get_loop(cid, paths=p) or {}
            if loop_after.get("status") == "done":
                return _deny("refusing to mark the campaign done")
            return _view(
                cid,
                paths=p,
                ok=True,
                result_line=line,
                stages=stages,
                draft_path=draft_path,
                published=published,
                outcome="ok",
            )
        loop_after = get_loop(cid, paths=p) or {}
        if str(loop_after.get("current_stage") or "") == before and before != "push":
            return _view(
                cid,
                paths=p,
                ok=False,
                result_line=f"{before} did not advance.",
                stages=stages,
                draft_path=draft_path,
                started=True,
            )
    return _view(
        cid,
        paths=p,
        ok=False,
        result_line="The page did not reach push.",
        stages=stages,
        draft_path=draft_path,
        started=True,
    )
