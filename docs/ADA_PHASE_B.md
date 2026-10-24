# ADA Phase B — Motor, skills, programme ingress

Phase B unifies execution behind `src/ada/motor/` and adds programme design ingress without loosening Phase A security boundaries.

## Delivered

- **Motor plane:** `motor.execute(MotorRequest)` routes shell, `ada` argv, and skills
- **Skills:** `skills/*.yaml` merged with `playbooks/registry.yaml`; chat tool `run_skill`
- **Programme mode:** `ada chat --programme`, `propose_programme` (read-only), `ada programme apply`
- **Templates:** `templates/missions/*.yaml`, `ada mission apply-template`
- **WORK snapshot:** `get_mission_control_snapshot` when mission bound (not setup-only)
- **Manifest drift:** `tests/test_allowlist_manifest_drift.py`
- **Mission-over-env:** ingest GSC site + triage cap from `missions.defaults_json`

See also: [SKILL_SPEC.md](SKILL_SPEC.md), [PROGRAMME_MODE.md](PROGRAMME_MODE.md), [ALLOWLIST_MANIFEST.md](ALLOWLIST_MANIFEST.md).

## Chat ingress modes

| Mode | CLI | Motor writes |
|------|-----|--------------|
| OPEN | `ada chat` | `run_skill` with approval for high-risk |
| PROGRAMME | `ada chat --programme` | propose only until apply |
| WORK | `--mission` / `ADA_CHAT_DEFAULT_MISSION` | full skills + snapshot |
| SETUP | `--setup` | setup assist (unchanged) |

## Operator commands

```bash
ada mission apply-template research --dry-run
ada programme apply packet.json    # Y/n confirm
ada chat --programme
ada chat --mission jarvis-ops
```
