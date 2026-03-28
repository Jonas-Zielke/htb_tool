"""
HTB Tool — Activity Logger

Records every action taken during a project into the project's activity_log.
This data feeds directly into report generation.
"""
from datetime import datetime, timezone


class ActivityLogger:
    """Logs activities to a project's activity_log list."""

    def __init__(self, project_data: dict):
        self.project_data = project_data
        if "activity_log" not in self.project_data:
            self.project_data["activity_log"] = []

    def log(self, action: str, details: str = "", result: str = "",
            command: str = "", output_file: str = "") -> dict:
        """Record an activity entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details,
            "command": command,
            "result": result,
            "output_file": output_file,
        }
        self.project_data["activity_log"].append(entry)
        return entry

    def log_scan(self, scan_type: str, command: str, output_file: str = "",
                 summary: str = "") -> dict:
        """Record a scan activity."""
        return self.log(
            action=f"scan:{scan_type}",
            details=f"Ran {scan_type} scan",
            command=command,
            result=summary,
            output_file=output_file,
        )

    def log_enum(self, enum_type: str, command: str, output_file: str = "",
                 summary: str = "") -> dict:
        """Record an enumeration activity."""
        return self.log(
            action=f"enum:{enum_type}",
            details=f"Ran {enum_type} enumeration",
            command=command,
            result=summary,
            output_file=output_file,
        )

    def log_web(self, test_type: str, command: str, output_file: str = "",
                summary: str = "") -> dict:
        """Record a web vulnerability test activity."""
        return self.log(
            action=f"web:{test_type}",
            details=f"Ran {test_type} web test",
            command=command,
            result=summary,
            output_file=output_file,
        )

    def log_payload(self, payload_type: str, details: str = "",
                    output_file: str = "") -> dict:
        """Record a payload generation activity."""
        return self.log(
            action=f"payload:{payload_type}",
            details=details,
            output_file=output_file,
        )

    def log_target(self, action_detail: str) -> dict:
        """Record a target-related action."""
        return self.log(action="target", details=action_detail)

    def get_log(self) -> list:
        """Return the full activity log."""
        return self.project_data.get("activity_log", [])

    def get_log_summary(self) -> dict:
        """Return summary counts by action type."""
        log = self.get_log()
        summary = {}
        for entry in log:
            action = entry.get("action", "unknown")
            category = action.split(":")[0]
            summary[category] = summary.get(category, 0) + 1
        return summary
