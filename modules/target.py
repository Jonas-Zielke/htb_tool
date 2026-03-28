"""
HTB Tool — Target Management Module

Commands:
  htb target set <ip> [--hostname]   Set target IP and hostname
  htb target show                    Display current target info
  htb target hosts add <hostname>    Add /etc/hosts entry
  htb target hosts remove <hostname> Remove /etc/hosts entry
  htb target hosts list              List managed hosts entries
"""
import subprocess

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.project import require_active_project, save_project
from core.logger import ActivityLogger

console = Console()

# ── Hosts file management ────────────────────────────────────────────────────

HOSTS_FILE = "/etc/hosts"
HOSTS_MARKER = "# HTB-TOOL-MANAGED"


def _read_hosts_file() -> list[str]:
    """Read /etc/hosts lines."""
    with open(HOSTS_FILE, "r") as f:
        return f.readlines()


def _write_hosts_file(lines: list[str]) -> None:
    """Write to /etc/hosts via sudo tee."""
    content = "".join(lines)
    proc = subprocess.run(
        ["sudo", "tee", HOSTS_FILE],
        input=content, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise PermissionError(f"Failed to write to {HOSTS_FILE}: {proc.stderr}")


# ── Click commands ───────────────────────────────────────────────────────────

@click.group("target")
def target_group():
    """🎯 Manage target IP, hostname, and DNS entries."""
    pass


@target_group.command("set")
@click.argument("ip")
@click.option("--hostname", "-n", default=None, help="Hostname for the target (e.g. box.htb)")
@click.option("--os", "os_guess", default=None, help="OS guess (linux/windows)")
def target_set(ip, hostname, os_guess):
    """Set the target IP address and optional hostname."""
    data = require_active_project()
    logger = ActivityLogger(data)

    data["target"]["ip"] = ip
    if hostname:
        data["target"]["hostname"] = hostname
    if os_guess:
        data["target"]["os_guess"] = os_guess

    save_project(data)
    logger.log_target(f"Set target to {ip}" + (f" ({hostname})" if hostname else ""))
    save_project(data)

    console.print(f"[bold green]✓[/] Target set to [cyan]{ip}[/]", end="")
    if hostname:
        console.print(f" ([yellow]{hostname}[/])", end="")
    console.print()

    # Auto-add to /etc/hosts if hostname provided
    if hostname:
        console.print(f"[dim]  → Adding {hostname} to /etc/hosts...[/]")
        try:
            _add_hosts_entry(ip, hostname, data)
            save_project(data)
            console.print(f"[bold green]  ✓[/] Added [yellow]{hostname}[/] → [cyan]{ip}[/] to /etc/hosts")
        except PermissionError as e:
            console.print(f"[bold red]  ✗[/] {e}")
            console.print("[dim]    Run with sudo or add manually.[/]")


@target_group.command("show")
def target_show():
    """Show current target information."""
    data = require_active_project()
    target = data.get("target", {})

    panel_lines = []
    panel_lines.append(f"[bold yellow]IP:[/]       {target.get('ip') or '[dim]not set[/]'}")
    panel_lines.append(f"[bold yellow]Hostname:[/] {target.get('hostname') or '[dim]not set[/]'}")
    panel_lines.append(f"[bold yellow]OS:[/]       {target.get('os_guess') or '[dim]unknown[/]'}")

    managed = target.get("managed_hosts", [])
    if managed:
        panel_lines.append("")
        panel_lines.append("[bold yellow]Managed /etc/hosts entries:[/]")
        for entry in managed:
            panel_lines.append(f"  [cyan]{entry['ip']}[/]  →  [white]{entry['hostname']}[/]")

    console.print(Panel(
        "\n".join(panel_lines),
        title=f"[bold]🎯 Target — {data['name']}[/]",
        border_style="cyan",
    ))

    # Show open ports if any
    ports = data.get("open_ports", [])
    if ports:
        table = Table(title="Open Ports", header_style="bold green")
        table.add_column("Port", style="cyan", justify="right")
        table.add_column("State", style="green")
        table.add_column("Service", style="yellow")
        table.add_column("Version", style="white")
        for p in ports:
            table.add_row(
                str(p.get("port", "?")),
                p.get("state", "open"),
                p.get("service", "?"),
                p.get("version", ""),
            )
        console.print(table)


# ── Hosts subgroup ───────────────────────────────────────────────────────────

@target_group.group("hosts")
def hosts_group():
    """🌐 Manage /etc/hosts entries for the target."""
    pass


def _add_hosts_entry(ip: str, hostname: str, data: dict) -> None:
    """Add an entry to /etc/hosts."""
    lines = _read_hosts_file()

    # Check if already exists
    for line in lines:
        if HOSTS_MARKER in line and hostname in line:
            return  # Already exists

    # Add new entry
    entry = f"{ip}\t{hostname}\t{HOSTS_MARKER}\n"
    lines.append(entry)
    _write_hosts_file(lines)

    # Track in project
    managed = data["target"].setdefault("managed_hosts", [])
    managed.append({"ip": ip, "hostname": hostname})


@hosts_group.command("add")
@click.argument("hostname")
@click.option("--ip", default=None, help="Override IP (defaults to target IP)")
def hosts_add(hostname, ip):
    """Add a hostname to /etc/hosts pointing to target IP."""
    data = require_active_project()
    logger = ActivityLogger(data)

    target_ip = ip or data["target"].get("ip")
    if not target_ip:
        console.print("[bold red]✗[/] No target IP set. Run [cyan]htb target set <ip>[/] first.")
        raise SystemExit(1)

    try:
        _add_hosts_entry(target_ip, hostname, data)
        logger.log_target(f"Added /etc/hosts entry: {target_ip} → {hostname}")
        save_project(data)
        console.print(f"[bold green]✓[/] Added [yellow]{hostname}[/] → [cyan]{target_ip}[/] to /etc/hosts")
    except PermissionError as e:
        console.print(f"[bold red]✗[/] {e}")


@hosts_group.command("remove")
@click.argument("hostname")
def hosts_remove(hostname):
    """Remove a hostname from /etc/hosts (HTB-managed entries only)."""
    data = require_active_project()
    logger = ActivityLogger(data)

    lines = _read_hosts_file()
    new_lines = []
    removed = False
    for line in lines:
        if HOSTS_MARKER in line and hostname in line:
            removed = True
            continue
        new_lines.append(line)

    if removed:
        _write_hosts_file(new_lines)
        # Remove from project tracking
        managed = data["target"].get("managed_hosts", [])
        data["target"]["managed_hosts"] = [
            m for m in managed if m["hostname"] != hostname
        ]
        logger.log_target(f"Removed /etc/hosts entry: {hostname}")
        save_project(data)
        console.print(f"[bold green]✓[/] Removed [yellow]{hostname}[/] from /etc/hosts")
    else:
        console.print(f"[bold yellow]![/] No HTB-managed entry found for [yellow]{hostname}[/]")


@hosts_group.command("list")
def hosts_list():
    """List all HTB-managed /etc/hosts entries."""
    data = require_active_project()
    managed = data["target"].get("managed_hosts", [])

    if not managed:
        console.print("[dim]No managed /etc/hosts entries.[/]")
        return

    table = Table(title="/etc/hosts — HTB Managed", header_style="bold cyan")
    table.add_column("IP", style="cyan")
    table.add_column("Hostname", style="yellow")
    for m in managed:
        table.add_row(m["ip"], m["hostname"])
    console.print(table)
