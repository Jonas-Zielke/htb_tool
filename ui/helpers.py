"""
HTB Toolbox — UI Helper Functions
Shared display utilities, prompts, and menu renderer.
"""
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich import box

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.project import (
    load_project, get_active_project_name,
)

console = Console()

BANNER = r"""[bold green]
  ╦ ╦╔╦╗╔╗    ╔╦╗╔═╗╔═╗╦  ╔╗ ╔═╗═╗ ╦
  ╠═╣ ║ ╠╩╗    ║ ║ ║║ ║║  ╠╩╗║ ║╔╩╦╝
  ╩ ╩ ╩ ╚═╝    ╩ ╚═╝╚═╝╩═╝╚═╝╚═╝╩ ╚═[/]
[dim]         Hack The Box — Toolbox v2.0[/]"""


def clear():
    os.system("clear" if os.name == "posix" else "cls")


def pause(msg="[dim]\n  Press Enter to continue...[/]"):
    console.print(msg)
    input()


def ask(prompt_text, default=None):
    return Prompt.ask(f"  [bold cyan]{prompt_text}[/]", default=default, console=console)


def ask_int(prompt_text, default=None):
    while True:
        val = ask(prompt_text, str(default) if default is not None else None)
        try:
            return int(val)
        except ValueError:
            console.print("  [red]Please enter a number.[/]")


def confirm(prompt_text):
    return Confirm.ask(f"  [bold yellow]{prompt_text}[/]", console=console)


def show_error(msg):
    console.print(f"\n  [bold red]✗[/] {msg}")


def show_success(msg):
    console.print(f"\n  [bold green]✓[/] {msg}")


def show_info(msg):
    console.print(f"\n  [bold cyan]ℹ[/] {msg}")


def get_project_or_warn():
    """Get active project data, or show warning and return None."""
    name = get_active_project_name()
    if not name:
        show_error("No active project. Go to [cyan]Project Management[/] first.")
        pause()
        return None
    try:
        return load_project(name)
    except FileNotFoundError:
        show_error(f"Project '{name}' not found.")
        pause()
        return None


def get_target_or_warn(data):
    """Get target IP or show warning. Returns None on failure."""
    ip = data["target"].get("ip")
    if not ip:
        show_error("No target IP set. Go to [cyan]Target & DNS Setup[/] first.")
        pause()
        return None
    return ip


def status_bar():
    """Render project/target status bar at top of screen."""
    name = get_active_project_name()
    if not name:
        console.print(Panel(
            "[dim italic]  No active project — select or create one in Project Management[/]",
            border_style="dim", box=box.ROUNDED,
        ))
        return

    try:
        data = load_project(name)
    except FileNotFoundError:
        return

    target = data.get("target", {})
    ports = data.get("open_ports", [])
    creds = data.get("credentials", [])
    log = data.get("activity_log", [])

    ip = target.get("ip", "—")
    hostname = target.get("hostname")
    os_guess = target.get("os_guess", "")

    target_str = f"[cyan]{ip}[/]"
    if hostname:
        target_str += f" [dim]({hostname})[/]"
    if os_guess:
        target_str += f" [dim][{os_guess}][/]"

    port_str = ", ".join(str(p["port"]) for p in ports[:8])
    if len(ports) > 8:
        port_str += f" [dim]+{len(ports) - 8} more[/]"
    if not port_str:
        port_str = "[dim]none yet[/]"

    status = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    status.add_column(ratio=1)
    status.add_column(ratio=1)
    status.add_column(ratio=1)
    status.add_row(
        f"[bold]📁[/] [green]{name}[/]",
        f"[bold]🎯[/] {target_str}",
        f"[bold]🔌[/] {port_str}",
    )
    status.add_row(
        f"[bold]📊[/] [yellow]{len(log)}[/] activities",
        f"[bold]🔑[/] [yellow]{len(creds)}[/] creds",
        f"[bold]📝[/] [yellow]{len(data.get('notes', []))}[/] notes",
    )

    console.print(Panel(status, border_style="cyan", box=box.ROUNDED))


def render_menu(title, items, back_label="Back"):
    """Render a styled menu panel.
    items: list of (key, emoji, label) or (key, emoji, label, badge)
    """
    lines = []
    for item in items:
        key, icon, label = item[0], item[1], item[2]
        badge = item[3] if len(item) > 3 else ""
        badge_str = f"  [dim italic]{badge}[/]" if badge else ""
        lines.append(f"    [bold cyan]\\[{key}][/]  {icon}  {label}{badge_str}")
    lines.append("")
    lines.append(f"    [bold cyan]\\[0][/]  ←  {back_label}")

    content = "\n".join(lines)
    console.print(Panel(
        content, title=f"[bold white] {title} [/]",
        border_style="green", padding=(1, 2), box=box.HEAVY,
    ))


def choose(items, back_label="Back"):
    """Get user choice from rendered menu items. Returns lowercase key string."""
    valid_keys = [item[0].lower() for item in items] + ["0"]
    while True:
        choice = console.input("\n  [bold green]❯[/] ").strip().lower()
        if choice in valid_keys:
            return choice
        console.print(f"  [dim red]Invalid choice. Try again.[/]")


def menu_header(title=None):
    """Clear screen and show banner + status bar. Optionally a section title."""
    clear()
    console.print(BANNER)
    console.print()
    status_bar()
    if title:
        console.print(f"\n  [bold underline]{title}[/]\n")
