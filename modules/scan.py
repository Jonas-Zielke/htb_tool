"""
HTB Tool — Nmap Scan Module

Commands:
  htb scan quick          Quick top-ports scan (-sC -sV)
  htb scan full           Full port scan (-p-)
  htb scan udp            UDP top-100 scan
  htb scan vuln           Vulnerability scripts scan
  htb scan stealth        Stealth SYN scan
  htb scan custom -- ...  Custom nmap arguments
"""
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from core.config import NMAP_DEFAULT_TIMING, NMAP_TOP_PORTS, NMAP_UDP_TOP_PORTS
from core.project import (
    require_active_project, save_project, get_project_output_dir
)
from core.logger import ActivityLogger

console = Console()


# ── Nmap runner ──────────────────────────────────────────────────────────────

def _run_nmap(args: list[str], data: dict, scan_label: str, sudo: bool = False) -> str:
    """Run nmap with given args, save output, parse results, update project."""
    target_ip = data["target"].get("ip")
    if not target_ip:
        console.print("[bold red]✗[/] No target IP set. Run [cyan]htb target set <ip>[/] first.")
        raise SystemExit(1)

    logger = ActivityLogger(data)
    output_dir = get_project_output_dir(data["name"])

    # Build output prefix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_prefix = output_dir / f"nmap_{scan_label}_{timestamp}"

    # Full command
    cmd = []
    if sudo:
        cmd.append("sudo")
    cmd.extend(["nmap"] + args + ["-oA", str(output_prefix), target_ip])

    cmd_str = " ".join(cmd)
    console.print(f"\n[bold cyan]⚡ Running:[/] [dim]{cmd_str}[/]\n")

    # Run with live output
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]Scanning ({scan_label})...", total=None)

        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=1800,  # 30 min timeout
        )

        progress.update(task, completed=True)

    # Display output
    if proc.stdout:
        console.print(Panel(
            proc.stdout,
            title=f"[bold]Nmap {scan_label} Results[/]",
            border_style="green",
            expand=True,
        ))

    if proc.returncode != 0 and proc.stderr:
        console.print(f"[bold yellow]⚠ stderr:[/] {proc.stderr}")

    # Parse XML results
    xml_file = Path(f"{output_prefix}.xml")
    parsed_ports = []
    if xml_file.exists():
        parsed_ports = _parse_nmap_xml(xml_file)
        if parsed_ports:
            _update_project_ports(data, parsed_ports)
            _display_port_table(parsed_ports, scan_label)

    # Log activity
    logger.log_scan(
        scan_type=f"nmap-{scan_label}",
        command=cmd_str,
        output_file=str(output_prefix),
        summary=f"Found {len(parsed_ports)} open ports" if parsed_ports else "Scan completed",
    )

    # Save scan result reference
    data.setdefault("scan_results", []).append({
        "type": f"nmap-{scan_label}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output_file": str(output_prefix),
        "command": cmd_str,
        "ports_found": len(parsed_ports),
    })
    save_project(data)

    return proc.stdout


def _parse_nmap_xml(xml_path: Path) -> list[dict]:
    """Parse nmap XML output and extract port/service info."""
    ports = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        for host in root.findall(".//host"):
            for port_elem in host.findall(".//port"):
                state_elem = port_elem.find("state")
                service_elem = port_elem.find("service")

                if state_elem is not None and state_elem.get("state") == "open":
                    port_info = {
                        "port": int(port_elem.get("portid", 0)),
                        "protocol": port_elem.get("protocol", "tcp"),
                        "state": "open",
                        "service": service_elem.get("name", "unknown") if service_elem is not None else "unknown",
                        "version": "",
                    }
                    if service_elem is not None:
                        version_parts = []
                        for attr in ["product", "version", "extrainfo"]:
                            val = service_elem.get(attr, "")
                            if val:
                                version_parts.append(val)
                        port_info["version"] = " ".join(version_parts)

                    ports.append(port_info)
    except ET.ParseError:
        console.print("[bold yellow]⚠[/] Could not parse nmap XML output.")
    return ports


