@echo off
REM ── TradeRadar — Arret force des serveurs uvicorn ───────────────────
echo.
echo  Arret des processus TradeRadar...
echo.

REM Tue tous les processus python utilisant le port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo [INFO] Arret du processus PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo  Serveur arrete.
timeout /t 2 /nobreak >nul
