@echo off
REM ── TradeRadar — Lancement ──────────────────────────────────────────
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════╗
echo  ║         TradeRadar — Demarrage       ║
echo  ╚══════════════════════════════════════╝
echo.

REM Active l'environnement virtuel
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERREUR] Environnement virtuel introuvable.
    echo Executez d'abord : python -m venv .venv ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

REM Ouvre le navigateur après 2 secondes (en parallèle)
start "" /min cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"

REM Lance le serveur (bloque jusqu'à Ctrl+C)
echo [INFO] Serveur sur http://localhost:8000
echo [INFO] Appuyez sur Ctrl+C pour arreter
echo.
uvicorn main:app --reload
