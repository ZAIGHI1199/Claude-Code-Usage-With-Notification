# Claude Usage for Windows

A Windows system-tray implementation of Claude Usage. The Windows app reuses the upstream Python usage API, OAuth/PKCE flow, usage snapshot parser, Claude Code transcript parser and refresh store, while replacing GTK with PySide6.

## Requirements

- Windows 10/11
- Python 3.10+
- Claude Code installed for local context-window monitoring (optional)

## Development

From this directory in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m claude_usage_windows
```

The app appears in the notification area. Use **Import Claude Code login** if Claude Code is already authenticated, or **Sign in** to complete OAuth in your browser.

## Build

```powershell
.\build.ps1
```

PyInstaller creates `dist\ClaudeUsage\ClaudeUsage.exe`. Use Inno Setup or another installer builder to package the directory for distribution.

## Data and security

- Preferences: `%APPDATA%\ClaudeUsage\settings.json`
- Claude Code transcripts and credentials: read from `%USERPROFILE%\.claude` unless `CLAUDE_CONFIG_DIR` is set.
- OAuth tokens are stored through Python keyring's Windows Credential Manager backend. A private-profile file fallback exists only if keyring is unavailable; prefer installing the declared keyring dependency.
- Transcript files are read locally and are never uploaded by this application.
- The usage endpoint is an Anthropic OAuth endpoint used by Claude Code and is not a documented public API. Availability and response formats can change without notice.

## Scope

The initial Windows port includes usage windows, reset times, OAuth login, importing an existing Claude Code login, background refresh, system tray UI and local context-window monitoring. Historical analytics and forecasting are intentionally deferred until reliable snapshot collection and data semantics are established.


### Browser sign-in on Windows

The **Sign in with Chrome** action locates Google Chrome from PATH, common per-user/system install locations, and the Windows App Paths registry entry, then opens the Claude authorization URL in a new Chrome window. If Chrome is not installed or cannot be launched, the app falls back to the Windows default browser.

If the local callback cannot be completed (for example, because another process occupies the callback port or a browser/network policy blocks localhost redirects), use **Use sign-in code**. It opens the manual OAuth flow in Chrome and accepts the `code#state` value displayed by Claude. The authorization page and available identity providers (Google, Apple, or email) are controlled by Anthropic, not by this application.
