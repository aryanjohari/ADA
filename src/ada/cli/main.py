"""Body sense + chat harness + HUD + memory/Dream CLI (M00/M02/M03/M04)."""

from __future__ import annotations

import json
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
campaigns_app = typer.Typer(
    help="Campaign STATUS on disk (M06) — metal truth, no Gemini.",
    no_args_is_help=True,
)
app.add_typer(body_app, name="body")
app.add_typer(hud_app, name="hud")
app.add_typer(memory_app, name="memory")
app.add_typer(dream_app, name="dream")
app.add_typer(campaigns_app, name="campaigns")


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
    """Create identity once if missing; idempotent if already born."""
    try:
        card, created = identity_mod.create_identity()
    except BodyFault as exc:
        _exit_body_fault(exc)
        return
    if created:
        console.print(f"[green]born[/green] at {card.born_at} on {card.body_hostname}")
    else:
        console.print(f"already born at {card.born_at} (born_at unchanged)")


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
    else:
        table.add_row("urgent", "none")
    console.print(table)

    if not mounted:
        raise typer.Exit(code=3)
    if urgent and not snap.mounts.ada_data_ok:
        raise typer.Exit(code=3)
    if snap.probe_errors or urgent:
        raise typer.Exit(code=2)


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
        console.print(format_campaign_head(c, max_len=400))
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
) -> None:
    """Local due/stale/blocked campaign list — no LLM. Quiet/mute suppress nudges."""
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
            }
        else:
            payload = campaign_check()
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
    if not due:
        console.print("(no due campaigns)")
        return
    for item in due:
        console.print(
            f"- [{item.get('id')}] {item.get('title')} "
            f"STATUS={item.get('status')} due={item.get('due_reason')}"
        )


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


@app.callback()
def main_callback() -> None:
    """ADA — body sense + chat harness + HUD + memory/Dream."""


def main() -> None:
    app()


if __name__ == "__main__":
    app()
