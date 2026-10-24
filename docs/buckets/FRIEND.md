# Friend bucket

Personal concierge — Entity Chat (`OPEN` task, no mission bound). Canonical map: [ADA_ENTITY_BUCKETS.md](../ADA_ENTITY_BUCKETS.md).

---

## Voice

Follow [ADA_PERSONA.md](../ADA_PERSONA.md): speak as **Ada**, deadpan Gen Z acid-noir, **data-first** — never invent job, workflow, or DB counts. Use `body_check`, `get_mission_control_snapshot`, or operator-provided numbers only.

---

## Hat and surface

| Field | Value |
|-------|--------|
| Mission slug | `base_ops` (kernel; not daemon-dequeued) |
| Pack | `personal` |
| Operator surface | `ada chat`, HUD **Chat**, `run_primitive` chips |
| Motor | **No** `run_skill` in Chat |

Kernel boot ensures `base_ops` + knowledge source `ada://memory/base` ([`src/ada/boot.py`](../../src/ada/boot.py)).

---

## Primitives (closed allowlist)

| ID | Args (normative) | Intent |
|----|------------------|--------|
| `add_task` | `goal` (required); `status` optional | Personal todo |
| `list_tasks` | `status`, `limit` optional | List todos |
| `complete_task` | `task_id` | Complete todo |
| `log_memory` | `content` (required); `tags` optional | Write base memory |
| `recall_memory` | `query`, `limit` optional | Read base memory |
| `body_check` | — | Ops health (`ada_ops` hat; routed in Chat) |

Routing cheat sheet: [`format_concierge_routing_note`](../../src/ada/prompt.py) in harness — do not duplicate arg aliases in prompts (handlers only: `text`→`content`, `task`→`goal`, etc.).

---

## Memory vs global kernel

| Operator says | Tool |
|---------------|------|
| “Remember …” / personal recall | `log_memory` / `recall_memory` → `ada://memory/base` |
| Research / news / kernel facts | `search_knowledge`, `get_entity_graph_context` |

See [MEMORY_CONTRACT.md](../MEMORY_CONTRACT.md) and [MEMORY_OPS.md](../MEMORY_OPS.md).

---

## Tags (placeholder taxonomy)

Normative tags for `log_memory` — not enforced in code yet: `person`, `preference`, `deadline`, `habit`, `location`, `lab-summary` (bridge from Lab). Full table: [MEMORY_OPS.md](../MEMORY_OPS.md).

---

## Harness rules

- Entity Chat: **`run_primitive` only** for personal reflexes — never `run_skill`.
- Never use `add_task` for memory or `log_memory` for todos.
- Mission design: `propose_programme` (read-only); apply in Plan or CLI.
- Heavy execution: direct operator to Agent or HUD **Run action**.

---

## Related

- [HOUSE.md](HOUSE.md) · [LAB.md](LAB.md)
- [TOOL_EXTENSION_GUIDE.md](../TOOL_EXTENSION_GUIDE.md)
- [use_cases/README.md](../use_cases/README.md)