def _update_project_ports(data: dict, new_ports: list[dict]) -> None:
    """Merge newly discovered ports into the project."""
    existing = {p["port"]: p for p in data.get("open_ports", [])}
    for p in new_ports:
        existing[p["port"]] = p  # Update or add
    data["open_ports"] = sorted(existing.values(), key=lambda x: x["port"])


def _display_port_table(ports: list[dict], scan_label: str) -> None:
    """Display a formatted table of discovered ports."""
    table = Table(
        title=f"🔍 Discovered Ports ({scan_label})",
        header_style="bold green",
        border_style="green",
    )
    table.add_column("Port", style="cyan", justify="right")
    table.add_column("Protocol", style="dim")
    table.add_column("State", style="bold green")
    table.add_column("Service", style="yellow")
    table.add_column("Version", style="white")
    for p in ports:
        table.add_row(
            str(p["port"]),
            p.get("protocol", "tcp"),
            p["state"],
            p["service"],
            p.get("version", ""),
        )
    console.print(table)


# ── Click commands ───────────────────────────────────────────────────────────

@click.group("scan")
def scan_group():
    """🔍 Run Nmap scans against the target."""
    pass


@scan_group.command("quick")
@click.option("--timing", "-T", default=NMAP_DEFAULT_TIMING, help="Nmap timing template")
@click.option("--top-ports", default=NMAP_TOP_PORTS, help="Number of top ports", type=int)
def scan_quick(timing, top_ports):
    """Quick scan — top ports with service/script detection."""
    data = require_active_project()
    args = ["-sC", "-sV", f"-{timing}", "--top-ports", str(top_ports)]
    _run_nmap(args, data, "quick")


@scan_group.command("full")
@click.option("--timing", "-T", default=NMAP_DEFAULT_TIMING, help="Nmap timing template")
def scan_full(timing):
    """Full port scan — all 65535 ports with service detection."""
    data = require_active_project()
    args = ["-sC", "-sV", "-p-", f"-{timing}"]
    _run_nmap(args, data, "full")


@scan_group.command("udp")
@click.option("--top-ports", default=NMAP_UDP_TOP_PORTS, help="Number of top UDP ports", type=int)
def scan_udp(top_ports):
    """UDP scan — top UDP ports (requires sudo)."""
    data = require_active_project()
    args = ["-sU", "--top-ports", str(top_ports), "-T4"]
    _run_nmap(args, data, "udp", sudo=True)


@scan_group.command("vuln")
@click.option("--timing", "-T", default=NMAP_DEFAULT_TIMING, help="Nmap timing template")
def scan_vuln(timing):
    """Vulnerability scan — run vuln NSE scripts."""
    data = require_active_project()
    args = ["--script", "vuln", f"-{timing}"]
    _run_nmap(args, data, "vuln")


@scan_group.command("stealth")
def scan_stealth():
    """Stealth SYN scan — low and slow (requires sudo)."""
    data = require_active_project()
    args = ["-sS", "-T2", "-f", "--data-length", "50", "-p-"]
    _run_nmap(args, data, "stealth", sudo=True)


@scan_group.command("scripts")
@click.argument("scripts")
@click.option("--ports", "-p", default=None, help="Port specification")
def scan_scripts(scripts, ports):
    """Run specific NSE scripts against target."""
    data = require_active_project()
    args = ["--script", scripts]
    if ports:
        args.extend(["-p", ports])
    _run_nmap(args, data, f"scripts-{scripts.replace(',', '_')}")


@scan_group.command("custom")
@click.argument("nmap_args", nargs=-1, required=True)
def scan_custom(nmap_args):
    """Run nmap with custom arguments. Pass args after --."""
    data = require_active_project()
    _run_nmap(list(nmap_args), data, "custom")
