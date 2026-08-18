"""Body sense + chat harness + HUD + memory/Dream CLI (M00/M02/M03/M04)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ada import __version__
from ada.body import identity as identity_mod
from ada.body import lifecycle as lifecycle_mod
from ada.body import narrative
from ada.body.vitals import VitalsSnapshot, collect_vitals, urgent_faults
from ada.hud import DEFAULT_HOST, DEFAULT_PORT, assert_loopback_host
from ada.io.paths import BodyFault, ada_data_mounted, get_paths, require_ada_data

console = Console(stderr=False)
err_console = Console(stderr=True)

app = typer.Typer(
    name="ada",
    help="ADA — body organs + chat harness + HUD + memory/Dream.",
    no_args_is_help=True,
)
body_app = typer.Typer(help="Body sense: vitals, identity, lifecycle.", no_args_is_help=True)
hud_app = typer.Typer(help="Control-plane HUD (localhost + Tailscale Serve).", no_args_is_help=True)
memory_app = typer.Typer(help="FACTS / WORLDVIEW / open loops (M04).", no_args_is_help=True)
dream_app = typer.Typer(help="Dream seal / status (M04).", no_args_is_help=True)
staging_app = typer.Typer(
    help="Dream staging confirm/reject (M11) — never auto-done.",
    no_args_is_help=True,
)
campaigns_app = typer.Typer(
    help="Campaign STATUS on disk (M06) — metal truth, no Gemini.",
    no_args_is_help=True,
)
watch_app = typer.Typer(
    help="RSS/feed watches on campaigns (M09) — ingest + wake.",
    no_args_is_help=True,
)
web_app = typer.Typer(
    help="Allowlisted web fetch + cite library (M07) + pack seed (M08).",
    no_args_is_help=True,
)
tier_a_app = typer.Typer(
    help="Tier A kernel close gate (M18).",
    no_args_is_help=True,
)
life_app = typer.Typer(
    help="Life capture: meals, gym, time (M19a).",
    no_args_is_help=True,
)
app.add_typer(body_app, name="body")
app.add_typer(hud_app, name="hud")
app.add_typer(memory_app, name="memory")
app.add_typer(dream_app, name="dream")
app.add_typer(staging_app, name="staging")
app.add_typer(campaigns_app, name="campaigns")
app.add_typer(watch_app, name="watch")
app.add_typer(web_app, name="web")
app.add_typer(tier_a_app, name="tier-a")
app.add_typer(life_app, name="life")


def _exit_body_fault(exc: BodyFault) -> None:
    err_console.print(f"[red]body fault:[/red] {exc.message}")
    raise typer.Exit(code=exc.code)


@body_app.command("status")
def body_status(
    json_out: bool = typer.Option(False, "--json", help="Machine-readable snapshot."),
) -> None:
    """Vitals summary + identity born_at + last wake/fault."""
    snap = collect_vitals()
    ident = None
    last_wake = None
    last_fault = None
    try:
        paths = require_ada_data()
        if identity_mod.identity_exists(paths):
            ident = identity_mod.load_identity(paths)
        last_wake = lifecycle_mod.last_of_type("wake", paths)
        last_fault = lifecycle_mod.last_of_type("fault", paths)
    except BodyFault:
        pass

    if json_out:
        payload = {
            "version": __version__,
            "vitals": snap.model_dump(),
            "identity": ident.model_dump() if ident else None,
            "last_wake": last_wake.model_dump() if last_wake else None,
            "last_fault": last_fault.model_dump() if last_fault else None,
            "urgent": urgent_faults(snap),
        }
        console.print_json(data=payload)
        _status_exit(snap)
        return

    table = Table(title=f"ADA body status (v{__version__})")
    table.add_column("field")
    table.add_column("value")
    table.add_row("host", snap.host.hostname)
    table.add_row("temp_c", str(snap.thermal.temp_c))
    table.add_row("ada_data_ok", str(snap.mounts.ada_data_ok))
    mem_gib = snap.memory.mem_available_bytes / (1024**3)
    table.add_row("mem_available_gib", f"{mem_gib:.2f}")
    if ident:
        table.add_row("born_at", ident.born_at)
        table.add_row("name", f"{ident.name} ({ident.pronouns})")
    else:
        table.add_row("born_at", "(not born yet)")
    if last_wake:
        table.add_row("last_wake", f"{last_wake.ts} — {last_wake.summary}")
    if last_fault:
        table.add_row("last_fault", f"{last_fault.ts} — {last_fault.summary}")
    for fault in urgent_faults(snap):
        table.add_row("[red]urgent[/red]", fault)
    console.print(table)
    _status_exit(snap)


def _status_exit(snap: VitalsSnapshot) -> None:
    if not snap.mounts.ada_data_ok and not ada_data_mounted():
        raise typer.Exit(code=3)
    if snap.probe_errors and not urgent_faults(snap):
        raise typer.Exit(code=2)
    if urgent_faults(snap) and not snap.mounts.ada_data_ok:
        raise typer.Exit(code=3)


@body_app.command("vitals")
def body_vitals(
    json_out: bool = typer.Option(False, "--json", help="Emit VitalsSnapshot JSON."),
) -> None:
    """Host vitals only."""
    snap = collect_vitals()
    if json_out:
        console.print_json(data=snap.model_dump())
    else:
        console.print(Panel.fit(json.dumps(snap.model_dump(), indent=2)[:4000]))
    if not snap.mounts.ada_data_ok and not ada_data_mounted():
        raise typer.Exit(code=3)
    if snap.probe_errors:
        raise typer.Exit(code=2)


@body_app.command("whoami")
def body_whoami(
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Print identity card (error if missing)."""
    try:
        card = identity_mod.load_identity()
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data=card.model_dump())
    else:
        console.print(f"{card.name} ({card.pronouns}) — born {card.born_at}")
        console.print(f"host={card.body_hostname} board={card.board_model}")
        console.print(f"operator={card.operator} version={card.version}")


