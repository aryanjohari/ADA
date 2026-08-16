# M16 Phase 0+1 operator note — first daily package

**Shipped:** birth pack, syllabus heads, `due_at` / dues, `artifact_write`, Today strip, ntfy path, artifact shelf, brief check JSON.

## One-time setup

1. **Birth / seeds** (idempotent; never overwrites your edits):
   ```bash
   ada body birth
   # or just: ada body birth-pack
   ```
   Expect `ada-data/syllabus/SELF.md` + `OPERATOR.md`.

2. **ntfy secret** (never commit):
   ```bash
   install -d -m 700 /mnt/ada-data/secrets
   cat >/mnt/ada-data/secrets/ntfy.env <<'EOF'
   NTFY_URL=https://ntfy.sh
   NTFY_TOPIC=your-private-topic
   # optional: NTFY_TOKEN=tk_…
   EOF
   chmod 600 /mnt/ada-data/secrets/ntfy.env
   ```
   Enable push in Agent chat: *“enable notify”* → Confirm card (first enable only).  
   Or Confirm `prefs.notify_enabled=true`. Quiet hours + `mute_proactivity` still win. Budget default: **5/day**, **60m** cooldown.

3. **Morning brief timer** (optional ritual):
   ```bash
   sudo cp deploy/systemd/ada-brief.{service,timer} /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now ada-brief.timer
   ```
   Check payload: `ada campaigns check --json` (dues + campaigns).  
   Optional ping: `ada campaigns check --json --notify`.

## Try for a week

| Move | Expect |
|------|--------|
| Agent: “add due: pay rent Friday” / upsert with `due_at` | Shows on Today strip + boot `due_todos` + `campaigns check` |
| Agent: “ping me in a minute…” / upsert with `remind_at` (not `next_wake_at`) | Reminds on Today / notify-due path; wrong field → tool error |
| Agent: summarize allowlisted link → `artifact_write` | File under `artifacts/YYYY-MM-DD/…` + receipt; Body → Shelf |
| Open HUD | Chat remains first viewport; **Today** is a thin strip above chat (F12) |
| Due + notify enabled | Budgeted ntfy ping (or skip receipt if quiet/mute/cooldown) |

## Still deferred (Phase 2)

Inbox capture, Google Calendar OAuth, HA, voice wake, campaign productization, PDF, Mem0.
