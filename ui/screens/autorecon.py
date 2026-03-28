"""
HTB Toolbox — Auto-Recon (Full Automated Reconnaissance)
"""
from ui.helpers import (
    console, pause, show_success, show_info, confirm,
    menu_header, get_project_or_warn, get_target_or_warn,
)
from core.project import save_project
from core.config import DIR_WORDLIST, DNS_WORDLIST, WEB_EXTENSIONS, DEFAULT_THREADS
from core.logger import ActivityLogger
from modules.scan import _run_nmap
from modules.enumerate import _run_tool


def action_autorecon():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    hostname = data["target"].get("hostname")

    menu_header("🚀 Auto-Recon — Full Automated Reconnaissance")
    console.print(f"  [bold]Target:[/] [cyan]{ip}[/]" + (f" ([yellow]{hostname}[/])" if hostname else ""))
    console.print()
    console.print("  This will run in sequence:")
    console.print("    [cyan]1.[/] Nmap Quick Scan (top 1000 ports)")
    console.print("    [cyan]2.[/] Nmap Full Port Scan (all 65535)")
    console.print("    [cyan]3.[/] WhatWeb fingerprint")
    console.print("    [cyan]4.[/] Gobuster directory scan")
    console.print("    [cyan]5.[/] SMB enumeration (enum4linux)")
    if hostname:
        console.print("    [cyan]6.[/] DNS zone transfer attempt")
    console.print()

    if not confirm("Start auto-recon?"):
        return

    logger = ActivityLogger(data)
    logger.log("autorecon:start", details="Started full auto-recon")

    # 1. Quick scan
    console.print("\n[bold magenta]━━━ Phase 1: Quick Nmap Scan ━━━[/]\n")
    try:
        _run_nmap(["-sC", "-sV", "-T4", "--top-ports", "1000"], data, "quick")
    except (SystemExit, Exception) as e:
        console.print(f"  [yellow]Quick scan issue: {e}[/]")

    # 2. Full port scan
    console.print("\n[bold magenta]━━━ Phase 2: Full Port Scan ━━━[/]\n")
    try:
        _run_nmap(["-sC", "-sV", "-p-", "-T4"], data, "full")
    except (SystemExit, Exception) as e:
        console.print(f"  [yellow]Full scan issue: {e}[/]")

    # 3. WhatWeb
    host = hostname or ip
    console.print("\n[bold magenta]━━━ Phase 3: WhatWeb Fingerprint ━━━[/]\n")
    _run_tool(["whatweb", "-a", "3", f"http://{host}"], data, "whatweb")

    # 4. Gobuster
    wordlist = str(DIR_WORDLIST) if DIR_WORDLIST.exists() else "/usr/share/wordlists/dirb/common.txt"
    console.print("\n[bold magenta]━━━ Phase 4: Directory Scan ━━━[/]\n")
    _run_tool(
        ["gobuster", "dir", "-u", f"http://{host}", "-w", wordlist,
         "-x", WEB_EXTENSIONS, "-t", str(DEFAULT_THREADS), "--no-error", "-q"],
        data, "gobuster-dir",
    )

    # 5. SMB
    console.print("\n[bold magenta]━━━ Phase 5: SMB Enumeration ━━━[/]\n")
    _run_tool(["enum4linux", "-a", ip], data, "enum4linux", timeout=300)

    # 6. DNS
    if hostname:
        console.print("\n[bold magenta]━━━ Phase 6: DNS Enumeration ━━━[/]\n")
        _run_tool(["dig", "axfr", hostname, f"@{ip}"], data, "dns-zonetransfer", timeout=30)

    logger.log("autorecon:complete", details="Auto-recon complete")
    save_project(data)

    console.print("\n[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")
    show_success("Auto-Recon complete! Check scan results for findings.")
    console.print(f"  [dim]Open ports found: {len(data.get('open_ports', []))}[/]")
    console.print("[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")
    pause()
