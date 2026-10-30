$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m pip install --upgrade pip
python -m pip install -e . pyinstaller
python -m PyInstaller --noconfirm --clean --windowed --name ClaudeUsage --collect-all keyring --collect-all PySide6 run.py
Write-Host "Build complete: windows/dist/ClaudeUsage/ClaudeUsage.exe"
