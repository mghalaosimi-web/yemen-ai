$ErrorActionPreference='Stop'; $root=Split-Path -Parent $PSScriptRoot; Set-Location $root
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onedir --name Yemen_AI --add-data "app;app" --add-data "backend;backend" --add-data "data;data" launcher.py
Write-Host "Build complete: $root\dist\Yemen_AI\Yemen_AI.exe"
if(Get-Command makensis -ErrorAction SilentlyContinue){ makensis installer\YemenAI.nsi; Write-Host 'Installer created.' } else { Write-Host 'NSIS not found. Install NSIS then run: makensis installer\YemenAI.nsi' }
