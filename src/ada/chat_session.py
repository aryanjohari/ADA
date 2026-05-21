"""Shared chat session for CLI REPL and Streamlit (H3 surfaces: chat | plan | agent | setup)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from ada.chat_capability import (
    ChatCapabilityProfile,
    build_profile_orchestrate_flags,
    profile_for_surface,
    profile_work_legacy,
)
from ada.chat_ingress import (
    ChatIngressMode,
    ChatSurfaceMode,
    resolve_chat_ingress_mode,
    resolve_chat_surface_mode,
)
from ada.config import Settings
from ada.orchestration_profile import (
    INTERACTIVE_FAST,
    SETUP_ASSIST,
    orchestrate_turn_kwargs,
)
from ada.orchestrator import (
    SessionTokenLimitExceeded,
    file_guard_audit_hook,
    orchestrate_turn,
)
from ada.profile_runtime import enforce_profile_identity
from ada.mission_control.inject_policy import (
    should_inject_profile_digest,
    should_inject_programme_digest,
)
from ada.mission_control.profile_digest import build_profile_digest
from ada.mission_control.programme_digest import build_programme_digest
from ada.observability.queries import open_readonly_connection
from ada.prompt import (
    build_system_instruction,
    format_allowlist_summary,
    format_file_tools_note,
    format_knowledge_tools_note,
    format_profile_digest_appendix,
    format_programme_digest_appendix,
    format_schema_digest_note,
    format_session_web_sources_list_note,
    format_web_tools_note,
    format_workflow_tools_note,
    read_soul_text,
    read_text_file,
)
from ada.query_engine import TASK_KIND_CHAT, QueryEngine
from ada.tool_executor import FileToolConfig, MemoryToolConfig, build_web_tool_config
from ada.tools.shell_allowlist import load_allowlist_exact_lines


def _memory_tool_config(settings: Settings) -> MemoryToolConfig | None:
    if not settings.enable_memory_tools:
        return None
    return MemoryToolConfig(
        master_path=settings.master_path,
        soul_path=settings.soul_path,
        backups_dir=settings.memory_backups_dir,
        memory_dir=settings.memory_dir,
        max_append_bytes=settings.memory_max_append_bytes,
        max_file_bytes=settings.memory_max_file_bytes,
    )


def _file_tool_config(settings: Settings) -> FileToolConfig | None:
    if not settings.enable_file_tools:
        return None
    roots = settings.file_sandbox_roots
    return FileToolConfig(
        roots=roots,
        primary_root=roots[0],
        max_read_bytes=settings.file_max_read_bytes,
        max_write_bytes=settings.file_max_write_bytes,
        deny_prefixes=settings.file_deny_prefixes,
        deny_basenames_extra=settings.file_deny_basenames_extra,
        max_list_entries=settings.file_max_list_entries,
    )


def _boot_state_key(task_id: int) -> str:
    return f"session.{task_id}.boot_complete"


def _user_turn_count_key(task_id: int) -> str:
    return f"session.{task_id}.user_turn_count"


async def complete_chat_task_if_any(
    settings: Settings,
    task_id: int | None,
    *,
    schema_path: Path | None = None,
) -> None:
    """Mark a prior interactive chat task completed (e.g. Streamlit session rotation)."""
    if task_id is None:
        return
    if schema_path is None:
        schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    try:
        await qe.update_task(int(task_id), status="completed")
    finally:
        await qe.close()


def chat_setup_mode_enabled(explicit: bool) -> bool:
    if explicit:
        return True
    return os.environ.get("ADA_CHAT_SETUP_MODE", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


async def resolve_chat_mission_id(
    qe: QueryEngine,
    settings: Settings,
    mission_slug: str | None,
    *,
    apply_env_default: bool = True,
) -> int | None:
    slug = (mission_slug or "").strip()
    if not slug and apply_env_default:
        slug = os.environ.get("ADA_CHAT_DEFAULT_MISSION", "").strip()
    if not slug:
        return None
    row = await qe.get_mission_by_slug(slug)
    if row is None:
        raise ValueError(f"no mission with slug {slug!r}")
    return int(row["id"])


def _resolved_mission_slug(
    mission_slug: str | None,
    *,
    apply_env_default: bool,
) -> str | None:
    slug = (mission_slug or "").strip()
    if not slug and apply_env_default:
        slug = os.environ.get("ADA_CHAT_DEFAULT_MISSION", "").strip()
    return slug or None


def mission_control_snapshot_fn(
    settings: Settings,
    *,
    surface: ChatSurfaceMode,
    mission_id: int | None,
    mission_slug: str | None,
    effective_mission_id: int | None,
) -> Callable[[], Awaitable[dict[str, Any]]] | None:
    from ada.mission_control.snapshot import build_snapshot_from_settings

    if surface in (ChatSurfaceMode.CHAT, ChatSurfaceMode.PLAN):
        async def _profile_fn() -> dict[str, Any]:
            return build_snapshot_from_settings(
                settings,
                mission_id=None,
                mission_slug=None,
                profile_scope=True,
                include_programme=False,
            )

        return _profile_fn

    scope_id = mission_id if mission_id is not None else effective_mission_id
    if scope_id is None:
        if surface == ChatSurfaceMode.AGENT:
            async def _agent_profile_fn() -> dict[str, Any]:
                return build_snapshot_from_settings(
                    settings,
                    mission_id=None,
                    mission_slug=None,
                    profile_scope=True,
                    include_programme=False,
                )

            return _agent_profile_fn
        return None
    slug = (mission_slug or "").strip()
    if not slug:
        return None

    async def _mission_fn() -> dict[str, Any]:
        return build_snapshot_from_settings(
            settings,
            mission_id=scope_id,
            mission_slug=slug,
            profile_scope=True,
            include_programme=True,
        )

    return _mission_fn


def _orchestrate_profile_kwargs(
    settings: Settings, *, setup_mode: bool, web_cfg: object | None
) -> dict[str, object]:
    if not setup_mode:
        return {}
    return orchestrate_turn_kwargs(
        SETUP_ASSIST,
        base_max_tool_rounds=settings.max_tool_rounds,
        include_gsc_read_tools=settings.enable_gsc_read_tools,
        web_config=web_cfg,
    )


@dataclass
class ChatSession:
    """One interactive chat task bound to surface mode and capability profile."""

    qe: QueryEngine
    settings: Settings
    task_id: int
    surface: ChatSurfaceMode
    mission_id: int | None
    mission_slug: str | None
    default_mission_slug: str | None
    effective_mission_id: int | None
    ingress: ChatIngressMode
    profile: ChatCapabilityProfile
    sys_instr: str
    allow: list[str]
    file_cfg: FileToolConfig | None
    web_cfg: Any
    profile_kw: dict[str, object]
    snap_fn: Callable[[], Awaitable[dict[str, Any]]] | None
    entity_mode: bool
    plan_mode: bool
    wakeup: str

    @property
    def include_run_skill(self) -> bool:
        return self.profile.include_run_skill

    @property
    def include_propose(self) -> bool:
        return self.profile.include_propose_programme

    @property
    def knowledge_tool_subset(self) -> frozenset[str] | None:
        return self.profile.knowledge_tool_subset

    @classmethod
    async def open(
        cls,
        settings: Settings,
        *,
        new_session: bool = False,
        surface_mode: ChatSurfaceMode | None = None,
        setup_mode: bool = False,
        plan_mode: bool = False,
        agent_mode: bool = False,
        mission_slug: str | None = None,
        programme_mode: bool = False,
        apply_env_default: bool = True,
        legacy_work: bool = False,
        schema_path: Path | None = None,
    ) -> ChatSession:
        settings.ensure_data_dir()
        if schema_path is None:
            schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
        qe = QueryEngine(
            settings.state_db_path,
            schema_path,
            debounce_ms=settings.persist_debounce_ms,
        )
        await qe.connect()
        await enforce_profile_identity(qe, settings)
        setup_mode = chat_setup_mode_enabled(setup_mode)
        if programme_mode:
            print(
                "ada chat --programme is deprecated; use `ada chat --plan` for programme design.",
                file=sys.stderr,
            )
        if surface_mode is None:
            surface_mode = resolve_chat_surface_mode(
                setup_mode=setup_mode,
                plan_mode=plan_mode or programme_mode,
                agent_mode=agent_mode or legacy_work,
            )

        resolved_slug = _resolved_mission_slug(
            mission_slug, apply_env_default=apply_env_default
        )
        default_mission_slug: str | None = None
        if surface_mode == ChatSurfaceMode.AGENT and resolved_slug:
            default_mission_slug = resolved_slug

        bind_task_mission = legacy_work or surface_mode == ChatSurfaceMode.SETUP
        mission_id: int | None = None
        if bind_task_mission and resolved_slug:
            mission_id = await resolve_chat_mission_id(
                qe,
                settings,
                resolved_slug,
                apply_env_default=apply_env_default and legacy_work,
            )

        effective_mission_id: int | None = None
        if surface_mode == ChatSurfaceMode.AGENT and default_mission_slug:
            row = await qe.get_mission_by_slug(default_mission_slug)
            if row is not None:
                effective_mission_id = int(row["id"])

        if legacy_work:
            profile = profile_work_legacy(settings)
        else:
            profile = profile_for_surface(surface_mode, settings)

        ingress = resolve_chat_ingress_mode(
            setup_mode=setup_mode,
            programme_mode=False,
            mission_id=mission_id if legacy_work else None,
            surface=surface_mode,
        )
        entity_mode = profile.entity_harness
        plan_mode_h = surface_mode == ChatSurfaceMode.PLAN
        snap_fn = mission_control_snapshot_fn(
            settings,
            surface=surface_mode,
            mission_id=mission_id,
            mission_slug=resolved_slug or default_mission_slug,
            effective_mission_id=effective_mission_id,
        )

        task_mission_id = mission_id if bind_task_mission else None
        if new_session:
            task_id = await qe.insert_task(
                "Interactive session",
                status="executing",
                task_kind=TASK_KIND_CHAT,
                mission_id=task_mission_id,
            )
        else:
            existing = await qe.latest_cli_session_task_id()
            if existing is not None:
                task_id = existing
                await qe.update_task(task_id, status="executing")
                if task_mission_id is not None:
                    await qe.attach_task_to_mission(task_id, task_mission_id)
            else:
                task_id = await qe.insert_task(
                    "Interactive session",
                    status="executing",
                    task_kind=TASK_KIND_CHAT,
                    mission_id=task_mission_id,
                )

        allow = load_allowlist_exact_lines(settings.allowlist_path)
        soul = read_soul_text(settings.soul_path)
        master = read_text_file(settings.master_path)
        wakeup = read_text_file(settings.wakeup_path)
        file_note = (
            format_file_tools_note(settings) if profile.include_file_tools else None
        )
        web_note = format_web_tools_note(settings) if settings.enable_web_tools else None
        digest_note = format_schema_digest_note(
            read_text_file(settings.memory_dir / "schema_digest.md")
        )
        ws_list_note = format_session_web_sources_list_note(settings)
        knowledge_note = format_knowledge_tools_note(settings)
        workflow_note = (
            format_workflow_tools_note(settings)
            if profile.include_workflow_status
            else None
        )
        chat_slug_hint = default_mission_slug or resolved_slug
        sys_instr = build_system_instruction(
            soul_text=soul,
            master_text=master,
            state_db_display_path=str(settings.state_db_path),
            allowlist_summary=format_allowlist_summary(allow),
            file_tools_note=file_note if not entity_mode else None,
            web_tools_note=web_note,
            schema_digest_note=digest_note,
            session_web_sources_list_note=ws_list_note,
            knowledge_tools_note=knowledge_note if not entity_mode else None,
            workflow_tools_note=workflow_note,
            worker_mode=False,
            setup_mode=surface_mode == ChatSurfaceMode.SETUP,
            programme_mode=False,
            entity_mode=entity_mode,
            plan_mode=plan_mode_h,
            agent_mode=surface_mode == ChatSurfaceMode.AGENT,
            mission_bound=profile.mission_bound_harness and bool(chat_slug_hint),
            default_mission_slug=chat_slug_hint,
        )
        file_cfg = _file_tool_config(settings) if profile.include_file_tools else None
        web_cfg = build_web_tool_config(settings)
        profile_kw = _orchestrate_profile_kwargs(
            settings,
            setup_mode=surface_mode == ChatSurfaceMode.SETUP,
            web_cfg=web_cfg,
        )
        if (
            surface_mode != ChatSurfaceMode.SETUP
            and os.environ.get("ADA_INTERACTION_PROFILE", "").strip().lower()
            == "interactive_fast"
        ):
            profile_kw = orchestrate_turn_kwargs(
                INTERACTIVE_FAST,
                base_max_tool_rounds=settings.max_tool_rounds,
                include_gsc_read_tools=settings.enable_gsc_read_tools,
                web_config=web_cfg,
            )

        return cls(
            qe=qe,
            settings=settings,
            task_id=task_id,
            surface=surface_mode,
            mission_id=task_mission_id,
            mission_slug=resolved_slug or default_mission_slug,
            default_mission_slug=default_mission_slug,
            effective_mission_id=effective_mission_id,
            ingress=ingress,
            profile=profile,
            sys_instr=sys_instr,
            allow=allow,
            file_cfg=file_cfg,
            web_cfg=web_cfg,
            profile_kw=profile_kw,
            snap_fn=snap_fn,
            entity_mode=entity_mode,
            plan_mode=plan_mode_h,
            wakeup=wakeup,
        )

    async def close(self) -> None:
        await self.qe.close()

    def _orchestrate_common(self) -> dict[str, Any]:
        s = self.settings
        entity = self.entity_mode
        prof_flags = build_profile_orchestrate_flags(self.profile, s, entity_mode=entity)
        kw: dict[str, Any] = {
            "qe": self.qe,
            "session_id": self.task_id,
            "system_instruction": self.sys_instr,
            "api_key": s.gemini_api_key,
            "model": s.gemini_model,
            "shell_allowlist": self.allow,
            "max_tool_rounds": s.max_tool_rounds,
            "shell_max_output_bytes": s.shell_max_output_bytes,
            "shell_timeout_sec": s.shell_timeout_sec,
            "stream_chunk_idle_timeout_sec": s.stream_chunk_idle_timeout_sec,
            "stream_leg_max_wall_sec": s.stream_leg_max_wall_sec,
            "rewire_after_tombstone": s.rewire_after_tombstone,
            "enable_memory_tools": s.enable_memory_tools,
            "memory_config": _memory_tool_config(s),
            "include_goal_recall_tool": s.enable_goal_recall_tool,
            "file_config": self.file_cfg,
            "max_session_tokens": s.max_session_tokens,
            "on_file_guard_violation": file_guard_audit_hook(
                self.qe,
                self.task_id,
                enabled=s.file_audit_denials,
            ),
            "web_config": self.web_cfg,
            "enable_list_session_web_sources": s.enable_web_sources_tool,
            "knowledge_feed_host_allowlist": s.knowledge_feed_host_allowlist,
            "knowledge_embeddings_enabled": s.enable_knowledge_embeddings,
            "knowledge_embedding_model": s.knowledge_embedding_model,
            "knowledge_embedding_dim": s.knowledge_embedding_dim,
            "knowledge_embedding_min_cosine": s.knowledge_embedding_min_cosine,
            "knowledge_tool_max_results": s.knowledge_tool_max_results,
            "knowledge_tool_excerpt_chars": s.knowledge_tool_excerpt_chars,
            "debug_stream": s.debug_stream,
            "workflow_max_steps": s.ada_max_task_steps,
            "mission_control_snapshot_fn": self.snap_fn,
            "motor_settings": s,
            "chat_mission_slug": self.default_mission_slug or self.mission_slug,
            "effective_mission_id": self.effective_mission_id,
            **prof_flags,
            **self.profile_kw,
        }
        return kw

    async def run_boot_if_needed(
        self,
        *,
        on_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        if not self.settings.gemini_api_key:
            return
        if not self.wakeup.strip():
            return
        if await self.qe.state_get(_boot_state_key(self.task_id)) is not None:
            return

        async def _noop(chunk: str) -> None:
            if on_delta is not None:
                await on_delta(chunk)

        cb = on_delta if on_delta is not None else _noop
        await orchestrate_turn(
            user_text=self.wakeup.strip(),
            on_delta=cb,
            **self._orchestrate_common(),
        )
        await self.qe.state_set(_boot_state_key(self.task_id), "1")

    async def _turn_harness_appendix_for_message(self, user_text: str) -> str | None:
        from ada.mission_control.inject_policy import (
            should_inject_programme_digest_for_chat,
        )
        from ada.observability.queries import mission_id_from_slug

        turn_key = _user_turn_count_key(self.task_id)
        raw = await self.qe.state_get(turn_key)
        try:
            turn_before = int(raw) if raw is not None else 0
        except ValueError:
            turn_before = 0

        s = self.settings
        conn = open_readonly_connection(s.state_db_path)
        try:
            inject_chat_prog, matched_slug = should_inject_programme_digest_for_chat(
                surface=self.surface,
                mission_id=self.mission_id,
                user_turn_count_before=turn_before,
                user_text=user_text,
                conn=conn,
            )
            if inject_chat_prog and matched_slug:
                prog_mid = mission_id_from_slug(conn, matched_slug)
                if prog_mid is not None:
                    digest = build_programme_digest(
                        conn,
                        prog_mid,
                        mission_slug=matched_slug,
                        profile_scope=True,
                        gemini_api_key=s.gemini_api_key,
                        ada_job_queue=s.ada_job_queue,
                        ada_kill_switch=s.ada_kill_switch,
                        ada_profile=s.ada_profile,
                        ada_profile_data_root=str(s.ada_profile_data_root),
                        profile_fingerprint=s.profile_fingerprint,
                    )
                    return format_programme_digest_appendix(digest)

            if should_inject_profile_digest(
                entity_mode=self.entity_mode,
                mission_id=self.mission_id,
                user_turn_count_before=turn_before,
                user_text=user_text,
            ):
                digest = build_profile_digest(
                    conn,
                    gemini_api_key=s.gemini_api_key,
                    ada_job_queue=s.ada_job_queue,
                    ada_kill_switch=s.ada_kill_switch,
                    ada_profile=s.ada_profile,
                    ada_profile_data_root=str(s.ada_profile_data_root),
                    profile_fingerprint=s.profile_fingerprint,
                )
                return format_profile_digest_appendix(digest)

            prog_mid = (
                self.mission_id
                if self.mission_id is not None
                else self.effective_mission_id
            )
            if not should_inject_programme_digest(
                work_mode=self.mission_id is not None,
                mission_id=self.mission_id,
                agent_default_mission_id=self.effective_mission_id,
                user_turn_count_before=turn_before,
                user_text=user_text,
            ):
                return None
            if prog_mid is None:
                return None
            digest = build_programme_digest(
                conn,
                prog_mid,
                mission_slug=self.default_mission_slug or self.mission_slug,
                profile_scope=True,
                gemini_api_key=s.gemini_api_key,
                ada_job_queue=s.ada_job_queue,
                ada_kill_switch=s.ada_kill_switch,
                ada_profile=s.ada_profile,
                ada_profile_data_root=str(s.ada_profile_data_root),
                profile_fingerprint=s.profile_fingerprint,
            )
            return format_programme_digest_appendix(digest)
        finally:
            conn.close()

    async def send_message(
        self,
        user_text: str,
        *,
        on_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        if not self.settings.gemini_api_key:
            raise RuntimeError("Set GEMINI_API_KEY (see .env.example).")

        async def _noop(chunk: str) -> None:
            if on_delta is not None:
                await on_delta(chunk)

        cb = on_delta if on_delta is not None else _noop
        turn_key = _user_turn_count_key(self.task_id)
        raw = await self.qe.state_get(turn_key)
        try:
            turn_before = int(raw) if raw is not None else 0
        except ValueError:
            turn_before = 0
        appendix = await self._turn_harness_appendix_for_message(user_text)
        try:
            final = await orchestrate_turn(
                user_text=user_text,
                on_delta=cb,
                turn_harness_appendix=appendix,
                **self._orchestrate_common(),
            )
            await self.qe.state_set(turn_key, str(turn_before + 1))
            await self.qe.update_task(
                self.task_id,
                status="executing",
                current_output=final,
            )
            return final
        except SessionTokenLimitExceeded as e:
            await self.qe.update_task(
                self.task_id,
                status="failed",
                current_output=str(e),
            )
            raise
