# Programme apply semantics

`apply_programme` (Plan mode) and `ada mission apply-template` call **`apply_packet`** after operator approval.

## What apply does

- Upsert **`missions`** row: `slug`, `title`, `defaults_json`, `schedule_hint_json`, **`brief_md`**
- Merge `skills_enabled` into `defaults_json`
- Insert **`knowledge_sources`** from the packet (per URL)
- Write **`artifacts/cron/<slug>.snippet`** when `recommended_cron` is set

## What apply does not do

- Does **not** start the daemon or run `ada mission tick`
- Does **not** enqueue workflows or call `run_skill`
- Operator installs cron lines manually, then runs `ada mission tick --mission <slug>` on schedule

## `brief_md` on re-apply

Re-apply **replaces** `missions.brief_md` with the packet value (including empty string if the packet clears it). Plan operators should treat apply as the source of truth for programme intent.

## Optional future

`run_initial_tick` on the packet is not implemented in H4.