@body_app.command("birth")
def body_birth() -> None:
    """Create identity once if missing; idempotent if already born.

    Also applies birth pack seeds (SELF/OPERATOR) when missing.
    """
    try:
        card, created = identity_mod.create_identity()
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if created:
        console.print(f"[green]born[/green] at {card.born_at} on {card.body_hostname}")
    else:
        console.print(f"already born at {card.born_at} (born_at unchanged)")
    from ada.memory.birth_pack import apply_birth_pack

    try:
        pack = apply_birth_pack()
        if pack.get("applied"):
            console.print(f"birth pack applied: {', '.join(pack['applied'])}")
        elif pack.get("skipped"):
            console.print("birth pack: seeds already present (not overwritten)")
    except BodyFault:
        pass


@body_app.command("birth-pack")
def body_birth_pack(
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite seeds (tests/lab only — never for operator bio).",
    ),
) -> None:
    """Copy repo syllabus seeds into ada-data if missing (M16)."""
    from ada.memory.birth_pack import apply_birth_pack

    try:
        pack = apply_birth_pack(force=force)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    console.print_json(data=pack)


@body_app.command("wake")
def body_wake(
    ensure_birth: bool = typer.Option(
        False,
        "--ensure-birth",
        help="Create identity first if missing.",
    ),
) -> None:
    """Append a wake event (process/service start)."""
    try:
        ev = lifecycle_mod.append_wake(ensure_birth=ensure_birth)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    console.print(f"[green]wake[/green] {ev.id} @ {ev.ts}")


@body_app.command("sleep")
def body_sleep() -> None:
    """Append a clean sleep/stop event."""
    try:
        ev = lifecycle_mod.append_sleep()
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    console.print(f"sleep {ev.id} @ {ev.ts}")


@body_app.command("fault")
def body_fault(
    summary: str = typer.Option(..., "--summary", "-s", help="Fault summary text."),
) -> None:
    """Append a manual/test fault event."""
    try:
        ev = lifecycle_mod.append_fault(summary)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    console.print(f"[yellow]fault[/yellow] {ev.id}: {summary}")


@body_app.command("story")
def body_story(
    n: int = typer.Option(20, "--n", "-n", help="Last N ledger events."),
) -> None:
    """Plain autobiography from the lifecycle ledger only."""
    try:
        events = lifecycle_mod.tail(n)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    console.print(narrative.story(events, n=n))


@body_app.command("doctor")
def body_doctor() -> None:
    """Mount honesty + probe_errors + urgent flags. Exit ≠0 on hard fault."""
    paths = get_paths()
    mounted = ada_data_mounted(paths.root)
    snap = collect_vitals()
    urgent = urgent_faults(snap)

    table = Table(title="ada body doctor")
    table.add_column("check")
    table.add_column("result")
    table.add_row("ADA_DATA_ROOT", str(paths.root))
    table.add_row("mounted/ok", "yes" if mounted else "[red]NO[/red]")
    table.add_row("ada_data_ok (vitals)", str(snap.mounts.ada_data_ok))
    table.add_row("probe_errors", str(len(snap.probe_errors)))
    for err in snap.probe_errors:
        table.add_row(f"  probe:{err.probe}", err.message)
    if urgent:
        for u in urgent:
            table.add_row("[red]urgent[/red]", u)
        console.print(table)
        console.print(f"[red]urgent:[/red] {'; '.join(urgent)}")
    else:
        table.add_row("urgent", "none")
        console.print(table)
        if snap.probe_errors:
            console.print(
                f"probe issues ({len(snap.probe_errors)}); no urgent faults"
            )
        else:
            console.print("[green]all clear[/green]")

    if not mounted:
        raise typer.Exit(code=3)
    if urgent and not snap.mounts.ada_data_ok:
        raise typer.Exit(code=3)
    if snap.probe_errors or urgent:
        raise typer.Exit(code=2)


