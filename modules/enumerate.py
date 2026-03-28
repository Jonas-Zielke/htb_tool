"""
HTB Tool — Service Enumeration Module

Commands:
  htb enum web       Web enumeration (whatweb + gobuster)
  htb enum dirs      Directory brute-force
  htb enum smb       SMB enumeration
  htb enum dns       DNS enumeration
  htb enum vhosts    Virtual host discovery
  htb enum all       Run all enumeration
"""
import subprocess
from datetime import datetime, timezone

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from core.config import (
    DIR_WORDLIST, DIR_WORDLIST_BIG, DNS_WORDLIST, VHOST_WORDLIST,
    WEB_EXTENSIONS, DEFAULT_THREADS,
)
from core.project import (
    require_active_project, save_project, get_project_output_dir,
)
from core.logger import ActivityLogger

console = Console()


def _run_tool(cmd: list[str], data: dict, label: str, timeout: int = 600) -> str:
    """Run an external tool, display output, and log the activity."""
    logger = ActivityLogger(data)
    output_dir = get_project_output_dir(data["name"])

    from ui.helpers import check_tool_installed
    if not check_tool_installed(cmd[0]):
        return ""

    cmd_str = " ".join(cmd)
    console.print(f"\n[bold cyan]⚡ Running:[/] [dim]{cmd_str}[/]\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{label}_{timestamp}.txt"

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"[cyan]{label}...", total=None)
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            console.print(f"[bold yellow]⚠[/] {label} timed out after {timeout}s")
            progress.update(task, completed=True)
            return ""
        progress.update(task, completed=True)

    output = proc.stdout or ""
    if output:
        # Save to file
        with open(output_file, "w") as f:
            f.write(output)

        console.print(Panel(
            output[:5000] + ("\n[dim]... (truncated)[/]" if len(output) > 5000 else ""),
            title=f"[bold]{label} Results[/]",
            border_style="green",
            expand=True,
        ))

    if proc.stderr:
        stderr_clean = proc.stderr.strip()
        if stderr_clean and "Progress:" not in stderr_clean:
            console.print(f"[dim yellow]{stderr_clean[:500]}[/]")

    logger.log_enum(
        enum_type=label,
        command=cmd_str,
        output_file=str(output_file),
        summary=f"Completed {label}" + (f" — {len(output.splitlines())} lines" if output else ""),
    )
    save_project(data)
    return output


# ── Click commands ───────────────────────────────────────────────────────────

@click.group("enum")
def enum_group():
    """📡 Enumerate services on the target."""
    pass


@enum_group.command("web")
@click.option("--port", "-p", default=80, help="Port to enumerate", type=int)
def enum_web(port):
    """Web enumeration — whatweb + gobuster directory scan."""
    data = require_active_project()
    target = data["target"].get("ip")
    hostname = data["target"].get("hostname")
    base_url = f"http://{hostname or target}:{port}"

    if not target:
        console.print("[bold red]✗[/] No target set.")
        raise SystemExit(1)

    console.print(f"[bold]🌐 Web Enumeration on {base_url}[/]\n")

    # 1. WhatWeb
    _run_tool(["whatweb", "-a", "3", base_url], data, "whatweb")

    # 2. Gobuster dir
    wordlist = str(DIR_WORDLIST) if DIR_WORDLIST.exists() else "/usr/share/wordlists/dirb/common.txt"
    _run_tool(
        ["gobuster", "dir",
         "-u", base_url,
         "-w", wordlist,
         "-x", WEB_EXTENSIONS,
         "-t", str(DEFAULT_THREADS),
         "--no-error",
         "-q"],
        data, "gobuster-dir",
    )


@enum_group.command("dirs")
@click.option("--url", "-u", default=None, help="Target URL (auto-detected from target)")
@click.option("--wordlist", "-w", default=None, help="Wordlist path")
@click.option("--extensions", "-x", default=WEB_EXTENSIONS, help="File extensions to check")
@click.option("--tool", "-t", type=click.Choice(["gobuster", "ffuf"]), default="gobuster")
@click.option("--threads", default=DEFAULT_THREADS, type=int)
def enum_dirs(url, wordlist, extensions, tool, threads):
    """Directory brute-force with gobuster or ffuf."""
    data = require_active_project()
    target = data["target"].get("ip")
    hostname = data["target"].get("hostname")

    if not url:
        url = f"http://{hostname or target}"
    if not wordlist:
        wordlist = str(DIR_WORDLIST) if DIR_WORDLIST.exists() else "/usr/share/wordlists/dirb/common.txt"

    if tool == "gobuster":
        _run_tool(
            ["gobuster", "dir",
             "-u", url,
             "-w", wordlist,
             "-x", extensions,
             "-t", str(threads),
             "--no-error",
             "-q"],
            data, "gobuster-dirs",
        )
    else:
        _run_tool(
            ["ffuf",
             "-u", f"{url}/FUZZ",
             "-w", wordlist,
             "-e", "," + extensions.replace(",", ",."),
             "-t", str(threads),
             "-mc", "200,204,301,302,307,401,403",
             "-c"],
            data, "ffuf-dirs",
        )


