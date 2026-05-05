#!/usr/bin/env bash
# Keyword track: GSC ingest → keyword-select → workflow enqueue publish_keyword_v1.
# Prerequisites:
#   - ADA_ENABLE_GSC_INGEST=1 and GSC_* credentials in .env
#   - jq(1) for JSON merge
#   - ADA_KEYWORD_ENTITY_ID, ADA_KEYWORD_SITE, ADA_KEYWORD_START_DATE, ADA_KEYWORD_END_DATE
#   - ADA_PROJECT_ID, ADA_CAMPAIGN_ID, ADA_KEYWORD_NICHE (niche string for publish params)
# Optional: ADA_KEYWORD_IDEMPOTENCY_KEY for safe reruns (passed to --idempotency-key)
# Optional: ADA_MISSION_SLUG or MISSION_SLUG — passed through to ada workflow enqueue --mission (scopes workflows/tasks).
# Note: publish_keyword_v1 has NO graph GATE; ADA_REQUIRE_APPROVAL_FOR_PUBLISH still gates DEPLOY when set.
set -euo pipefail

ROOT="${ADA_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$ROOT"

if [[ -f "${ROOT}/.venv/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "${ROOT}/.venv/bin/activate"
fi

: "${ADA_KEYWORD_ENTITY_ID:?set ADA_KEYWORD_ENTITY_ID}"
: "${ADA_KEYWORD_SITE:?set ADA_KEYWORD_SITE}"
: "${ADA_KEYWORD_START_DATE:?set ADA_KEYWORD_START_DATE}"
: "${ADA_KEYWORD_END_DATE:?set ADA_KEYWORD_END_DATE}"
: "${ADA_PROJECT_ID:?set ADA_PROJECT_ID}"
: "${ADA_CAMPAIGN_ID:?set ADA_CAMPAIGN_ID}"
: "${ADA_KEYWORD_NICHE:?set ADA_KEYWORD_NICHE}"

command -v jq >/dev/null 2>&1 || {
  echo "jq is required for ada_keyword_track.sh" >&2
  exit 1
}

GSC_DAYS="${ADA_KEYWORD_GSC_DAYS:-28}"
ada ingest-gsc --site "${ADA_KEYWORD_SITE}" --days "${GSC_DAYS}" --dimensions "date,query,page,country,device" --row-limit 25000

SEL_JSON="$(ada keyword-select \
  --entity-id "${ADA_KEYWORD_ENTITY_ID}" \
  --site "${ADA_KEYWORD_SITE}" \
  --start-date "${ADA_KEYWORD_START_DATE}" \
  --end-date "${ADA_KEYWORD_END_DATE}")"

if ! jq -e '.target_keyword_cluster | length > 0' <<<"${SEL_JSON}" >/dev/null 2>&1; then
  echo "keyword-select: no target_keyword_cluster (fallback or empty)" >&2
  echo "${SEL_JSON}" >&2
  exit 1
fi

PARAMS_JSON="$(jq -n \
  --argjson sel "${SEL_JSON}" \
  --arg project_id "${ADA_PROJECT_ID}" \
  --arg campaign_id "${ADA_CAMPAIGN_ID}" \
  --arg niche "${ADA_KEYWORD_NICHE}" \
  '{
    target_keyword_cluster: $sel.target_keyword_cluster,
    keyword_source: $sel.keyword_source,
    project_id: $project_id,
    campaign_id: $campaign_id,
    niche: $niche
  } | with_entries(select(.value != null))')"

IDEM_ARGS=()
if [[ -n "${ADA_KEYWORD_IDEMPOTENCY_KEY:-}" ]]; then
  IDEM_ARGS=(--idempotency-key "${ADA_KEYWORD_IDEMPOTENCY_KEY}")
fi

MS_ARGS=()
MS="${ADA_MISSION_SLUG:-${MISSION_SLUG:-}}"
if [[ -n "${MS}" ]]; then
  MS_ARGS=(--mission "${MS}")
fi

ada workflow enqueue \
  --kind publish_keyword_v1 \
  --goal "Publish keyword-led page: $(jq -r '.target_keyword_cluster' <<<"${PARAMS_JSON}")" \
  --params-json "${PARAMS_JSON}" \
  "${MS_ARGS[@]}" \
  "${IDEM_ARGS[@]}"
