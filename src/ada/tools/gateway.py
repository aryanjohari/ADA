"""Tool gateway: schema validate → mode allowlist → execute → receipt.

Consent Integrity: denials and confirms render gateway {tool, args}, never
model prose alone (M02 §6.2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from ada.body.vitals import utc_now_iso
from ada.io.paths import BodyFault
from ada.runs.append import new_receipt_id
from ada.tools import body_tools
from ada.tools.schemas import TOOL_NAMES, WRITE_TOOL_NAMES

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

    def allowed_tools(self) -> frozenset[str]:
        # v1: all four body reads in Observe/Agent/Plan.
        # Write tools never allowed in Observe; Agent would allow later — none in M02.
        return TOOL_NAMES

    def execute(self, tool: str, args: dict[str, Any] | None = None) -> GatewayResult:
        args = dict(args or {})
        receipt_id = new_receipt_id()
        ts = utc_now_iso()

        # Future write tools: deny in Observe/Plan; M02 Agent has no write tools yet.
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

        handler = self.extra_handlers.get(tool) or body_tools.DISPATCH.get(tool)
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

        return GatewayResult(
            ok=True,
            tool=tool,
            args=args,
            receipt_id=receipt_id,
            ts=ts,
            data=data,
            outcome="ok",
        )
