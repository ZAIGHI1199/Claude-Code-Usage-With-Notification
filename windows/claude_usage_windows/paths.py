"""Windows-aware application and Claude Code paths."""
from __future__ import annotations
import os
from pathlib import Path

APP_DIR = "ClaudeUsage"

def config_dir() -> Path:
    root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return root / APP_DIR

def cache_dir() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return root / APP_DIR / "Cache"

def autostart_dir() -> Path:
    root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return root / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

def claude_code_dir() -> Path:
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(override).expanduser() if override else Path.home() / ".claude"
