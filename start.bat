@echo off
REM ====================================================================
REM  TradeRadar - Lancement du serveur local
REM --------------------------------------------------------------------
REM  GUIDE :
REM   - PY      : interpreteur Python DU VENV, chemin RELATIF au .bat.
REM               On l'appelle directement plutot que de passer par
REM               "activate.bat" : ce dernier contient un chemin ABSOLU
REM               fige a la creation du venv, donc il casse des que le
REM               dossier du projet est deplace ou copie ailleurs.
REM   - PORT    : port HTTP du serveur (doit correspondre a l'URL ouverte)
REM   - dev     : "start.bat dev" ajoute --reload (rechargement auto des
REM               .py pendant le developpement). Sans argument : normal.
REM
REM  PREMIER LANCEMENT (machine neuve) : ce script cree tout seul le venv
REM  et installe requirements.txt. Il suffit d'avoir Python 3.11+ installe.
REM ====================================================================

cd /d "%~dp0"

REM --- Console en UTF-8 -----------------------------------------------
REM  Sans ca, un simple accent ou une fleche dans un print() Python leve
REM  UnicodeEncodeError sur la console Windows (cp1252) et peut faire
REM  disparaitre silencieusement des donnees du dashboard.
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"

set "PY=%~dp0.venv\Scripts\python.exe"
set "PORT=8000"

echo.
echo  ==========================================
echo            TradeRadar - Demarrage
echo  ==========================================
echo.

REM --- Etape 1 : venv present ? sinon on l'installe -------------------
if exist "%PY%" goto :venv_pret

echo [INFO] Environnement virtuel absent - installation automatique.
echo.

REM  Recherche d'un Python systeme. "py" = Python Launcher, livre avec
REM  l'installeur officiel Windows ; "python" en solution de repli.
set "SYSPY="
where py >nul 2>&1
if not errorlevel 1 set "SYSPY=py -3"
if not defined SYSPY goto :essai_python
goto :creer_venv

:essai_python
where python >nul 2>&1
if not errorlevel 1 set "SYSPY=python"

:creer_venv
if not defined SYSPY (
    echo [ERREUR] Aucun Python trouve sur cette machine.
    echo  Installez Python 3.11 ou plus depuis https://www.python.org/downloads/
    echo  IMPORTANT : cochez "Add python.exe to PATH" pendant l'installation.
    echo.
    pause
    exit /b 1
)

echo [INFO] Creation du venv avec "%SYSPY%" ...
%SYSPY% -m venv .venv
if not exist "%PY%" (
    echo [ERREUR] La creation du venv a echoue.
    echo.
    pause
    exit /b 1
)

echo [INFO] Installation des dependances depuis requirements.txt ...
"%PY%" -m pip install --upgrade pip --quiet
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERREUR] Installation des dependances echouee - verifiez la connexion internet.
    echo.
    pause
    exit /b 1
)
echo [INFO] Installation terminee.
echo.

:venv_pret

REM --- Etape 2 : dependances reellement importables ? -----------------
REM  "-c import uvicorn" renvoie un code non nul si le module manque
REM  (venv incomplet, install interrompue, venv copie depuis une autre
REM  machine avec un Python d'une autre version...).
"%PY%" -c "import uvicorn, fastapi, httpx, dotenv" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Dependances manquantes - reinstallation ...
    "%PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERREUR] Reinstallation echouee.
        echo  Solution : supprimez le dossier .venv puis relancez start.bat
        echo.
        pause
        exit /b 1
    )
)

REM --- Etape 3 : fichier .env ------------------------------------------
REM  .env n'est pas versionne (il contient des cles API). On le cree a
REM  partir de .env.example pour que l'app demarre quand meme : sans cle,
REM  les prix marchent (Yahoo/CoinGecko sont publics), seuls les
REM  fondamentaux, les actualites et le calendrier restent vides.
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [INFO] .env cree depuis .env.example - pensez a y mettre vos cles API.
    )
)

REM --- Etape 4 : le port est-il deja occupe ? --------------------------
REM  Si un ancien serveur tourne encore, uvicorn planterait au demarrage.
netstat -ano | findstr ":%PORT%" | findstr LISTENING >nul 2>&1
if not errorlevel 1 (
    echo [ATTENTION] Le port %PORT% est deja utilise.
    echo  Un serveur TradeRadar tourne probablement deja.
    echo  Fermez-le avec stop.bat, puis relancez start.bat.
    echo.
    pause
    exit /b 1
)

REM --- Etape 5 : ouverture du navigateur en parallele ------------------
REM  3 secondes : laisse le temps a uvicorn de binder le port avant que
REM  le navigateur ne tape sur l'URL (sinon ERR_CONNECTION_REFUSED).
REM  Chemin absolu de timeout.exe : le "timeout" de Git/coreutils, s'il
REM  est dans le PATH, a une syntaxe incompatible avec /t.
start "" /min cmd /c "%SystemRoot%\System32\timeout.exe /t 3 /nobreak >nul && start http://localhost:%PORT%"

echo [INFO] Serveur sur http://localhost:%PORT%
echo [INFO] Appuyez sur Ctrl+C pour arreter
echo.

REM --- Etape 6 : mode dev optionnel ------------------------------------
REM  "start.bat dev" active --reload (redemarrage auto quand un .py change).
REM  Desactive par defaut : le reloader lance un 2e processus et peut rester
REM  bloque a l'arret sur Windows quand des requetes HTTP sont en cours.
set "RELOAD="
if /i "%~1"=="dev" set "RELOAD=--reload"
if defined RELOAD echo [INFO] Mode dev : rechargement auto active

REM --- Etape 7 : lancement (bloque la fenetre jusqu'a Ctrl+C) ----------
"%PY%" -m uvicorn main:app --port %PORT% %RELOAD%

REM  Si uvicorn s'arrete sur une erreur, on garde la fenetre ouverte
REM  pour que le message reste lisible.
if errorlevel 1 (
    echo.
    echo [ERREUR] Le serveur s'est arrete anormalement. Voir le message ci-dessus.
    pause
)
