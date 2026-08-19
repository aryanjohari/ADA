"""ToolSpec FunctionDeclaration schemas — Gemini requires array items."""

from __future__ import annotations

from typing import Any

from ada.cortex.adapter import CortexTurn
from ada.cortex.gemini import GeminiAdapter
from ada.harness.loop import run_turn
from ada.harness.session import ChatSession
from ada.tools.toolspec import function_declarations


def _schema_arrays_missing_items(schema: Any, path: str) -> list[str]:
    missing: list[str] = []
    if schema is None:
        return missing
    typ = getattr(schema, "type", None)
    typ_val = getattr(typ, "value", typ)
    if typ_val is not None and str(typ_val).upper() == "ARRAY":
        if getattr(schema, "items", None) is None:
            missing.append(path)
        else:
            missing.extend(
                _schema_arrays_missing_items(schema.items, path + ".items")
            )
    props = getattr(schema, "properties", None) or {}
    for key, child in props.items():
        missing.extend(_schema_arrays_missing_items(child, f"{path}.{key}"))
    return missing


class _CaptureClient:
    def __init__(self) -> None:
        self.models = self
        self.last_config = None

    def generate_content(self, *, model, contents, config):
        self.last_config = config

        class _Resp:
            function_calls = None
            candidates = []
            usage_metadata = None

        return _Resp()


class _Schema400Cortex:
    """Would 400 if FunctionDeclaration arrays lacked items (pre-fix)."""

    model = "fake"

    def generate(self, *, system, contents, tools=None):
        decls = function_declarations()
        missing = []
        for d in decls:
            params = d.get("parameters") or {}
            props = params.get("properties") or {}
            for key, spec in props.items():
                if isinstance(spec, dict) and spec.get("type") == "array":
                    if "items" not in spec:
                        missing.append(f"{d.get('name')}.{key}")
        if missing:
            raise ValueError(
                "400 INVALID_ARGUMENT missing items: " + ",".join(missing)
            )
        return CortexTurn(text="ok", tool_calls=[], usage={})


def test_gemini_generate_tools_none_array_items() -> None:
    client = _CaptureClient()
    adapter = GeminiAdapter(api_key="x", client=client)
    adapter.generate(system="s", contents=["hi"], tools=None)
    tools = getattr(client.last_config, "tools", None) or []
    assert tools, "tools=None must send function_declarations"
    missing: list[str] = []
    for tool in tools:
        for decl in tool.function_declarations or []:
            missing.extend(
                _schema_arrays_missing_items(decl.parameters, decl.name)
            )
    assert missing == []


def test_observe_social_turn_would_have_been_400(data_root) -> None:
    session = ChatSession(mode="observe", model="fake")
    result = run_turn(session, "Hi Ada. How are you doing?", _Schema400Cortex())
    assert result.stop_reason != "error"
    assert result.text == "ok"
