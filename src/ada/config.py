"""Paths and environment configuration."""

from __future__ import annotations

import hashlib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from ada.tools.file_sandbox import load_denylist_paths_from_file, parse_sandbox_roots

# Default Gemini model: 2.5 Flash-Lite (verify against https://ai.google.dev/gemini-api/docs/models ).
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
PROFILE_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


def _find_project_root() -> Path:
    """Directory containing pyproject.toml, or cwd."""
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def _resolve_env_path(raw: str, *, project_root: Path) -> Path:
    """Expand user; non-absolute paths are resolved under project_root."""
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (project_root / p).resolve()
    return p.resolve()


def _unique_resolved_paths(*paths: Path) -> tuple[Path, ...]:
    seen: dict[str, Path] = {}
    for p in paths:
        r = p.resolve()
        seen[str(r)] = r
    return tuple(seen.values())


def build_file_deny_prefixes(
    *,
    project_root: Path,
    data_dir: Path,
    memory_dir: Path,
    primary_sandbox_root: Path,
    extra_comma_separated: str,
    denylist_file: Path | None,
) -> tuple[Path, ...]:
    """
    Always deny data_dir and memory_dir for file tools.
    Deny project_root when sandbox primary root strictly contains the project
    (e.g. home-wide sandbox, ADA lives in a subdirectory).
    """
    parts: list[Path] = [data_dir, memory_dir]
    proj = project_root.resolve()
    pri = primary_sandbox_root.resolve()
    if proj != pri and proj.is_relative_to(pri):
        parts.append(project_root)
    for raw in [p.strip() for p in extra_comma_separated.split(",") if p.strip()]:
        parts.append(Path(raw).expanduser())
    if denylist_file is not None:
        parts.extend(load_denylist_paths_from_file(denylist_file))
    return _unique_resolved_paths(*parts)


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    state_db_path: Path
    memory_dir: Path
    soul_path: Path
    master_path: Path
    wakeup_path: Path
    allowlist_path: Path
    gemini_api_key: str
    gemini_model: str
    max_tool_rounds: int
    persist_debounce_ms: int
    shell_max_output_bytes: int
    shell_timeout_sec: float
    stream_chunk_idle_timeout_sec: float
    stream_leg_max_wall_sec: float
    rewire_after_tombstone: bool
    enable_memory_tools: bool
    enable_plan_tools: bool
    enable_goal_recall_tool: bool
    memory_backups_dir: Path
    memory_max_append_bytes: int
    memory_max_file_bytes: int
    dream_max_soul_bytes: int
    dream_default_max_messages: int
    max_session_tokens: int
    enable_file_tools: bool
    file_sandbox_roots: tuple[Path, ...]
    file_max_read_bytes: int
    file_max_write_bytes: int
    file_deny_prefixes: tuple[Path, ...]
    file_deny_basenames_extra: frozenset[str]
    file_max_list_entries: int
    file_audit_denials: bool
    enable_web_tools: bool
    serper_api_key: str
    web_search_max_results: int
    web_search_timeout_sec: float
    web_fetch_mode: str
    web_fetch_max_urls: int
    web_fetch_max_chars: int
    web_fetch_max_bytes: int
    web_fetch_timeout_sec: float
    web_fetch_host_allowlist: frozenset[str]
    jina_reader_base_url: str
    jina_api_key: str
    enable_web_sources_tool: bool
    debug_stream: bool
    enable_knowledge_tools: bool
    knowledge_feed_host_allowlist: frozenset[str]
    ingest_rss_max_items: int
    ingest_rss_max_response_bytes: int
    ingest_rss_timeout_sec: float
    enable_knowledge_embeddings: bool
    knowledge_embedding_model: str
    knowledge_embedding_dim: int
    knowledge_embedding_min_cosine: float
    knowledge_default_retention_days: int | None
    ingest_gatekeeper: bool
    ingest_gate_model: str
    ingest_gate_max_output_tokens: int | None
    triage_model: str
    triage_batch_size: int
    triage_deep_dive_min_score: int
    triage_lead_daily_cap: int
    knowledge_tool_max_results: int
    knowledge_tool_excerpt_chars: int
    ada_kill_switch: bool
    ada_daily_token_budget: int | None
    ada_monthly_token_budget: int | None
    ada_max_task_steps: int | None
    enable_workflow_tools: bool
    # Phase 1 deterministic ingest
    dataforseo_login: str
    dataforseo_password: str
    ada_keyword_max_terms_per_run: int
    ada_keyword_location_code: int
    ada_keyword_language_code: str
    ada_keyword_terms: str
    ada_dataforseo_use_live: bool
    gov_api_host_allowlist: frozenset[str]
    ada_gets_poll_url: str
    ingest_rss_max_feeds: int | None
    brand_site_url: str
    brand_ingest_max_urls: int
    brand_ingest_timeout_sec: float
    brand_ingest_max_response_bytes: int
    enable_graph_lite: bool
    graph_lite_extract_limit: int
    graph_lite_token_cap_per_job: int
    graph_lite_extract_model: str
    # B2B pSEO / S3 publisher
    s3_bucket_name: str
    aws_region: str
    aws_endpoint_url: str | None
    ada_publish_min_unique_facts: int
    publish_draft_model: str
    # ENRICH live: optional DB-only preflight; skip Serper/Jina when graph is already dense
    enrich_suff_min_unique_facts: int | None
    enrich_suff_min_outgoing_edges: int
    enrich_suff_mode: str
    enrich_suff_force_web: bool
    enrich_suff_graph_refine: bool
    # DRAFT: subject subgraph in prompt; graph-anchored knowledge_items RAG (lexical / embedding)
    publish_draft_graph_anchored_knowledge: bool
    publish_draft_subgraph_max_json_chars: int
    publish_draft_knowledge_retrieval: bool
    publish_draft_knowledge_top_k: int
    publish_draft_knowledge_max_total_chars: int
    publish_draft_knowledge_excerpt_per_item: int
    publish_draft_knowledge_min_cosine: float
    publish_draft_knowledge_search_mode: str
    # DRAFT: if set, used when the model leaves `og_image` empty; else curated Unsplash CDN URL
    publish_draft_og_image_default: str
    # Unsplash API access key (https://api.unsplash.com) — DRAFT uses /photos/random with a
    # niche/category-biased query; falls back to static CDN if unset or on error.
    unsplash_access_key: str
    ada_matrix_enable: bool
    ada_matrix_max_enqueues: int
    ada_matrix_entity_types: frozenset[str]
    ada_matrix_planner: bool
    ada_matrix_planner_fallback_legacy: bool
    ada_matrix_planner_model: str
    # Profile isolation
    ada_require_profile_isolation: bool
    ada_profile: str
    ada_profile_data_root: Path
    profile_data_dir: Path
    profile_artifacts_dir: Path
    profile_audit_dir: Path
    profile_fingerprint: str
    # Directory containing policies/default.yaml (merge plane); see ADA_POLICY_ROOT.
    policy_root: Path
    # Analytics / GSC
    enable_gsc_ingest: bool
    gsc_site_url: str
    gsc_auth_mode: str
    gsc_service_account_json: str
    gsc_service_account_file: str
    gsc_api_base_url: str
    gsc_timeout_connect_sec: float
    gsc_timeout_read_sec: float
    gsc_timeout_total_sec: float
    gsc_retry_max_attempts: int
    gsc_retry_base_ms: int
    gsc_retry_max_ms: int
    gsc_page_size: int
    gsc_max_days_per_request: int
    gsc_max_rows_per_run: int
    gsc_dry_run_default: bool
    enable_gsc_read_tools: bool
    gsc_plan_default_lookback_days: int
    gsc_plan_max_items: int
    # Approval gates
    require_approval_for_enqueue: bool
    require_approval_for_publish: bool

    @classmethod
    def load(cls) -> "Settings":
        root = _find_project_root()
        require_profile_isolation = os.environ.get(
            "ADA_REQUIRE_PROFILE_ISOLATION", "0"
        ).strip().lower() in ("1", "true", "yes", "on")
        profile_raw = os.environ.get("ADA_PROFILE", "").strip().lower()
        profile_root_raw = os.environ.get("ADA_PROFILE_DATA_ROOT", "").strip()
        commercial_raw = os.environ.get("ADA_COMMERCIAL_DATA_DIR", "").strip()
        if profile_raw or profile_root_raw:
            if commercial_raw:
                raise ValueError(
                    "ADA_COMMERCIAL_DATA_DIR cannot be combined with ADA_PROFILE/ADA_PROFILE_DATA_ROOT"
                )
            if not profile_raw:
                raise ValueError("ADA_PROFILE is required when ADA_PROFILE_DATA_ROOT is set")
            if not PROFILE_SLUG_RE.match(profile_raw):
                raise ValueError(
                    "ADA_PROFILE must match ^[a-z0-9][a-z0-9_-]{1,63}$"
                )
            if not profile_root_raw:
                raise ValueError("ADA_PROFILE_DATA_ROOT is required when ADA_PROFILE is set")
            profile_data_root = Path(profile_root_raw).expanduser()
            if not profile_data_root.is_absolute():
                raise ValueError("ADA_PROFILE_DATA_ROOT must be an absolute path")
            profile_data_dir = (profile_data_root / profile_raw).resolve()
            data_dir = profile_data_dir
            ada_profile = profile_raw
            ada_profile_data_root = profile_data_root.resolve()
        elif commercial_raw:
            data_dir = Path(commercial_raw).expanduser()
            ada_profile = "legacy-commercial"
            ada_profile_data_root = data_dir.parent.resolve()
        else:
            data_dir = Path(
                os.environ.get("ADA_DATA_DIR", str(root / "data"))
            ).expanduser()
            ada_profile = "legacy-default"
            ada_profile_data_root = data_dir.parent.resolve()
        if require_profile_isolation and not profile_raw:
            raise ValueError(
                "ADA_REQUIRE_PROFILE_ISOLATION=1 requires ADA_PROFILE and ADA_PROFILE_DATA_ROOT"
            )
        profile_data_dir = data_dir.resolve()
        profile_artifacts_dir = profile_data_dir / "artifacts"
        profile_audit_dir = profile_data_dir / "audit"
        fp_seed = f"{ada_profile}|{profile_data_dir}|{root.resolve()}"
        profile_fingerprint = hashlib.sha256(fp_seed.encode("utf-8")).hexdigest()[:24]

        root_resolved = root.resolve()
        repo_memory = root_resolved / "memory"
        repo_policies = root_resolved / "policies"

        memory_env = os.environ.get("ADA_MEMORY_DIR", "").strip()
        if memory_env:
            memory_dir = _resolve_env_path(memory_env, project_root=root_resolved)
        elif profile_raw:
            memory_dir = (profile_data_dir / "memory").resolve()
        else:
            memory_dir = repo_memory

        policy_env = os.environ.get("ADA_POLICY_ROOT", "").strip()
        if policy_env:
            policy_root = _resolve_env_path(policy_env, project_root=root_resolved)
        elif profile_raw:
            profile_default_yaml = (profile_data_dir / "policies" / "default.yaml").resolve()
            if profile_default_yaml.is_file():
                policy_root = (profile_data_dir / "policies").resolve()
            else:
                policy_root = repo_policies
                print(
                    "ada: policy_root_fallback "
                    f"profile={profile_raw!r} policy_root={policy_root}",
                    file=sys.stderr,
                )
        else:
            policy_root = repo_policies

        # TODO(strict-fail-closed): optional fail-fast when profile mode uses repo policy fallback
        # (policy_root under project_root) for operators who require full policy isolation.

        if require_profile_isolation:
            try:
                mem_rel = memory_dir.is_relative_to(root_resolved)
            except (OSError, ValueError):
                mem_rel = False
            try:
                pol_rel = policy_root.is_relative_to(root_resolved)
            except (OSError, ValueError):
                pol_rel = False
            if mem_rel:
                raise ValueError(
                    "ADA_REQUIRE_PROFILE_ISOLATION=1 requires ADA_MEMORY_DIR outside "
                    f"the project tree; got {memory_dir} under {root_resolved}"
                )
            if pol_rel:
                raise ValueError(
                    "ADA_REQUIRE_PROFILE_ISOLATION=1 requires ADA_POLICY_ROOT outside "
                    f"the project tree; got {policy_root} under {root_resolved}"
                )

        key = os.environ.get("GEMINI_API_KEY", "").strip()
        model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()
        max_rounds = int(os.environ.get("ADA_MAX_TOOL_ROUNDS", "12"))
        debounce = int(os.environ.get("ADA_PERSIST_DEBOUNCE_MS", "100"))
        shell_max = int(os.environ.get("ADA_SHELL_MAX_OUTPUT_BYTES", "65536"))
        shell_timeout = float(os.environ.get("ADA_SHELL_TIMEOUT_SEC", "60"))
        stream_idle = float(os.environ.get("ADA_STREAM_CHUNK_IDLE_SEC", "120"))
        stream_wall = float(os.environ.get("ADA_STREAM_LEG_MAX_SEC", "600"))
        rewire = os.environ.get("ADA_REWIRE_AFTER_TOMBSTONE", "1").strip().lower() not in (
            "0",
            "false",
            "no",
        )
        mem_tools = os.environ.get("ADA_ENABLE_MEMORY_TOOLS", "1").strip().lower() not in (
            "0",
            "false",
            "no",
        )
        plan_tools = os.environ.get("ADA_ENABLE_PLAN_TOOLS", "1").strip().lower() not in (
            "0",
            "false",
            "no",
        )
        goal_recall_tool = os.environ.get(
            "ADA_ENABLE_GOAL_RECALL_TOOL", "1"
        ).strip().lower() not in ("0", "false", "no")
        mem_append = int(os.environ.get("ADA_MEMORY_MAX_APPEND_BYTES", "8192"))
        mem_file = int(os.environ.get("ADA_MEMORY_MAX_FILE_BYTES", str(512 * 1024)))
        dream_soul = int(os.environ.get("ADA_DREAM_MAX_SOUL_BYTES", "1024"))
        dream_msgs = int(os.environ.get("ADA_DREAM_MAX_MESSAGES", "60"))
        max_session_tokens = int(os.environ.get("ADA_MAX_SESSION_TOKENS", "50000"))
        file_tools = os.environ.get("ADA_ENABLE_FILE_TOOLS", "0").strip().lower() not in (
            "0",
            "false",
            "no",
        )
        sandbox_raw = os.environ.get("ADA_FILE_SANDBOX_ROOTS", "").strip()
        file_roots = parse_sandbox_roots(sandbox_raw, fallback=root)
        file_max_read = int(os.environ.get("ADA_FILE_MAX_READ_BYTES", str(512 * 1024)))
        file_max_write = int(os.environ.get("ADA_FILE_MAX_WRITE_BYTES", str(256 * 1024)))
        deny_extra = os.environ.get("ADA_FILE_DENY_PREFIXES", "").strip()
        deny_file_raw = os.environ.get("ADA_FILE_DENYLIST_FILE", "").strip()
        deny_file_path: Path | None = None
        if deny_file_raw:
            deny_file_path = Path(deny_file_raw).expanduser()
            if not deny_file_path.is_absolute():
                deny_file_path = (root / deny_file_path).resolve()
        file_deny_prefixes = build_file_deny_prefixes(
            project_root=root,
            data_dir=data_dir,
            memory_dir=memory_dir,
            primary_sandbox_root=file_roots[0],
            extra_comma_separated=deny_extra,
            denylist_file=deny_file_path,
        )
        extra_base_raw = os.environ.get("ADA_FILE_DENY_BASENAMES", "").strip()
        file_deny_basenames_extra = frozenset(
            p.strip() for p in extra_base_raw.split(",") if p.strip()
        )
        file_max_list_entries = max(
            1, int(os.environ.get("ADA_FILE_MAX_LIST_ENTRIES", "200"))
        )
        file_audit_denials = os.environ.get(
            "ADA_FILE_AUDIT_DENIALS", "1"
        ).strip().lower() not in ("0", "false", "no")
        web_tools = os.environ.get("ADA_ENABLE_WEB_TOOLS", "0").strip().lower() not in (
            "0",
            "false",
            "no",
        )
        serper = (
            os.environ.get("ADA_SERPER_API_KEY", "").strip()
            or os.environ.get("SERPER_API_KEY", "").strip()
        )
        web_search_max = max(
            1, int(os.environ.get("ADA_WEB_SEARCH_MAX_RESULTS", "10"))
        )
        web_search_to = float(os.environ.get("ADA_WEB_SEARCH_TIMEOUT_SEC", "30"))
        fetch_mode = os.environ.get("ADA_WEB_FETCH_MODE", "jina").strip().lower()
        if fetch_mode not in ("jina", "httpx"):
            fetch_mode = "jina"
        fetch_max_urls = max(1, int(os.environ.get("ADA_WEB_FETCH_MAX_URLS", "3")))
        fetch_max_chars = max(
            1024, int(os.environ.get("ADA_WEB_FETCH_MAX_CHARS", "65536"))
        )
        fetch_max_bytes = max(
            4096, int(os.environ.get("ADA_WEB_FETCH_MAX_BYTES", str(1024 * 512)))
        )
        fetch_to = float(os.environ.get("ADA_WEB_FETCH_TIMEOUT_SEC", "45"))
        allow_raw = os.environ.get("ADA_WEB_FETCH_HOST_ALLOWLIST", "").strip()
        host_allow = frozenset(
            p.strip().lower() for p in allow_raw.split(",") if p.strip()
        )
        jina_base = os.environ.get(
            "ADA_JINA_READER_URL",
            os.environ.get("JINA_READER_BASE_URL", "https://r.jina.ai/"),
        ).strip()
        if not jina_base.endswith("/"):
            jina_base = jina_base + "/"
        jina_key = os.environ.get("ADA_JINA_API_KEY", "").strip()
        web_sources_tool = os.environ.get(
            "ADA_ENABLE_WEB_SOURCES_TOOL", "0"
        ).strip().lower() not in ("0", "false", "no")
        debug_stream = os.environ.get("ADA_DEBUG_STREAM", "0").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        knowledge_tools = os.environ.get(
            "ADA_ENABLE_KNOWLEDGE_TOOLS", "0"
        ).strip().lower() not in ("0", "false", "no")
        know_hosts_raw = os.environ.get("ADA_KNOWLEDGE_FEED_HOST_ALLOWLIST", "").strip()
        knowledge_feed_host_allowlist = frozenset(
            h.strip().lower() for h in know_hosts_raw.split(",") if h.strip()
        )
        ingest_rss_max_items = max(1, int(os.environ.get("ADA_INGEST_RSS_MAX_ITEMS", "50")))
        ingest_rss_max_response_bytes = max(
            4096, int(os.environ.get("ADA_INGEST_RSS_MAX_RESPONSE_BYTES", "2000000"))
        )
        ingest_rss_timeout_sec = float(os.environ.get("ADA_INGEST_RSS_TIMEOUT_SEC", "45"))
        know_embed = os.environ.get(
            "ADA_KNOWLEDGE_EMBEDDINGS", "0"
        ).strip().lower() not in ("0", "false", "no")
        know_emb_model = os.environ.get(
            "ADA_KNOWLEDGE_EMBEDDING_MODEL", "gemini-embedding-001"
        ).strip()
        know_emb_dim = max(8, int(os.environ.get("ADA_KNOWLEDGE_EMBEDDING_DIM", "768")))
        know_emb_min = float(os.environ.get("ADA_KNOWLEDGE_EMBEDDING_MIN_COSINE", "0.25"))
        retention_raw = os.environ.get("ADA_KNOWLEDGE_DEFAULT_RETENTION_DAYS", "").strip()
        knowledge_default_retention_days: int | None = None
        if retention_raw:
            try:
                rd = int(retention_raw)
                if rd > 0:
                    knowledge_default_retention_days = rd
            except ValueError:
                knowledge_default_retention_days = None
        ingest_gatekeeper = os.environ.get(
            "ADA_INGEST_GATEKEEPER", "0"
        ).strip().lower() not in ("0", "false", "no")
        ingest_gate_model = os.environ.get(
            "ADA_INGEST_GATE_MODEL", DEFAULT_GEMINI_MODEL
        ).strip() or DEFAULT_GEMINI_MODEL
        gate_tok_raw = os.environ.get("ADA_INGEST_GATE_MAX_OUTPUT_TOKENS", "").strip()
        ingest_gate_max_output_tokens: int | None = None
        if gate_tok_raw:
            try:
                ingest_gate_max_output_tokens = max(64, int(gate_tok_raw))
            except ValueError:
                ingest_gate_max_output_tokens = None
        triage_model = os.environ.get("ADA_TRIAGE_MODEL", "").strip() or DEFAULT_GEMINI_MODEL
        triage_batch_size = max(1, int(os.environ.get("ADA_TRIAGE_BATCH_SIZE", "20")))
        _dd_raw = os.environ.get("ADA_TRIAGE_DEEP_DIVE_MIN_SCORE", "6").strip()
        try:
            triage_deep_dive_min_score = max(1, min(10, int(_dd_raw)))
        except ValueError:
            triage_deep_dive_min_score = 6
        triage_lead_daily_cap = max(
            0, int(os.environ.get("ADA_TRIAGE_LEAD_DAILY_CAP", "10"))
        )
        knowledge_tool_max_results = max(
            1, min(25, int(os.environ.get("ADA_KNOWLEDGE_TOOL_MAX_RESULTS", "8")))
        )
        knowledge_tool_excerpt_chars = max(
            200,
            min(
                4000,
                int(os.environ.get("ADA_KNOWLEDGE_TOOL_EXCERPT_CHARS", "1200")),
            ),
        )

        ada_kill_switch = os.environ.get("ADA_KILL_SWITCH", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

        def _optional_positive_int(name: str) -> int | None:
            raw = os.environ.get(name, "").strip()
            if not raw:
                return None
            try:
                v = int(raw)
                return v if v > 0 else None
            except ValueError:
                return None

        ada_daily_token_budget = _optional_positive_int("ADA_DAILY_TOKEN_BUDGET")
        ada_monthly_token_budget = _optional_positive_int("ADA_MONTHLY_TOKEN_BUDGET")
        _steps_raw = os.environ.get("ADA_MAX_TASK_STEPS", "").strip()
        ada_max_task_steps: int | None = None
        if _steps_raw:
            try:
                ada_max_task_steps = max(1, int(_steps_raw))
            except ValueError:
                ada_max_task_steps = None

        enable_workflow_tools = os.environ.get(
            "ADA_ENABLE_WORKFLOW_TOOLS", "0"
        ).strip().lower() in ("1", "true", "yes", "on")

        dataforseo_login = os.environ.get("DATAFORSEO_LOGIN", "").strip()
        dataforseo_password = os.environ.get("DATAFORSEO_PASSWORD", "").strip()
        ada_keyword_max_terms_per_run = max(
            1, int(os.environ.get("ADA_KEYWORD_MAX_TERMS_PER_RUN", "100"))
        )
        try:
            ada_keyword_location_code = int(
                os.environ.get("ADA_KEYWORD_LOCATION_CODE", "2004")
            )
        except ValueError:
            ada_keyword_location_code = 2004
        ada_keyword_language_code = os.environ.get(
            "ADA_KEYWORD_LANGUAGE_CODE", "en"
        ).strip() or "en"
        ada_keyword_terms = os.environ.get("ADA_KEYWORD_TERMS", "").strip()
        ada_dataforseo_use_live = os.environ.get(
            "ADA_DATAFORSEO_USE_LIVE", "0"
        ).strip().lower() in ("1", "true", "yes", "on")
        gov_api_raw = os.environ.get("ADA_GOV_API_HOST_ALLOWLIST", "").strip()
        gov_api_host_allowlist = frozenset(
            h.strip().lower() for h in gov_api_raw.split(",") if h.strip()
        )
        ada_gets_poll_url = os.environ.get(
            "ADA_GETS_POLL_URL",
            "https://www.gets.govt.nz/ExternalIndex.htm",
        ).strip() or "https://www.gets.govt.nz/ExternalIndex.htm"
        ingest_rss_max_feeds_raw = os.environ.get(
            "ADA_INGEST_RSS_MAX_FEEDS", ""
        ).strip()
        ingest_rss_max_feeds: int | None = None
        if ingest_rss_max_feeds_raw:
            try:
                ingest_rss_max_feeds = max(1, int(ingest_rss_max_feeds_raw))
            except ValueError:
                ingest_rss_max_feeds = None
        brand_site_url = os.environ.get("ADA_BRAND_SITE_URL", "").strip()
        brand_ingest_max_urls = max(
            1, min(20, int(os.environ.get("ADA_BRAND_INGEST_MAX_URLS", "8")))
        )
        brand_ingest_timeout_sec = float(
            os.environ.get("ADA_BRAND_INGEST_TIMEOUT_SEC", "30")
        )
        brand_ingest_max_response_bytes = max(
            4096, int(os.environ.get("ADA_BRAND_INGEST_MAX_RESPONSE_BYTES", "1500000"))
        )
        enable_graph_lite = os.environ.get(
            "ADA_ENABLE_GRAPH_LITE", "0"
        ).strip().lower() in ("1", "true", "yes", "on")
        graph_lite_extract_limit = max(
            1, min(500, int(os.environ.get("ADA_GRAPH_LITE_EXTRACT_LIMIT", "40")))
        )
        graph_lite_token_cap_per_job = max(
            256,
            int(os.environ.get("ADA_GRAPH_LITE_TOKEN_CAP_PER_JOB", "8000")),
        )
        graph_lite_extract_model = (
            os.environ.get("ADA_GRAPH_LITE_EXTRACT_MODEL", "").strip()
            or triage_model
        )

        s3_raw = os.environ.get("S3_BUCKET_NAME", "").strip() or os.environ.get(
            "ADA_S3_BUCKET", ""
        ).strip()
        aws_region = os.environ.get("AWS_REGION", "us-east-1").strip() or "us-east-1"
        aws_ep = os.environ.get("AWS_ENDPOINT_URL", "").strip() or None
        try:
            ada_publish_min = max(0, int(os.environ.get("ADA_PUBLISH_MIN_UNIQUE_FACTS", "3")))
        except ValueError:
            ada_publish_min = 3
        publish_draft_model = os.environ.get("ADA_PUBLISH_DRAFT_MODEL", "").strip() or (
            model or DEFAULT_GEMINI_MODEL
        )
        raw_esuf = os.environ.get("ADA_ENRICH_SUFF_MIN_UNIQUE_FACTS", "").strip()
        if not raw_esuf:
            enrich_suff_min_unique_facts: int | None = None
        else:
            try:
                enrich_suff_min_unique_facts = int(raw_esuf)
            except ValueError:
                enrich_suff_min_unique_facts = None
        try:
            enrich_suff_min_outgoing_edges = max(
                0, int(os.environ.get("ADA_ENRICH_SUFF_MIN_OUTGOING_EDGES", "0"))
            )
        except ValueError:
            enrich_suff_min_outgoing_edges = 0
        enrich_suff_mode = (os.environ.get("ADA_ENRICH_SUFF_MODE", "all").strip().lower() or "all")
        enrich_suff_force_web = os.environ.get(
            "ADA_ENRICH_SUFF_FORCE_WEB", "0"
        ).strip().lower() in ("1", "true", "yes", "on")
        enrich_suff_graph_refine = os.environ.get(
            "ADA_ENRICH_SUFF_GRAPH_REFINE", "0"
        ).strip().lower() in ("1", "true", "yes", "on")
        publish_draft_graph_anchored_knowledge = os.environ.get(
            "ADA_PUBLISH_DRAFT_GRAPH_ANCHORED", "1"
        ).strip().lower() in ("1", "true", "yes", "on")
        try:
            publish_draft_subgraph_max_json_chars = max(
                4096,
                int(os.environ.get("ADA_PUBLISH_DRAFT_SUBGRAPH_MAX_JSON", "40000")),
            )
        except ValueError:
            publish_draft_subgraph_max_json_chars = 40_000
        publish_draft_knowledge_retrieval = os.environ.get(
            "ADA_PUBLISH_DRAFT_KNOWLEDGE_RETRIEVAL", "0"
        ).strip().lower() in ("1", "true", "yes", "on")
        try:
            publish_draft_knowledge_top_k = max(
                1, int(os.environ.get("ADA_PUBLISH_DRAFT_KNOWLEDGE_TOP_K", "8"))
            )
        except ValueError:
            publish_draft_knowledge_top_k = 8
        try:
            publish_draft_knowledge_max_total_chars = max(
                500,
                int(os.environ.get("ADA_PUBLISH_DRAFT_KNOWLEDGE_MAX_TOTAL_CHARS", "12000")),
            )
        except ValueError:
            publish_draft_knowledge_max_total_chars = 12_000
        try:
            publish_draft_knowledge_excerpt_per_item = max(
                200,
                int(os.environ.get("ADA_PUBLISH_DRAFT_KNOWLEDGE_EXCERPT_PER_ITEM", "2000")),
            )
        except ValueError:
            publish_draft_knowledge_excerpt_per_item = 2000
        pdk_mcos = os.environ.get("ADA_PUBLISH_DRAFT_KNOWLEDGE_MIN_COSINE", "").strip()
        if pdk_mcos:
            try:
                publish_draft_knowledge_min_cosine = float(pdk_mcos)
            except ValueError:
                publish_draft_knowledge_min_cosine = know_emb_min
        else:
            publish_draft_knowledge_min_cosine = know_emb_min
        pdk_raw = os.environ.get("ADA_PUBLISH_DRAFT_KNOWLEDGE_SEARCH_MODE", "auto").strip()
        publish_draft_knowledge_search_mode = (pdk_raw or "auto").lower()
        publish_draft_og_image_default = os.environ.get(
            "ADA_PUBLISH_DRAFT_OG_IMAGE_DEFAULT", ""
        ).strip()
        unsplash_access_key = (
            os.environ.get("ADA_UNSPLASH_ACCESS_KEY", "").strip()
            or os.environ.get("UNSPLASH_ACCESS_KEY", "").strip()
        )
        ada_matrix_enable = os.environ.get("ADA_MATRIX_ENABLE", "0").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        try:
            ada_matrix_max = max(1, int(os.environ.get("ADA_MATRIX_MAX_ENQUEUES", "20")))
        except ValueError:
            ada_matrix_max = 20
        matrix_types_raw = os.environ.get("ADA_MATRIX_ENTITY_TYPES", "").strip()
        if matrix_types_raw:
            ada_matrix_types = frozenset(
                t.strip().lower() for t in matrix_types_raw.split(",") if t.strip()
            )
        else:
            ada_matrix_types = frozenset(
                {"service", "regulation", "organization", "jurisdiction"}
            )
        ada_matrix_planner = os.environ.get("ADA_MATRIX_PLANNER", "0").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        ada_matrix_planner_fallback_legacy = os.environ.get(
            "ADA_MATRIX_PLANNER_LEGACY_FALLBACK",
            "",
        ).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        ada_matrix_planner_model = (
            os.environ.get("ADA_MATRIX_PLANNER_MODEL", "").strip() or ""
        )

        enable_gsc_ingest = os.environ.get("ADA_ENABLE_GSC_INGEST", "0").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        gsc_site_url = os.environ.get("GSC_SITE_URL", "").strip()
        gsc_auth_mode = os.environ.get("GSC_AUTH_MODE", "service_account_json").strip()
        if gsc_auth_mode not in ("service_account_json",):
            raise ValueError("GSC_AUTH_MODE must be 'service_account_json'")
        gsc_service_account_json = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "").strip()
        gsc_service_account_file = os.environ.get("GSC_SERVICE_ACCOUNT_FILE", "").strip()
        gsc_api_base_url = os.environ.get(
            "GSC_API_BASE_URL", "https://www.googleapis.com/webmasters/v3"
        ).strip()
        gsc_timeout_connect_sec = float(os.environ.get("ADA_GSC_TIMEOUT_CONNECT_SEC", "5"))
        gsc_timeout_read_sec = float(os.environ.get("ADA_GSC_TIMEOUT_READ_SEC", "30"))
        gsc_timeout_total_sec = float(os.environ.get("ADA_GSC_TIMEOUT_TOTAL_SEC", "120"))
        gsc_retry_max_attempts = max(1, int(os.environ.get("ADA_GSC_RETRY_MAX_ATTEMPTS", "5")))
        gsc_retry_base_ms = max(10, int(os.environ.get("ADA_GSC_RETRY_BASE_MS", "250")))
        gsc_retry_max_ms = max(100, int(os.environ.get("ADA_GSC_RETRY_MAX_MS", "8000")))
        gsc_page_size = max(1, min(25000, int(os.environ.get("ADA_GSC_PAGE_SIZE", "25000"))))
        gsc_max_days_per_request = max(
            1, int(os.environ.get("ADA_GSC_MAX_DAYS_PER_REQUEST", "7"))
        )
        gsc_max_rows_per_run = max(100, int(os.environ.get("ADA_GSC_MAX_ROWS_PER_RUN", "200000")))
        gsc_dry_run_default = os.environ.get("ADA_GSC_DRY_RUN_DEFAULT", "0").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        enable_gsc_read_tools = os.environ.get(
            "ADA_ENABLE_GSC_READ_TOOLS", "0"
        ).strip().lower() in ("1", "true", "yes", "on")
        gsc_plan_default_lookback_days = max(
            1, int(os.environ.get("ADA_GSC_PLAN_DEFAULT_LOOKBACK_DAYS", "28"))
        )
        gsc_plan_max_items = max(1, min(200, int(os.environ.get("ADA_GSC_PLAN_MAX_ITEMS", "25"))))
        require_approval_for_enqueue = os.environ.get(
            "ADA_REQUIRE_APPROVAL_FOR_ENQUEUE", "0"
        ).strip().lower() in ("1", "true", "yes", "on")
        require_approval_for_publish = os.environ.get(
            "ADA_REQUIRE_APPROVAL_FOR_PUBLISH", "0"
        ).strip().lower() in ("1", "true", "yes", "on")

        return cls(
            project_root=root,
            data_dir=data_dir,
            state_db_path=data_dir / "state.db",
            memory_dir=memory_dir,
            soul_path=memory_dir / "soul.md",
            master_path=memory_dir / "master.md",
            wakeup_path=memory_dir / "wakeup.md",
            allowlist_path=memory_dir / "shell_allowlist.txt",
            gemini_api_key=key,
            gemini_model=model or DEFAULT_GEMINI_MODEL,
            max_tool_rounds=max_rounds,
            persist_debounce_ms=debounce,
            shell_max_output_bytes=shell_max,
            shell_timeout_sec=shell_timeout,
            stream_chunk_idle_timeout_sec=stream_idle,
            stream_leg_max_wall_sec=stream_wall,
            rewire_after_tombstone=rewire,
            enable_memory_tools=mem_tools,
            enable_plan_tools=plan_tools,
            enable_goal_recall_tool=goal_recall_tool,
            memory_backups_dir=memory_dir / "backups",
            memory_max_append_bytes=mem_append,
            memory_max_file_bytes=mem_file,
            dream_max_soul_bytes=dream_soul,
            dream_default_max_messages=dream_msgs,
            max_session_tokens=max_session_tokens,
            enable_file_tools=file_tools,
            file_sandbox_roots=file_roots,
            file_max_read_bytes=file_max_read,
            file_max_write_bytes=file_max_write,
            file_deny_prefixes=file_deny_prefixes,
            file_deny_basenames_extra=file_deny_basenames_extra,
            file_max_list_entries=file_max_list_entries,
            file_audit_denials=file_audit_denials,
            enable_web_tools=web_tools,
            serper_api_key=serper,
            web_search_max_results=web_search_max,
            web_search_timeout_sec=web_search_to,
            web_fetch_mode=fetch_mode,
            web_fetch_max_urls=fetch_max_urls,
            web_fetch_max_chars=fetch_max_chars,
            web_fetch_max_bytes=fetch_max_bytes,
            web_fetch_timeout_sec=fetch_to,
            web_fetch_host_allowlist=host_allow,
            jina_reader_base_url=jina_base,
            jina_api_key=jina_key,
            enable_web_sources_tool=web_sources_tool,
            debug_stream=debug_stream,
            enable_knowledge_tools=knowledge_tools,
            knowledge_feed_host_allowlist=knowledge_feed_host_allowlist,
            ingest_rss_max_items=ingest_rss_max_items,
            ingest_rss_max_response_bytes=ingest_rss_max_response_bytes,
            ingest_rss_timeout_sec=ingest_rss_timeout_sec,
            enable_knowledge_embeddings=know_embed,
            knowledge_embedding_model=know_emb_model or "gemini-embedding-001",
            knowledge_embedding_dim=know_emb_dim,
            knowledge_embedding_min_cosine=know_emb_min,
            knowledge_default_retention_days=knowledge_default_retention_days,
            ingest_gatekeeper=ingest_gatekeeper,
            ingest_gate_model=ingest_gate_model,
            ingest_gate_max_output_tokens=ingest_gate_max_output_tokens,
            triage_model=triage_model,
            triage_batch_size=triage_batch_size,
            triage_deep_dive_min_score=triage_deep_dive_min_score,
            triage_lead_daily_cap=triage_lead_daily_cap,
            knowledge_tool_max_results=knowledge_tool_max_results,
            knowledge_tool_excerpt_chars=knowledge_tool_excerpt_chars,
            ada_kill_switch=ada_kill_switch,
            ada_daily_token_budget=ada_daily_token_budget,
            ada_monthly_token_budget=ada_monthly_token_budget,
            ada_max_task_steps=ada_max_task_steps,
            enable_workflow_tools=enable_workflow_tools,
            dataforseo_login=dataforseo_login,
            dataforseo_password=dataforseo_password,
            ada_keyword_max_terms_per_run=ada_keyword_max_terms_per_run,
            ada_keyword_location_code=ada_keyword_location_code,
            ada_keyword_language_code=ada_keyword_language_code,
            ada_keyword_terms=ada_keyword_terms,
            ada_dataforseo_use_live=ada_dataforseo_use_live,
            gov_api_host_allowlist=gov_api_host_allowlist,
            ada_gets_poll_url=ada_gets_poll_url,
            ingest_rss_max_feeds=ingest_rss_max_feeds,
            brand_site_url=brand_site_url,
            brand_ingest_max_urls=brand_ingest_max_urls,
            brand_ingest_timeout_sec=brand_ingest_timeout_sec,
            brand_ingest_max_response_bytes=brand_ingest_max_response_bytes,
            enable_graph_lite=enable_graph_lite,
            graph_lite_extract_limit=graph_lite_extract_limit,
            graph_lite_token_cap_per_job=graph_lite_token_cap_per_job,
            graph_lite_extract_model=graph_lite_extract_model,
            s3_bucket_name=s3_raw,
            aws_region=aws_region,
            aws_endpoint_url=aws_ep,
            ada_publish_min_unique_facts=ada_publish_min,
            publish_draft_model=publish_draft_model,
            enrich_suff_min_unique_facts=enrich_suff_min_unique_facts,
            enrich_suff_min_outgoing_edges=enrich_suff_min_outgoing_edges,
            enrich_suff_mode=enrich_suff_mode,
            enrich_suff_force_web=enrich_suff_force_web,
            enrich_suff_graph_refine=enrich_suff_graph_refine,
            publish_draft_graph_anchored_knowledge=publish_draft_graph_anchored_knowledge,
            publish_draft_subgraph_max_json_chars=publish_draft_subgraph_max_json_chars,
            publish_draft_knowledge_retrieval=publish_draft_knowledge_retrieval,
            publish_draft_knowledge_top_k=publish_draft_knowledge_top_k,
            publish_draft_knowledge_max_total_chars=publish_draft_knowledge_max_total_chars,
            publish_draft_knowledge_excerpt_per_item=publish_draft_knowledge_excerpt_per_item,
            publish_draft_knowledge_min_cosine=publish_draft_knowledge_min_cosine,
            publish_draft_knowledge_search_mode=publish_draft_knowledge_search_mode,
            publish_draft_og_image_default=publish_draft_og_image_default,
            unsplash_access_key=unsplash_access_key,
            ada_matrix_enable=ada_matrix_enable,
            ada_matrix_max_enqueues=ada_matrix_max,
            ada_matrix_entity_types=ada_matrix_types,
            ada_matrix_planner=ada_matrix_planner,
            ada_matrix_planner_fallback_legacy=ada_matrix_planner_fallback_legacy,
            ada_matrix_planner_model=ada_matrix_planner_model,
            ada_require_profile_isolation=require_profile_isolation,
            ada_profile=ada_profile,
            ada_profile_data_root=ada_profile_data_root,
            profile_data_dir=profile_data_dir,
            profile_artifacts_dir=profile_artifacts_dir,
            profile_audit_dir=profile_audit_dir,
            profile_fingerprint=profile_fingerprint,
            policy_root=policy_root,
            enable_gsc_ingest=enable_gsc_ingest,
            gsc_site_url=gsc_site_url,
            gsc_auth_mode=gsc_auth_mode,
            gsc_service_account_json=gsc_service_account_json,
            gsc_service_account_file=gsc_service_account_file,
            gsc_api_base_url=gsc_api_base_url,
            gsc_timeout_connect_sec=gsc_timeout_connect_sec,
            gsc_timeout_read_sec=gsc_timeout_read_sec,
            gsc_timeout_total_sec=gsc_timeout_total_sec,
            gsc_retry_max_attempts=gsc_retry_max_attempts,
            gsc_retry_base_ms=gsc_retry_base_ms,
            gsc_retry_max_ms=gsc_retry_max_ms,
            gsc_page_size=gsc_page_size,
            gsc_max_days_per_request=gsc_max_days_per_request,
            gsc_max_rows_per_run=gsc_max_rows_per_run,
            gsc_dry_run_default=gsc_dry_run_default,
            enable_gsc_read_tools=enable_gsc_read_tools,
            gsc_plan_default_lookback_days=gsc_plan_default_lookback_days,
            gsc_plan_max_items=gsc_plan_max_items,
            require_approval_for_enqueue=require_approval_for_enqueue,
            require_approval_for_publish=require_approval_for_publish,
        )

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.profile_artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.profile_audit_dir.mkdir(parents=True, exist_ok=True)
        repo_memory = (self.project_root / "memory").resolve()
        if self.memory_dir.resolve() != repo_memory:
            self.memory_dir.mkdir(parents=True, exist_ok=True)


def load_dotenv_if_present() -> None:
    """Populate os.environ from .env at project root if file exists."""
    root = _find_project_root()
    env_path = root / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v
