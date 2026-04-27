# Claude-logic norms (pointer)

This repository’s **authoritative behavior** for transcripts, tool execution, tombstones, retries, and persistence boundaries lives in **code** and module docstrings. This file is a **stub** so README and tooling links resolve; it does not duplicate a full external spec.

## Where to read

| Topic | Location |
|-------|----------|
| SQLite transcript, tasks, single-writer patterns | [`src/ada/persistent/store.py`](../src/ada/persistent/store.py) |
| Debounced streaming, assistant writes, task helpers | [`src/ada/query_engine.py`](../src/ada/query_engine.py) |
| Agentic turn: streaming legs, allowlisted shell, caps | [`src/ada/orchestrator.py`](../src/ada/orchestrator.py) |
| Tool executor (shell + memory) | [`src/ada/tool_executor.py`](../src/ada/tool_executor.py) |
| System prompt assembly | [`src/ada/prompt.py`](../src/ada/prompt.py) |

## Security posture (non-negotiable)

- **No arbitrary SQL** for the model; use tools and allowlisted queries only.
- **Env-gated** web, knowledge, workflow, and file tools (`Settings` in [`src/ada/config.py`](../src/ada/config.py)).
- **PersistentState** vs **QueryEngine**: store owns raw SQL; QueryEngine is the higher-level boundary used by the harness.
- **Tombstones / rewire** and stream timeouts: see `orchestrator.py` and README §6.

## Operator scheduling

For cron, systemd, spend caps, and approval gates, see [`docs/operator-runbook-raspberry-pi.md`](operator-runbook-raspberry-pi.md).
