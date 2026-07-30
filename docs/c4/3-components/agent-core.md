# Components — Agent core

Zoom of the shared turn loop used by `ada chat` (and by the daemon when a goal needs model work).

## Components

| ID | Role |
|----|------|
| **Chat ingress** | Selects Entity vs Work (Agent) / Plan / Setup; different tool sets ([`docs/ADA_CORE.md`](../../ADA_CORE.md)) |
| **Orchestrator** | Multi-leg Gemini turns; persists each leg; tombstones failed turns ([`src/ada/orchestrator.py`](../../../src/ada/orchestrator.py)) |
| **Gemini adapter** | Streaming via `google-genai`; automatic function calling disabled ([`src/ada/adapters/gemini_stream.py`](../../../src/ada/adapters/gemini_stream.py)) |
| **Tool executor** | Registry dispatch for model-requested tools |
| **Motor / skills** | Exact-line shell allowlist + YAML skills via `run_skill` |
| **Transcript writes** | SQLite `messages` with `parent_uuid`, sequence, optional rewire ([`docs/claude_logic.md`](../../claude_logic.md)) |

## Out of scope here

Mission / programme control plane, ingest CLIs, and publish workflow steps—see sibling C3 diagrams and Containers.
