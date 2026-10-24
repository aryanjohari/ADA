# ADA Hands architecture

**Brain** (orchestrator, harness, Entity/Work ingress) is decoupled from **hands** (motor + tools).

- **Brain:** chat sessions, prompts, mission control digests, programme design.
- **Hands:** declared Gemini tools (`src/ada/tools/registry.py`), motor Actions (`run_skill` → `src/ada/motor/execute.py`), CLI ops, internal enqueue paths.

See also: [HANDS_CONTRACT.md](HANDS_CONTRACT.md), [HANDS_CATALOG.md](HANDS_CATALOG.md), [hands_catalog.json](hands_catalog.json).
