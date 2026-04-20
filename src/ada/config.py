"""Paths and environment configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ada.tools.file_sandbox import load_denylist_paths_from_file, parse_sandbox_roots

# Default Gemini model: 2.5 Flash-Lite (verify against https://ai.google.dev/gemini-api/docs/models ).
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"


def _find_project_root() -> Path:
    """Directory containing pyproject.toml, or cwd."""
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


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

    @classmethod
    def load(cls) -> "Settings":
        root = _find_project_root()
        data_dir = Path(
            os.environ.get("ADA_DATA_DIR", str(root / "data"))
        ).expanduser()
        memory_dir = root / "memory"
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
        )

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


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
