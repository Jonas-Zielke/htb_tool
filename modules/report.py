"""
HTB Tool — Report Generation Module

Commands:
  htb report generate    Generate HTML report
  htb report markdown    Generate Markdown report
  htb report show        Show report summary in terminal
  htb report notes add   Add manual notes
  htb report notes list  List all notes
  htb report creds add   Add credentials
  htb report creds list  List credentials
"""
import webbrowser
from datetime import datetime
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from core.project import (
    require_active_project, save_project, get_project_output_dir,
)
from core.logger import ActivityLogger

console = Console()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


# ── Report generators ────────────────────────────────────────────────────────

def _generate_html_report(data: dict, output_path: Path) -> None:
    """Generate an HTML report using Jinja2 template."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("report.html.j2")

    html = template.render(
        project=data,
        target=data.get("target", {}),
        ports=data.get("open_ports", []),
        scans=data.get("scan_results", []),
        credentials=data.get("credentials", []),
        notes=data.get("notes", []),
        activity_log=data.get("activity_log", []),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    with open(output_path, "w") as f:
        f.write(html)


def _generate_markdown_report(data: dict, output_path: Path) -> None:
    """Generate a Markdown report."""
    target = data.get("target", {})
    ports = data.get("open_ports", [])
    scans = data.get("scan_results", [])
    creds = data.get("credentials", [])
    notes = data.get("notes", [])
    log = data.get("activity_log", [])

    lines = [
        f"# HTB Report — {data['name']}",
        f"",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Created:** {data.get('created', '—')}",
        f"",
        f"---",
        f"",
        f"## Target Information",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| **IP** | `{target.get('ip', '—')}` |",
        f"| **Hostname** | `{target.get('hostname', '—')}` |",
        f"| **OS** | {target.get('os_guess', '—')} |",
        f"",
    ]

    # Open ports
    if ports:
        lines.extend([
            f"## Open Ports",
            f"",
            f"| Port | Protocol | Service | Version |",
            f"|------|----------|---------|---------|",
        ])
        for p in ports:
            lines.append(
                f"| {p.get('port', '?')} | {p.get('protocol', 'tcp')} | "
                f"{p.get('service', '?')} | {p.get('version', '')} |"
            )
        lines.append("")

    # Scan results
    if scans:
        lines.extend([
            f"## Scan Results",
            f"",
            f"| Type | Timestamp | Ports Found | Command |",
            f"|------|-----------|-------------|---------|",
        ])
        for s in scans:
            lines.append(
                f"| {s.get('type', '?')} | {s.get('timestamp', '?')[:19]} | "
                f"{s.get('ports_found', '—')} | `{s.get('command', '—')[:60]}` |"
            )
        lines.append("")

    # Credentials
    if creds:
        lines.extend([
            f"## Credentials Found",
            f"",
            f"| Username | Password | Source | Notes |",
            f"|----------|----------|--------|-------|",
        ])
        for c in creds:
            lines.append(
                f"| `{c.get('username', '—')}` | `{c.get('password', '—')}` | "
                f"{c.get('source', '—')} | {c.get('notes', '')} |"
            )
        lines.append("")

    # Notes
    if notes:
        lines.extend([f"## Notes", f""])
        for n in notes:
            ts = n.get("timestamp", "")[:19]
            lines.append(f"- **[{ts}]** {n.get('text', '')}")
        lines.append("")

    # Activity log
    if log:
        lines.extend([
            f"## Activity Log",
            f"",
            f"| Timestamp | Action | Details | Command |",
            f"|-----------|--------|---------|---------|",
        ])
        for entry in log:
            ts = entry.get("timestamp", "")[:19]
            action = entry.get("action", "—")
            details = entry.get("details", "")[:50]
            command = entry.get("command", "")[:40]
            lines.append(f"| {ts} | `{action}` | {details} | `{command}` |")
        lines.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


# ── Click commands ───────────────────────────────────────────────────────────

@click.group("report")
def report_group():
    """📄 Generate reports and manage notes/credentials."""
    pass


@report_group.command("generate")
@click.option("--format", "-f", "fmt", type=click.Choice(["html", "md", "both"]),
              default="both", help="Report format")
@click.option("--open", "open_browser", is_flag=True, help="Open HTML report in browser")
def report_generate(fmt, open_browser):
    """Generate a report from project data."""
    data = require_active_project()
    logger = ActivityLogger(data)
    output_dir = get_project_output_dir(data["name"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    generated = []

    if fmt in ("html", "both"):
        html_path = output_dir / f"report_{timestamp}.html"
        _generate_html_report(data, html_path)
        generated.append(("HTML", html_path))
        console.print(f"[bold green]✓[/] HTML report: [cyan]{html_path}[/]")
        if open_browser:
            webbrowser.open(f"file://{html_path}")

    if fmt in ("md", "both"):
        md_path = output_dir / f"report_{timestamp}.md"
        _generate_markdown_report(data, md_path)
        generated.append(("Markdown", md_path))
        console.print(f"[bold green]✓[/] Markdown report: [cyan]{md_path}[/]")

    logger.log("report:generate", details=f"Generated {fmt} report(s)")
    save_project(data)


@report_group.command("show")
def report_show():
    """Display a summary of the current project in the terminal."""
    from core.project import display_project_status
    data = require_active_project()
    display_project_status(data)

    # Also show recent activity
    log = data.get("activity_log", [])
    if log:
        console.print()
        table = Table(title="Recent Activity (last 10)", header_style="bold magenta")
        table.add_column("Time", style="dim", width=20)
        table.add_column("Action", style="cyan")
        table.add_column("Details", style="white")
        for entry in log[-10:]:
            table.add_row(
                entry.get("timestamp", "")[:19],
                entry.get("action", "—"),
                entry.get("details", "")[:60],
            )
        console.print(table)

    # Show credentials
    creds = data.get("credentials", [])
    if creds:
        console.print()
        cred_table = Table(title="🔑 Credentials", header_style="bold red")
        cred_table.add_column("Username", style="cyan")
        cred_table.add_column("Password", style="yellow")
        cred_table.add_column("Source", style="dim")
        for c in creds:
            cred_table.add_row(c.get("username", ""), c.get("password", ""), c.get("source", ""))
        console.print(cred_table)


# ── Notes sub-group ──────────────────────────────────────────────────────────

@report_group.group("notes")
def notes_group():
    """📝 Manage project notes."""
    pass


@notes_group.command("add")
@click.argument("text")
def notes_add(text):
    """Add a note to the project."""
    data = require_active_project()
    logger = ActivityLogger(data)

    note = {
        "timestamp": datetime.now().isoformat(),
        "text": text,
    }
    data.setdefault("notes", []).append(note)
    logger.log("notes:add", details=text[:100])
    save_project(data)
    console.print(f"[bold green]✓[/] Note added: [white]{text}[/]")


@notes_group.command("list")
def notes_list():
    """List all project notes."""
    data = require_active_project()
    notes = data.get("notes", [])

    if not notes:
        console.print("[dim]No notes yet. Add one with [bold]htb report notes add 'your note'[/][/]")
        return

    for i, note in enumerate(notes, 1):
        ts = note.get("timestamp", "")[:19]
        console.print(f"  [dim]{i}.[/] [dim cyan]{ts}[/]  {note.get('text', '')}")


# ── Credentials sub-group ───────────────────────────────────────────────────

@report_group.group("creds")
def creds_group():
    """🔑 Manage discovered credentials."""
    pass


@creds_group.command("add")
@click.argument("username")
@click.argument("password")
@click.option("--source", "-s", default="manual", help="Where the credential was found")
@click.option("--notes", "-n", default="", help="Additional notes")
def creds_add(username, password, source, notes):
    """Add discovered credentials."""
    data = require_active_project()
    logger = ActivityLogger(data)

    cred = {
        "username": username,
        "password": password,
        "source": source,
        "notes": notes,
        "timestamp": datetime.now().isoformat(),
    }
    data.setdefault("credentials", []).append(cred)
    logger.log("creds:add", details=f"Added credential: {username}")
    save_project(data)

    console.print(f"[bold green]✓[/] Credential added: [cyan]{username}[/]:[yellow]{password}[/] [dim]({source})[/]")


@creds_group.command("list")
def creds_list():
    """List all discovered credentials."""
    data = require_active_project()
    creds = data.get("credentials", [])

    if not creds:
        console.print("[dim]No credentials yet.[/]")
        return

    table = Table(title="🔑 Credentials", header_style="bold red")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Username", style="cyan")
    table.add_column("Password", style="yellow")
    table.add_column("Source", style="white")
    table.add_column("Notes", style="dim")
    for i, c in enumerate(creds, 1):
        table.add_row(str(i), c["username"], c["password"], c.get("source", ""), c.get("notes", ""))
    console.print(table)
