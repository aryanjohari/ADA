"""Streamlit chat tab — boss UI (H6/H7: sidebar + Plan apply + Agent run action)."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from typing import Any

import streamlit as st

from ada.chat_ingress import ChatSurfaceMode
from ada.chat_session import ChatSession, complete_chat_task_if_any
from ada.config import Settings
from ada.mission_cli import list_mission_template_names, load_mission_template
from ada.mission_control.snapshot import build_snapshot_from_settings
from ada.observability.hud_actions import (
    hud_apply_programme,
    hud_run_skill,
    parse_params_json,
    skills_for_mission_defaults,
)
from ada.observability.queries import open_readonly_connection
from ada.programme.packet import ProgrammePacket


async def _open_chat_session(
    *,
    new_session: bool,
    surface_mode: ChatSurfaceMode,
    mission_slug: str | None,
    apply_env_default: bool,
) -> ChatSession:
    settings = Settings.load()
    agent = surface_mode == ChatSurfaceMode.AGENT
    session = await ChatSession.open(
        settings,
        new_session=new_session,
        surface_mode=surface_mode,
        agent_mode=agent,
        plan_mode=surface_mode == ChatSurfaceMode.PLAN,
        mission_slug=mission_slug,
        apply_env_default=apply_env_default,
    )
    await session.run_boot_if_needed()
    return session


async def _send_chat_message(
    session: ChatSession,
    prompt: str,
    on_delta: Callable[[str], Awaitable[None]],
) -> str:
    return await session.send_message(prompt, on_delta=on_delta)


def _ensure_chat_session(
    *,
    new_session: bool,
    surface_mode: ChatSurfaceMode,
    mission_slug: str | None,
    apply_env_default: bool,
) -> ChatSession | None:
    if st.session_state.get("chat_session") is not None:
        return st.session_state.chat_session
    try:
        with st.spinner("Opening chat session…"):
            session = asyncio.run(
                _open_chat_session(
                    new_session=new_session,
                    surface_mode=surface_mode,
                    mission_slug=mission_slug,
                    apply_env_default=apply_env_default,
                )
            )
        st.session_state.chat_session = session
        return session
    except Exception as e:
        st.error(f"Failed to open chat session: {e}")
        return None


def _get_query_mission() -> str:
    try:
        qp = st.query_params
        return str(qp.get("mission", "") or "").strip()
    except Exception:
        return ""


def _render_sidebar(cfg: dict[str, Any]) -> None:
    settings = Settings.load()
    profile = settings.ada_profile or "(default)"
    st.sidebar.markdown(f"**Profile:** `{profile}`")
    try:
        snap = build_snapshot_from_settings(
            settings,
            mission_id=None,
            mission_slug=None,
            profile_scope=True,
            include_programme=False,
        )
    except Exception as e:
        st.sidebar.warning(f"Snapshot unavailable: {e}")
        return
    flags = snap.get("flags") or []
    if flags:
        st.sidebar.markdown("**Flags (top)**")
        for f in flags[:5]:
            sev = f.get("severity", "")
            msg = str(f.get("message", ""))[:120]
            st.sidebar.caption(f"`{sev}` {msg}")
    overview = snap.get("missions_overview") or []
    if overview:
        st.sidebar.markdown("**Programmes**")
        for row in overview[:12]:
            slug = str(row.get("slug") or "")
            title = str(row.get("title") or slug)
            pending = row.get("pending_goals", 0)
            label = f"{slug} ({pending} goals)" if slug else title
            if st.sidebar.button(label, key=f"sidebar_mission_{slug}"):
                st.session_state["hud_agent_mission_slug"] = slug
                st.session_state["hud_surface_mode"] = "agent"
                st.rerun()
    with st.sidebar.expander("Profile snapshot (JSON)"):
        st.json(snap)


def _render_plan_panel(settings: Settings) -> None:
    st.markdown("#### Apply programme")
    st.caption(
        "Apply from template without the terminal. LLM `apply_programme` in chat still works."
    )
    templates = list_mission_template_names()
    if not templates:
        st.info("No templates in templates/missions/*.yaml")
        return
    if "hud_plan_template" not in st.session_state:
        st.session_state["hud_plan_template"] = templates[0]
    template_name = st.selectbox(
        "Template",
        templates,
        index=templates.index(st.session_state["hud_plan_template"])
        if st.session_state["hud_plan_template"] in templates
        else 0,
        key="hud_plan_template_select",
    )
    st.session_state["hud_plan_template"] = template_name
    try:
        base = load_mission_template(template_name)
    except (FileNotFoundError, ValueError) as e:
        st.error(str(e))
        return
    with st.expander("Packet preview"):
        st.json(base)
    slug = st.text_input("Mission slug", value=base.get("mission_slug", ""))
    title = st.text_input("Title", value=base.get("title", ""))
    brief_md = st.text_area("brief_md", value=base.get("brief_md", ""), height=120)
    with st.expander("Advanced: skills_enabled override (JSON array)"):
        skills_override = st.text_area(
            "skills_enabled",
            value=json.dumps(base.get("skills_enabled") or [], indent=2),
            height=80,
        )
    approved = st.checkbox("Approved", value=False)
    if st.button("Apply programme", type="primary"):
        packet_data = dict(base)
        packet_data["mission_slug"] = slug.strip()
        packet_data["title"] = title.strip() or slug.strip()
        packet_data["brief_md"] = brief_md
        if skills_override.strip():
            try:
                parsed = json.loads(skills_override)
                if isinstance(parsed, list):
                    packet_data["skills_enabled"] = parsed
            except json.JSONDecodeError as e:
                st.error(f"Invalid skills_enabled JSON: {e}")
                return
        try:
            ProgrammePacket.model_validate(packet_data)
        except Exception as e:
            st.error(f"Invalid packet: {e}")
            return
        with st.spinner("Applying…"):
            result = asyncio.run(
                hud_apply_programme(settings, packet_data, approved=approved)
            )
        if result.get("denied"):
            st.warning("Apply denied (approved checkbox required).")
        elif result.get("ok"):
            st.success(
                f"Mission `{result.get('mission_slug')}` "
                f"({'created' if result.get('created') else 'updated'})."
            )
            if result.get("cron_snippet_path"):
                st.caption(f"Cron snippet: `{result['cron_snippet_path']}`")
        else:
            st.error(result.get("error", "Apply failed"))


def _render_agent_panel(settings: Settings, default_slug: str) -> None:
    st.markdown("#### Run action")
    st.caption(
        "Motor `run_skill` with H5 pack/skills enforcement. Chat `run_skill` is optional."
    )
    slug = st.text_input(
        "Mission slug",
        value=st.session_state.get("hud_agent_mission_slug", default_slug),
        key="hud_agent_mission_input",
    ).strip()
    st.session_state["hud_agent_mission_slug"] = slug
    if not slug:
        st.info("Enter a mission slug to list allowed actions.")
        return
    conn = open_readonly_connection(settings.state_db_path)
    try:
        cur = conn.execute(
            "SELECT defaults_json FROM missions WHERE slug = ?",
            (slug,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        st.warning(f"Mission `{slug}` not found.")
        return
    try:
        defaults = json.loads(str(row["defaults_json"] or "{}"))
    except json.JSONDecodeError:
        defaults = {}
    if not isinstance(defaults, dict):
        defaults = {}
    skills = skills_for_mission_defaults(defaults)
    if not skills:
        st.warning("No catalog skills available for this mission.")
        return
    labels = [
        f"{s.id} — {s.description[:60]}… ({s.risk_tier})"
        if len(s.description) > 60
        else f"{s.id} — {s.description} ({s.risk_tier})"
        for s in skills
    ]
    idx = st.selectbox("Action", range(len(skills)), format_func=lambda i: labels[i])
    spec = skills[idx]
    params_text = st.text_area("Params (JSON object)", value="{}", height=80)
    needs_approval = spec.require_approval or spec.risk_tier == "high"
    approved = True
    if needs_approval:
        approved = st.checkbox("Approved (high-risk)", value=False)
    if st.button("Run action", type="primary"):
        params, err = parse_params_json(params_text)
        if err:
            st.error(err)
            return
        with st.spinner(f"Running {spec.id}…"):
            result = asyncio.run(
                hud_run_skill(
                    settings,
                    skill_id=spec.id,
                    mission_slug=slug,
                    params=params,
                    approved=approved,
                )
            )
        with st.expander("Motor result"):
            st.json(result)
        if result.get("pending_approval"):
            st.warning("Skill requires approval — check Approved and retry.")
        elif result.get("ok"):
            st.success("Action completed.")
        else:
            st.error(result.get("error", "Action failed"))


def _render_chat_snapshot_expander(settings: Settings) -> None:
    with st.expander("Refresh profile snapshot"):
        try:
            snap = build_snapshot_from_settings(
                settings,
                profile_scope=True,
                include_programme=False,
            )
            st.json(snap)
        except Exception as e:
            st.error(str(e))


def render_chat_tab(cfg: dict[str, Any]) -> None:
    settings = Settings.load()
    _render_sidebar(cfg)

    st.subheader("Operator chat")
    st.caption(
        "**Chat** — concierge (`propose_programme`, ProfileDigest). "
        "**Plan** — template **Apply programme** or `propose_programme` / `apply_programme`. "
        "**Agent** — **Run action** panel or chat `run_skill`; optional default mission slug. "
        "No `enqueue_workflow` in chat."
    )

    if not settings.gemini_api_key and not str(
        cfg.get("merged_environ", {}).get("GEMINI_API_KEY", "")
    ).strip():
        st.warning("Set GEMINI_API_KEY in profile .env to use chat.")

    mode_options = ["chat", "plan", "agent"]
    default_mode = st.session_state.get("hud_surface_mode", "chat")
    if default_mode not in mode_options:
        default_mode = "chat"
    mode_label = st.radio(
        "Surface mode",
        options=mode_options,
        index=mode_options.index(default_mode),
        horizontal=True,
        help="Chat: concierge. Plan: apply template. Agent: run_skill / Run action.",
    )
    st.session_state["hud_surface_mode"] = mode_label
    surface = ChatSurfaceMode(mode_label)
    agent_mode = surface == ChatSurfaceMode.AGENT
    plan_mode = surface == ChatSurfaceMode.PLAN

    agent_default_mission = (
        cfg.get("mission_filter")
        or os.environ.get("ADA_OPERATOR_DEFAULT_MISSION", "").strip()
        or _get_query_mission()
        or os.environ.get("ADA_CHAT_DEFAULT_MISSION", "").strip()
        or st.session_state.get("hud_agent_mission_slug", "")
    )

    if plan_mode:
        _render_plan_panel(settings)

    if agent_mode:
        _render_agent_panel(settings, agent_default_mission)

    if surface == ChatSurfaceMode.CHAT:
        _render_chat_snapshot_expander(settings)

    if not settings.gemini_api_key and not str(
        cfg.get("merged_environ", {}).get("GEMINI_API_KEY", "")
    ).strip():
        return

    mission_slug = ""
    if agent_mode:
        mission_slug = st.text_input(
            "Default mission slug (Agent chat)",
            value=agent_default_mission,
            help="Optional hint for run_skill mission_slug when omitted in chat.",
        ).strip()

    new_session = st.checkbox("New session", value=False)
    mission_arg: str | None = mission_slug if agent_mode and mission_slug else None
    apply_env_default = agent_mode and bool(mission_arg)

    session_key = (mode_label, mission_slug, new_session)
    if (
        "chat_session" not in st.session_state
        or st.session_state.get("chat_session_key") != session_key
    ):
        prior_task_id = st.session_state.get("chat_task_id")
        if prior_task_id is not None:
            try:
                asyncio.run(complete_chat_task_if_any(settings, int(prior_task_id)))
            except Exception:
                pass
        st.session_state.chat_session_key = session_key
        st.session_state.chat_messages = []
        if "chat_session" in st.session_state:
            try:
                asyncio.run(st.session_state.chat_session.close())
            except Exception:
                pass
            del st.session_state.chat_session

    session = _ensure_chat_session(
        new_session=new_session or st.session_state.get("chat_session") is None,
        surface_mode=surface,
        mission_slug=mission_arg,
        apply_env_default=apply_env_default,
    )
    if session is None:
        return
    st.session_state.chat_task_id = session.task_id

    for msg in st.session_state.get("chat_messages", []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Message ADA…")
    if not prompt:
        return

    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        chunks: list[str] = []

        async def on_delta(chunk: str) -> None:
            chunks.append(chunk)
            placeholder.markdown("".join(chunks))

        final = ""
        try:
            final = asyncio.run(_send_chat_message(session, prompt, on_delta))
            if not chunks:
                placeholder.markdown(final)
        except Exception as e:
            final = f"Error: {e}"
            placeholder.error(final)

    st.session_state.chat_messages.append({"role": "assistant", "content": final})
