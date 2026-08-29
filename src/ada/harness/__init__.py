"""Chat harness — ReAct loop, session, stream hooks.

Import submodules directly (``ada.harness.loop``, ``ada.harness.session``).
Do not eager-import loop here — ``gateway → life_tools → resolve_gate`` must
not pull ``loop → gemini → tools → gateway`` during startup.
"""

__all__ = ["ChatSession", "Mode", "LoopResult", "run_turn"]
