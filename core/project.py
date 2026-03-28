"""
HTB Tool — Project Management

Each project is a JSON file stored in ~/.htb_projects/.
Tracks target info, scan results, credentials, notes, and full activity log.
"""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.config import ensure_projects_dir, PROJECTS_DIR

console = Console()

# ── Active project state file ────────────────────────────────────────────────
ACTIVE_PROJECT_FILE = PROJECTS_DIR / ".active_project"


def _project_file(name: str) -> Path:
    """Return the JSON file path for a project name."""
    return ensure_projects_dir() / f"{name}.json"


def _blank_project(name: str) -> dict:
    """Create a blank project data structure."""
    return {
        "name": name,
        "created": datetime.now(timezone.utc).isoformat(),
        "updated": datetime.now(timezone.utc).isoformat(),
        "target": {
            "ip": None,
            "hostname": None,
            "os_guess": None,
            "managed_hosts": [],
        },
        "open_ports": [],
        "services": [],
        "scan_results": [],
        "credentials": [],
        "notes": [],
        "activity_log": [],
    }


# ── CRUD ─────────────────────────────────────────────────────────────────────

def create_project(name: str) -> dict:
    """Create a new project. Raises if already exists."""
    filepath = _project_file(name)
    if filepath.exists():
        raise FileExistsError(f"Project '{name}' already exists.")
    data = _blank_project(name)
    save_project(data)
    set_active_project(name)
    return data


def load_project(name: str) -> dict:
    """Load a project by name. Raises if not found."""
    filepath = _project_file(name)
    if not filepath.exists():
        raise FileNotFoundError(f"Project '{name}' not found.")
    with open(filepath, "r") as f:
        return json.load(f)


def save_project(data: dict) -> None:
    """Save project data to disk."""
    data["updated"] = datetime.now(timezone.utc).isoformat()
    filepath = _project_file(data["name"])
    ensure_projects_dir()
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


def delete_project(name: str) -> None:
    """Delete a project."""
    filepath = _project_file(name)
    if not filepath.exists():
        raise FileNotFoundError(f"Project '{name}' not found.")
    filepath.unlink()
    # Also remove output directory if it exists
    output_dir = get_project_output_dir(name)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    # Clear active project if this was it
    if get_active_project_name() == name:
        clear_active_project()


def list_projects() -> list[dict]:
    """List all projects with summary info."""
    projects_dir = ensure_projects_dir()
    projects = []
    for f in sorted(projects_dir.glob("*.json")):
        try:
            with open(f, "r") as fh:
                data = json.load(fh)
            projects.append({
                "name": data.get("name", f.stem),
                "target_ip": data.get("target", {}).get("ip", "—"),
                "hostname": data.get("target", {}).get("hostname", "—"),
                "created": data.get("created", "—"),
                "updated": data.get("updated", "—"),
                "activities": len(data.get("activity_log", [])),
                "ports": len(data.get("open_ports", [])),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return projects


# ── Active project ───────────────────────────────────────────────────────────

def set_active_project(name: str) -> None:
    """Set the active project by name."""
    ensure_projects_dir()
    ACTIVE_PROJECT_FILE.write_text(name)


def get_active_project_name() -> str | None:
    """Get the name of the active project, or None."""
    if ACTIVE_PROJECT_FILE.exists():
        name = ACTIVE_PROJECT_FILE.read_text().strip()
        if name and _project_file(name).exists():
            return name
    return None


def clear_active_project() -> None:
    """Clear the active project."""
    if ACTIVE_PROJECT_FILE.exists():
        ACTIVE_PROJECT_FILE.unlink()


def require_active_project() -> dict:
    """Load the active project or exit with an error message."""
    name = get_active_project_name()
    if not name:
        console.print(
            "[bold red]✗[/] No active project. "
            "Run [cyan]htb project create <name>[/] or [cyan]htb project use <name>[/] first."
        )
        raise SystemExit(1)
    return load_project(name)


# ── Output directory ─────────────────────────────────────────────────────────

def get_project_output_dir(name: str | None = None) -> Path:
    """Get/create the output directory for a project."""
    if name is None:
        name = get_active_project_name()
    if not name:
        raise RuntimeError("No active project.")
    output_dir = ensure_projects_dir() / name / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


# ── Display helpers ──────────────────────────────────────────────────────────

def display_project_status(data: dict) -> None:
    """Display a rich summary of the current project."""
    target = data.get("target", {})
    ports = data.get("open_ports", [])
    creds = data.get("credentials", [])
    notes = data.get("notes", [])
    log = data.get("activity_log", [])

    # Header
    console.print(Panel(
        f"[bold cyan]{data['name']}[/]",
        title="[bold white]🎯 Active Project[/]",
        border_style="cyan",
    ))

    # Target info
    target_table = Table(show_header=False, box=None, padding=(0, 2))
    target_table.add_column("Key", style="bold yellow")
    target_table.add_column("Value", style="white")
    target_table.add_row("IP", target.get("ip") or "[dim]not set[/]")
    target_table.add_row("Hostname", target.get("hostname") or "[dim]not set[/]")
    target_table.add_row("OS Guess", target.get("os_guess") or "[dim]unknown[/]")
    console.print(Panel(target_table, title="[bold]Target[/]", border_style="yellow"))

    # Stats
    stats = Table(show_header=True, header_style="bold magenta")
    stats.add_column("Metric", style="cyan")
    stats.add_column("Count", justify="right", style="bold white")
    stats.add_row("Open Ports", str(len(ports)))
    stats.add_row("Credentials", str(len(creds)))
    stats.add_row("Notes", str(len(notes)))
    stats.add_row("Activities", str(len(log)))
    console.print(stats)

    # Open ports
    if ports:
        port_table = Table(title="Open Ports", header_style="bold green")
        port_table.add_column("Port", style="cyan", justify="right")
        port_table.add_column("State", style="green")
        port_table.add_column("Service", style="yellow")
        port_table.add_column("Version", style="white")
        for p in ports:
            port_table.add_row(
                str(p.get("port", "?")),
                p.get("state", "open"),
                p.get("service", "?"),
                p.get("version", ""),
            )
        console.print(port_table)
