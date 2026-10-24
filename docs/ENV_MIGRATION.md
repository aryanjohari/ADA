# Environment migration — profile vs mission

Programme-shaped variables move from profile `.env` to `missions.defaults_json`. Source of truth for the mapping: [`src/ada/config_deprecation.py`](../src/ada/config_deprecation.py).

## Stay in profile `.env`

| Category | Variables |
|----------|-----------|
| Secrets | `GEMINI_API_KEY`, `SERPER_API_KEY`, … |
| Profile paths | `ADA_PROFILE`, `ADA_PROFILE_DATA_ROOT`, `ADA_MEMORY_DIR`, `ADA_POLICY_ROOT` |
| Chat binding | `ADA_CHAT_DEFAULT_MISSION` (greenfield: `jarvis-ops`) |
| Job plane | `ADA_JOB_QUEUE` (greenfield: `system_jobs`) |
| Tool toggles | `ADA_ENABLE_*` |
| Caps | `ADA_MAX_TOOL_ROUNDS`, `ADA_DAILY_TOKEN_BUDGET`, shell/web/file limits |
| Host allowlists | `ADA_WEB_FETCH_HOST_ALLOWLIST`, `ADA_KNOWLEDGE_FEED_HOST_ALLOWLIST`, `ADA_GOV_API_HOST_ALLOWLIST` |
| Kill switch | `ADA_KILL_SWITCH` |

## Move to `missions.defaults_json`

| Env (deprecated) | JSON key |
|------------------|----------|
| `ADA_PROJECT_ID` | `project_id` |
| `ADA_CAMPAIGN_ID` | `campaign_id` |
| `ADA_BRAND_SITE_URL` | `brand_site_url` |
| `GSC_SITE_URL` | `gsc_site_url` |
| `ADA_KEYWORD_TERMS` | `keyword_terms` |
| `ADA_KEYWORD_LOCATION_CODE` | `keyword_location_code` |
| `ADA_KEYWORD_LANGUAGE_CODE` | `keyword_language_code` |
| `ADA_KEYWORD_MAX_TERMS_PER_RUN` | `keyword_max_terms_per_run` |
| `ADA_GETS_POLL_URL` | `gets_poll_url` |
| `ADA_MATRIX_ENTITY_TYPES` | `matrix_entity_types` (list) |
| `ADA_MATRIX_MAX_ENQUEUES` | `matrix_max_enqueues` |
| `ADA_PUBLISH_MIN_UNIQUE_FACTS` | `publish_min_unique_facts` |
| `ADA_TRIAGE_LEAD_DAILY_CAP` | `triage_lead_daily_cap` |

Template: [`templates/mission_defaults.json`](../templates/mission_defaults.json).

## Migrate workflow

```bash
# Preview patch from current env
ada mission migrate-env jarvis-ops

# Write into DB
ada mission migrate-env jarvis-ops --apply
```

Then remove deprecated keys from `.env` to silence warnings (`Settings.load` → `_warn_deprecated_envs`).

## Read path (Phase A)

| Consumer | Mission vs env |
|----------|----------------|
| `ada mission tick` (GSC job) | `defaults_json` merged into job action; **A10** overlays `gsc_site_url` from mission over env when both set |
| `ada matrix-scan` ISR ids | `resolve_matrix_isr_ids` — mission `project_id` / `campaign_id` over env |
| `workflow enqueue` (playbook params) | policy → mission defaults → params (playbook `allowed_params` only) |
| `ada ingest-*`, `triage`, `matrix-scan` limits | Still **`Settings` / env** in Phase A |

Honest rule: **ingest paths still prefer env today** until Phase B.

## Suppress warnings

```bash
# Only after you accept env-as-global fallback
ADA_DEPRECATED_ENV_SUPPRESS=1
```

## Examples

Greenfield profile: [`profiles/jarvis.env.example`](../profiles/jarvis.env.example) — no `GSC_SITE_URL`.

```json
{
  "project_id": "jarvis-main",
  "campaign_id": "ops",
  "gsc_site_url": "https://example.com/"
}
```

Use fake secrets in tests only; never commit real keys.
