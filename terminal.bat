@echo off
REM ── Ouvre PowerShell directement dans le projet avec venv active ────
start powershell -NoExit -Command "cd '%~dp0'; .\.venv\Scripts\Activate.ps1; Write-Host '[OK] Environnement TradeRadar pret' -ForegroundColor Green"
