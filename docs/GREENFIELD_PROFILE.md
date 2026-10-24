# Greenfield profile checklist

Stand up `ADA_PROFILE=jarvis` without reading 100 env vars.

## Prerequisites

- Python ≥ 3.11, `pip install -e .` from repo root
- `GEMINI_API_KEY` for chat/daemon (fake key OK for DB-only tests)

## Steps

1. **Profile env**
   ```bash
   export ADA_PROFILE=jarvis
   export ADA_PROFILE_DATA_ROOT=/path/to/ada-profiles
   export ADA_REQUIRE_PROFILE_ISOLATION=1
   ```

2. **Copy slim `.env`**
   ```bash
   mkdir -p "$ADA_PROFILE_DATA_ROOT/jarvis"
   cp profiles/jarvis.env.example "$ADA_PROFILE_DATA_ROOT/jarvis/.env"
   # Edit: GEMINI_API_KEY, paths
   ```

3. **Kernel + ops mission** (slug must match `ADA_CHAT_DEFAULT_MISSION` = `ada_ops`)
   ```bash
   ada boot
   ada mission apply-template ada_ops --dry-run
   ada mission apply-template ada_ops   # Y/n confirm
   ```
   Full post-apply checklist (cron, daemon, tick, reload): [ADA_CORE_OPS.md](ADA_CORE_OPS.md).

4. **Optional migrate** (if deprecated vars still in shell env)
   ```bash
   ada mission migrate-env ada_ops --apply
   ```

5. **Memory bootstrap**
   ```bash
   # Under $ADA_PROFILE_DATA_ROOT/jarvis/memory/ or ADA_MEMORY_DIR
   touch memory/master.md memory/soul.md memory/wakeup.md memory/shell_allowlist.txt
   ```

6. **Doctor**
   ```bash
   ada doctor
   # Expect exit 0 (warnings OK for missing API key in CI)
   ```

7. **Chat binding**
   ```bash
   ada chat --new-session
   # Ctrl+C after start — Entity chat keeps tasks.mission_id NULL (J2)
   ```

8. **Audit** (after graph activity)
   ```bash
   ada mission audit-scope ada_ops
   ```

## Automated gate (A6)

`tests/test_greenfield_profile.py` runs a dry-run: temp profile dir, mission init, doctor, mission id on chat task.

## Job plane

Only one daemon mode — see [JOB_QUEUE_SINGLE_OWNER.md](JOB_QUEUE_SINGLE_OWNER.md). Template sets `ADA_JOB_QUEUE=system_jobs`.

## Global vs mission chat

- With `ADA_CHAT_DEFAULT_MISSION=ada_ops`: Work chat / HUD default to that slug; plain `ada chat` stays Entity (NULL task mission).
- Unset for global-capable free talk — see [MEMORY_CONTRACT.md](MEMORY_CONTRACT.md).
