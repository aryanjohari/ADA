# Programme templates and packs

Mission templates live under `templates/missions/*.yaml`. Load with `ada mission apply-template <name>` or Plan mode `propose_programme` / `apply_programme` after cloning the packet.

**After apply** (cron install, daemon, tick, brief): see [ADA_CORE_OPS.md](ADA_CORE_OPS.md) — applying a programme arms the mission; autonomy requires operator-installed cron and `ada daemon`.

Each template sets:

- **`pack`** → stored in `missions.defaults_json["pack"]`
- **`skills_enabled`** → merged into `defaults_json["skills_enabled"]` on apply
- **`brief_md`** → programme intent on the mission row

## Templates

| Template | Default slug | Pack |
|----------|--------------|------|
| `ada_ops` | `ada_ops` | `core-ops` |
| `base_ops` | `base_ops` | `personal` |
| `isr-publish` | (from YAML) | `isr-publish` |
| `isr-research` | (from YAML) | `isr-research` |
| `research` | (from YAML) | `generic-research` |
| `job-hunt` | (from YAML) | `job-hunt` |
| `archetype-minimal` | (from YAML) | `generic-research` |

## Pack → allowed skill ids

Must match `PACK_SKILL_ALLOWLIST` in `src/ada/programme/packs.py`.

| Pack | Allowed skills |
|------|----------------|
| `core-ops` | `daily_brief`, `mission_tick_dry_run` |
| `personal` | _(none — primitives use base_ops hat, not motor skills)_ |
| `isr-publish` | `publish_entity_v1`, `publish_keyword_v1` |
| `isr-research` | `ingest_rss_mission`, `weekly_research_goal` |
| `generic-research` | `ingest_rss_mission`, `weekly_research_goal` |
| `job-hunt` | `ingest_rss_mission`, `weekly_research_goal` |

## Apply rules (H5)

- Every id in `skills_enabled` must exist in `skills/*.yaml`.
- If `defaults_json.pack` is set, it must be a known pack.
- Pack set with empty `skills_enabled` is rejected: `pack '<name>' requires explicit skills_enabled`.
- `skills_enabled` must be a subset of the pack allowlist.

## Examples

- **Ada ops:** `ada_ops` template — no publish skills; `run_skill` for `publish_keyword_v1` fails on `ada_ops`. Kernel boot (`ada boot`) also ensures this mission without a separate apply.
- **ISR publish:** `isr-publish` template — publish skills allowed; approval gates unchanged.

See [HANDS_CONTRACT.md](HANDS_CONTRACT.md) for motor enforcement and bypass notes.
