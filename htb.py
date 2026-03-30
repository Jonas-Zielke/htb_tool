#!/usr/bin/env python3
"""
HTB Toolbox — Hack The Box Interactive Tool Manager
====================================================

Launch with:  python3 htb.py
Or:           htb  (if alias is set)

An interactive TUI that provides menus for all common HTB tasks:
scanning, enumeration, web exploits, payloads, brute force, and reporting.
"""
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

from ui.helpers import (
    console, clear, pause, menu_header, render_menu, choose, BANNER, status_bar,
)

from ui.screens.project import menu_project
from ui.screens.target import menu_target
from ui.screens.scanning import menu_scan
from ui.screens.enumeration import menu_enum
from ui.screens.web import menu_web
from ui.screens.payloads import menu_payload
from ui.screens.bruteforce import menu_bruteforce
from ui.screens.utils import menu_utils
from ui.screens.reports import menu_report
from ui.screens.autorecon import action_autorecon
from ui.screens.workflow import menu_workflow


def main():
    """Main application loop — displays the top-level menu."""
    try:
        while True:
            clear()
            console.print(BANNER)
            console.print()
            status_bar()

            items = [
                ("w", "🧠", "Workflow & AI Setup", "⚡"),
                ("1", "📁", "Project Management"),
                ("2", "🎯", "Target & DNS Setup"),
                ("3", "🔍", "Port Scanning"),
                ("4", "📡", "Service Enumeration"),
                ("5", "🕸️ ", "Web Vulnerability Testing"),
                ("6", "💣", "Payloads & Reverse Shells"),
                ("7", "🔓", "Brute Force & Cracking"),
                ("8", "🔧", "Utilities & Helpers"),
                ("9", "📄", "Reports, Notes & Creds"),
                ("a", "🚀", "Auto-Recon (Full Automated)", "⚡"),
            ]
            render_menu("Main Menu", items, back_label="Exit")
            c = choose(items, back_label="Exit")

            if c == "0":
                break
            elif c == "w":
                menu_workflow()
            elif c == "1":
                menu_project()
            elif c == "2":
                menu_target()
            elif c == "3":
                menu_scan()
            elif c == "4":
                menu_enum()
            elif c == "5":
                menu_web()
            elif c == "6":
                menu_payload()
            elif c == "7":
                menu_bruteforce()
            elif c == "8":
                menu_utils()
            elif c == "9":
                menu_report()
            elif c == "a":
                action_autorecon()

    except KeyboardInterrupt:
        pass

    clear()
    console.print("\n  [bold green]👋 Happy hacking! See you next time.[/]\n")


if __name__ == "__main__":
    main()
