"""
HTB Toolbox — Reports, Notes & Credentials Screens
"""
import webbrowser
from datetime import datetime
from pathlib import Path

from ui.helpers import (
    console, pause, ask, show_error, show_success, show_info,
    menu_header, render_menu, choose, get_project_or_warn,
)
from core.project import save_project, get_project_output_dir, display_project_status
from core.logger import ActivityLogger
from modules.report import _generate_html_report, _generate_markdown_report
from rich.table import Table
from rich.panel import Panel


def menu_report():
    while True:
        menu_header()
        items = [
            ("1", "📊", "View Dashboard"),
            ("2", "📄", "Generate HTML Report"),
            ("3", "📝", "Generate Markdown Report"),
            ("4", "📑", "Generate Both Reports"),
            ("5", "➕", "Add Note"),
            ("6", "📋", "View Notes"),
            ("7", "🔑", "Add Credentials"),
            ("8", "🗝️ ", "View Credentials"),
            ("9", "📜", "View Activity Log"),
        ]
        render_menu("Reports, Notes & Credentials", items)
        c = choose(items)
        if c == "0": return
        elif c == "1": action_dashboard()
        elif c == "2": action_gen_html()
        elif c == "3": action_gen_md()
        elif c == "4": action_gen_both()
        elif c == "5": action_add_note()
        elif c == "6": action_view_notes()
        elif c == "7": action_add_creds()
        elif c == "8": action_view_creds()
        elif c == "9": action_view_log()


def action_dashboard():
    data = get_project_or_warn()
    if not data:
        return
    menu_header("Project Dashboard")
    display_project_status(data)

    log = data.get("activity_log", [])
    if log:
        console.print()
        table = Table(title="Recent Activity (last 15)", header_style="bold magenta")
        table.add_column("Time", style="dim", width=20)
        table.add_column("Action", style="cyan")
        table.add_column("Details", style="white", max_width=50)
        for entry in log[-15:]:
            table.add_row(
                entry.get("timestamp", "")[:19],
                entry.get("action", "—"),
                entry.get("details", "")[:50],
            )
        console.print(table)
    pause()


def _gen_report(fmt):
    data = get_project_or_warn()
    if not data:
        return
    output_dir = get_project_output_dir(data["name"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = ActivityLogger(data)

    if fmt in ("html", "both"):
        path = output_dir / f"report_{timestamp}.html"
        _generate_html_report(data, path)
        show_success(f"HTML report: [cyan]{path}[/]")

    if fmt in ("md", "both"):
        path = output_dir / f"report_{timestamp}.md"
        _generate_markdown_report(data, path)
        show_success(f"Markdown report: [cyan]{path}[/]")

    logger.log("report:generate", details=f"Generated {fmt} report")
    save_project(data)
    pause()


def action_gen_html():
    menu_header("Generate HTML Report")
    _gen_report("html")


def action_gen_md():
    menu_header("Generate Markdown Report")
    _gen_report("md")


def action_gen_both():
    menu_header("Generate Reports")
    _gen_report("both")


def action_add_note():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Add Note")
    text = ask("Note text")
    if not text:
        return

    note = {"timestamp": datetime.now().isoformat(), "text": text}
    data.setdefault("notes", []).append(note)

    logger = ActivityLogger(data)
    logger.log("notes:add", details=text[:100])
    save_project(data)
    show_success(f"Note added!")
    pause()


def action_view_notes():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Project Notes")
    notes = data.get("notes", [])
    if not notes:
        show_info("No notes yet.")
        pause()
        return

    for i, note in enumerate(notes, 1):
        ts = note.get("timestamp", "")[:19]
        console.print(f"  [dim]{i:3}.[/] [dim cyan]{ts}[/]  {note.get('text', '')}")
    pause()


def action_add_creds():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Add Credentials")
    username = ask("Username")
    password = ask("Password")
    source = ask("Source/where found", "manual")
    notes = ask("Notes (optional)", "")

    if not username or not password:
        show_error("Username and password are required.")
        pause()
        return

    cred = {
        "username": username, "password": password,
        "source": source, "notes": notes,
        "timestamp": datetime.now().isoformat(),
    }
    data.setdefault("credentials", []).append(cred)

    logger = ActivityLogger(data)
    logger.log("creds:add", details=f"Added credential: {username}")
    save_project(data)
    show_success(f"Credential added: [cyan]{username}[/]:[yellow]{password}[/]")
    pause()


def action_view_creds():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Credentials")
    creds = data.get("credentials", [])
    if not creds:
        show_info("No credentials yet.")
        pause()
        return

    table = Table(title="🔑 Credentials", header_style="bold red")
    table.add_column("#", justify="right", width=4)
    table.add_column("Username", style="cyan")
    table.add_column("Password", style="yellow")
    table.add_column("Source", style="white")
    table.add_column("Notes", style="dim")
    for i, c in enumerate(creds, 1):
        table.add_row(str(i), c["username"], c["password"], c.get("source", ""), c.get("notes", ""))
    console.print(table)
    pause()


def action_view_log():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Activity Log")
    log = data.get("activity_log", [])
    if not log:
        show_info("No activities recorded yet.")
        pause()
        return

    table = Table(title="📜 Full Activity Log", header_style="bold magenta")
    table.add_column("#", justify="right", width=4)
    table.add_column("Time", style="dim", width=20)
    table.add_column("Action", style="cyan", width=20)
    table.add_column("Details", style="white", max_width=40)
    table.add_column("Command", style="dim", max_width=30)
    for i, entry in enumerate(log, 1):
        table.add_row(
            str(i),
            entry.get("timestamp", "")[:19],
            entry.get("action", "—"),
            entry.get("details", "")[:40],
            entry.get("command", "")[:30],
        )
    console.print(table)
    pause()
