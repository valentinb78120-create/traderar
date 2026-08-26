#!/usr/bin/env bash
# =====================================================================
#  TradeRadar - Lancement du serveur local (macOS / Linux)
# ---------------------------------------------------------------------
#  GUIDE :
#   - PY   : interpreteur Python DU VENV, chemin relatif au script.
#            On l'appelle directement plutot que de "source activate" :
#            les scripts d'activation contiennent un chemin ABSOLU fige
#            a la creation du venv, donc ils cassent si le dossier bouge.
#   - PORT : port HTTP du serveur (doit correspondre a l'URL ouverte)
#   - dev  : "./start.sh dev" ajoute --reload (rechargement auto des .py)
#
#  PREMIER LANCEMENT : le script cree le venv et installe requirements.txt
#  tout seul. Il suffit d'avoir Python 3.11+ installe.
#
#  Rendre executable une seule fois :  chmod +x start.sh
# =====================================================================
set -euo pipefail

# Se placer dans le dossier du script, quel que soit le repertoire courant
cd "$(dirname "$0")"

PORT=8000

# Chemin de l'interpreteur du venv : Unix le place dans .venv/bin, Windows
# (Git Bash, MSYS, Cygwin) dans .venv/Scripts. On teste les deux pour que ce
# script marche aussi depuis un terminal bash sous Windows.
detect_py() {
    if   [ -x ".venv/bin/python" ];        then PY=".venv/bin/python"
    elif [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe"
    else PY=""
    fi
}
detect_py

echo
echo " =========================================="
echo "           TradeRadar - Demarrage"
echo " =========================================="
echo

# --- Etape 1 : venv present ? sinon on l'installe --------------------
if [ -z "$PY" ]; then
    echo "[INFO] Environnement virtuel absent - installation automatique."

    # python3 d'abord (standard sur macOS/Linux), python en repli
    if command -v python3 >/dev/null 2>&1; then
        SYSPY=python3
    elif command -v python >/dev/null 2>&1; then
        SYSPY=python
    else
        echo "[ERREUR] Aucun Python trouve. Installez Python 3.11 ou plus :"
        echo "         macOS  : brew install python"
        echo "         Debian : sudo apt install python3 python3-venv"
        exit 1
    fi

    echo "[INFO] Creation du venv avec $SYSPY ..."
    "$SYSPY" -m venv .venv
    detect_py                      # le chemin n'existait pas avant la creation
    if [ -z "$PY" ]; then
        echo "[ERREUR] La creation du venv a echoue."
        exit 1
    fi

    echo "[INFO] Installation des dependances depuis requirements.txt ..."
    "$PY" -m pip install --upgrade pip --quiet
    "$PY" -m pip install -r requirements.txt
    echo "[INFO] Installation terminee."
    echo
fi

# --- Etape 2 : dependances reellement importables ? ------------------
# Un venv peut exister mais etre incomplet (install interrompue, venv copie
# depuis une autre machine avec un Python d'une autre version...).
if ! "$PY" -c "import uvicorn, fastapi, httpx, dotenv" >/dev/null 2>&1; then
    echo "[INFO] Dependances manquantes - reinstallation ..."
    "$PY" -m pip install -r requirements.txt
fi

# --- Etape 3 : fichier .env ------------------------------------------
# .env n'est pas versionne (cles API). On le cree depuis .env.example pour
# que l'app demarre quand meme : sans cle les prix marchent (Yahoo et
# CoinGecko sont publics), seuls fondamentaux/actualites/calendrier restent
# vides.
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo "[INFO] .env cree depuis .env.example - pensez a y mettre vos cles API."
fi

# --- Etape 4 : le port est-il deja occupe ? --------------------------
# Meme detection multi-outils que stop.sh : lsof (macOS / la plupart des
# Linux), fuser et ss (Linux minimalistes), netstat (Git Bash sous Windows).
# Si aucun de ces outils n'est present, on laisse simplement demarrer :
# uvicorn affichera lui-meme l'erreur "address already in use".
pids_on_port() {
    if command -v lsof >/dev/null 2>&1; then
        lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null
    elif command -v fuser >/dev/null 2>&1; then
        fuser -n tcp "$PORT" 2>/dev/null | tr -s ' ' '
' | grep -E '^[0-9]+$'
    elif command -v ss >/dev/null 2>&1; then
        ss -lptnH "sport = :$PORT" 2>/dev/null | grep -oE 'pid=[0-9]+' | cut -d= -f2
    elif command -v netstat >/dev/null 2>&1; then
        netstat -ano 2>/dev/null | grep -E "[:.]$PORT[[:space:]]"             | grep -iE 'listen' | awk '{print $NF}' | grep -E '^[0-9]+$'
    fi | sort -u
}

if [ -n "$(pids_on_port)" ]; then
    echo "[ATTENTION] Le port $PORT est deja utilise."
    echo " Un serveur TradeRadar tourne probablement deja."
    echo " Fermez-le avec ./stop.sh, puis relancez ./start.sh"
    exit 1
fi

# --- Etape 5 : ouverture du navigateur en parallele ------------------
# 3 secondes : le temps qu'uvicorn ecoute vraiment sur le port, sinon le
# navigateur affiche "connexion refusee".
(
    sleep 3
    if   command -v open     >/dev/null 2>&1; then open "http://localhost:$PORT"
    elif command -v xdg-open >/dev/null 2>&1; then xdg-open "http://localhost:$PORT"
    fi
) >/dev/null 2>&1 &

echo "[INFO] Serveur sur http://localhost:$PORT"
echo "[INFO] Appuyez sur Ctrl+C pour arreter"
echo

# --- Etape 6 : mode dev optionnel ------------------------------------
RELOAD=""
if [ "${1:-}" = "dev" ]; then
    RELOAD="--reload"
    echo "[INFO] Mode dev : rechargement auto active"
fi

# --- Etape 7 : lancement (bloque le terminal jusqu'a Ctrl+C) ---------
exec "$PY" -m uvicorn main:app --port "$PORT" $RELOAD
