# Streamlit boss UI (Hands H7)

The **Chat** tab in the Ada operator Streamlit app (`scripts/ada_observability_app.py`) is the primary HUD for concierge chat, programme apply, and motor actions.

## Layout

| Area | Content |
|------|---------|
| **Sidebar** | Active profile, top flags, programme list (slug → switch to Agent), profile snapshot JSON |
| **Main — Chat** | Surface radio + conversation + optional **Refresh profile snapshot** expander |
| **Main — Plan** | Template picker, packet preview, slug/title/brief overrides, **Apply programme** (approved checkbox) |
| **Main — Agent** | Mission slug, filtered **Run action** (skill selectbox, params JSON, high-risk approval) + optional chat `run_skill` |

Apply and Run action run **outside** the chat message loop via `ada.observability.hud_actions` (direct `confirm_and_apply` / `motor.execute`).

**Quick actions** (Log memory, Add todo, Body check) use `hud_run_primitive` on the same handler path as Chat — see [`STREAMLIT_DAILY_USE.md`](STREAMLIT_DAILY_USE.md).

## Surfaces

| Surface | Chat tools | HUD |
|---------|------------|-----|
| **chat** | `propose_programme`, profile tools; no `run_skill` | Profile snapshot expander |
| **plan** | `propose_programme`, `apply_programme` | Template **Apply programme** |
| **agent** | `run_skill`, mission-scoped tools | **Run action** panel |

`enqueue_workflow` is not exposed in any chat surface (H2 single bus).

## CLI parity

| Operator task | Streamlit | CLI |
|---------------|-----------|-----|
| Concierge chat | Chat surface + `st.chat_input` | `ada chat` (default) |
| Apply template | Plan → Apply programme | `ada mission apply-template <name>` |
| Run skill | Agent → Run action | `ada chat --agent --mission <slug>` or motor paths |
| Profile status | Sidebar snapshot / Chat expander | `get_mission_control_snapshot` in chat |

## H5 enforcement

Agent **Run action** and motor `execute` enforce `skills_enabled` and pack allowlists. Wrong skill selections show the motor error in the result expander.

## Environment

Same profile env as CLI: `ADA_PROFILE`, `ADA_DATA_DIR`, `GEMINI_API_KEY`. Optional: `ADA_OPERATOR_DEFAULT_MISSION`, `ADA_CHAT_DEFAULT_MISSION`, sidebar mission filter.

```bash
pip install -e ".[streamlit]"
streamlit run scripts/ada_observability_app.py
```
