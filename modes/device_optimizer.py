from pydantic import BaseModel
from typing import List

class DeviceState(BaseModel):
    os: str
    ram_gb: int
    disk_space_gb: int
    cpu_usage_percent: float
    startup_programs: List[str]
    junk_files_mb: int

class OptimizationSuggestion(BaseModel):
    title: str
    description: str
    recommended_action: str

def optimize_device(state: DeviceState) -> List[OptimizationSuggestion]:
    suggestions = []

    if state.cpu_usage_percent > 80:
        suggestions.append(OptimizationSuggestion(
            title="High CPU Usage",
            description="Your CPU usage is above 80%, which may slow your computer.",
            recommended_action="Close background apps or check Task Manager for heavy processes."
        ))

    if state.junk_files_mb > 500:
        suggestions.append(OptimizationSuggestion(
            title="Junk Files Detected",
            description=f"You have {state.junk_files_mb}MB of junk files.",
            recommended_action="Run Disk Cleanup or use a cleanup tool like CCleaner."
        ))

    if len(state.startup_programs) > 5:
        suggestions.append(OptimizationSuggestion(
            title="Too Many Startup Programs",
            description=f"{len(state.startup_programs)} startup programs detected.",
            recommended_action="Disable unnecessary startup apps in Task Manager > Startup tab."
        ))

    if state.ram_gb < 4:
        suggestions.append(OptimizationSuggestion(
            title="Low RAM",
            description="You have less than 4GB of RAM, which may cause lag.",
            recommended_action="Close unused programs or consider upgrading RAM."
        ))

    if state.disk_space_gb < 10:
        suggestions.append(OptimizationSuggestion(
            title="Low Disk Space",
            description="Less than 10GB of disk space remaining.",
            recommended_action="Delete unused files or uninstall unused apps."
        ))

    if not suggestions:
        suggestions.append(OptimizationSuggestion(
            title="System Looks Good 🎉",
            description="No major issues detected with your system.",
            recommended_action="No action needed at this time."
        ))

    return suggestions
