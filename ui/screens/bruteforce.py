"""
HTB Toolbox — Brute Force & Cracking Screens
"""
import subprocess
from pathlib import Path

from ui.helpers import (
    console, pause, ask, ask_int, show_error, show_success, show_info,
    menu_header, render_menu, choose, get_project_or_warn, get_target_or_warn,
)
from core.project import save_project, get_project_output_dir
from core.logger import ActivityLogger
from rich.panel import Panel


ROCKYOU = Path("/usr/share/wordlists/rockyou.txt")
COMMON_USERS = Path("/usr/share/seclists/Usernames/top-usernames-shortlist.txt")


def _run_hydra(cmd, data, label):
    """Run hydra and log the result."""
    logger = ActivityLogger(data)
    output_dir = get_project_output_dir(data["name"])
    outfile = output_dir / f"hydra_{label}.txt"

    from ui.helpers import check_tool_installed
    if not check_tool_installed(cmd[0]):
        return

    cmd_str = " ".join(cmd)
    console.print(f"\n  [bold cyan]⚡ Running:[/] [dim]{cmd_str}[/]\n")

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    output = proc.stdout or ""

    if output:
        with open(outfile, "w") as f:
            f.write(output)
        console.print(Panel(output, title=f"[bold]Hydra — {label}[/]", border_style="green"))
    if proc.stderr:
        err = proc.stderr.strip()
        if err:
            console.print(f"  [dim]{err[:500]}[/]")

    logger.log("bruteforce:" + label, command=cmd_str, details=f"Hydra {label}")
    save_project(data)


def menu_bruteforce():
    while True:
        menu_header()
        items = [
            ("1", "🔐", "Hydra — SSH Brute Force"),
            ("2", "🌐", "Hydra — HTTP Login Brute Force"),
            ("3", "📁", "Hydra — FTP Brute Force"),
            ("4", "📧", "Hydra — SMTP Brute Force"),
            ("5", "⌨️ ", "Hydra — Custom Service"),
            ("6", "🔨", "John the Ripper — Crack Hash"),
            ("7", "⚡", "Hashcat — Crack Hash"),
            ("8", "🔑", "Hash Identifier"),
        ]
        render_menu("Brute Force & Cracking", items)
        c = choose(items)
        if c == "0": return
        elif c == "1": action_hydra_ssh()
        elif c == "2": action_hydra_http()
        elif c == "3": action_hydra_ftp()
        elif c == "4": action_hydra_smtp()
        elif c == "5": action_hydra_custom()
        elif c == "6": action_john()
        elif c == "7": action_hashcat()
        elif c == "8": action_hashid()


def _get_wordlists():
    """Ask user for username and password wordlists."""
    console.print("  [dim]Password wordlist:[/]")
    console.print("    [cyan]1[/]. rockyou.txt")
    console.print("    [cyan]2[/]. Custom path")
    wl_c = ask("Password wordlist", "1")
    if wl_c == "2":
        pass_wl = ask("Path to password wordlist")
    else:
        pass_wl = str(ROCKYOU) if ROCKYOU.exists() else ask("Path to password wordlist")

    return pass_wl


def action_hydra_ssh():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Hydra — SSH Brute Force")

    console.print("  [dim]Mode:[/]")
    console.print("    [cyan]1[/]. Single username + password list")
    console.print("    [cyan]2[/]. Username list + password list")
    mode = ask("Mode", "1")

    if mode == "1":
        username = ask("Username to attack", "root")
        pass_wl = _get_wordlists()
        cmd = ["hydra", "-l", username, "-P", pass_wl, f"ssh://{ip}", "-t", "4", "-V"]
    else:
        user_wl = ask("Username wordlist path", str(COMMON_USERS) if COMMON_USERS.exists() else "")
        pass_wl = _get_wordlists()
        cmd = ["hydra", "-L", user_wl, "-P", pass_wl, f"ssh://{ip}", "-t", "4", "-V"]

    port = ask_int("SSH port", 22)
    if port != 22:
        cmd.extend(["-s", str(port)])

    try:
        _run_hydra(cmd, data, "ssh")
    except subprocess.TimeoutExpired:
        show_error("Hydra timed out.")
    pause()


