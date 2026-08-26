# TradeRadar

Tableau de bord d'investissement personnel — actions internationales, ETFs et cryptomonnaies, en temps quasi réel.

> ⚠️ Outil de recherche personnel. **Pas un conseil en investissement.**

---

## En deux mots (pour tout le monde)

**Le problème que ça résout** : suivre des centaines d'actions et cryptos à la main, sur plein de sites différents, est long et pénible. TradeRadar rassemble tout au même endroit et met en avant automatiquement ce qui bouge ou qui a l'air intéressant.

**Ce que fait concrètement l'application** :
- Elle va chercher, toutes les 5 minutes, les prix de ~300 actions (Apple, LVMH, Airbus...), d'ETF et de cryptomonnaies (Bitcoin, Ethereum...) sur des sites financiers publics et gratuits.
- Elle calcule pour chaque titre un **score sur 100** (façon "note") qui combine plusieurs indicateurs boursiers classiques, pour repérer en un coup d'œil ce qui monte fort, ce qui est sous-évalué, ou ce qui approche d'un plus bas sur un an.
- Elle affiche tout ça dans un tableau de bord clair dans le navigateur : cartes, tableau compact, ou heatmap (carte de chaleur colorée) — trié, filtré par secteur ou région (Europe / USA / Asie), exportable en fichier tableur (CSV).
- Elle affiche aussi les actualités financières du jour, un calendrier économique, et permet de simuler un portefeuille fictif pour suivre des positions sans y mettre un centime réel.
- Elle fonctionne **en local, sur votre ordinateur** : aucune donnée personnelle n'est envoyée où que ce soit, il n'y a pas de compte à créer.

**Comment on la fait tourner** : on double-clique sur un fichier (`start.bat` sous Windows, ou une commande sous Mac/Linux), et l'application s'installe et se lance toute seule, puis s'ouvre automatiquement dans le navigateur à l'adresse `http://localhost:8000` (c'est l'adresse "chez moi, sur ma machine" — rien ne sort sur Internet).

**Ce que ça montre comme compétences** (pour un recruteur) : construire une application complète de bout en bout — un serveur qui va chercher et combine des données de plusieurs sources externes en temps réel, les traite avec des calculs financiers (indicateurs techniques), et les restitue dans une interface web réactive — tout en la rendant installable en une seule commande sur n'importe quel ordinateur, sans connaissance technique requise de la part de l'utilisateur final.

---

## Démarrage rapide (pour l'installer soi-même)

