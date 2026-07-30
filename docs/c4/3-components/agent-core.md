# Components — Agent core

Zoom of the shared turn loop used by `ada chat` (and by the daemon when a goal needs model work). Maps to C2 containers `cli-chat`, `orchestrator`, and `tool-executor`.

## Components

| ID | Role | Evidence |
|----|------|----------|
| `chat-ingress` | Selects Entity vs Work (Agent) / Plan / Setup; different tool sets | [`chat_ingress.py`](../../../src/ada/chat_ingress.py), [`chat_session.py`](../../../src/ada/chat_session.py) |
| `orchestrator` | Multi-leg Gemini turns; persists each leg; tombstones failed turns | [`orchestrator.py`](../../../src/ada/orchestrator.py) |
| `gemini-adapter` | Streaming via `google-genai`; `automatic_function_calling` disabled | [`adapters/gemini_stream.py`](../../../src/ada/adapters/gemini_stream.py) (~L621) |
| `tool-executor` | Registry dispatch for model-requested tools | [`tool_executor.py`](../../../src/ada/tool_executor.py), [`tools/registry.py`](../../../src/ada/tools/registry.py) |
| `motor-skills` | Exact-line shell allowlist + YAML skills via `run_skill` | [`motor/`](../../../src/ada/motor/), [`skills/*.yaml`](../../../skills/), [`tools/shell_allowlist.py`](../../../src/ada/tools/shell_allowlist.py) |
| `web-runtime` | Env-gated Serper / Jina | [`tools/web_runtime.py`](../../../src/ada/tools/web_runtime.py) |
| `transcript-writes` | SQLite `messages` with `parent_uuid`, sequence, optional rewire | [`persistent/store.py`](../../../src/ada/persistent/store.py), [`claude_logic.md`](../../claude_logic.md) |

## Out of scope here

Mission / programme control plane, ingest CLIs, graph-lite, and publish workflow steps—see sibling C3 diagrams and Containers.
