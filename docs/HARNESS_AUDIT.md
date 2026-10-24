# Harness audit checklist

Mapped to Phase A code. Run after harness changes; pytest: `tests/test_harness_contract.py`, `tests/test_prompt_harness.py`.

| Requirement | Status | Pointer |
|-------------|--------|---------|
| Trusted system prompt only | Pass | `prompt.build_system_instruction` — no `defaults_json` / job payloads |
| Setup vs work modes | Pass (A5) | `SETUP_ASSIST`, `_SETUP_MODE_NOTE`; `_WORK_MODE_MISSION_NOTE` when mission bound |
| Mission scope on turns | Conditional | `orchestrator` → `knowledge_mission_scope` from `get_task_mission_id` |
| No model SQL | Pass | `tools/registry`; Streamlit `sql_guard.validate_select_only` |
| Subprocess safety | Pass | `operator_subprocess.run_ada` — `shell=False`, closed argv |
| Status truth | Pass (D) | WORK: injected ProgrammeDigest + `get_mission_control_snapshot`; SETUP: snapshot tool + setup note |
| Payload redaction | Ops only | `observability/sanitize.py` — not chat transcript |
| Transcript integrity | Pass | Tombstone / rewire — [claude_logic.md](claude_logic.md) |
| Single job plane | Pass (docs) | [JOB_QUEUE_SINGLE_OWNER.md](JOB_QUEUE_SINGLE_OWNER.md) |
| Empty shell allowlist | Pass | No `run_allowlisted_shell` declaration; orchestrator preflight |

## Phase D (grounded mission chat)

| Requirement | Status | Pointer |
|-------------|--------|---------|
| ProgrammeDigest allowlist | Pass | `mission_control/programme_digest.py` — no raw defaults/payloads |
| Ephemeral turn appendix | Pass | `orchestrate_turn(turn_harness_appendix)` — API-only via `apply_turn_harness_appendix_to_contents`; clean `persist_user` |
| WORK snapshot tool | Pass | `chat_session.mission_control_snapshot_fn` — optional call; `include_programme` on tool response |
| Inject policy | Pass | `inject_policy.py` — first turn + intent; `ADA_INJECT_PROGRAMME_DIGEST` |

## Gaps (Phase B / E)

- `INTERACTIVE_FAST` on `ada chat` (optional profile)
- Transcript-level secret redaction
- CLI `run_chat` exit hook to mark chat task `completed`

## Manual smoke

```bash
pytest tests/test_harness_contract.py tests/test_prompt_harness.py tests/test_programme_digest.py tests/test_programme_digest_inject.py -q
ada doctor
```
