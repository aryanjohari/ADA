"""Single ChatSession owner for the HUD process — calls harness.run_turn only."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable

from ada.cortex.adapter import CortexAdapter
from ada.cortex.charter import build_system_charter
from ada.cortex.gemini import GeminiAdapter
from ada.cortex.models import resolve_model
from ada.harness.loop import LoopResult, run_turn
from ada.harness.pack_router import resolve_chip, route_utterance
from ada.harness.plan_artifact import new_plan_id
from ada.harness.session import ChatSession, Mode
from ada.harness.stream_events import StreamSink
from ada.secrets.load import MissingSecret, load_gemini_api_key


AdapterFactory = Callable[[], CortexAdapter]

_PLAN_AGENT = frozenset({"plan", "agent"})


def _resolve_row_key(row: dict[str, Any]) -> str:
    return str(row.get("query_norm") or row.get("query") or "").strip()


def _meal_line_key(line: dict[str, Any]) -> str:
    return str(line.get("_query_norm") or line.get("_query") or "").strip()


def _meal_candidate_pool(
    resolve: dict[str, Any], row: dict[str, Any]
) -> list[dict[str, Any]]:
    pool: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cand in list(row.get("candidates") or []) + list(resolve.get("candidates") or []):
        if not isinstance(cand, dict):
            continue
        ref = str(cand.get("ref_id") or "").strip()
        if ref and ref not in seen:
            seen.add(ref)
            pool.append(cand)
    return pool


def _meal_candidate_by_ref(
    pool: list[dict[str, Any]], ref_id: str
) -> dict[str, Any] | None:
    for cand in pool:
        if str(cand.get("ref_id") or "") == ref_id:
            return cand
    return None


def _preview_per_100g(cand: dict[str, Any]) -> dict[str, Any] | None:
    """Per-100g CORE from Confirm picker preview (nutrients or kcal_per_100g)."""
    nutrients = cand.get("nutrients")
    if isinstance(nutrients, dict) and any(v is not None for v in nutrients.values()):
        return dict(nutrients)
    raw = cand.get("nutrients_per_100g")
    if isinstance(raw, dict) and any(v is not None for v in raw.values()):
        return dict(raw)
    kcal = cand.get("kcal_per_100g")
    if kcal is not None:
        return {
            "energy_kcal": kcal,
            "protein_g": None,
            "fat_g": None,
            "carb_g": None,
        }
    return None


def _scale_preview_nutrients(
    per_100g: dict[str, Any], grams: float | None
) -> dict[str, float | None]:
    nutrients: dict[str, float | None] = {}
    factor = (grams / 100.0) if grams not in (None, 0) else 1.0
    for key, value in per_100g.items():
        if value is None:
            nutrients[key] = None
            continue
        try:
            nutrients[key] = round(float(value) * factor, 3)
        except (TypeError, ValueError):
            nutrients[key] = None
    return nutrients


def _scale_preview_to_line(
    line: dict[str, Any], per_100g: dict[str, Any]
) -> dict[str, Any]:
    """Scale preview per-100g macros onto a meal line (serving_grams aware)."""
    serving_grams = line.get("serving_grams")
    if serving_grams is None:
        qty = float(line.get("serving_qty") or 1.0)
        unit = str(line.get("serving_unit") or "serving").lower()
        if unit in {"g", "gram", "grams", "ml"}:
            serving_grams = qty
    nutrients = _scale_preview_nutrients(per_100g, serving_grams)
    out = dict(line)
    out["nutrients"] = nutrients
    snap = (
        dict(out.get("snapshot_json") or {})
        if isinstance(out.get("snapshot_json"), dict)
        else {}
    )
    snap.setdefault("schema_version", 1)
    snap["nutrients"] = nutrients
    src = (
        dict(snap.get("source") or {})
        if isinstance(snap.get("source"), dict)
        else {}
    )
    src.setdefault("provider", "confirm_preview")
    snap["source"] = src
    out["snapshot_json"] = snap
    return out


def _habit_candidate_ids(args: dict[str, Any]) -> set[str]:
    cands = list(args.get("candidates") or [])
    resolve = args.get("resolve") if isinstance(args.get("resolve"), dict) else {}
    if not cands:
        cands = list(resolve.get("candidates") or [])
    ids: set[str] = set()
    for cand in cands:
        if not isinstance(cand, dict):
            continue
        hid = str(cand.get("habit_id") or cand.get("ref_id") or "").strip()
        if hid:
            ids.add(hid)
    return ids


def _people_candidate_ids(args: dict[str, Any]) -> set[str]:
    cands = list(args.get("candidates") or [])
    resolve = args.get("resolve") if isinstance(args.get("resolve"), dict) else {}
    if not cands:
        cands = list(resolve.get("candidates") or [])
    ids: set[str] = set()
    for cand in cands:
        if not isinstance(cand, dict):
            continue
        pid = str(cand.get("person_id") or cand.get("ref_id") or "").strip()
        if pid:
            ids.add(pid)
    return ids


def _patch_habit_confirm_selection(
    args: dict[str, Any],
    selected_ref_ids: dict[str, str] | None,
    selected_ref_id: str | None = None,
) -> dict[str, Any]:
    """Apply operator habit pick to stashed tick args (Consent Integrity).

    HACK / invented habit_id from the client is ignored. Only ids in the
    Confirm candidate pool bind.
    """
    pool = _habit_candidate_ids(args)
    picked = (selected_ref_id or "").strip() or None
    if selected_ref_ids:
        for value in selected_ref_ids.values():
            token = str(value or "").strip()
            if token and token in pool:
                picked = token
                break
    if not picked:
        return args
    if picked not in pool:
        raise ValueError(f"invalid habit selection {picked!r}")
    merged = dict(args)
    merged["habit_id"] = picked
    resolve = merged.get("resolve")
    if isinstance(resolve, dict):
        resolve_copy = dict(resolve)
        resolve_copy["proposed_habit_id"] = picked
        merged["resolve"] = resolve_copy
    return merged


def _patch_people_confirm_selection(
    args: dict[str, Any],
    selected_ref_ids: dict[str, str] | None,
    selected_ref_id: str | None = None,
) -> dict[str, Any]:
    """Apply operator person pick to stashed capture/note/alias args.

    HACK / invented person_id from the client is ignored. Only ids in the
    Confirm candidate pool bind.
    """
    pool = _people_candidate_ids(args)
    picked = (selected_ref_id or "").strip() or None
    if selected_ref_ids:
        for value in selected_ref_ids.values():
            token = str(value or "").strip()
            if not token:
                continue
            if token not in pool:
                raise ValueError(f"invalid person selection {token!r}")
            picked = token
            break
    if picked and picked not in pool:
        raise ValueError(f"invalid person selection {picked!r}")
    if not picked:
        return args
    merged = dict(args)
    merged["person_id"] = picked
    resolve = merged.get("resolve")
    if isinstance(resolve, dict):
        resolve_copy = dict(resolve)
        resolve_copy["proposed_person_id"] = picked
        merged["resolve"] = resolve_copy
    return merged


def _patch_meal_confirm_selection(
    args: dict[str, Any],
    selected_ref_ids: dict[str, str] | None,
) -> dict[str, Any]:
    """Apply operator food picks to stashed meal_log args (Consent Integrity).

    Copies preview macros into the line when present so Confirm Yes does not
    rely solely on a later DB rehydrate (null-CORE cache miss → empty_macros).
    """
    resolve = args.get("resolve")
    if not isinstance(resolve, dict):
        return args

    rows = list(resolve.get("rows") or [])
    if not rows:
        return args

    merged = dict(args)
    lines = [
        dict(ln) if isinstance(ln, dict) else ln for ln in list(merged.get("lines") or [])
    ]
    resolve_copy = dict(resolve)
    resolve_rows = [dict(r) if isinstance(r, dict) else r for r in rows]

    if len(resolve_rows) == 1 and not resolve_copy.get("candidates"):
        only = resolve_rows[0]
        if isinstance(only, dict) and only.get("candidates"):
            resolve_copy["candidates"] = list(only.get("candidates") or [])

    for row in resolve_rows:
        if not isinstance(row, dict):
            continue
        key = _resolve_row_key(row)
        pool = _meal_candidate_pool(resolve_copy, row)
        proposed = str(row.get("proposed_ref_id") or "").strip()
        ref_id = proposed
        if selected_ref_ids:
            picked = None
            if key:
                picked = selected_ref_ids.get(key)
            if picked is None:
                picked = selected_ref_ids.get(str(row.get("query") or ""))
            if picked is not None:
                ref_id = str(picked).strip()
                if not ref_id or not _meal_candidate_by_ref(pool, ref_id):
                    raise ValueError(f"invalid meal selection for {key!r}")

        if not ref_id:
            continue

        row["proposed_ref_id"] = ref_id
        cand = _meal_candidate_by_ref(pool, ref_id) or {}
        label = str(cand.get("label") or cand.get("name") or "").strip()
        preview_macros = _preview_per_100g(cand)

        for i, line in enumerate(lines):
            if not isinstance(line, dict):
                continue
            lk = _meal_line_key(line)
            if lk == key or (not lk and len(resolve_rows) == 1):
                line["ref_id"] = ref_id
                if label:
                    line["display_name"] = label
                if preview_macros is not None:
                    line = _scale_preview_to_line(line, preview_macros)
                else:
                    # No preview macros — clear so DB enrich is the sole source.
                    line.pop("nutrients", None)
                    line.pop("snapshot_json", None)
                lines[i] = line
                break

    merged["lines"] = lines
    resolve_copy["rows"] = resolve_rows
    merged["resolve"] = resolve_copy
    return merged


class ChatService:
    """One interactive writer assumption (v1): do not also run `ada chat` on same JSONL."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.session: ChatSession | None = None
        self.adapter: CortexAdapter | None = None
        self.history: list[Any] = []
        self.last_denials: list[dict[str, Any]] = []
        self.mode: Mode = "observe"
        # Tests inject a fake cortex via this hook.
        self.adapter_factory: AdapterFactory | None = None
        self._no_key_message: str | None = None
        self.last_plan: dict[str, Any] | None = None
        # Consent Integrity: receipt_id → {tool, args} for pending confirms.
        self.pending_confirms: dict[str, dict[str, Any]] = {}

    def current_mode(self) -> Mode:
        if self.session is not None:
            return self.session.mode
        return self.mode

    def run_path(self) -> Path | None:
        if self.session is None:
            return None
        return self.session.run_path

    def _ensure_session(self, mode: Mode) -> None:
        if self.session is not None and self.session.mode == mode:
            return
        prev = self.session.mode if self.session is not None else None
        preserve = (
            prev is not None
            and prev in _PLAN_AGENT
            and mode in _PLAN_AGENT
        )
        # Mode change: end previous session cleanly.
        if self.session is not None and self.session._started:
            self.session.end(stop_reason="mode_switch")
        if not preserve:
            self.history = []
        self.mode = mode
        model = resolve_model("chat_interactive")
        self.session = ChatSession(mode=mode, model=model)
        if self.adapter_factory is not None:
            self.adapter = self.adapter_factory()
            self._no_key_message = None
            return
        try:
            api_key = load_gemini_api_key()
        except MissingSecret as exc:
            self.adapter = None
            self._no_key_message = exc.message
            return
        self.adapter = GeminiAdapter(api_key, model=model)
        self._no_key_message = None

    def run_user_turn(
        self,
        user_text: str,
        *,
        mode: Mode = "observe",
        sink: StreamSink | None = None,
        chip: str | None = None,
        input_kind: str | None = None,
        face: str | None = None,
        device_id: str | None = None,
        device_name: str | None = None,
        tailscale_user: str | None = None,
    ) -> dict[str, Any]:
        """Synchronous turn — intended to run off the ASGI event loop thread."""
        with self._lock:
            self._ensure_session(mode)
            assert self.session is not None

            if self.adapter is None:
                self.session.ensure_started()
                self.session.writer.append(
                    "fault",
                    {"error": "no_key", "detail": self._no_key_message or "missing"},
                )
                if sink is not None:
                    sink.emit("mode_info", {"mode": self.session.mode})
                    sink.emit(
                        "session_receipt_path",
                        {"path": str(self.session.run_path)},
                    )
                    sink.emit(
                        "fault",
                        {
                            "error": "no_key",
                            "message": self._no_key_message or "GEMINI_API_KEY missing",
                        },
                    )
                self.session.end(stop_reason="no_key")
                path = str(self.session.run_path)
                # Reset so next attempt can retry key load.
                self.session = None
                self.adapter = None
                return {
                    "stop_reason": "no_key",
                    "text": None,
                    "steps": 0,
                    "run_path": path,
                    "plan": None,
                }

            hint = resolve_chip(chip) if chip else None
            if hint is None:
                hint = route_utterance(user_text)
            self.session.pack_hint = hint
            system = build_system_charter(
                mode=mode,
                chill_active=self.session.chill_active,
                pack_hint=hint,
            )
            result: LoopResult = run_turn(
                self.session,
                user_text,
                self.adapter,
                system=system,
                sink=sink,
                contents=self.history,
                end_session=False,
                input_kind=input_kind,
                face=face,
                device_id=device_id,
                device_name=device_name,
                tailscale_user=tailscale_user,
            )
            for receipt in result.tool_receipts:
                if receipt.get("outcome") == "denied" or receipt.get("denied_reason"):
                    self.last_denials.append(
                        {
                            "tool": receipt.get("tool"),
                            "args": receipt.get("args"),
                            "denied_reason": receipt.get("denied_reason"),
                            "receipt_id": receipt.get("receipt_id"),
                        }
                    )
                if receipt.get("needs_confirm") or receipt.get("outcome") == "needs_confirm":
                    rid = str(receipt.get("receipt_id") or "")
                    if rid:
                        self.pending_confirms[rid] = {
                            "tool": receipt.get("tool"),
                            "args": dict(receipt.get("args") or {}),
                        }
            if result.plan is not None:
                self.last_plan = result.plan
            out: dict[str, Any] = {
                "stop_reason": result.stop_reason,
                "text": result.text,
                "steps": result.steps,
                "run_path": result.run_path,
            }
            if result.plan is not None:
                out["plan"] = result.plan
            return out

    def accept_plan(
        self,
        *,
        steps: list[dict[str, Any]],
        plan_id: str | None = None,
        raw_text: str | None = None,
        campaign_id: str | None = None,
    ) -> dict[str, Any]:
        """Materialize plan steps as open_loops kind:todo (no cortex, no write tools)."""
        from ada.memory.open_loops import get_loop, upsert_loop

        with self._lock:
            pid = (plan_id or "").strip() or new_plan_id()
            cid = (campaign_id or "").strip() or None
            todos: list[dict[str, str]] = []
            for step in steps:
                text = str(
                    step.get("text") if isinstance(step, dict) else step or ""
                ).strip()
                if not text:
                    continue
                due_at = None
                remind_at = None
                if isinstance(step, dict):
                    if step.get("due_at"):
                        due_at = str(step.get("due_at")).strip() or None
                    if step.get("remind_at"):
                        remind_at = str(step.get("remind_at")).strip() or None
                result = upsert_loop(
                    text=text,
                    kind="todo",
                    status="open",
                    due_at=due_at,
                    remind_at=remind_at,
                    plan_id=pid,
                    campaign_id=cid,
                )
                loop = result.get("loop") if isinstance(result.get("loop"), dict) else {}
                loop_id = str(loop.get("id") or result.get("id") or "")
                todos.append({"id": loop_id, "text": text})

            if cid:
                camp = get_loop(cid)
                if camp and camp.get("kind") == "campaign":
                    upsert_loop(loop_id=cid, plan_id=pid)

            if self.last_plan and (
                not plan_id or self.last_plan.get("plan_id") == plan_id
            ):
                self.last_plan = dict(self.last_plan)
                self.last_plan["status"] = "accepted"

            if self.session is not None:
                self.session.ensure_started()
                self.session.writer.append(
                    "plan_accepted",
                    {
                        "plan_id": pid,
                        "campaign_id": cid,
                        "todos": todos,
                        "count": len(todos),
                        "raw_text": raw_text,
                    },
                )

            return {
                "plan_id": pid,
                "campaign_id": cid,
                "todos": todos,
                "count": len(todos),
            }

    def confirm_tool(
        self,
        tool: str,
        args: dict[str, Any],
        *,
        pending_id: str | None = None,
        selected_ref_ids: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Operator confirm — gateway execute with confirmed=true (no model)."""
        from ada.tools.gateway import Gateway

        with self._lock:
            stashed = False
            client_selected_ref_id = None
            if isinstance(args, dict):
                raw_sel = args.get("selected_ref_id")
                if raw_sel:
                    client_selected_ref_id = str(raw_sel).strip() or None
            if pending_id:
                pending = self.pending_confirms.get(pending_id)
                if pending is None:
                    raise ValueError(f"unknown pending_id {pending_id!r}")
                if pending.get("tool") != tool:
                    raise ValueError(
                        f"pending_id tool mismatch: expected {pending.get('tool')!r}"
                    )
                # Bind to stashed args (Consent Integrity) — ignore client rewrite.
                args = dict(pending.get("args") or {})
                stashed = True

            self._ensure_session("agent")
            assert self.session is not None
            self.session.ensure_started()
            merged = dict(args or {})
            if (
                stashed
                and tool in {"life_meal_log", "life_meal_draft_add", "life_meal_preset_log"}
                and isinstance(merged.get("resolve"), dict)
            ):
                merged = _patch_meal_confirm_selection(merged, selected_ref_ids)
            if stashed and tool in {"life_habit_do", "life_habit_miss"}:
                merged = _patch_habit_confirm_selection(
                    merged,
                    selected_ref_ids,
                    selected_ref_id=client_selected_ref_id,
                )
            if stashed and tool in {
                "life_person_capture",
                "life_person_note",
                "life_alias_set",
            }:
                merged = _patch_people_confirm_selection(
                    merged,
                    selected_ref_ids,
                    selected_ref_id=client_selected_ref_id,
                )
            # Draft tools need the HUD session id if missing from stash.
            if tool.startswith("life_meal_draft_") and not merged.get("session_id"):
                merged["session_id"] = self.session.session_id
            merged["confirmed"] = True
            gateway = Gateway(mode="agent", turn_user_text="[hud confirm]")
            result = gateway.execute(tool, merged)
            obs = result.as_observation()
            if pending_id:
                self.pending_confirms.pop(pending_id, None)
            if result.outcome == "denied":
                self.session.writer.append("tool_denied", obs)
                self.last_denials.append(
                    {
                        "tool": obs.get("tool"),
                        "args": obs.get("args"),
                        "denied_reason": obs.get("denied_reason"),
                        "receipt_id": obs.get("receipt_id"),
                    }
                )
            else:
                self.session.writer.append("tool_result", obs)
            return obs