@body_app.command(
    "cmd",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def body_cmd(
    ctx: typer.Context,
    argv: list[str] | None = typer.Argument(
        None,
        help="Allowlisted argv only (e.g. nproc | uname -m | df -h /mnt/ada-data).",
    ),
) -> None:
    """Allowlisted read-only host command (same policy as body_readonly_cmd tool)."""
    from ada.body.readonly_cmd import run_readonly_cmd

    tokens = list(argv or []) + list(ctx.args or [])
    if not tokens:
        err_console.print("[red]denied:[/red] empty argv")
        raise typer.Exit(code=2)
    result = run_readonly_cmd(tokens)
    if result.denied_reason:
        err_console.print(f"[red]denied:[/red] {result.denied_reason}")
        raise typer.Exit(code=2)
    if result.error and not result.ok:
        err_console.print(f"[red]error:[/red] {result.error}")
        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            err_console.print(result.stderr)
        raise typer.Exit(code=result.exit_code or 1)
    if result.stdout:
        console.print(result.stdout)
    if result.stderr:
        err_console.print(result.stderr)


def _chat_sink_printer(event: str, payload: dict) -> None:
    if event == "tool_call_started":
        tool = payload.get("tool")
        args = payload.get("args") or {}
        console.print(f"[cyan]tool[/cyan] {tool}({json.dumps(args, default=str)})")
    elif event == "tool_call_finished":
        ok = payload.get("ok")
        rid = payload.get("receipt_id", "")[:12]
        mark = "[green]ok[/green]" if ok else "[red]fail[/red]"
        console.print(f"  ↳ {mark} receipt={rid}…")


@app.command("chat")
def chat(
    query: Optional[str] = typer.Option(
        None,
        "--query",
        "-q",
        help="Single-turn question then exit.",
    ),
    mode: str = typer.Option(
        "observe",
        "--mode",
        help="observe (default) | agent | plan",
    ),
    estimate: bool = typer.Option(
        False,
        "--estimate",
        help="Print rough pre-call USD estimate (labeled).",
    ),
    jsonl_path: Optional[Path] = typer.Option(
        None,
        "--jsonl-path",
        help="Override run transcript path (tests).",
        exists=False,
        dir_okay=False,
        writable=True,
        resolve_path=True,
    ),
) -> None:
    """Gemini ReAct chat — body tools via gateway; receipts under runs/."""
    from ada.cortex.charter import build_system_charter
    from ada.cortex.cost import estimate_from_text
    from ada.cortex.gemini import GeminiAdapter
    from ada.cortex.models import resolve_model
    from ada.harness.loop import run_turn
    from ada.harness.session import ChatSession
    from ada.harness.stream_events import CallbackSink
    from ada.secrets.load import MissingSecret, load_gemini_api_key

    mode_l = mode.lower().strip()
    if mode_l not in ("observe", "agent", "plan"):
        err_console.print(f"[red]invalid mode:[/red] {mode}")
        raise typer.Exit(code=2)

    try:
        api_key = load_gemini_api_key()
    except MissingSecret as exc:
        err_console.print(f"[red]no_key:[/red] {exc.message}")
        try:
            session = ChatSession(mode=mode_l, jsonl_path=jsonl_path)  # type: ignore[arg-type]
            session.ensure_started()
            session.end(stop_reason="no_key")
            err_console.print(f"run: {session.run_path}")
        except Exception:  # noqa: BLE001
            pass
        raise typer.Exit(code=1)

    model = resolve_model("chat_interactive")
    session = ChatSession(mode=mode_l, model=model, jsonl_path=jsonl_path)  # type: ignore[arg-type]
    adapter = GeminiAdapter(api_key, model=model)
    sink = CallbackSink()
    sink.on(_chat_sink_printer)

    system = build_system_charter(mode=mode_l)

    def _one(user_text: str, *, end_session: bool, history: list) -> int:
        if estimate:
            est = estimate_from_text(model, system, user_text)
            console.print(
                f"[dim]estimate ~${est.usd_estimate:.6f} "
                f"(~{est.prompt_tokens}+{est.candidates_tokens} tok, labeled estimate)[/dim]"
            )
        result = run_turn(
            session,
            user_text,
            adapter,
            system=system,
            sink=sink,
            contents=history,
            end_session=end_session,
        )
        if result.text:
            console.print(Panel(result.text, title="ADA", border_style="magenta"))
        else:
            console.print("[yellow](no assistant text)[/yellow]")
        console.print(
            f"[dim]stop={result.stop_reason} steps={result.steps} run={result.run_path}[/dim]"
        )
        if result.stop_reason in ("error", "no_key"):
            return 1
        return 0

    if query is not None:
        code = _one(query, end_session=True, history=[])
        raise typer.Exit(code=code)

    console.print(
        f"[bold]ADA chat[/bold] mode={mode_l} model={model} (Ctrl-D /exit to quit)"
    )
    console.print(f"[dim]session={session.session_id}[/dim]")
    history: list = []
    exit_code = 0
    try:
        while True:
            try:
                line = console.input("[bold green]you>[/bold green] ").strip()
            except EOFError:
                console.print()
                break
            if not line:
                continue
            if line in ("/exit", "/quit", ":q"):
                break
            exit_code = _one(line, end_session=False, history=history)
    finally:
        if session._started:
            session.end(stop_reason="completed")
            console.print(f"[dim]run: {session.run_path}[/dim]")
    raise typer.Exit(code=exit_code)


@hud_app.command("serve")
def hud_serve(
    host: str = typer.Option(
        DEFAULT_HOST,
        "--host",
        help="Bind address (loopback only; default 127.0.0.1).",
    ),
    port: int = typer.Option(
        DEFAULT_PORT,
        "--port",
        help="Local port (Tailscale Serve proxies here).",
    ),
) -> None:
    """Serve the control-plane HUD on localhost (use Tailscale Serve; Funnel NO)."""
    try:
        bind_host = assert_loopback_host(host)
    except ValueError as exc:
        err_console.print(f"[red]bind refused:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    import uvicorn

    from ada.hud.app import create_app

    console.print(
        f"[bold]ADA HUD[/bold] http://{bind_host}:{port}/  "
        f"(Tailscale: [dim]tailscale serve --bg {port}[/dim]; Funnel off)"
    )
    console.print(
        "[dim]v1: one interactive run writer — avoid concurrent `ada chat` on same session.[/dim]"
    )
    uvicorn.run(create_app(), host=bind_host, port=port, log_level="info")


@memory_app.command("get")
def memory_get(
    key: str = typer.Argument(..., help="Fact key, e.g. prefs.brief_time"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Get a FACT by key."""
    from ada.memory.facts import get_fact

    try:
        result = get_fact(key)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data=result)
    else:
        console.print(result)


@memory_app.command("search")
def memory_search(
    query: str = typer.Argument(..., help="Key or grep query"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Search FACTS (key lookup + grep)."""
    from ada.memory.facts import search_facts

    try:
        result = search_facts(query)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data=result)
    else:
        console.print_json(data=result)


@memory_app.command("append")
def memory_append(
    key: str = typer.Option(..., "--key", "-k", help="e.g. prefs.brief_time"),
    value: str = typer.Option(..., "--value", "-v"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Append/set a FACT field (overwrite of different value → needs_confirm)."""
    from ada.memory.facts import append_fact

    # Coerce obvious bools.
    coerced: object = value
    low = value.strip().lower()
    if low in {"true", "false"}:
        coerced = low == "true"
    try:
        result = append_fact(key, coerced)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    except ValueError as exc:
        err_console.print(f"[red]bad args:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    if json_out:
        console.print_json(data=result)
    else:
        if result.get("needs_confirm"):
            console.print(f"[yellow]needs_confirm[/yellow] {result.get('reason')}")
        else:
            console.print(f"[green]ok[/green] {key}={result.get('value')!r}")
    if result.get("needs_confirm"):
        raise typer.Exit(code=2)


@memory_app.command("loops")
def memory_loops(
    json_out: bool = typer.Option(False, "--json"),
    campaigns: bool = typer.Option(
        False, "--campaigns", help="List campaigns only (any non-done STATUS)."
    ),
    kind: Optional[str] = typer.Option(
        None, "--kind", help="Filter kind: todo | campaign"
    ),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        help="Filter status (default: open for todos; omit with --campaigns).",
    ),
) -> None:
    """List open loops / campaigns (metal truth)."""
    from ada.memory.open_loops import list_campaigns, list_loops

    try:
        if campaigns or kind == "campaign":
            loops = list_campaigns(
                status=status,
                include_done=bool(status in {"done", "failed"}),
            )
        else:
            status_filter = "open" if status is None else status
            loops = list_loops(status=status_filter, kind=kind)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data={"loops": loops, "count": len(loops)})
    else:
        if not loops:
            console.print("(no loops)")
            return
        for loop in loops:
            if loop.get("kind") == "campaign":
                title = loop.get("title") or loop.get("text")
                console.print(
                    f"- [{loop.get('id')}] {title} "
                    f"STATUS={loop.get('status')} stage={loop.get('current_stage') or '-'}"
                )
            else:
                console.print(f"- [{loop.get('id')}] {loop.get('text')}")


@campaigns_app.command("status")
def campaigns_status(
    loop_id: Optional[str] = typer.Option(None, "--id", help="Campaign id"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Show campaign STATUS from disk (no Gemini)."""
    from ada.memory.open_loops import format_campaign_head, get_loop, list_campaigns

    try:
        if loop_id:
            item = get_loop(loop_id)
            if item is None or item.get("kind") != "campaign":
                err_console.print(f"[red]campaign not found:[/red] {loop_id}")
                raise typer.Exit(code=1)
            camps = [item]
        else:
            camps = list_campaigns(include_done=True, limit=100)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data={"campaigns": camps, "count": len(camps)})
        return
    if not camps:
        console.print("(no campaigns)")
        return
    for c in camps:
        console.print(format_campaign_head(c, max_len=400), markup=False)
        if c.get("blocked_reason"):
            console.print(f"    blocked_reason: {c.get('blocked_reason')}")
        if c.get("next_wake_at"):
            console.print(f"    next_wake_at: {c.get('next_wake_at')}")
        if c.get("last_receipt"):
            console.print(f"    last_receipt: {c.get('last_receipt')}")
        stages = c.get("stages") or []
        if stages:
            for s in stages:
                gate = f" gate={s.get('gate')}" if s.get("gate") else ""
                console.print(f"    - {s.get('id')}: {s.get('state')}{gate}")


@campaigns_app.command("check")
def campaigns_check(
    json_out: bool = typer.Option(False, "--json"),
    notify: bool = typer.Option(
        False,
        "--notify",
        help="Also attempt budgeted ntfy for due/remind todos (Phase 1).",
    ),
) -> None:
    """Local due/stale/blocked campaign list + due todos — no LLM.

    Quiet/mute suppress nudges. Enable ada-brief.timer for morning ritual.
    """
    from ada.memory.open_loops import campaign_check
    from ada.memory.proactivity import proactivity_suppressed

    try:
        suppress = proactivity_suppressed()
        if suppress.get("suppressed"):
            payload = {
                "ok": True,
                "outcome": "ok",
                "suppressed": True,
                "reasons": suppress.get("reasons"),
                "count": 0,
                "due": [],
                "due_todos": [],
                "due_todo_count": 0,
            }
        else:
            payload = campaign_check()
            if notify:
                from ada.memory.notify import notify_check_and_send

                payload["notify"] = notify_check_and_send(limit=1)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data=payload)
        return
    if payload.get("suppressed"):
        console.print(
            f"(suppressed: {', '.join(payload.get('reasons') or [])})"
        )
        return
    due = payload.get("due") or []
    due_todos = payload.get("due_todos") or []
    if not due and not due_todos:
        console.print("(no due campaigns or todos)")
        return
    for item in due_todos:
        console.print(
            f"- todo [{item.get('id')}] {item.get('title') or item.get('text')} "
            f"due={item.get('due_at')}"
        )
    for item in due:
        console.print(
            f"- [{item.get('id')}] {item.get('title')} "
            f"STATUS={item.get('status')} due={item.get('due_reason')}"
        )
    if payload.get("notify"):
        console.print(f"notify: {payload['notify'].get('results')}")


@watch_app.command("list")
def watch_list(
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Campaigns with non-empty watches[] (M09)."""
    from ada.memory.open_loops import list_watch_campaigns

    try:
        camps = list_watch_campaigns(include_done=False, limit=100)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data={"campaigns": camps, "count": len(camps)})
        return
    if not camps:
        console.print("(no watch campaigns)")
        return
    for c in camps:
        n = len(c.get("watches") or [])
        console.print(
            f"- [{c.get('id')}] {c.get('title') or c.get('text')} "
            f"STATUS={c.get('status')} watches={n}",
            markup=False,
        )


@watch_app.command("status")
def watch_status(
    loop_id: Optional[str] = typer.Option(None, "--campaign", "--id", help="Campaign id"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Watch cursors, last_error, last_receipt (M09)."""
    from ada.memory.open_loops import get_loop, list_watch_campaigns

    try:
        if loop_id:
            item = get_loop(loop_id)
            if item is None or not item.get("watches"):
                err_console.print(f"[red]watch campaign not found:[/red] {loop_id}")
                raise typer.Exit(code=1)
            camps = [item]
        else:
            camps = list_watch_campaigns(include_done=True, limit=100)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data={"campaigns": camps, "count": len(camps)})
        return
    if not camps:
        console.print("(no watch campaigns)")
        return
    for c in camps:
        console.print(f"[{c.get('id')}] {c.get('title') or c.get('text')}", markup=False)
        if c.get("last_receipt"):
            console.print(f"  last_receipt: {c.get('last_receipt')}")
        for w in c.get("watches") or []:
            cur = w.get("cursor") or {}
            seen_n = len(cur.get("seen_guids") or [])
            console.print(
                f"  - {w.get('id')} kind={w.get('kind')} "
                f"seen_guids={seen_n} last_checked={cur.get('last_checked_at') or '-'}"
            )
            if cur.get("last_error"):
                console.print(f"      last_error: {cur.get('last_error')}")


@watch_app.command("run")
def watch_run_cmd(
    campaign_id: Optional[str] = typer.Option(
        None, "--campaign", help="Run one campaign by id (default: one due watch)"
    ),
    ingest_only: bool = typer.Option(
        True,
        "--ingest-only/--digest",
        help="Phase A ingest only (default). Digest harness deferred (M09 Phase B).",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Triage + list would-fetch; no article web_fetch"
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Execute one campaign watch wake — bounded fetch → cites (M09)."""
    from ada.memory.proactivity import proactivity_suppressed
    from ada.watch.run import watch_run

    try:
        # Ingest-only runs during quiet hours (heal-first). Digest/nudges defer.
        if not ingest_only:
            suppress = proactivity_suppressed()
            if suppress.get("suppressed"):
                payload = {
                    "ok": True,
                    "outcome": "suppressed",
                    "reasons": suppress.get("reasons"),
                }
                if json_out:
                    console.print_json(data=payload)
                else:
                    console.print(
                        f"(suppressed digest: {', '.join(suppress.get('reasons') or [])})"
                    )
                return
        result = watch_run(
            campaign_id=campaign_id,
            ingest_only=ingest_only,
            dry_run=dry_run,
        )
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data=result)
        return
    if not result.get("ok"):
        err_console.print(f"[red]watch failed:[/red] {result.get('error')}")
        raise typer.Exit(code=1)
    if result.get("outcome") == "idle" and result.get("reason") == "no_due_watch_campaign":
        console.print("(no due watch campaigns)")
        return
    mode = "dry-run" if dry_run else "live"
    console.print(
        f"[green]watch_ok[/green] campaign={result.get('campaign_id')} "
        f"mode={mode} fetched={result.get('fetched')} skipped={result.get('skipped')}"
    )
    if result.get("session"):
        console.print(f"  session: {result.get('session')}")
    if result.get("last_receipt"):
        console.print(f"  last_receipt: {result.get('last_receipt')}")


@dream_app.command("status")
def dream_status_cmd(
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Show last dream_ok/fail + outbox pending."""
    from ada.dream.run import dream_status

    try:
        status = dream_status()
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data=status)
    else:
        ok = status.get("last_dream_ok")
        fail = status.get("last_dream_fail")
        console.print(f"last_dream_ok: {ok['ts'] if ok else '(none)'} id={ok['id'] if ok else '-'}")
        console.print(
            f"last_dream_fail: {fail['ts'] if fail else '(none)'} "
            f"id={fail['id'] if fail else '-'}"
        )
        console.print(f"outbox_pending: {status.get('outbox_count')} {status.get('outbox_pending')}")
        console.print(f"staging_pending: {status.get('staging_pending')}")
        console.print(f"push: {status.get('push')}")


@staging_app.command("list")
def staging_list_cmd(
    limit: int = typer.Option(50, "--limit", "-n"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """List pending (and recent) Dream staging files."""
    from ada.memory.staging import list_staged

    try:
        items = list_staged(limit=limit)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data={"staged": items, "count": len(items)})
        return
    pending = [s for s in items if s.get("status") == "pending"]
    console.print(f"staging: {len(pending)} pending / {len(items)} shown")
    for s in items:
        console.print(
            f"- [{s.get('id')}] status={s.get('status')} reason={s.get('reason')} "
            f"ts={s.get('ts')}"
        )


@staging_app.command("confirm")
def staging_confirm_cmd(
    staging_id: str = typer.Argument(..., help="Staging id from memory/staging/<id>.json"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Confirm-once a staged open_loop / FACT candidate (M11-B)."""
    from ada.memory.staging import confirm_staged

    try:
        result = confirm_staged(staging_id)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data=result)
        return
    if result.get("needs_confirm"):
        console.print(
            f"[yellow]needs_confirm[/yellow] {result.get('reason')} "
            f"(staging {staging_id} still pending)"
        )
        raise typer.Exit(code=2)
    if not result.get("ok"):
        err_console.print(f"[red]staging confirm failed:[/red] {result.get('error')}")
        raise typer.Exit(code=1)
    console.print(f"[green]confirmed[/green] {staging_id}")


@staging_app.command("reject")
def staging_reject_cmd(
    staging_id: str = typer.Argument(..., help="Staging id"),
    reason: Optional[str] = typer.Option(None, "--reason", "-r"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Reject a staged proposal without applying it."""
    from ada.memory.staging import reject_staged

    try:
        result = reject_staged(staging_id, reason=reason)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data=result)
        return
    if not result.get("ok"):
        err_console.print(f"[red]staging reject failed:[/red] {result.get('error')}")
        raise typer.Exit(code=1)
    console.print(f"[yellow]rejected[/yellow] {staging_id}")


@dream_app.command("run")
def dream_run_cmd(
    skip_manage: bool = typer.Option(
        False,
        "--skip-manage",
        help="Seal only — skip Gemini manage-pass (still dream_ok on seal).",
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Local Dream: delta → seal → capped manage → whitelist merge → push stub."""
    from ada.dream.run import dream_run

    try:
        result = dream_run(skip_manage=skip_manage)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        # Avoid dumping huge nested objects with non-JSON types.
        slim = {
            "ok": result.get("ok"),
            "status": result.get("status"),
            "dream_id": result.get("dream_id"),
            "receipts": result.get("receipts"),
            "push": result.get("push"),
            "manage": {
                "ok": (result.get("manage") or {}).get("ok"),
                "skipped": (result.get("manage") or {}).get("skipped"),
                "reason": (result.get("manage") or {}).get("reason"),
            },
        }
        console.print_json(data=slim)
    else:
        rid = result.get("dream_id")
        push = (result.get("push") or {}).get("push")
        manage = result.get("manage") or {}
        console.print(f"[green]dream_ok[/green] {rid}")
        console.print(
            f"  seal={result.get('seal', {}).get('package_sha256', '')[:16]}… "
            f"manage_skipped={manage.get('skipped')} push={push}"
        )
        console.print(f"  outbox={result.get('seal', {}).get('outbox_path')}")


@web_app.command("fetch")
def web_fetch_cmd(
    url: str = typer.Argument(..., help="Absolute https URL"),
    force: bool = typer.Option(False, "--force", help="Bypass TTL / skip 304"),
    ignore_robots: bool = typer.Option(
        False, "--ignore-robots", help="User-intent robots override"
    ),
    confirm_host: bool = typer.Option(
        False, "--confirm-host", help="Allowlist new host after confirm"
    ),
    user_pasted: bool = typer.Option(
        True,
        "--user-pasted/--no-user-pasted",
        help="Treat URL as pasted this turn (default true for CLI)",
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Allowlisted GET + extract + durable cite (gateway-equivalent)."""
    from ada.web.fetch import web_fetch

    try:
        require_ada_data()
        result = web_fetch(
            url,
            force=force,
            user_pasted=user_pasted,
            turn_user_text=url if user_pasted else None,
            ignore_robots=ignore_robots,
            confirm_host=confirm_host,
        )
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data=result)
    else:
        if result.get("needs_confirm"):
            console.print(
                f"[yellow]needs_confirm[/yellow] host={result.get('host')} "
                f"— re-run with --confirm-host"
            )
            raise typer.Exit(code=2)
        if not result.get("ok"):
            err_console.print(f"[red]fetch failed:[/red] {result.get('error')}")
            raise typer.Exit(code=1)
        console.print(
            f"[green]ok[/green] cite_id={result.get('cite_id')} "
            f"cache={result.get('cache')} truncated={result.get('truncated')}"
        )
        if result.get("title"):
            console.print(f"  title: {result.get('title')}")
        console.print(f"  url: {result.get('final_url') or result.get('url')}")


@web_app.command("cite")
def web_cite_cmd(
    cite_id: str = typer.Argument(..., help="Cite id (c_…) or cite:c_…"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Read a durable cite from disk (no network; cortex-down OK)."""
    from ada.web.fetch import web_cite_get

    try:
        require_ada_data()
        result = web_cite_get(cite_id)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data=result)
    else:
        if not result.get("ok"):
            err_console.print(f"[red]cite failed:[/red] {result.get('error')}")
            raise typer.Exit(code=1)
        console.print(f"[green]cite[/green] {result.get('cite_id')}")
        console.print(f"  title: {result.get('title')}")
        console.print(f"  url: {result.get('url')}")
        console.print(f"  fetched_at: {result.get('fetched_at')}")
        for i, ex in enumerate(result.get("excerpts") or [], 1):
            preview = ex if len(ex) <= 240 else ex[:240] + "…"
            console.print(f"  excerpt[{i}]: {preview}")


@web_app.command("search")
def web_search_cmd(
    query: str = typer.Argument(..., help="Substring over title/url/cite id"),
    max_hits: int = typer.Option(10, "--max", help="Max hits"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Search local cite library (no network — not vendor web_search)."""
    from ada.web.fetch import web_cite_search

    try:
        require_ada_data()
        result = web_cite_search(query, max_hits=max_hits)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data=result)
        return
    if not result.get("ok"):
        err_console.print(f"[red]search failed:[/red] {result.get('error')}")
        raise typer.Exit(code=1)
    hits = result.get("hits") or []
    if not hits:
        console.print(f"(no cites matching {query!r})")
        return
    for h in hits:
        console.print(
            f"- {h.get('cite_id')}  {h.get('title') or '(no title)'}  "
            f"{h.get('url')}"
        )


@web_app.command("reclassify")
def web_reclassify_cmd(
    dry_run: bool = typer.Option(False, "--dry-run", help="Report only; do not rewrite"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Mark legacy js_shell / feed_blob cites (tombstone; no delete) — M10."""
    from ada.web.cites import reclassify_existing_cites

    try:
        require_ada_data()
        result = reclassify_existing_cites(dry_run=dry_run)
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if json_out:
        console.print_json(data=result)
        return
    console.print(
        f"[green]reclassify[/green] updated={result.get('count')} "
        f"dry_run={result.get('dry_run')}"
    )
    for row in result.get("updated") or []:
        console.print(
            f"  - {row.get('cite_id')} kind={row.get('kind')} "
            f"status={row.get('extract_status')} ({row.get('reason')})"
        )


@web_app.command("allowlist")
def web_allowlist_cmd(
    action: str = typer.Argument("list", help="list | add | packs | seed"),
    host: Optional[str] = typer.Argument(
        None, help="Host for add, or pack id for seed (e.g. lab.papers; alias: lab)"
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """List/add live prefs hosts, list catalog packs, or seed a named pack (M08)."""
    from ada.web import allowlist as allowlist_mod
    from ada.web.packs import list_pack_summaries, seed_pack

    try:
        paths = require_ada_data()
        if action == "list":
            entries = allowlist_mod.load_allowlist(paths)
            if json_out:
                console.print_json(data={"allowlist": entries})
            else:
                if not entries:
                    console.print("(empty allowlist)")
                for e in entries:
                    line = f"- {e.get('host')} ttl={e.get('ttl_seconds')}"
                    if e.get("note"):
                        line += f" note={e.get('note')}"
                    console.print(line)
            return
        if action == "add":
            if not host:
                err_console.print("[red]host required for add[/red]")
                raise typer.Exit(code=2)
            result = allowlist_mod.add_host(host, paths=paths)
            if json_out:
                console.print_json(data=result)
            else:
                if not result.get("ok"):
                    err_console.print(f"[red]refused:[/red] {result.get('error')}")
                    raise typer.Exit(code=2)
                mark = "already" if result.get("already") else "allowlisted"
                console.print(f"[green]{mark}[/green] {result.get('host')}")
            if not result.get("ok"):
                raise typer.Exit(code=2)
            return
        if action == "packs":
            rows = list_pack_summaries()
            if json_out:
                console.print_json(data={"packs": rows, "count": len(rows)})
                return
            if not rows:
                console.print("(no packs in catalog)")
                return
            for row in rows:
                extra = ""
                if row.get("inherits"):
                    extra = f" inherits={','.join(row['inherits'])}"
                day = " day-one" if row.get("day_one") else ""
                console.print(
                    f"- {row['id']}  {row['host_count']} hosts{day}  {row['title']}{extra}"
                )
            return
        if action == "seed":
            if not host:
                err_console.print(
                    "[red]pack id required for seed[/red] "
                    "(e.g. lab.papers, nz.law, or alias lab)"
                )
                raise typer.Exit(code=2)
            result = seed_pack(host, paths=paths)
            if json_out:
                console.print_json(data=result)
            else:
                if not result.get("ok"):
                    err_console.print(f"[red]seed failed:[/red] {result.get('error')}")
                    raise typer.Exit(code=2)
                ids = ", ".join(result.get("pack_ids") or [])
                console.print(
                    f"[green]seeded[/green] {ids} "
                    f"added={len(result.get('added') or [])} "
                    f"already={len(result.get('already') or [])} "
                    f"total={result.get('count')}"
                )
            if not result.get("ok"):
                raise typer.Exit(code=2)
            return
        err_console.print(f"[red]unknown action:[/red] {action} (list|add|packs|seed)")
        raise typer.Exit(code=2)
    except BodyFault as exc:
        _exit_body_fault(exc)


@life_app.command("food-import-nz")
def life_food_import_nz(
    path: Path = typer.Argument(..., help="Directory with NZ FOODfiles CSV"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Import NZ FOODfiles CSV into food_reference.db."""
    from ada.logs.food_import_nz import import_nz_foodfiles

    try:
        result = import_nz_foodfiles(path)
    except BodyFault as exc:
        _exit_body_fault(exc)
    if json_out:
        console.print_json(data=result)
    elif result.get("ok"):
        console.print(f"imported {result.get('imported', 0)} rows from {result.get('files', 0)} files")
    else:
        err_console.print(f"[red]import failed:[/red] {result.get('error')}")
        raise typer.Exit(code=1)


@life_app.command("food-search")
def life_food_search_cli(
    query: str = typer.Argument(..., help="Food name query"),
    json_out: bool = typer.Option(False, "--json"),
    no_fetch: bool = typer.Option(False, "--no-fetch", help="Cache only"),
) -> None:
    from ada.tools.life_tools import run_life_food_search

    result = run_life_food_search({"query": query, "fetch_remote": not no_fetch})
    if json_out:
        console.print_json(data=result)
    else:
        for c in result.get("candidates") or []:
            console.print(f"{c.get('ref_id')}  {c.get('name')}  ({c.get('source')})")


@life_app.command("food-forget")
def life_food_forget_cli(
    name: Optional[str] = typer.Option(None, "--name", help="Forget custom cache rows matching name"),
    ref_id: Optional[str] = typer.Option(None, "--ref-id", help="Delete one food row by ref_id"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Remove custom food-cache stubs. Never deletes USDA/OFF rows by name-match."""
    from ada.logs.food import delete_food, forget_foods

    if ref_id:
        result = delete_food(ref_id)
    elif name:
        result = forget_foods(name, source="custom")
    else:
        err_console.print("[red]need --name or --ref-id[/red]")
        raise typer.Exit(code=2)
    if json_out:
        console.print_json(data=result)
    elif result.get("ok"):
        console.print(f"deleted={result.get('deleted', 0)}")
    else:
        err_console.print(f"[red]forget failed:[/red] {result.get('reason')}")
        raise typer.Exit(code=1)


@life_app.command("barcode-lookup")
def life_barcode_lookup_cli(
    barcode: str = typer.Argument(..., help="GTIN barcode"),
    json_out: bool = typer.Option(False, "--json"),
    no_fetch: bool = typer.Option(False, "--no-fetch", help="Cache only"),
) -> None:
    from ada.tools.life_tools import run_life_barcode_lookup

    result = run_life_barcode_lookup(
        {"barcode": barcode, "fetch_remote": not no_fetch}
    )
    if json_out:
        console.print_json(data=result)
    elif result.get("ok"):
        console.print(f"{result.get('name')}  ref={result.get('ref_id')}")
    else:
        err_console.print(f"[red]miss:[/red] {result.get('reason')}")
        raise typer.Exit(code=1)


@life_app.command("gym-import-seed")
def life_gym_import_seed(
    json_out: bool = typer.Option(False, "--json"),
    path: Optional[Path] = typer.Option(None, "--path", help="Override seed JSON"),
) -> None:
    """Import bundled exercise catalog (idempotent). Optional --path for wger/exercisedb JSON."""
    from ada.logs.gym_import import import_exercise_seed

    try:
        result = import_exercise_seed(path=path)
    except BodyFault as exc:
        _exit_body_fault(exc)
    if json_out:
        console.print_json(data=result)
    else:
        console.print(f"imported {result.get('imported', 0)} exercises")


@life_app.command("gym-init")
def life_gym_init(
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Ensure exercise catalog is populated (same auto-init as first DB open)."""
    from ada.logs.connection import open_life_db

    try:
        with open_life_db() as conn:
            count = int(
                conn.execute("SELECT COUNT(*) FROM exercise_catalog").fetchone()[0]
            )
        result = {"ok": True, "catalog_count": count}
    except BodyFault as exc:
        _exit_body_fault(exc)
    if json_out:
        console.print_json(data=result)
    else:
        console.print(f"exercise catalog: {result.get('catalog_count', 0)} rows")


@life_app.command("capture")
def life_capture_cli(
    text: str = typer.Option(..., "--text", "-t"),
    kind: Optional[str] = typer.Option(None, "--kind"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    obs = _life_gw().execute("life_capture", {"text": text, "kind": kind})
    if json_out:
        console.print_json(data=obs.as_observation())
    elif obs.ok:
        console.print(f"kind={obs.data.get('kind')} id={obs.data.get('open_loop_id') or obs.data.get('path')}")
    else:
        raise typer.Exit(code=1)


def _life_gw():
    from ada.tools.gateway import Gateway

    return Gateway(mode="agent")


@life_app.command("meal-log")
def life_meal_log_cli(
    lines_json: str = typer.Option(..., "--lines", help="JSON array of food lines"),
    note: Optional[str] = typer.Option(None, "--note"),
    meal_slot: Optional[str] = typer.Option(None, "--meal-slot"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    lines = json.loads(lines_json)
    obs = _life_gw().execute(
        "life_meal_log", {"lines": lines, "note": note, "meal_slot": meal_slot}
    )
    if json_out:
        console.print_json(data=obs.as_observation())
    elif obs.ok:
        console.print(f"meal_id={obs.data.get('meal_id')} kcal={obs.data.get('kcal')}")
    else:
        raise typer.Exit(code=1)


@life_app.command("nutrition-day")
def life_nutrition_day_cli(
    date: Optional[str] = typer.Option(None, "--date"),
    today: bool = typer.Option(False, "--today"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    from ada.tools.gateway import Gateway

    obs = Gateway(mode="observe").execute(
        "life_nutrition_day",
        {"date": None if today else date},
    )
    if json_out:
        console.print_json(data=obs.as_observation())
    else:
        d = obs.data or {}
        console.print(f"day={d.get('date')} totals={d.get('totals')}")


@life_app.command("lift-log")
def life_lift_log_cli(
    sets_json: str = typer.Option(..., "--sets", help="JSON array of sets"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    sets = json.loads(sets_json)
    obs = _life_gw().execute("life_lift_log", {"sets": sets})
    if json_out:
        console.print_json(data=obs.as_observation())
    elif obs.ok:
        console.print(f"session={obs.data.get('session_id')} volume={obs.data.get('volume_kg')}")
    else:
        raise typer.Exit(code=1)


@life_app.command("time-start")
def life_time_start_cli(
    kind: str = typer.Option(..., "--kind"),
    label: Optional[str] = typer.Option(None, "--label"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    obs = _life_gw().execute("life_time_start", {"kind": kind, "label": label})
    if json_out:
        console.print_json(data=obs.as_observation())
    elif obs.ok:
        console.print(f"block={obs.data.get('block_id')} kind={obs.data.get('kind')}")
    else:
        raise typer.Exit(code=1)


@life_app.command("time-stop")
def life_time_stop_cli(
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    obs = _life_gw().execute("life_time_stop", {})
    if json_out:
        console.print_json(data=obs.as_observation())
    elif obs.ok:
        console.print(f"duration_s={obs.data.get('duration_s')}")
    else:
        raise typer.Exit(code=1)


@life_app.command("time-status")
def life_time_status_cli(
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    from ada.tools.gateway import Gateway

    obs = Gateway(mode="observe").execute("life_time_status", {})
    if json_out:
        console.print_json(data=obs.as_observation())
    else:
        console.print_json(data=obs.data)


def _repo_root() -> Path:
    # src/ada/cli/main.py → parents[3] = repo root
    return Path(__file__).resolve().parents[3]


def _git_sha(repo: Path) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    sha = (proc.stdout or "").strip()
    return sha or None


def _parse_pytest_counts(output: str) -> dict[str, int]:
    """Parse quiet pytest summary for pass/fail/skip/error counts."""
    counts = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "xfailed": 0}
    # Prefer the final summary line (e.g. "12 passed, 1 skipped in 2.34s").
    for line in reversed(output.splitlines()):
        low = line.strip().lower()
        if not any(k in low for k in ("passed", "failed", "skipped", "error")):
            continue
        for key, pat in (
            ("passed", r"(\d+)\s+passed"),
            ("failed", r"(\d+)\s+failed"),
            ("skipped", r"(\d+)\s+skipped"),
            ("errors", r"(\d+)\s+error"),
            ("xfailed", r"(\d+)\s+xfailed"),
        ):
            m = re.search(pat, low)
            if m:
                counts[key] = int(m.group(1))
        if any(counts[k] for k in counts):
            break
    return counts


@tier_a_app.command("check")
def tier_a_check(
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Machine-readable receipt (no secrets).",
    ),
) -> None:
    """Run pytest -m tier_a and print a pass/fail receipt (M18 Close-1)."""
    repo = _repo_root()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sha = _git_sha(repo)
    cmd = [sys.executable, "-m", "pytest", "-m", "tier_a", "-q", "--tb=line"]
    proc = subprocess.run(
        cmd,
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    counts = _parse_pytest_counts(combined)
    verdict = "PASS" if proc.returncode == 0 else "FAIL"
    receipt = {
        "gate": "tier_a",
        "verdict": verdict,
        "timestamp": ts,
        "git_sha": sha,
        "exit_code": proc.returncode,
        "passed": counts["passed"],
        "failed": counts["failed"],
        "skipped": counts["skipped"],
        "errors": counts["errors"],
        "xfailed": counts["xfailed"],
        "command": " ".join(cmd),
    }
    if json_out:
        console.print_json(data=receipt)
    else:
        console.print(f"[bold]Tier A gate[/bold]  verdict={verdict}")
        console.print(f"  timestamp: {ts}")
        console.print(f"  git_sha:   {sha or '(unavailable)'}")
        console.print(
            f"  counts:    passed={counts['passed']} failed={counts['failed']} "
            f"skipped={counts['skipped']} errors={counts['errors']}"
        )
        console.print(f"  exit_code: {proc.returncode}")
        # Tail of pytest output (no secrets expected in unit suite).
        tail = "\n".join(combined.strip().splitlines()[-12:])
        if tail:
            console.print()
            console.print(tail)
    if proc.returncode != 0:
        raise typer.Exit(code=proc.returncode)


@app.callback()
def main_callback() -> None:
    """ADA — body sense + chat harness + HUD + memory/Dream + web."""


def main() -> None:
    app()


if __name__ == "__main__":
    app()
