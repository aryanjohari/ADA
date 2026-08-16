# Operator slots (seed)

How ADA learns **you**. Empty slots only — no private biography in git.
Copied into `ada-data/syllabus/OPERATOR.md` **only if missing**.

## Prefs (standing FACTS)

Keys live in `facts/prefs.yaml`. Common ones:

| Key | Meaning |
|-----|---------|
| `brief_time` | Morning brief anchor (HH:MM local) |
| `quiet_hours_start` / `quiet_hours_end` | No nudge window |
| `mute_proactivity` | Hard mute for nudges / notify |
| `preferred_tz` | Plain-speech timezone |
| `tease_ok` / roast dials | Voice register |
| `notify_enabled` | Push master (first enable → Confirm) |
| `notify_channel` | Phase 1: `ntfy` only |
| `notify_budget_per_day` | Default 5 |
| `notify_cooldown_minutes` | Default 60 |

Say “remember …” in Agent mode to append; overwrites may need Confirm.

## People

Files under `facts/people/<id>.yaml`. Soft-link from todos via `people_ids`.
Template: `facts/people/_template.yaml` (from seeds). Operator bio stays on ada-data only.

## How to update me

1. Chat (Agent): “remember I prefer …” / “add due …” / “remind me at …”  
2. Plan → Accept for multi-step work (fetch→cite→artifact).  
3. Confirm cards bind `{tool, args}` — gateway owns permission, not model prose.  
4. Body drawer: vitals truth + artifact shelf + x-ray (no secrets).  

## Out of scope for this syllabus

Private jokes, medical notes, passwords, calendar OAuth — keep those in ada-data / secrets, never in the ADA git repo.
