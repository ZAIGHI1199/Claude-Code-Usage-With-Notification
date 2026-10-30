"""Windows browser discovery and launch helpers."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def find_chrome() -> str | None:
    """Return the Chrome executable path, including common per-user installs."""
    found = shutil.which("chrome") or shutil.which("chrome.exe")
    if found:
        return found

    candidates: list[Path] = []
    for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        root = os.environ.get(variable)
        if root:
            candidates.append(Path(root) / "Google/Chrome/Application/chrome.exe")

    # App Paths also covers custom installation locations.
    if os.name == "nt":
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                    try:
                        key = winreg.OpenKey(
                            hive,
                            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                            0,
                            winreg.KEY_READ | view,
                        )
                        with key:
                            value, _ = winreg.QueryValueEx(key, None)
                            candidates.insert(0, Path(value))
                    except OSError:
                        continue
        except ImportError:
            pass

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def open_in_chrome(url: str) -> bool:
    """Open URL in Google Chrome. Returns False when Chrome is not installed."""
    chrome = find_chrome()
    if not chrome:
        return False
    try:
        subprocess.Popen(
            [chrome, "--new-window", url],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    except OSError:
        return False
    return True
