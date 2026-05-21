"""Terminal chat — one `tasks` row per session (claude_logic + system_arch)."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from ada.config import Settings
from ada.dream.run import run_dream_job
from ada.extract.graph_lite import (
    build_llm_graph_extractor,
    resolve_graph_lite_system_instruction,
    run_graph_lite_extraction,
)
from ada.policy.load import clamp_graph_lite_job_limits, load_merged_policy_for
from ada.publish.batch_enrich_context import resolve_batch_enrich_system_instruction
from ada.workflow.publish_enrich_step import run_publish_entity_enrich
from ada.chat_ingress import ChatIngressMode, ChatSurfaceMode, surface_operator_label
from ada.chat_session import ChatSession, chat_setup_mode_enabled
from ada.orchestrator import SessionTokenLimitExceeded
from ada.profile_runtime import enforce_profile_identity
from ada.query_engine import QueryEngine
from ada.tool_executor import (
    FileToolConfig,
    MemoryToolConfig,
)


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


from ada.chat_session import mission_control_snapshot_fn as _mission_control_snapshot_fn


async def run_chat(
    settings: Settings,
    *,
    new_session: bool,
    mission_slug: str | None = None,
    setup_mode: bool = False,
    plan_mode: bool = False,
    agent_mode: bool = False,
    programme_mode: bool = False,
) -> None:
    setup_mode = chat_setup_mode_enabled(setup_mode)
    if programme_mode and not plan_mode:
        plan_mode = True
    if os.environ.get("ADA_REQUIRE_CHAT_MISSION", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        slug_check = (mission_slug or os.environ.get("ADA_CHAT_DEFAULT_MISSION", "")).strip()
        if not slug_check and agent_mode:
            print(
                "ADA_REQUIRE_CHAT_MISSION=1: set --mission or ADA_CHAT_DEFAULT_MISSION "
                "for Agent mode.",
                file=sys.stderr,
            )
            raise SystemExit(2)

    explicit_mission = mission_slug is not None or agent_mode
    session = await ChatSession.open(
        settings,
        new_session=new_session,
        mission_slug=mission_slug,
        setup_mode=setup_mode,
        plan_mode=plan_mode,
        agent_mode=agent_mode,
        programme_mode=programme_mode,
        apply_env_default=explicit_mission and agent_mode,
    )
    try:
        if not settings.gemini_api_key:
            print("Set GEMINI_API_KEY (see .env.example).", file=sys.stderr)
            return

        surface = session.surface
        mission_id = session.mission_id

        async def boot_on_delta(chunk: str) -> None:
            print(chunk, end="", flush=True)

        if session.wakeup.strip():
            print("Boot: running wakeup prompt once for this session…", flush=True)
            try:
                await session.run_boot_if_needed(on_delta=boot_on_delta)
                print(flush=True)
            except SessionTokenLimitExceeded as e:
                print(f"\n[boot error] {e}", file=sys.stderr)
            except Exception as e:
                print(f"\n[boot error] {e}", file=sys.stderr)

        mode_bits: list[str] = [surface_operator_label(surface)]
        if session.default_mission_slug:
            mode_bits.append(f"default_mission={session.default_mission_slug}")
        if mission_id is not None:
            mode_bits.append(f"mission_id={mission_id}")
        if surface == ChatSurfaceMode.SETUP:
            mode_bits.append("setup_assist")
        if mode_bits:
            print(f"ADA chat ({', '.join(mode_bits)}) — empty line or Ctrl-D to exit.", flush=True)
        else:
            print("ADA chat — empty line or Ctrl-D to exit.", flush=True)

        while True:
            try:
                line = input("you> ").strip()
            except EOFError:
                print()
                break
            if not line:
                break

            async def on_delta(chunk: str) -> None:
                print(chunk, end="", flush=True)

            try:
                await session.send_message(line, on_delta=on_delta)
                print()
            except SessionTokenLimitExceeded as e:
                print(f"\n[error] {e}", file=sys.stderr)
            except Exception as e:
                print(f"\n[error] {e}", file=sys.stderr)
                await session.qe.update_task(
                    session.task_id,
                    status="executing",
                    current_output=f"Error: {e}",
                )
    finally:
        await session.close()


async def run_dream_cli(
    settings: Settings,
    *,
    session_id: int | None,
    dry_run: bool,
    max_messages: int,
) -> None:
    """Manual dream compression (invoke `ada dream`; schedule cron separately)."""
    settings.ensure_data_dir()
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    await enforce_profile_identity(qe, settings)
    try:
        out = await run_dream_job(
            qe,
            settings,
            session_id=session_id,
            dry_run=dry_run,
            max_messages=max_messages,
        )
        print(out)
    finally:
        await qe.close()


async def run_extract_graph_lite_cli(
    settings: Settings,
    *,
    limit: int,
    token_cap: int,
    source_id: int | None = None,
    mission_slug: str | None = None,
) -> int:
    settings.ensure_data_dir()
    policy = load_merged_policy_for(settings)
    eff_limit, eff_token_cap = clamp_graph_lite_job_limits(limit, token_cap, policy)
    sys_instr = resolve_graph_lite_system_instruction(
        settings,
        policy,
        effective_limit=eff_limit,
        effective_token_cap=eff_token_cap,
    )
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    await enforce_profile_identity(qe, settings)
    mission_id: int | None = None
    if mission_slug is not None and str(mission_slug).strip():
        m = await qe.get_mission_by_slug(str(mission_slug).strip())
        if m is None:
            print(
                f"extract-graph-lite: unknown mission slug {str(mission_slug).strip()!r}",
                file=sys.stderr,
            )
            return 2
        mission_id = int(m["id"])
    try:
        extractor = None
        if settings.gemini_api_key.strip():
            extractor = build_llm_graph_extractor(
                api_key=settings.gemini_api_key,
                model=settings.graph_lite_extract_model,
                token_cap=eff_token_cap,
                system_instruction=sys_instr,
            )
        stats = await run_graph_lite_extraction(
            qe,
            limit=eff_limit,
            token_cap=eff_token_cap,
            source_id=source_id,
            extractor=extractor,
            mission_id=mission_id,
        )
        print(
            "extract-graph-lite:"
            f" processed_docs={stats.processed_docs}"
            f" entities_upserted={stats.entities_upserted}"
            f" edges_created={stats.edges_created}"
            f" evidence_links_created={stats.evidence_links_created}"
            f" rejected={stats.rejected}"
        )
        return 0
    finally:
        await qe.close()


log_enrich_graph = logging.getLogger("ada.cli.enrich_graph")


async def run_enrich_graph_cli(
    settings: Settings,
    *,
    entity_ids: list[int] | None,
    limit: int | None,
) -> int:
    """Bounded batch ENRICH using intent + merged policy system instruction (not chat harness)."""
    policy = load_merged_policy_for(settings)
    entity_cap = limit if limit is not None else policy.batch_enrich_max_entities
    entity_cap = max(1, min(int(entity_cap), policy.batch_enrich_max_entities))

    settings.ensure_data_dir()
    schema_path = Path(__file__).resolve().parent / "db" / "schema.sql"
    qe = QueryEngine(
        settings.state_db_path,
        schema_path,
        debounce_ms=settings.persist_debounce_ms,
    )
    await qe.connect()
    await enforce_profile_identity(qe, settings)

    sys_instr = resolve_batch_enrich_system_instruction(settings, policy)
    goal_base = "[batch_enrich_graph] background widen for publish DRAFT inputs"

    explicit = list(entity_ids) if entity_ids else []
    seen: set[int] = set()
    ordered: list[int] = []

    try:
        for eid in explicit:
            if len(ordered) >= entity_cap:
                break
            ent = await qe.get_entity_by_id(int(eid))
            if ent is None:
                log_enrich_graph.warning("enrich-graph: skip unknown entity_id=%s", eid)
                continue
            eid_i = int(eid)
            if eid_i in seen:
                continue
            seen.add(eid_i)
            ordered.append(eid_i)

        pool_lim = max(entity_cap * 4, int(settings.ada_matrix_max_enqueues))
        rows = await qe.list_subjects_with_classified_category_recent_for_planner(
            entity_types=settings.ada_matrix_entity_types,
            limit=pool_lim,
        )
        for r in rows:
            if len(ordered) >= entity_cap:
                break
            eid_i = int(r["id"])
            if eid_i in seen:
                continue
            seen.add(eid_i)
            ordered.append(eid_i)

        if not ordered:
            print("enrich-graph: no eligible entity ids (check --entity-id or matrix subject pool)")
            return 1

        any_ok = False
        for eid_i in ordered:
            tid = await qe.insert_task(
                f"{goal_base} entity_id={eid_i}",
                status="executing",
            )
            ent = await qe.get_entity_by_id(eid_i)
            assert ent is not None
            merged = {"entity_id": eid_i}
            try:
                out = await run_publish_entity_enrich(
                    qe,
                    settings,
                    entity_id=eid_i,
                    entity=ent,
                    merged_params=merged,
                    goal_text=f"{goal_base} entity_id={eid_i}",
                    system_instruction=sys_instr,
                    session_id=tid,
                    max_tool_rounds=settings.max_tool_rounds,
                    shell_max_output_bytes=settings.shell_max_output_bytes,
                    shell_timeout_sec=settings.shell_timeout_sec,
                    stream_chunk_idle_timeout_sec=settings.stream_chunk_idle_timeout_sec,
                    stream_leg_max_wall_sec=settings.stream_leg_max_wall_sec,
                    rewire_after_tombstone=settings.rewire_after_tombstone,
                    max_session_tokens=settings.max_session_tokens,
                    debug_stream=settings.debug_stream,
                    knowledge_feed_host_allowlist=settings.knowledge_feed_host_allowlist,
                    knowledge_embeddings_enabled=settings.enable_knowledge_embeddings,
                    knowledge_embedding_model=settings.knowledge_embedding_model,
                    knowledge_embedding_dim=settings.knowledge_embedding_dim,
                    knowledge_embedding_min_cosine=settings.knowledge_embedding_min_cosine,
                    knowledge_tool_max_results=settings.knowledge_tool_max_results,
                    knowledge_tool_excerpt_chars=settings.knowledge_tool_excerpt_chars,
                    enrich_tool_rounds_cap=policy.batch_enrich_max_tool_rounds,
                )
                await qe.append_action_log(
                    "batch_graph_enrich",
                    {
                        "entity_id": eid_i,
                        "session_task_id": tid,
                        "path": out.get("path"),
                        "last_enriched_at": out.get("last_enriched_at"),
                        "ok": True,
                    },
                    session_id=tid,
                )
                await qe.update_task(
                    tid,
                    status="completed",
                    current_output=str(out.get("path") or "ok")[:2000],
                )
                any_ok = True
                print(f"enrich-graph: entity_id={eid_i} path={out.get('path')!r} ok=1")
            except Exception as exc:
                log_enrich_graph.exception("enrich-graph: entity_id=%s failed", eid_i)
                await qe.append_action_log(
                    "batch_graph_enrich",
                    {
                        "entity_id": eid_i,
                        "session_task_id": tid,
                        "ok": False,
                        "error": str(exc)[:800],
                    },
                    session_id=tid,
                )
                await qe.update_task(
                    tid,
                    status="failed",
                    current_output=str(exc)[:2000],
                )
                print(f"enrich-graph: entity_id={eid_i} ok=0 err={exc!s}")

        return 0 if any_ok else 1
    finally:
        await qe.close()