@enum_group.command("smb")
def enum_smb():
    """SMB enumeration — enum4linux + smbclient."""
    data = require_active_project()
    target = data["target"].get("ip")
    if not target:
        console.print("[bold red]✗[/] No target set.")
        raise SystemExit(1)

    console.print(f"[bold]📁 SMB Enumeration on {target}[/]\n")

    # enum4linux
    _run_tool(["enum4linux", "-a", target], data, "enum4linux", timeout=300)

    # smbclient list shares
    _run_tool(
        ["smbclient", "-L", f"//{target}", "-N"],
        data, "smbclient-list",
        timeout=30,
    )


@enum_group.command("dns")
@click.option("--domain", "-d", default=None, help="Domain to enumerate")
def enum_dns(domain):
    """DNS enumeration — zone transfer + subdomain brute-force."""
    data = require_active_project()
    target = data["target"].get("ip")
    hostname = data["target"].get("hostname")

    if not domain:
        domain = hostname
    if not domain:
        console.print("[bold red]✗[/] No hostname/domain set. Use --domain or set target hostname.")
        raise SystemExit(1)

    console.print(f"[bold]🔤 DNS Enumeration for {domain}[/]\n")

    # Zone transfer attempt
    _run_tool(["dig", "axfr", domain, f"@{target}"], data, "dns-zonetransfer", timeout=30)

    # Subdomain brute-force with gobuster
    wordlist = str(DNS_WORDLIST) if DNS_WORDLIST.exists() else "/usr/share/wordlists/dirb/common.txt"
    _run_tool(
        ["gobuster", "dns",
         "-d", domain,
         "-w", wordlist,
         "-t", str(DEFAULT_THREADS),
         "-q"],
        data, "gobuster-dns",
    )


@enum_group.command("vhosts")
@click.option("--domain", "-d", default=None, help="Domain for vhost discovery")
@click.option("--port", "-p", default=80, type=int)
def enum_vhosts(domain, port):
    """Virtual host discovery with ffuf."""
    data = require_active_project()
    target = data["target"].get("ip")
    hostname = data["target"].get("hostname")

    if not domain:
        domain = hostname
    if not domain:
        console.print("[bold red]✗[/] No hostname set. Use --domain or set target hostname.")
        raise SystemExit(1)

    wordlist = str(VHOST_WORDLIST) if VHOST_WORDLIST.exists() else "/usr/share/wordlists/dirb/common.txt"

    console.print(f"[bold]🏠 VHost Discovery for {domain}[/]\n")
    _run_tool(
        ["ffuf",
         "-u", f"http://{target}:{port}",
         "-H", f"Host: FUZZ.{domain}",
         "-w", wordlist,
         "-mc", "200,204,301,302,307,401,403",
         "-c",
         "-t", str(DEFAULT_THREADS),
         "-fs", "0"],  # filter empty responses
        data, "ffuf-vhosts",
    )


@enum_group.command("all")
@click.option("--port", "-p", default=80, type=int)
def enum_all(port):
    """Run all enumeration modules (web, smb, dns)."""
    data = require_active_project()
    target = data["target"].get("ip")
    hostname = data["target"].get("hostname")

    if not target:
        console.print("[bold red]✗[/] No target set.")
        raise SystemExit(1)

    console.print("[bold magenta]🚀 Running full enumeration suite...[/]\n")

    # Web
    ctx = click.Context(enum_web, info_name="web")
    ctx.invoke(enum_web, port=port)

    # SMB
    ctx = click.Context(enum_smb, info_name="smb")
    ctx.invoke(enum_smb)

    # DNS (if hostname set)
    if hostname:
        ctx = click.Context(enum_dns, info_name="dns")
        ctx.invoke(enum_dns, domain=hostname)
    else:
        console.print("[dim]Skipping DNS — no hostname set.[/]")

    console.print("\n[bold green]✓[/] Full enumeration complete.")
