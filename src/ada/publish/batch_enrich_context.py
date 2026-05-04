"""System instruction for ``ada enrich-graph`` (intent + numeric policy; not chat harness)."""

from __future__ import annotations

from ada.config import Settings
from ada.llm_context import build_llm_context
from ada.policy.load import PolicyConfig, load_intent_md
from ada.prompt import format_knowledge_tools_note


def resolve_batch_enrich_system_instruction(
    settings: Settings,
    policy: PolicyConfig,
) -> str:
    base = (
        "You run a background ENRICH pass for one publish subject entity at a time. "
        "Use knowledge tools and optional web tools per the tool policy to add verifiable "
        "facts via record_edge, link_evidence, and record_entity when needed."
    )
    invariants = (
        "Follow the user message [WORKFLOW_STEP:ENRICH] contract. "
        "Do not invent URLs; persist only tool-backed graph and knowledge writes. "
        "Operator goals in the intent section are steering only."
    )
    intent_txt = load_intent_md(settings.memory_dir, max_bytes=policy.intent_max_bytes)
    core = build_llm_context(
        "batch_enrich_graph",
        base=base,
        invariants=invariants,
        intent_text=intent_txt,
        policy=policy,
    )
    kn = format_knowledge_tools_note(settings)
    if kn and kn.strip():
        return f"{core}\n\n{kn.strip()}"
    return core
