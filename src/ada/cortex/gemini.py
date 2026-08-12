"""Gemini cortex via google-genai — AFC disabled; gateway executes tools."""

from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types

from ada.cortex.adapter import CortexTurn, ProposedToolCall
from ada.cortex.models import resolve_model
from ada.tools.schemas import function_declarations


def _declarations_as_tool() -> types.Tool:
    decls = []
    for d in function_declarations():
        params = d.get("parameters") or {"type": "object", "properties": {}}
        decls.append(
            types.FunctionDeclaration(
                name=d["name"],
                description=d.get("description"),
                parameters=params,
            )
        )
    return types.Tool(function_declarations=decls)


def _usage_dict(response: Any) -> dict[str, Any]:
    meta = getattr(response, "usage_metadata", None)
    if meta is None:
        return {}
    out: dict[str, Any] = {}
    for key in (
        "prompt_token_count",
        "candidates_token_count",
        "total_token_count",
        "thoughts_token_count",
        "cached_content_token_count",
    ):
        val = getattr(meta, key, None)
        if val is not None:
            out[key] = int(val)
    return out


def _extract_turn(response: Any) -> CortexTurn:
    text_parts: list[str] = []
    tool_calls: list[ProposedToolCall] = []

    # Prefer SDK helper when present.
    fc_list = getattr(response, "function_calls", None)
    if fc_list:
        for fc in fc_list:
            name = getattr(fc, "name", None) or ""
            args = dict(getattr(fc, "args", None) or {})
            call_id = getattr(fc, "id", None)
            tool_calls.append(ProposedToolCall(name=name, args=args, call_id=call_id))

    candidates = getattr(response, "candidates", None) or []
    for cand in candidates:
        content = getattr(cand, "content", None)
        if content is None:
            continue
        for part in getattr(content, "parts", None) or []:
            t = getattr(part, "text", None)
            if t:
                text_parts.append(t)
            if not fc_list:
                fcall = getattr(part, "function_call", None)
                if fcall is not None:
                    name = getattr(fcall, "name", None) or ""
                    args = dict(getattr(fcall, "args", None) or {})
                    call_id = getattr(fcall, "id", None)
                    tool_calls.append(
                        ProposedToolCall(name=name, args=args, call_id=call_id)
                    )

    text = "\n".join(text_parts).strip() or None
    return CortexTurn(text=text, tool_calls=tool_calls, usage=_usage_dict(response), raw=response)


class GeminiAdapter:
    """Primary cortex adapter. Never passes Python callables as tools."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.model = model or resolve_model("chat_interactive")
        self._client = client or genai.Client(api_key=api_key)

    def generate(
        self,
        *,
        system: str,
        contents: list[Any],
        tools: list[Any] | None = None,
    ) -> CortexTurn:
        tool_list = tools if tools is not None else [_declarations_as_tool()]
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=tool_list,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )
        response = self._client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )
        return _extract_turn(response)


def observation_to_content(result_obs: dict[str, Any], call_id: str | None = None) -> Any:
    """Build a model Content with function_response for the next round."""
    name = result_obs.get("tool") or "unknown"
    # Keep observation JSON-friendly; drop huge raw if needed later.
    fr = types.FunctionResponse(name=name, response=result_obs, id=call_id)
    return types.Content(role="user", parts=[types.Part(function_response=fr)])


def user_content(text: str) -> Any:
    return types.Content(role="user", parts=[types.Part(text=text)])