def action_hydra_http():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Hydra — HTTP Login Brute Force")
    host = data["target"].get("hostname") or ip

    console.print("  [dim]Method:[/]")
    console.print("    [cyan]1[/]. HTTP POST form")
    console.print("    [cyan]2[/]. HTTP GET form")
    console.print("    [cyan]3[/]. HTTP Basic Auth")
    method = ask("Method", "1")

    if method in ("1", "2"):
        path = ask("Login page path (e.g. /login.php)", "/login")
        form_data = ask("Form data (user=^USER^&pass=^PASS^)", "username=^USER^&password=^PASS^")
        fail_str = ask("Failed login indicator text", "Invalid")
        username = ask("Username (or ^USER^ for list)", "admin")
        pass_wl = _get_wordlists()

        http_method = "http-post-form" if method == "1" else "http-get-form"
        form_string = f"{path}:{form_data}:{fail_str}"

        if "^USER^" in username:
            user_wl = ask("Username wordlist path")
            cmd = ["hydra", "-L", user_wl, "-P", pass_wl, host, http_method, form_string, "-V"]
        else:
            cmd = ["hydra", "-l", username, "-P", pass_wl, host, http_method, form_string, "-V"]
    else:
        path = ask("Auth path", "/")
        username = ask("Username", "admin")
        pass_wl = _get_wordlists()
        cmd = ["hydra", "-l", username, "-P", pass_wl, f"http-get://{host}{path}", "-V"]

    try:
        _run_hydra(cmd, data, "http")
    except subprocess.TimeoutExpired:
        show_error("Hydra timed out.")
    pause()


def action_hydra_ftp():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Hydra — FTP Brute Force")
    username = ask("Username", "anonymous")
    pass_wl = _get_wordlists()
    cmd = ["hydra", "-l", username, "-P", pass_wl, f"ftp://{ip}", "-t", "4", "-V"]

    try:
        _run_hydra(cmd, data, "ftp")
    except subprocess.TimeoutExpired:
        show_error("Hydra timed out.")
    pause()


def action_hydra_smtp():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Hydra — SMTP Brute Force")
    username = ask("Email/username")
    pass_wl = _get_wordlists()
    cmd = ["hydra", "-l", username, "-P", pass_wl, f"smtp://{ip}", "-V"]

    try:
        _run_hydra(cmd, data, "smtp")
    except subprocess.TimeoutExpired:
        show_error("Hydra timed out.")
    pause()


def action_hydra_custom():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Hydra — Custom Service")
    service = ask("Service (ssh, ftp, http-post-form, smb, rdp, telnet, mysql, etc.)")
    username = ask("Username", "admin")
    pass_wl = _get_wordlists()
    port = ask("Port (leave empty for default)", "")

    cmd = ["hydra", "-l", username, "-P", pass_wl]
    if port:
        cmd.extend(["-s", port])
    cmd.extend([ip, service, "-V"])

    try:
        _run_hydra(cmd, data, f"custom-{service}")
    except subprocess.TimeoutExpired:
        show_error("Hydra timed out.")
    pause()


