# ADA Phase C — Ingress UX, proactivity, ecosystem polish

Phase C makes ADA feel like a single-ingress Jarvis for daily use: HUD home, SQL-grounded briefs, optional Streamlit chat, and a three-step operator loop — without new workflow kinds or motor rewrites.

Prerequisite: [ADA_PHASE_B.md](ADA_PHASE_B.md) gate green on your profile.

## Delivered

| Ticket | Feature |
|--------|---------|
| C0 | `ada jarvis` / `ada hud` — launch Streamlit operator UI |
| C1/C9 | `render_brief()`, `ada brief`, skill `daily_brief` |
| C2 | `templates/missions/ops.yaml` + cron snippets (never auto-install) |
| C3 | `notifications.py` — noop default; `ADA_NOTIFY_URL` documented |
| C4 | HUD Control plane — **Brief me** + **Enqueue brief goal** |
| C5 | Streamlit **Chat** tab — same `ChatSession` as `ada chat` |
| C6 | `ada profile brief` — read-only cross-mission JSON |
| C7 | This doc + [ADA_CORE.md](ADA_CORE.md) daily loop |

## Daily Jarvis loop (≤3 surfaces)

1. **`ada jarvis`** — HUD: flags, brief, chat tab (or terminal `ada chat --mission <slug>`)
2. **`ada doctor`** — or read flags in HUD Control plane
3. **`ada daemon`** — consumes goals (including optional `ada brief --enqueue`)

## Commands

```bash
ada jarvis
ada brief --mission jarvis-ops
ada brief --mission jarvis-ops --enqueue
ada profile brief
ada chat --mission jarvis-ops
ada mission apply-template ops --dry-run
```

## Harness rules

- Brief text from `collect_flags` + bounded snapshot only — no invented job counts
- LLM may summarize in daemon goals; must use `get_mission_control_snapshot` for counts
- Notifications never include secrets or `payload_json` (default off)
- Programme apply still requires terminal `ada programme apply`

## See also

- [CROSS_MISSION_READ.md](CROSS_MISSION_READ.md)
- [OPS_DAILY.md](OPS_DAILY.md)
- [mission-control-flags.md](mission-control-flags.md)
- [VOICE_DEFERRED.md](VOICE_DEFERRED.md)
