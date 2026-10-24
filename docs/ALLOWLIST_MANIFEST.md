# Allowlist manifest

Stable ids for chat tools, motor ops, and shell probes. Drift-tested against `ada.motor.manifest_sync.collect_code_ids`.

## Chat tools (`tool.*`)

| Id | Chat declared | Notes |
|----|---------------|-------|
| `tool.check_token_usage` | yes | Always |
| `tool.get_mission_control_snapshot` | yes | Wired in chat_session |
| `tool.propose_programme` | yes | Chat + Plan surfaces |
| `tool.apply_programme` | yes | Plan surface only |
| `tool.run_skill` | yes | Agent surface; Actions |
| `tool.run_allowlisted_shell` | yes | When shell_allowlist non-empty |
| `tool.append_master_section` | yes | `ADA_ENABLE_MEMORY_TOOLS` |
| `tool.append_soul_fragment` | yes | `ADA_ENABLE_MEMORY_TOOLS` |
| `tool.read_task_plan` | yes | `ADA_ENABLE_PLAN_TOOLS` |
| `tool.write_task_plan` | yes | `ADA_ENABLE_PLAN_TOOLS` |
| `tool.read_goal_task_view` | yes | `ADA_ENABLE_GOAL_RECALL_TOOL` |
| `tool.get_gsc_opportunities` | yes | `ADA_ENABLE_GSC_READ_TOOLS` |
| `tool.list_workspace_directory` | yes | `ADA_ENABLE_FILE_TOOLS` |
| `tool.read_workspace_file` | yes | `ADA_ENABLE_FILE_TOOLS` |
| `tool.write_workspace_file` | yes | `ADA_ENABLE_FILE_TOOLS` |
| `tool.web_search` | yes | `ADA_ENABLE_WEB_TOOLS` |
| `tool.fetch_url_text` | yes | `ADA_ENABLE_WEB_TOOLS` |
| `tool.list_session_web_sources` | yes | `ADA_ENABLE_WEB_SOURCES_TOOL` |
| `tool.search_knowledge` | yes | `ADA_ENABLE_KNOWLEDGE_TOOLS` |
| `tool.get_entity_graph_context` | yes | `ADA_ENABLE_KNOWLEDGE_TOOLS` |
| `tool.record_synthesis` | yes | `ADA_ENABLE_KNOWLEDGE_TOOLS` |
| `tool.record_market_edge` | yes | `ADA_ENABLE_KNOWLEDGE_TOOLS` |
| `tool.add_knowledge_source` | yes | `ADA_ENABLE_KNOWLEDGE_TOOLS` |
| `tool.record_entity` | yes | `ADA_ENABLE_KNOWLEDGE_TOOLS` |
| `tool.record_edge` | yes | `ADA_ENABLE_KNOWLEDGE_TOOLS` |
| `tool.link_evidence` | yes | `ADA_ENABLE_KNOWLEDGE_TOOLS` |
| `tool.get_workflow_status` | yes | `ADA_ENABLE_WORKFLOW_TOOLS`; read-only in chat |
| `tool.enqueue_workflow` | **no** | H2: CLI + `enqueue_workflow_via_tool` only |

## Host / Streamlit (manifest placeholders)

`host.web_fetch`, `host.knowledge_feed`, `host.gov_api`, `streamlit.sql_select`

## Motor ops (`op.*`)

| Id |
|----|
| `op.gate_failures` |
| `op.goal_list` |
| `op.help` |
| `op.matrix_scan_dry_run` |
| `op.mission_init` |
| `op.mission_list` |
| `op.mission_migrate_env_dry` |
| `op.mission_show` |
| `op.mission_tick_dry_run` |
| `op.workflow_status` |

## Shell

`shell.loader`, `tool.run_allowlisted_shell`, `shell.exact_line` (when allowlist file has lines)
