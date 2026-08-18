"""Tool gateway: schema validate → mode allowlist → execute → receipt.

Consent Integrity: denials and confirms render gateway {tool, args}, never
model prose alone (M02 §6.2). ToolSpec drives side_effect / egress (M07).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from ada.body.vitals import utc_now_iso
from ada.io.paths import BodyFault
from ada.runs.append import new_receipt_id
from ada.tools import artifact_tools, body_tools, life_tools, memory_tools, web_tools
from ada.tools.schemas import TOOL_NAMES, WRITE_TOOL_NAMES, spec_for

Mode = Literal["observe", "agent", "plan"]


@dataclass
class GatewayResult:
    ok: bool
    tool: str
    args: dict[str, Any]
    receipt_id: str
    ts: str
    data: Any = None
    error: str | None = None
    denied_reason: str | None = None
    needs_confirm: bool = False
    outcome: str = "ok"  # ok | denied | error | needs_confirm

    def as_observation(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "tool": self.tool,
            "args": self.args,
            "receipt_id": self.receipt_id,
            "ts": self.ts,
            "data": self.data,
            "error": self.error,
            "denied_reason": self.denied_reason,
            "needs_confirm": self.needs_confirm,
            "outcome": self.outcome,
        }


@dataclass
class Gateway:
    """Deterministic tool policy outside the model."""

    mode: Mode = "observe"
    # Extra handlers for tests (e.g. stub write tools).
    extra_handlers: dict[str, Any] = field(default_factory=dict)
    # Raw user utterance for this turn (harness-set). Paste allowlist evidence.
    turn_user_text: str | None = None

    def allowed_tools(self) -> frozenset[str]:
        return TOOL_NAMES

    def execute(self, tool: str, args: dict[str, Any] | None = None) -> GatewayResult:
        args = dict(args or {})
        receipt_id = new_receipt_id()
        ts = utc_now_iso()

        if tool in WRITE_TOOL_NAMES and self.mode in ("observe", "plan"):
            reason = (
                f"tool '{tool}' is a write tool; denied in {self.mode.capitalize()} mode"
            )
            return GatewayResult(
                ok=False,
                tool=tool,
                args=args,
                receipt_id=receipt_id,
                ts=ts,
                denied_reason=reason,
                outcome="denied",
            )

        if tool not in TOOL_NAMES and tool not in self.extra_handlers:
            return GatewayResult(
                ok=False,
                tool=tool,
                args=args,
                receipt_id=receipt_id,
                ts=ts,
                denied_reason=f"unknown tool '{tool}'",
                outcome="denied",
            )

        # ToolSpec mode gate (web_fetch denied in plan; etc.)
        spec = spec_for(tool)
        if (
            spec is not None
            and tool not in self.extra_handlers
            and self.mode not in spec.modes
        ):
            return GatewayResult(
                ok=False,
                tool=tool,
                args=args,
                receipt_id=receipt_id,
                ts=ts,
                denied_reason=(
                    f"tool '{tool}' not allowed in {self.mode.capitalize()} mode "
                    f"(side_effect={spec.side_effect})"
                ),
                outcome="denied",
            )

        if tool not in self.allowed_tools() and tool not in self.extra_handlers:
            return GatewayResult(
                ok=False,
                tool=tool,
                args=args,
                receipt_id=receipt_id,
                ts=ts,
                denied_reason=f"tool '{tool}' not allowed in mode {self.mode}",
                outcome="denied",
            )

        # Validate known tool args lightly (server-side).
        if tool == "body_vitals":
            section = args.get("section", "summary")
            if section not in (None, "summary", "full"):
                return GatewayResult(
                    ok=False,
                    tool=tool,
                    args=args,
                    receipt_id=receipt_id,
                    ts=ts,
                    error=f"invalid section: {section!r}",
                    outcome="error",
                )
        if tool == "body_story" and "n" in args and args["n"] is not None:
            try:
                args["n"] = int(args["n"])
            except (TypeError, ValueError):
                return GatewayResult(
                    ok=False,
                    tool=tool,
                    args=args,
                    receipt_id=receipt_id,
                    ts=ts,
                    error="n must be an integer",
                    outcome="error",
                )
        if tool == "body_readonly_cmd":
            argv = args.get("argv")
            if not isinstance(argv, list) or not argv:
                return GatewayResult(
                    ok=False,
                    tool=tool,
                    args=args,
                    receipt_id=receipt_id,
                    ts=ts,
                    error="argv must be a non-empty string list",
                    outcome="error",
                )
            if not all(isinstance(t, str) for t in argv):
                return GatewayResult(
                    ok=False,
                    tool=tool,
                    args=args,
                    receipt_id=receipt_id,
                    ts=ts,
                    error="argv tokens must be strings",
                    outcome="error",
                )
        if tool == "memory_worldview_write":
            cites = args.get("cites")
            if not cites or (
                isinstance(cites, list) and not any(str(c).strip() for c in cites)
            ):
                return GatewayResult(
                    ok=False,
                    tool=tool,
                    args=args,
                    receipt_id=receipt_id,
                    ts=ts,
                    error="WORLDVIEW write requires non-empty cites[]",
                    denied_reason="WORLDVIEW write requires non-empty cites[]",
                    outcome="denied",
                )

        # Pass gateway receipt_id + server-side turn text into web_fetch.
        # Model-supplied pasted_text is stripped — paste evidence is harness-owned.
        if tool == "web_fetch":
            args = {**args, "turn_user_text": self.turn_user_text}
            args.pop("pasted_text", None)
            if "receipt_id" not in args:
                args["receipt_id"] = receipt_id

        if tool.startswith("life_") and tool not in (
            "life_food_search",
            "life_barcode_lookup",
            "life_nutrition_day",
            "life_time_status",
            "life_gym_status",
            "life_habit_status",
            "life_who_is",
            "life_people_remind",
        ):
            if "receipt_id" not in args:
                args["receipt_id"] = receipt_id

        handler = (
            self.extra_handlers.get(tool)
            or life_tools.DISPATCH.get(tool)
            or web_tools.DISPATCH.get(tool)
            or memory_tools.DISPATCH.get(tool)
            or body_tools.DISPATCH.get(tool)
            or artifact_tools.DISPATCH.get(tool)
        )
        if handler is None:
            return GatewayResult(
                ok=False,
                tool=tool,
                args=args,
                receipt_id=receipt_id,
                ts=ts,
                denied_reason=f"no handler for '{tool}'",
                outcome="denied",
            )

        try:
            data = handler(args)
        except BodyFault as exc:
            return GatewayResult(
                ok=False,
                tool=tool,
                args=args,
                receipt_id=receipt_id,
                ts=ts,
                error=exc.message,
                outcome="error",
            )
        except Exception as exc:  # noqa: BLE001 — surface to model as observation
            return GatewayResult(
                ok=False,
                tool=tool,
                args=args,
                receipt_id=receipt_id,
                ts=ts,
                error=str(exc),
                outcome="error",
            )

        # Propagate needs_confirm from memory / web organs.
        needs_confirm = False
        outcome = "ok"
        ok = True
        if isinstance(data, dict):
            if data.get("needs_confirm"):
                needs_confirm = True
                outcome = "needs_confirm"
                ok = False
            elif data.get("ok") is False and data.get("outcome") == "error":
                ok = False
                outcome = "error"
                return GatewayResult(
                    ok=False,
                    tool=tool,
                    args=args,
                    receipt_id=receipt_id,
                    ts=ts,
                    data=data,
                    error=data.get("error") or data.get("denied_reason"),
                    denied_reason=data.get("denied_reason"),
                    outcome="error",
                )
            elif data.get("ok") is False and data.get("outcome") == "denied":
                ok = False
                outcome = "denied"
                return GatewayResult(
                    ok=False,
                    tool=tool,
                    args=args,
                    receipt_id=receipt_id,
                    ts=ts,
                    data=data,
                    error=data.get("error") or data.get("denied_reason"),
                    denied_reason=data.get("denied_reason"),
                    outcome="denied",
                )
            elif data.get("ok") is False and data.get("reason") == "already_done":
                ok = False
                outcome = "already_done"

        return GatewayResult(
            ok=ok,
            tool=tool,
            args=args,
            receipt_id=receipt_id,
            ts=ts,
            data=data,
            needs_confirm=needs_confirm,
            outcome=outcome,
        )
