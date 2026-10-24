# Lab bucket

Mission-scoped programmes — research, job hunt, ISR (later). Canonical map: [ADA_ENTITY_BUCKETS.md](../ADA_ENTITY_BUCKETS.md).

Templates: [PROGRAMME_TEMPLATES.md](../PROGRAMME_TEMPLATES.md) · Apply flow: [ADA_CORE_OPS.md](../ADA_CORE_OPS.md).

---

## When to create a mission slug

Create a slug when you have a **programme** (template + pack + `skills_enabled` + optional schedule), not for a small habit.

| Do | Don't |
|----|-------|
| `ada mission apply-template research` | New slug for “remember gym” (use Friend primitive + tags) |
| Distinct `brief_md`, knowledge sources, cron | One mission per skill you might add later |

Invariant: **mission = programme folder (hat), not a feature.**

---

## Apply flow

1. Pick template under `templates/missions/*.yaml`.
2. `ada mission apply-template <name> -y` or Streamlit Plan **Apply programme**.
3. Install cron from `{data_dir}/artifacts/cron/<slug>.snippet`.
4. Run skills via `ada chat --agent --mission <slug>` or HUD **Agent** + Run action.

Motor enforces `skills_enabled` + pack allowlist ([HANDS_CONTRACT.md](../HANDS_CONTRACT.md)).

---

## Workflows (H5 bypass)

Direct workflow enqueue (`ada workflow enqueue`, CLI, internal paths) **does not** pass motor `skills_enabled` gate. Document operator intent; prefer skills for scheduled Lab work. See HANDS_CONTRACT § **Bypass (out of H5 scope)**.

Entity Chat must **not** call `enqueue_workflow`.

---

## GSC two-site pattern

Set per-mission site URL in packet / `defaults_json`:

```yaml
defaults_json:
  gsc_site_url: https://example.com/
```

Mission value wins over deprecated env `GSC_SITE_URL`. Example template: [`research.yaml`](../../templates/missions/research.yaml). Resolver: `src/ada/mission_defaults_resolve.py`.

Do **not** put GSC/matrix jobs on default `ada_ops` House cron.

---

## ISR

Defer ISR publish programmes until House daily loop (brief + tick) is reliable. Use `isr-research` / `isr-publish` templates only when ready — separate slug from `ada_ops`.

---

## Bridge to Friend

Lab graph and mission knowledge stay scoped until you approve a summary and `log_memory` with tag `lab-summary`. See [MEMORY_OPS.md](../MEMORY_OPS.md).

---

## Related

- [FRIEND.md](FRIEND.md) · [HOUSE.md](HOUSE.md)
- [TOOL_EXTENSION_GUIDE.md](../TOOL_EXTENSION_GUIDE.md)
- [use_cases/INDEX.md](../use_cases/INDEX.md) — planned Lab use cases
