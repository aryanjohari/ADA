# Cross-Mission Read (Profile-Global Kernel)

Rows and sources with **`mission_id IS NULL`** are shared across all missions in a profile:

- Triage categories and shared classification pools
- Profile-wide RSS / web sources registered for the global kernel
- Market metrics and other unscoped knowledge items

Mission-bound rows (`mission_id` set) are visible in **Work** chat for that mission plus the global kernel (hybrid search).

Entity (`ada chat`) operates at profile scope: it reads the global kernel and profile flags but does not bind `tasks.mission_id` to a programme.

Use `ada profile brief` or Entity `get_mission_control_snapshot` for a cross-mission overview without loading raw `defaults_json`.
