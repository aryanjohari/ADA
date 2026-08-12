"""No-Gemini CLI for body sense: status, birth, wake, story, doctor."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ada import __version__
from ada.body import identity as identity_mod
from ada.body import lifecycle as lifecycle_mod
from ada.body import narrative
from ada.body.vitals import VitalsSnapshot, collect_vitals, urgent_faults
from ada.io.paths import BodyFault, ada_data_mounted, get_paths, require_ada_data

console = Console(stderr=False)
err_console = Console(stderr=True)

app = typer.Typer(name="ada", help="ADA body organs (M00 — no cortex).", no_args_is_help=True)
body_app = typer.Typer(help="Body sense: vitals, identity, lifecycle.", no_args_is_help=True)
app.add_typer(body_app, name="body")


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


@app.callback()
def main_callback() -> None:
    """ADA — body sense CLI (M00)."""


# Typer/Click entrypoint for console_scripts
def main() -> None:
    app()


# setuptools: ada = ada.cli.main:app — Typer instance is a Click command group
if __name__ == "__main__":
    app()