**Prérequis : Python 3.10 ou plus** (langage de programmation gratuit — [python.org/downloads](https://www.python.org/downloads/) si besoin). Pas d'autre logiciel à installer : le script s'occupe du reste tout seul au premier lancement (il télécharge et installe les quelques bibliothèques nécessaires).

### Windows
Double-cliquez sur `start.bat` (ou lancez-le depuis un terminal).

### macOS / Linux
Dans un terminal, à la racine du projet :
```bash
chmod +x start.sh   # une seule fois, autorise le script à s'exécuter
./start.sh
```

Le navigateur s'ouvre tout seul sur **http://localhost:8000** après quelques secondes.

Pour arrêter : `Ctrl+C` dans la fenêtre du serveur, ou `stop.bat` / `./stop.sh`.

Pour développer avec rechargement automatique à chaque modification d'un fichier `.py` :
```
start.bat dev        # Windows
./start.sh dev       # macOS / Linux
```

<details>
<summary>Installation manuelle, étape par étape (si vous préférez tout faire vous-même)</summary>

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt   # Windows
.venv/bin/python -m pip install -r requirements.txt           # macOS / Linux
cp .env.example .env
python -m uvicorn main:app --port 8000
```
</details>

---

## Clé API (facultative)

L'application fonctionne **sans aucune clé à créer** : les prix, graphiques, indicateurs techniques, cryptomonnaies et fondamentaux (capitalisation, P/E, dividende, croissance du chiffre d'affaires) passent par Yahoo Finance et CoinGecko, deux services publics et gratuits qui ne demandent pas d'inscription — et ce pour n'importe quel marché (US, Europe, Asie).

Une clé **Finnhub** (service gratuit, inscription en moins d'une minute sur https://finnhub.io) débloque en plus :

- les actualités des marchés et l'analyse de sentiment (positif/négatif),
- le calendrier économique et les publications de résultats trimestriels,
- des fondamentaux légèrement plus précis sur les valeurs américaines (source utilisée en priorité quand la clé est présente, avec Yahoo Finance en repli partout ailleurs).

Pour l'activer, ouvrez le fichier `.env` (créé automatiquement au premier lancement) et collez votre clé :

```env
FINNHUB_API_KEY=votre_cle
```

Sans clé, ces sections affichent simplement un message d'invite — rien ne casse, le reste de l'application fonctionne normalement.

---

## Fonctionnalités

| Section | Contenu |
|---|---|
| **Actions en forme** | Opportunités haussières du jour, triables par score, variation, perf 1 mois, capitalisation, P/E |
| **Top mouvements** | Plus fortes hausses et baisses de la séance |
| **Entreprises émergentes** | Univers biotech / tech / semi-conducteurs à plus fort potentiel |
| **Tout voir** | L'univers complet (295 titres : US, Europe, Asie), filtrable par région et secteur |
| **Cryptomonnaies** | Prix en EUR, dominance BTC/ETH, capitalisation globale, fiche détaillée par coin |
| **Actualités** | Flux marchés avec score de sentiment calculé sur les titres |
| **Calendrier** | Événements macro et publications de résultats à venir |
| **Portefeuille simulé** | Suivi de positions fictives et de leur performance |
| **Watchlist** | Vos tickers favoris, persistés dans le navigateur |

Et aussi : indicateurs techniques (RSI, MACD, moyennes mobiles, Bollinger, ATR, ADX, OBV, MFI, CMF, divergences — les outils classiques d'analyse technique boursière), sparklines 30 jours (mini-graphiques), position dans la fourchette 52 semaines (plus haut/plus bas de l'année), conversion automatique en euros de toutes les devises, 3 modes d'affichage (cartes / compact / heatmap), export CSV, et **PWA installable** (l'application peut s'ajouter comme une icône sur le bureau ou le téléphone, et reste consultable même hors connexion grâce à un cache local).

---

## Comment ça marche techniquement (stack)

- **Backend** — Python 3.10+ · FastAPI (framework web) · httpx (appels réseau asynchrones, c'est-à-dire que le serveur peut interroger plusieurs sources en même temps sans attendre l'une après l'autre)
- **Frontend** — HTML / CSS / JavaScript "vanilla" (sans framework comme React ou Vue : du code simple et direct, zéro étape de compilation)
- **Sources de données** — Yahoo Finance (prix, historique 1 an, fondamentaux), Finnhub (fondamentaux US en priorité si une clé est fournie, actualités, calendrier), CoinGecko (cryptomonnaies), open.er-api.com (taux de change)
- **PWA** — service worker (petit programme qui tourne en arrière-plan dans le navigateur pour gérer le cache et le mode hors ligne), manifest (fichier qui décrit l'app pour qu'elle soit installable)

Aucune base de données : tout est gardé en mémoire vive le temps d'une session (5 minutes pour les prix, 24 heures pour les fondamentaux), pour rester sous les limites de requêtes des services gratuits sans avoir besoin d'un serveur de stockage.

---

## API (les "routes" que le serveur expose)

Une API, ici, est simplement une liste d'adresses internes auxquelles le frontend (l'affichage) demande des données au backend (le serveur). Chaque ligne ci-dessous est une de ces adresses.

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/trending-stocks` | Actions haussières du jour |
| GET | `/api/top-movers` | Plus fortes hausses / baisses |
| GET | `/api/emerging` | Entreprises émergentes |
| GET | `/api/all-universe` | Univers complet |
| GET | `/api/stock-detail/{symbol}` | Fiche détaillée + historique + indicateurs |
| GET | `/api/search?q=` | Recherche de tickers |
| GET | `/api/watchlist?symbols=` | Cotations d'une liste de tickers |
| GET | `/api/indices` | Indices boursiers mondiaux |
| GET | `/api/forex` | Taux de change |
| GET | `/api/news` | Actualités + sentiment |
| GET | `/api/market-context` | VIX, sentiment macro, intensité de crise |
| GET | `/api/calendar` | Calendrier économique et résultats |
| GET | `/api/crypto` | Prix cryptos en EUR |
| GET | `/api/crypto-global` | Dominance BTC/ETH, cap. globale |
| GET | `/api/crypto-detail/{coin_id}` | Fiche détaillée d'une crypto |

Toutes les réponses suivent la forme `{"status": "ok", "data": ...}`.

---

## Personnalisation

Les univers de titres sont de simples listes Python dans `services/stocks.py` :

```python
TRENDING_WATCHLIST = [   # 188 valeurs : le coeur du dashboard
    {"symbol": "AI.PA", "name": "Air Liquide", "sector": "Industrie", "currency": "EUR", "tr": True},
    # ...
]

EMERGING_WATCHLIST = [   # 109 valeurs : biotech, tech, semi-conducteurs
    # ...
]
```

`tr: True` signale les titres disponibles sur Trade Republic (un lien direct
apparaît alors sur la fiche).

Ajoutez vos propres tickers au format Yahoo Finance (`AAPL`, `AIR.PA`, `SAP.DE`, `7203.T`...).

---

## Structure du projet

```
traderadar/
├── main.py              # Routes FastAPI + service des fichiers statiques
├── services/
│   ├── stocks.py        # Yahoo Finance, Finnhub, indicateurs, scoring
│   ├── crypto.py        # CoinGecko, forex
│   └── news.py          # Actualités et analyse de sentiment
├── static/
│   ├── index.html
│   ├── app.js           # Toute la logique front
│   ├── style.css
│   └── sw.js            # Service worker (PWA)
├── start.bat / start.sh # Lancement + installation automatique
├── stop.bat  / stop.sh  # Arrêt du serveur
└── requirements.txt      # Liste des bibliothèques Python nécessaires
```

---

## Limites connues

- Plan gratuit Finnhub : 60 requêtes/minute, utilisé uniquement pour les actualités et le calendrier (facultatifs) et en complément optionnel des fondamentaux US.
- Les fondamentaux via Yahoo Finance (source par défaut, sans clé) ne sont pas disponibles à 100 % : les ETF n'ont pas de P/E par nature, et quelques titres isolés renvoient des champs vides selon le moment de la requête — le titre affiche alors « Fondamentaux non disponibles ».
- CoinGecko public : 10 à 30 requêtes/minute.
- Les prix sont indicatifs et peuvent accuser quelques minutes de retard.
