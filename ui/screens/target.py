"""
HTB Toolbox — Target & DNS Management Screens
"""
from ui.helpers import (
    console, pause, ask, confirm, show_error, show_success, show_info,
    menu_header, render_menu, choose, get_project_or_warn, get_target_or_warn,
)
from core.project import save_project, load_project, get_active_project_name
from core.logger import ActivityLogger
from modules.target import _add_hosts_entry, _read_hosts_file, _write_hosts_file, HOSTS_MARKER
from rich.panel import Panel
from rich.table import Table


def menu_target():
    while True:
        menu_header()
        items = [
            ("1", "🎯", "Set Target IP & Hostname"),
            ("2", "➕", "Add DNS Entry (/etc/hosts)"),
            ("3", "➖", "Remove DNS Entry"),
            ("4", "📋", "List DNS Entries"),
            ("5", "👁️ ", "View Target Info"),
            ("6", "📡", "Ping Target"),
        ]
        render_menu("Target & DNS Setup", items)
        c = choose(items)
        if c == "0": return
        elif c == "1": action_set_target()
        elif c == "2": action_add_dns()
        elif c == "3": action_remove_dns()
        elif c == "4": action_list_dns()
        elif c == "5": action_view_target()
        elif c == "6": action_ping_target()


def action_set_target():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Set Target")
    ip = ask("Target IP address", data["target"].get("ip"))
    hostname = ask("Hostname (e.g. box.htb)", data["target"].get("hostname") or "")
    os_guess = ask("OS guess (linux/windows)", data["target"].get("os_guess") or "")

    if not ip:
        show_error("IP address is required.")
        pause()
        return

    data["target"]["ip"] = ip.strip()
    if hostname:
        data["target"]["hostname"] = hostname.strip()
    if os_guess:
        data["target"]["os_guess"] = os_guess.strip()

    logger = ActivityLogger(data)
    logger.log_target(f"Set target to {ip}" + (f" ({hostname})" if hostname else ""))
    save_project(data)

    show_success(f"Target set to [cyan]{ip}[/]" + (f" ([yellow]{hostname}[/])" if hostname else ""))

    if hostname and confirm("Add hostname to /etc/hosts?"):
        try:
            _add_hosts_entry(ip.strip(), hostname.strip(), data)
            save_project(data)
            show_success(f"Added [yellow]{hostname}[/] → [cyan]{ip}[/] to /etc/hosts")
        except PermissionError as e:
            show_error(f"Permission denied: {e}")
            show_info("Try running the tool with sudo.")
    pause()


def action_add_dns():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Add DNS Entry")
    hostname = ask("Hostname to add (e.g. admin.box.htb)")
    custom_ip = ask("IP address", ip)

    if not hostname:
        show_error("Hostname is required.")
        pause()
        return

    try:
        _add_hosts_entry(custom_ip, hostname.strip(), data)
        logger = ActivityLogger(data)
        logger.log_target(f"Added DNS: {custom_ip} → {hostname}")
        save_project(data)
        show_success(f"Added [yellow]{hostname}[/] → [cyan]{custom_ip}[/] to /etc/hosts")
    except PermissionError as e:
        show_error(f"Permission denied: {e}")
    pause()


def action_remove_dns():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Remove DNS Entry")
    managed = data["target"].get("managed_hosts", [])
    if not managed:
        show_info("No managed DNS entries to remove.")
        pause()
        return

    for i, m in enumerate(managed, 1):
        console.print(f"    [cyan]{i}[/]. {m['ip']}  →  {m['hostname']}")

    idx = ask(f"Select entry to remove (1-{len(managed)})")
    try:
        idx = int(idx) - 1
        if 0 <= idx < len(managed):
            entry = managed[idx]
            hostname = entry["hostname"]

            lines = _read_hosts_file()
            new_lines = [l for l in lines if not (HOSTS_MARKER in l and hostname in l)]
            _write_hosts_file(new_lines)

            data["target"]["managed_hosts"] = [m for m in managed if m["hostname"] != hostname]
            logger = ActivityLogger(data)
            logger.log_target(f"Removed DNS: {hostname}")
            save_project(data)
            show_success(f"Removed [yellow]{hostname}[/] from /etc/hosts")
        else:
            show_error("Invalid selection.")
    except (ValueError, PermissionError) as e:
        show_error(str(e))
    pause()


def action_list_dns():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Managed DNS Entries")
    managed = data["target"].get("managed_hosts", [])
    if not managed:
        show_info("No managed /etc/hosts entries.")
    else:
        table = Table(header_style="bold cyan", border_style="green")
        table.add_column("IP", style="cyan")
        table.add_column("Hostname", style="yellow")
        for m in managed:
            table.add_row(m["ip"], m["hostname"])
        console.print(table)
    pause()


def action_view_target():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Target Information")
    target = data.get("target", {})
    lines = []
    lines.append(f"  [bold yellow]IP:[/]         {target.get('ip') or '[dim]not set[/]'}")
    lines.append(f"  [bold yellow]Hostname:[/]   {target.get('hostname') or '[dim]not set[/]'}")
    lines.append(f"  [bold yellow]OS:[/]         {target.get('os_guess') or '[dim]unknown[/]'}")

    managed = target.get("managed_hosts", [])
    if managed:
        lines.append("")
        lines.append("  [bold yellow]DNS Entries:[/]")
        for m in managed:
            lines.append(f"    [cyan]{m['ip']}[/]  →  [white]{m['hostname']}[/]")

    console.print(Panel("\n".join(lines), title="[bold]🎯 Target[/]", border_style="cyan"))

    ports = data.get("open_ports", [])
    if ports:
        table = Table(title="Open Ports", header_style="bold green")
        table.add_column("Port", style="cyan", justify="right")
        table.add_column("Service", style="yellow")
        table.add_column("Version", style="white")
        for p in ports:
            table.add_row(str(p["port"]), p.get("service", "?"), p.get("version", ""))
        console.print(table)
    pause()


def action_ping_target():
    import subprocess
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Ping Target")
    console.print(f"  [dim]Pinging {ip}...[/]\n")
    proc = subprocess.run(["ping", "-c", "4", ip], capture_output=False, text=True)
    pause()
