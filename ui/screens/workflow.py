"""
HTB Toolbox — Hacker Workflow & AI Course of Action
"""
import sys
from ui.helpers import (
    console, pause, show_error, show_info, show_success,
    menu_header, render_menu, choose, get_project_or_warn
)
from rich.table import Table

def menu_workflow():
    while True:
        data = get_project_or_warn()
        if not data:
            return

        menu_header("AI Workflow & Recommendations")
        
        # Determine recommendations based on discovered data
        ports = {p.get("port", 0): p for p in data.get("open_ports", [])}
        os_guess = data.get("target", {}).get("os_guess", "").lower()
        
        recommendations = []
        
        if not ports:
            recommendations.append(("[bold red]Critical[/]", "No open ports found. Please run an Nmap/Rustscan port scan first."))
        else:
            if 80 in ports or 443 in ports or 8080 in ports or 8000 in ports:
                recommendations.append(("Web Services", "Run Web Directory Brute Force (gobuster/ffuf) and Nikto on HTTP/HTTPS ports."))
            
            if 445 in ports or 139 in ports:
                recommendations.append(("SMB Protocol", "Run smbmap, enum4linux, and smbclient to enumerate shares (NULL session testing)."))
                
            if 21 in ports:
                recommendations.append(("FTP Service", "Check for Anonymous FTP login and download any available files."))
                
            if 22 in ports:
                recommendations.append(("SSH Service", "Check for vulnerable versions (e.g., Debian Weak Keys), or wait for credential discovery to brute force."))
                
            if 53 in ports:
                recommendations.append(("DNS Service", "Perform zone transfer attempt (dig AXFR) and virtual host/sub-domain brute forcing."))

            if 1433 in ports or 3306 in ports or 5432 in ports or 1521 in ports:
                recommendations.append(("Databases", "Try default credentials, check for exposed SQL interfaces (MSSQL/MySQL/PostgreSQL/Oracle)."))

            if 88 in ports or 389 in ports or 636 in ports or 3268 in ports:
                recommendations.append(("Active Directory", "Domain Controller detected! Run LDAPDomainDump, AS-REP Roasting (GetNPUsers), and BloodHound/Sharphound."))
                
            if not os_guess:
                recommendations.append(("[dim]System[/]", "OS is still unknown. Consider running a stealth Nmap scan with OS detection (-O) if needed."))
                
        # Print table
        table = Table(title="🧠 Next Course of Action", header_style="bold cyan")
        table.add_column("Category", style="yellow", justify="right")
        table.add_column("Recommendation", style="white")
        
        for cat, rec in recommendations:
            table.add_row(cat, rec)
            
        console.print(table)
        
        # Tools to run directly from workflow
        items = [
            ("1", "🚀", "Action: Run Web Recon (Directory Brute Force)"),
            ("2", "📁", "Action: Run SMB Recon (enum4linux/smbclient)"),
            ("3", "🏰", "Action: Run Active Directory Recon"),
            ("4", "🔍", "Action: Go back to Scanning Menu"),
            ("5", "💣", "Action: Go to Payloads Generator Generator"),
        ]
        render_menu("Workflow Shortcuts", items)
        
        c = choose(items)
        if c == "0": return
        elif c == "1":
            from ui.screens.enumeration import action_enum_dirs
            action_enum_dirs()
        elif c == "2":
            from ui.screens.enumeration import action_enum_smb
            action_enum_smb()
        elif c == "3":
            show_info("Active Directory recon requires specific tools (ldapsearch, GetNPUsers).")
            # Usually AD recon falls into custom commands or specialized modules
            pause()
        elif c == "4":
            from ui.screens.scanning import menu_scan
            menu_scan()
        elif c == "5":
            from ui.screens.payloads import menu_payload
            menu_payload()
