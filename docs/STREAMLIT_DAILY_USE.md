# Streamlit daily use (J3)

Daily operator flows on a Raspberry Pi (or laptop) using the Ada HUD: **Chat** tab quick actions, kernel hats, and autonomic skills. For full tab layout see [`STREAMLIT_BOSS.md`](STREAMLIT_BOSS.md).

## Start the HUD

1. Profile env loaded (`ADA_PROFILE`, `ADA_DATA_DIR`, `GEMINI_API_KEY` for chat).
2. Kernel booted once per DB (or after schema/mission surgery):

   ```bash
   ada boot
   ```

3. Streamlit (same repo / venv as CLI):

   ```bash
   pip install -e ".[streamlit]"
   streamlit run scripts/ada_observability_app.py
   ```

   Legacy entry: `ada hud` (or deprecated `ada jarvis`) opens the same operator app when configured.

The sidebar shows **Kernel hats**: `base_ops` and `ada_ops` mission ids after boot. If missing, run `ada boot` and refresh the page.

## Quick actions (home chips)

At the top of the **Chat** tab, three chips call primitives **without** starting a chat turn (no Gemini, no `tasks` chat row):

| Chip | Primitive | Hat | What it does |
|------|-----------|-----|----------------|
| **Log memory** | `log_memory` | `base_ops` | Appends to knowledge source `ada://memory/base` (deduped by content hash) |
| **Add todo** | `add_task` | `base_ops` | Inserts `task_kind=system` todo (daemon does **not** dequeue system tasks) |
| **Body check** | `body_check` | `ada_ops` + profile | Read-only JSON: pending goals, tick state, brief artifact, paths |

Implementation: `ada.observability.hud_actions.hud_run_primitive` → `primitives.handlers.execute_primitive` (same path as Chat `run_primitive`).

## When to use chat vs chips vs Agent

| Need | Use |
|------|-----|
| Remember something, quick todo, health snapshot | **Quick actions** chips |
| Natural language, programme ideas, recall/list | **Chat** surface (`run_primitive` in the model) |
| Apply a mission template | **Plan** → Apply programme |
| `daily_brief`, `mission_tick_dry_run`, other pack skills | **Agent** → Run action on mission **`ada_ops`** |

Chat **does not** expose `run_skill` on the concierge surface; autonomic skills stay on **Agent** / CLI (`ada brief --mission ada_ops`, `ada mission tick --mission ada_ops`).

## Typical Pi day

1. Morning: open Streamlit → **Body check** chip → scan JSON (goals, daemon, last brief path).
2. During the day: **Log memory** / **Add todo** chips for personal CRM; use **Chat** for longer dialogue.
3. Cron (on `ada_ops`): brief and tick via CLI or Agent panel — not required for chips.
4. After `git pull` or manual DB edits: `ada boot` (J4 adds `ada reload` for daemon); **restart Streamlit** manually so the sidebar kernel ids refresh.

## Environment hints

| Variable | Role |
|----------|------|
| `ADA_OPERATOR_DEFAULT_MISSION` | Sidebar mission filter; Agent default slug |
| `ADA_CHAT_DEFAULT_MISSION` | Chat Agent mode default (often `ada_ops`) |
| `ADA_OPERATOR_FULL_UI=1` | Extra tabs (Env, Profiles, Memory, Playbooks) |

## Safety

- Chips and primitives do not wipe the database.
- System todos on `base_ops` are not picked up by `ada daemon` (goal queue only).
- Personal memory (`ada://memory/base`) is separate from ISR/global ingest pools — see [`ADA_BIOLOGY.md`](ADA_BIOLOGY.md) if present.

## Related docs

- [`STREAMLIT_BOSS.md`](STREAMLIT_BOSS.md) — full HUD layout (Plan / Agent / sidebar)
- [`ADA_CORE_OPS.md`](ADA_CORE_OPS.md) — autonomic ops, cron, deploy ritual (J4)
- [`HANDS_PHASES.md`](HANDS_PHASES.md) — J-track phase checklist
