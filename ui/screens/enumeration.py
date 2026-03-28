"""
HTB Toolbox — Service Enumeration Screens
"""
from ui.helpers import (
    console, pause, ask, ask_int, show_error, show_success, show_info,
    menu_header, render_menu, choose, get_project_or_warn, get_target_or_warn,
)
from core.project import save_project
from core.config import (
    DIR_WORDLIST, DNS_WORDLIST, VHOST_WORDLIST, WEB_EXTENSIONS, DEFAULT_THREADS,
)
from modules.enumerate import _run_tool


def menu_enum():
    while True:
        menu_header()
        items = [
            ("1", "🌐", "Web Enumeration (WhatWeb + Gobuster)"),
            ("2", "📂", "Directory Brute-force"),
            ("3", "📁", "SMB Enumeration"),
            ("4", "🔤", "DNS Enumeration"),
            ("5", "🏠", "Virtual Host Discovery"),
            ("6", "🚀", "Full Auto-Enum (all of the above)"),
        ]
        render_menu("Service Enumeration", items)
        c = choose(items)
        if c == "0": return
        elif c == "1": action_enum_web()
        elif c == "2": action_enum_dirs()
        elif c == "3": action_enum_smb()
        elif c == "4": action_enum_dns()
        elif c == "5": action_enum_vhosts()
        elif c == "6": action_enum_all()


def _get_base_url(data, default_port=80):
    hostname = data["target"].get("hostname")
    ip = data["target"].get("ip")
    host = hostname or ip
    port = ask_int("Port", default_port)
    scheme = "https" if port == 443 else "http"
    return f"{scheme}://{host}:{port}"


def action_enum_web():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Web Enumeration")
    base_url = _get_base_url(data)

    console.print(f"\n  [bold]🌐 Running WhatWeb + Gobuster on {base_url}[/]\n")

    _run_tool(["whatweb", "-a", "3", base_url], data, "whatweb")

    wordlist = str(DIR_WORDLIST) if DIR_WORDLIST.exists() else "/usr/share/wordlists/dirb/common.txt"
    _run_tool(
        ["gobuster", "dir", "-u", base_url, "-w", wordlist,
         "-x", WEB_EXTENSIONS, "-t", str(DEFAULT_THREADS), "--no-error", "-q"],
        data, "gobuster-dir",
    )
    pause()


def action_enum_dirs():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Directory Brute-force")
    base_url = _get_base_url(data)

    console.print("  [dim]Wordlists:[/]")
    console.print("    [cyan]1[/]. common.txt (fast)")
    console.print("    [cyan]2[/]. big.txt (thorough)")
    console.print("    [cyan]3[/]. Custom path")
    wl_choice = ask("Wordlist", "1")

    from core.config import DIR_WORDLIST_BIG
    if wl_choice == "2":
        wordlist = str(DIR_WORDLIST_BIG) if DIR_WORDLIST_BIG.exists() else str(DIR_WORDLIST)
    elif wl_choice == "3":
        wordlist = ask("Path to wordlist")
    else:
        wordlist = str(DIR_WORDLIST) if DIR_WORDLIST.exists() else "/usr/share/wordlists/dirb/common.txt"

    extensions = ask("File extensions", WEB_EXTENSIONS)

    console.print("  [dim]Tool:[/]  [cyan]1[/]. Gobuster  [cyan]2[/]. ffuf")
    tool = ask("Tool", "1")

    if tool == "2":
        _run_tool(
            ["ffuf", "-u", f"{base_url}/FUZZ", "-w", wordlist,
             "-e", "," + extensions.replace(",", ",."),
             "-t", str(DEFAULT_THREADS), "-mc", "200,204,301,302,307,401,403", "-c"],
            data, "ffuf-dirs",
        )
    else:
        _run_tool(
            ["gobuster", "dir", "-u", base_url, "-w", wordlist,
             "-x", extensions, "-t", str(DEFAULT_THREADS), "--no-error", "-q"],
            data, "gobuster-dirs",
        )
    pause()


def action_enum_smb():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("SMB Enumeration")
    console.print(f"  [bold]📁 Running enum4linux + smbclient on {ip}[/]\n")

    _run_tool(["enum4linux", "-a", ip], data, "enum4linux", timeout=300)
    _run_tool(["smbclient", "-L", f"//{ip}", "-N"], data, "smbclient-list", timeout=30)
    pause()


def action_enum_dns():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    hostname = data["target"].get("hostname")
    menu_header("DNS Enumeration")
    domain = ask("Domain to enumerate", hostname or "")
    if not domain:
        show_error("Domain is required for DNS enumeration.")
        pause()
        return

    console.print(f"\n  [bold]🔤 DNS Enumeration for {domain}[/]\n")

    _run_tool(["dig", "axfr", domain, f"@{ip}"], data, "dns-zonetransfer", timeout=30)

    wordlist = str(DNS_WORDLIST) if DNS_WORDLIST.exists() else "/usr/share/wordlists/dirb/common.txt"
    _run_tool(
        ["gobuster", "dns", "-d", domain, "-w", wordlist,
         "-t", str(DEFAULT_THREADS), "-q"],
        data, "gobuster-dns",
    )
    pause()


def action_enum_vhosts():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    hostname = data["target"].get("hostname")
    menu_header("Virtual Host Discovery")
    domain = ask("Base domain", hostname or "")
    port = ask_int("Port", 80)
    if not domain:
        show_error("Domain is required for VHost discovery.")
        pause()
        return

    wordlist = str(VHOST_WORDLIST) if VHOST_WORDLIST.exists() else "/usr/share/wordlists/dirb/common.txt"
    _run_tool(
        ["ffuf", "-u", f"http://{ip}:{port}", "-H", f"Host: FUZZ.{domain}",
         "-w", wordlist, "-mc", "200,204,301,302,307,401,403",
         "-c", "-t", str(DEFAULT_THREADS), "-fs", "0"],
        data, "ffuf-vhosts",
    )
    pause()


def action_enum_all():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Full Auto-Enumeration")
    console.print("  [bold magenta]🚀 Running full enumeration suite...[/]\n")

    hostname = data["target"].get("hostname")
    host = hostname or ip
    base_url = f"http://{host}:80"

    # WhatWeb
    _run_tool(["whatweb", "-a", "3", base_url], data, "whatweb")

    # Gobuster dir
    wordlist = str(DIR_WORDLIST) if DIR_WORDLIST.exists() else "/usr/share/wordlists/dirb/common.txt"
    _run_tool(
        ["gobuster", "dir", "-u", base_url, "-w", wordlist,
         "-x", WEB_EXTENSIONS, "-t", str(DEFAULT_THREADS), "--no-error", "-q"],
        data, "gobuster-dir",
    )

    # SMB
    _run_tool(["enum4linux", "-a", ip], data, "enum4linux", timeout=300)
    _run_tool(["smbclient", "-L", f"//{ip}", "-N"], data, "smbclient-list", timeout=30)

    # DNS
    if hostname:
        _run_tool(["dig", "axfr", hostname, f"@{ip}"], data, "dns-zonetransfer", timeout=30)
        dns_wl = str(DNS_WORDLIST) if DNS_WORDLIST.exists() else wordlist
        _run_tool(
            ["gobuster", "dns", "-d", hostname, "-w", dns_wl,
             "-t", str(DEFAULT_THREADS), "-q"],
            data, "gobuster-dns",
        )

    show_success("Full enumeration complete!")
    pause()
