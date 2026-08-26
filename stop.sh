#!/usr/bin/env bash
# =====================================================================
#  TradeRadar - Arret du serveur (macOS / Linux, et Git Bash sous Windows)
#  Tue le processus qui ecoute sur le port defini ci-dessous.
# =====================================================================
PORT=8000

# Liste les PID qui ecoutent sur $PORT.
# On essaie plusieurs outils : lsof (macOS/la plupart des Linux), fuser et ss
# (Linux minimalistes ou lsof absent), netstat (Git Bash sous Windows).
pids_on_port() {
    if command -v lsof >/dev/null 2>&1; then
        lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null
    elif command -v fuser >/dev/null 2>&1; then
        fuser -n tcp "$PORT" 2>/dev/null | tr -s ' ' '\n' | grep -E '^[0-9]+$'
    elif command -v ss >/dev/null 2>&1; then
        ss -lptnH "sport = :$PORT" 2>/dev/null | grep -oE 'pid=[0-9]+' | cut -d= -f2
    elif command -v netstat >/dev/null 2>&1; then
        # Windows : "netstat -ano" met le PID en derniere colonne
        netstat -ano 2>/dev/null | grep -E "[:.]$PORT[[:space:]]" \
            | grep -iE 'listen' | awk '{print $NF}' | grep -E '^[0-9]+$'
    fi | sort -u
}

echo
echo " Arret des processus TradeRadar..."
echo

PIDS=$(pids_on_port)

if [ -z "$PIDS" ]; then
    echo " Aucun serveur en ecoute sur le port $PORT."
    exit 0
fi

for pid in $PIDS; do
    echo "[INFO] Arret du processus PID $pid"
    # taskkill d'abord sous Windows : le "kill" de Git Bash ne gere pas les
    # PID Windows natifs. Sur Unix, taskkill n'existe pas -> on passe a kill.
    if command -v taskkill >/dev/null 2>&1; then
        taskkill //F //T //PID "$pid" >/dev/null 2>&1 || kill "$pid" 2>/dev/null || true
    else
        kill "$pid" 2>/dev/null || true
    fi
done

# 2 s pour un arret propre, puis on force ce qui reste (Unix uniquement)
sleep 2
for pid in $PIDS; do
    if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
    fi
done

echo
echo " Serveur arrete."
