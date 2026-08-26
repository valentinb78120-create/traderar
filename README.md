# TradeRadar

Tableau de bord d'investissement personnel — actions internationales, ETFs et cryptomonnaies, en temps quasi réel.

Application web locale : un backend **FastAPI** agrège plusieurs sources de marché publiques, un front **vanilla JS sans framework** les affiche. Aucune donnée ne quitte votre machine.

> ⚠️ Outil de recherche personnel. **Pas un conseil en investissement.**

---

## Démarrage rapide

**Prérequis : Python 3.10 ou plus.** C'est tout — les scripts créent l'environnement virtuel et installent les dépendances au premier lancement.

### Windows
```
start.bat
```
(double-clic, ou depuis un terminal)

### macOS / Linux
```bash
chmod +x start.sh   # une seule fois
./start.sh
```

Le navigateur s'ouvre automatiquement sur **http://localhost:8000**.

Pour arrêter : `Ctrl+C` dans la fenêtre, ou `stop.bat` / `./stop.sh`.

Pour développer avec rechargement automatique à chaque modification d'un `.py` :
```
start.bat dev        # Windows
./start.sh dev       # macOS / Linux
```

<details>
<summary>Installation manuelle (si vous préférez)</summary>

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

L'application fonctionne **sans aucune clé** : prix, graphiques, indicateurs techniques et cryptos passent par Yahoo Finance et CoinGecko, qui sont publics.

Une clé **Finnhub** gratuite (https://finnhub.io, inscription en moins d'une minute) débloque en plus :

- les actualités des marchés et l'analyse de sentiment,
- les fondamentaux : capitalisation, P/E, rendement du dividende, croissance du CA,
- le calendrier économique et les publications de résultats.

Renseignez-la dans le fichier `.env` (créé automatiquement au premier lancement) :

```env
FINNHUB_API_KEY=votre_cle
```

Sans clé, ces sections affichent simplement un message d'invite — rien ne casse.

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

Et aussi : indicateurs techniques (RSI, MACD, moyennes mobiles, Bollinger, ATR, ADX, OBV, MFI, CMF, divergences), sparklines 30 jours, position dans la fourchette 52 semaines, conversion EUR de toutes les devises, 3 modes d'affichage (cartes / compact / heatmap), export CSV, et **PWA installable** (service worker, fonctionne en lecture hors ligne).

---

## Stack

- **Backend** — Python 3.10+ · FastAPI · httpx (appels asynchrones et parallélisés)
- **Frontend** — HTML / CSS / JavaScript vanilla, zéro dépendance, zéro build
- **Données** — Yahoo Finance (prix + historique 1 an), Finnhub (fondamentaux, news, calendrier), CoinGecko (cryptos), open.er-api.com (taux de change)
- **PWA** — service worker (cache-first pour le shell, network-first pour l'API), manifest

Aucune base de données : tout est mis en cache en mémoire (5 min pour les prix, 24 h pour les fondamentaux) afin de rester sous les limites de taux des API gratuites.

---

## API

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
apparait alors sur la fiche).

Ajoutez vos propres tickers au format Yahoo Finance (`AAPL`, `AIR.PA`, `SAP.DE`, `7203.T`...).

---

## Structure

```
traderar/
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
└── requirements.txt
```

---

## Limites connues

- Plan gratuit Finnhub : 60 requêtes/minute et **fondamentaux US uniquement** (les valeurs européennes et asiatiques affichent « Fondamentaux non disponibles »).
- CoinGecko public : 10 à 30 requêtes/minute.
- Les prix sont indicatifs et peuvent accuser quelques minutes de retard.
