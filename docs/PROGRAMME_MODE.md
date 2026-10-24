# Programme mode

Design missions in chat without silent SQLite writes.

## ProgrammePacket (closed schema)

Pydantic model `ada.programme.packet.ProgrammePacket` with `extra=forbid`:

```json
{
  "mission_slug": "research",
  "title": "Weekly research",
  "defaults_json": {},
  "schedule_hint_json": {"version": 1, "jobs": []},
  "knowledge_sources": [{"url": "https://example.com/feed.xml", "kind": "rss"}],
  "recommended_cron": [{"comment": "Sunday tick", "line": "0 6 * * 0 ada mission tick --mission research"}],
  "skills_enabled": ["weekly_research_goal"],
  "risk_summary": "Human-readable risk note for operator"
}
```

## Flow

1. `ada chat --programme` — harness `_PROGRAMME_MODE_NOTE`; tools `propose_programme`, `get_mission_control_snapshot`
2. Model calls `propose_programme(packet_json)` → validated JSON returned; **no DB writes**
3. Operator runs `ada programme apply packet.json` or template apply — terminal `Y/n` (or `--yes`)
4. `apply_packet` closed mutations:
   - `missions` insert/update (slug, title, defaults, schedule)
   - `knowledge_sources` insert
   - `artifacts/cron/<slug>.snippet` only (never install crontab)

## action_log kinds

- `programme_apply`
- `programme_apply_denied`
- `programme_propose` (optional future)

## Harness rule

Never embed raw `ProgrammePacket` or `defaults_json` in system prompt text — tool returns only.
