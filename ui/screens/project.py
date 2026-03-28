"""
HTB Toolbox — Project Management Screens
"""
from ui.helpers import (
    console, clear, pause, ask, confirm, show_error, show_success,
    menu_header, render_menu, choose, get_project_or_warn,
)
from core.project import (
    create_project, load_project, save_project, delete_project,
    list_projects, set_active_project, get_active_project_name,
    display_project_status,
)
from rich.table import Table


def menu_project():
    while True:
        menu_header()
        items = [
            ("1", "✨", "Create New Project"),
            ("2", "🔄", "Switch Project"),
            ("3", "📋", "List All Projects"),
            ("4", "📊", "Project Dashboard"),
            ("5", "🗑️ ", "Delete Project"),
        ]
        render_menu("Project Management", items)
        c = choose(items)
        if c == "0": return
        elif c == "1": action_project_create()
        elif c == "2": action_project_switch()
        elif c == "3": action_project_list()
        elif c == "4": action_project_dashboard()
        elif c == "5": action_project_delete()


def action_project_create():
    menu_header("Create New Project")
    name = ask("Project name (e.g. box-name)")
    if not name:
        return
    try:
        create_project(name)
        show_success(f"Project [cyan]{name}[/] created and set as active!")
    except FileExistsError:
        show_error(f"Project '{name}' already exists.")
    pause()


def action_project_switch():
    menu_header("Switch Project")
    projects = list_projects()
    if not projects:
        show_error("No projects exist yet. Create one first.")
        pause()
        return

    active = get_active_project_name()
    table = Table(header_style="bold cyan", border_style="dim")
    table.add_column("#", style="bold", justify="right", width=4)
    table.add_column("Name", style="bold white")
    table.add_column("Target", style="cyan")
    table.add_column("Ports", justify="right")
    table.add_column("Activities", justify="right")
    for i, p in enumerate(projects, 1):
        marker = " [green]◆[/]" if p["name"] == active else ""
        table.add_row(
            str(i), p["name"] + marker, str(p["target_ip"]),
            str(p["ports"]), str(p["activities"]),
        )
    console.print(table)

    idx = ask(f"Select project (1-{len(projects)})")
    try:
        idx = int(idx) - 1
        if 0 <= idx < len(projects):
            name = projects[idx]["name"]
            set_active_project(name)
            show_success(f"Switched to [cyan]{name}[/]")
        else:
            show_error("Invalid selection.")
    except (ValueError, TypeError):
        show_error("Invalid input.")
    pause()


def action_project_list():
    menu_header("All Projects")
    projects = list_projects()
    if not projects:
        show_error("No projects yet.")
        pause()
        return

    active = get_active_project_name()
    table = Table(title="📁 HTB Projects", header_style="bold cyan", border_style="green")
    table.add_column("", width=2)
    table.add_column("Name", style="bold white")
    table.add_column("Target IP", style="cyan")
    table.add_column("Hostname", style="yellow")
    table.add_column("Ports", justify="right")
    table.add_column("Activities", justify="right")
    table.add_column("Updated", style="dim")
    for p in projects:
        marker = "[green]→[/]" if p["name"] == active else " "
        table.add_row(
            marker, p["name"], str(p["target_ip"]), str(p["hostname"]),
            str(p["ports"]), str(p["activities"]), str(p["updated"])[:19],
        )
    console.print(table)
    pause()


def action_project_dashboard():
    data = get_project_or_warn()
    if not data:
        return
    menu_header("Project Dashboard")
    display_project_status(data)
    pause()


def action_project_delete():
    menu_header("Delete Project")
    projects = list_projects()
    if not projects:
        show_error("No projects to delete.")
        pause()
        return

    for i, p in enumerate(projects, 1):
        console.print(f"    [cyan]{i}[/]. {p['name']}")

    idx = ask(f"Select project to delete (1-{len(projects)})")
    try:
        idx = int(idx) - 1
        if 0 <= idx < len(projects):
            name = projects[idx]["name"]
            if confirm(f"Delete project '{name}' and all its data?"):
                delete_project(name)
                show_success(f"Project '{name}' deleted.")
            else:
                show_info("Cancelled.")
        else:
            show_error("Invalid selection.")
    except (ValueError, TypeError):
        show_error("Invalid input.")
    pause()
