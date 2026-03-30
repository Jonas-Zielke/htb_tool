"""
HTB Toolbox — Scanning Screens
"""
import subprocess
from datetime import datetime

from ui.helpers import (
    console, pause, ask, ask_int, confirm, show_error, show_success, show_info,
    menu_header, render_menu, choose, get_project_or_warn, get_target_or_warn,
)
from core.project import save_project, get_project_output_dir
from core.logger import ActivityLogger
from modules.scan import _run_nmap
from rich.table import Table


def menu_scan():
    while True:
        menu_header()
        items = [
            ("1", "⚡", "Quick Nmap Scan (Top 1000 ports)"),
            ("2", "🔎", "Full Nmap Scan (all 65535)"),
            ("3", "🚀", "RustScan (Extremely Fast Port Scan)"),
            ("4", "🌊", "Masscan (Massive Network Scan)"),
            ("5", "📦", "UDP Scan (top 100)", "sudo"),
            ("6", "💀", "Vulnerability Scan (NSE vuln)"),
            ("7", "🥷", "Stealth SYN Scan", "sudo"),
            ("8", "📜", "Custom NSE Scripts"),
            ("9", "⌨️ ", "Custom Nmap Command"),
            ("h", "📋", "View Scan History"),
        ]
        render_menu("Port Scanning", items)
        c = choose(items)
        if c == "0": return
        elif c == "1": run_scan("quick", ["-sC", "-sV", "-T4", "--top-ports", "1000"])
        elif c == "2": run_scan("full", ["-sC", "-sV", "-p-", "-T4"])
        elif c == "3": action_rustscan()
        elif c == "4": action_masscan()
        elif c == "5": run_scan("udp", ["-sU", "--top-ports", "100", "-T4"], sudo=True)
        elif c == "6": run_scan("vuln", ["--script", "vuln", "-T4"])
        elif c == "7": run_scan("stealth", ["-sS", "-T2", "-f", "--data-length", "50", "-p-"], sudo=True)
        elif c == "8": action_nse_scripts()
        elif c == "9": action_custom_nmap()
        elif c == "h": action_scan_history()


def run_scan(label, args, sudo=False):
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header(f"Running {label.upper()} Scan")
    try:
        _run_nmap(args, data, label, sudo=sudo)
    except SystemExit:
        pass
    except subprocess.TimeoutExpired:
        show_error("Scan timed out (30 min limit).")
    pause()

def action_rustscan():
    data = get_project_or_warn()
    if not data: return
    ip = get_target_or_warn(data)
    if not ip: return
    
    from ui.helpers import check_tool_installed
    if not check_tool_installed("rustscan"): return
    
    menu_header("RustScan Integration")
    console.print(f"  [dim]Target: {ip}[/]")
    cmd = ["rustscan", "-a", ip, "--", "-sC", "-sV"]
    console.print(f"\n  [cyan]Running:[/] {' '.join(cmd)}\n")
    try:
        subprocess.run(cmd)
        save_scan_history(data, "rustscan", " ".join(cmd))
    except KeyboardInterrupt: pass
    pause()

def action_masscan():
    data = get_project_or_warn()
    if not data: return
    ip = get_target_or_warn(data)
    if not ip: return
    
    from ui.helpers import check_tool_installed
    if not check_tool_installed("masscan"): return
    
    menu_header("Masscan Integration")
    rate = ask("Packet rate", "1000")
    ports = ask("Ports", "1-65535")
    
    cmd = ["sudo", "masscan", "-p", ports, ip, "--rate", rate]
    console.print(f"\n  [cyan]Running:[/] {' '.join(cmd)}\n")
    try:
        subprocess.run(cmd)
        save_scan_history(data, "masscan", " ".join(cmd))
    except KeyboardInterrupt: pass
    pause()

def save_scan_history(data, type_str, cmd_str):
    data.setdefault("scan_results", []).append({
        "type": type_str,
        "timestamp": datetime.now().isoformat(),
        "command": cmd_str,
        "ports_found": "?"
    })
    save_project(data)

def action_nse_scripts():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Custom NSE Scripts")
    console.print("  [dim]Common scripts: http-enum, smb-enum-shares, ftp-anon, ssh-brute[/]")
    console.print("  [dim]               vuln, default, safe, auth, discovery[/]\n")
    scripts = ask("Script(s) to run (comma-separated)")
    if not scripts:
        return
    ports = ask("Port(s) to target (leave empty for default)", "")
    args = ["--script", scripts]
    if ports:
        args.extend(["-p", ports])
    try:
        _run_nmap(args, data, f"scripts-{scripts.replace(',', '_')[:20]}")
    except SystemExit:
        pass
    pause()


def action_custom_nmap():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Custom Nmap Command")
    console.print(f"  [dim]Target: {ip} (appended automatically)[/]\n")
    args_str = ask("Nmap arguments (e.g. -sV -p 80,443 --script http-headers)")
    if not args_str:
        return
    args = args_str.split()
    try:
        _run_nmap(args, data, "custom")
    except SystemExit:
        pass
    pause()


def action_scan_history():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Scan History")
    scans = data.get("scan_results", [])
    if not scans:
        show_info("No scans recorded yet.")
        pause()
        return

    table = Table(title="📋 Scan History", header_style="bold cyan", border_style="green")
    table.add_column("#", justify="right", width=4)
    table.add_column("Type", style="yellow")
    table.add_column("Timestamp", style="dim")
    table.add_column("Ports Found", justify="right", style="green")
    table.add_column("Command", style="dim", max_width=50)
    for i, s in enumerate(scans, 1):
        table.add_row(
            str(i), s.get("type", "?"), s.get("timestamp", "?")[:19],
            str(s.get("ports_found", "—")), s.get("command", "")[:50],
        )
    console.print(table)
    pause()