def action_john():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("John the Ripper")
    hash_file = ask("Hash file path")
    if not hash_file or not Path(hash_file).exists():
        show_error("Hash file not found.")
        pause()
        return

    console.print("\n  [dim]Format examples: raw-md5, raw-sha256, bcrypt, ntlm, sha512crypt[/]")
    fmt = ask("Hash format (leave empty for auto-detect)", "")

    wordlist = ask("Wordlist", str(ROCKYOU) if ROCKYOU.exists() else "")

    from ui.helpers import check_tool_installed
    if not check_tool_installed("john"):
        return

    cmd = ["john"]
    if fmt:
        cmd.extend([f"--format={fmt}"])
    if wordlist:
        cmd.extend([f"--wordlist={wordlist}"])
    cmd.append(hash_file)

    console.print(f"\n  [bold cyan]⚡ Running:[/] [dim]{' '.join(cmd)}[/]\n")
    try:
        subprocess.run(cmd, timeout=600)
    except subprocess.TimeoutExpired:
        show_error("John timed out (10 min limit).")
    except KeyboardInterrupt:
        console.print("\n  [dim]Stopped.[/]")

    # Show cracked
    console.print("\n  [bold]Cracked passwords:[/]")
    subprocess.run(["john", "--show", hash_file])

    logger = ActivityLogger(data)
    logger.log("crack:john", command=" ".join(cmd), details="John the Ripper")
    save_project(data)
    pause()


def action_hashcat():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Hashcat")
    hash_file = ask("Hash file path")
    if not hash_file or not Path(hash_file).exists():
        show_error("Hash file not found.")
        pause()
        return

    console.print("\n  [dim]Common modes: 0=MD5, 100=SHA1, 1400=SHA256, 1800=sha512crypt[/]")
    console.print("  [dim]             1000=NTLM, 3200=bcrypt, 500=md5crypt[/]")
    mode = ask("Hash mode", "0")
    wordlist = ask("Wordlist", str(ROCKYOU) if ROCKYOU.exists() else "")

    from ui.helpers import check_tool_installed
    if not check_tool_installed("hashcat"):
        return

    cmd = ["hashcat", "-m", mode, hash_file, wordlist, "--force"]
    console.print(f"\n  [bold cyan]⚡ Running:[/] [dim]{' '.join(cmd)}[/]\n")

    try:
        subprocess.run(cmd, timeout=600)
    except subprocess.TimeoutExpired:
        show_error("Hashcat timed out.")
    except KeyboardInterrupt:
        console.print("\n  [dim]Stopped.[/]")

    logger = ActivityLogger(data)
    logger.log("crack:hashcat", command=" ".join(cmd), details="Hashcat")
    save_project(data)
    pause()


def action_hashid():
    menu_header("Hash Identifier")
    hash_str = ask("Paste hash to identify")
    if not hash_str:
        return

    # Simple hash identification by length/pattern
    h = hash_str.strip()
    results = []
    if len(h) == 32:
        results = ["MD5", "NTLM", "LM"]
    elif len(h) == 40:
        results = ["SHA1", "MySQL 4.x"]
    elif len(h) == 64:
        results = ["SHA256", "SHA3-256"]
    elif len(h) == 128:
        results = ["SHA512", "SHA3-512"]
    elif h.startswith("$1$"):
        results = ["md5crypt (Unix)"]
    elif h.startswith("$2"):
        results = ["bcrypt"]
    elif h.startswith("$5$"):
        results = ["SHA256crypt (Unix)"]
    elif h.startswith("$6$"):
        results = ["SHA512crypt (Unix)"]
    elif h.startswith("$apr1$"):
        results = ["Apache APR1"]
    elif ":" in h:
        results = ["Possibly NTHash or username:hash format"]
    else:
        results = ["Unknown format"]

    console.print(f"\n  [bold]Hash:[/] [cyan]{h[:60]}{'...' if len(h) > 60 else ''}[/]")
    console.print(f"  [bold]Length:[/] {len(h)}")
    console.print(f"  [bold]Possible types:[/]")
    for r in results:
        console.print(f"    [yellow]• {r}[/]")

    # Try hashid if installed
    try:
        proc = subprocess.run(["hashid", h], capture_output=True, text=True, timeout=5)
        if proc.stdout:
            console.print(f"\n  [bold]hashid output:[/]")
            console.print(f"  [dim]{proc.stdout.strip()}[/]")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    pause()
