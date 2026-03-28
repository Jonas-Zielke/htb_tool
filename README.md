# HTB Toolbox v2.0

HTB Toolbox is a comprehensive, interactive Terminal User Interface (TUI) tool designed to manage and automate your Hack The Box (HTB) and penetration testing workflows. It provides a menu-driven interface, allowing you to seamlessly move between recon, scanning, exploitation, and reporting without having to remember complex command-line flags.

## Features

The toolbox contains **10 main modules** covering over **50 actions**:

- 📁 **Project Management**: Create, load, list, and delete project sessions. Everything you do is automatically tracked in a project-specific JSON file.
- 🎯 **Target & DNS Setup**: Set target IP addresses and automatically inject hostnames directly into your `/etc/hosts` file.
- 🔍 **Port Scanning**: Run various nmap scan profiles natively (Quick, Full, UDP, Stealth, Vulnerability, Custom) and parse findings centrally.
- 📡 **Service Enumeration**: Automate WhatWeb, Gobuster (dir/dns), ffuf, enum4linux, and smbclient.
- 🕸️ **Web Vulnerability Testing**: SQL injection scanning (sqlmap), LFI testing (20+ built-in payloads), RCE/SSTI parameter tests, Nikto, and fuzzing.
- 💣 **Payloads & Reverse Shells**: Built-in 18+ reverse shell generators, msfvenom integration (11 presets), webshell generator, and automatic listener startup (Netcat / Metasploit).
- 🔓 **Brute Force & Cracking**: Hydra wrappers for SSH, HTTP, FTP, SMTP, and more. Crack hashes using John the Ripper and Hashcat. Identify hashes directly from the TUI.
- 🔧 **Utilities & Helpers**: Quickly spin up an HTTP file server, Base64 encode/decode strings, Hash strings, and access critical cheatsheets for PrivEsc, Tunneling, and File Transfers.
- 📄 **Reports, Notes & Creds**: Log all commands you run. Manually save notes and credentials. Export everything to a clean, dark-themed HTML or Markdown report.
- 🚀 **Auto-Recon**: A one-click automated reconnaissance suite that chains together an nmap quick scan -> nmap full scan -> WhatWeb -> Gobuster -> smbclient -> DNS zone transfers.

## Requirements

The core script is written in Python 3. You won't need anything exotic, as it's designed to run seamlessly on an out-of-the-box **Kali Linux** installation. 

### Python Packages
- `click`
- `rich`
- `jinja2`
- `requests`
- `pyyaml`
- `beautifulsoup4`

*(These are generally pre-installed on Kali, or you can install them via `apt` or `pipx`)*.

### System Tools
The script acts as an intelligent wrapper around standard pentesting tools. It expects the following binaries to be in your `$PATH`:
- `nmap`, `sqlmap`, `nikto`, `gobuster`, `ffuf`, `whatweb`, `enum4linux`, `smbclient`
- `msfvenom`, `msfconsole`, `nc` (or `rlwrap` for stabilization)
- `hydra`, `john`, `hashcat`, `hashid`

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/htb-toolbox.git
   cd htb-toolbox
   ```

2. **Set up an alias (Recommended):**
   ```bash
   # For Zsh users
   echo 'alias htb="python3 /path/to/htb-toolbox/htb.py"' >> ~/.zshrc
   source ~/.zshrc
   
   # For Bash users
   echo 'alias htb="python3 /path/to/htb-toolbox/htb.py"' >> ~/.bashrc
   source ~/.bashrc
   ```

## Usage

Simply run the tool using your alias:

```bash
htb
```

Or execute it directly:
```bash
python3 htb.py
```

### Initial Workflow Example

1. Launch `htb`.
2. Navigate to **[1] Project Management** -> Create a new project (e.g., `htb-bizness`).
3. Navigate to **[2] Target & DNS Setup** -> Set target IP (`10.10.11.252`) and hostname (`bizness.htb`). Let it automatically add the entry to `/etc/hosts`.
4. Navigate to **[a] Auto-Recon** to start background reconnaissance.
5. Exit back to the main menu and use other tools as you uncover attack vectors!

### Project Storage
All project files, scans, outputs, and generated payloads are stored securely in:
`~/.htb_projects/<project-name>/`

## Contributing

Pull requests are welcome! If you have additional templates for reverse shells, new command suggestions, or wrapper integrations, feel free to open a PR.

## License

This project is licensed under the MIT License.
