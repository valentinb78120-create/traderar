# TradeRadar

Tableau de bord personnel d'investissement — actions internationales, ETFs et cryptos.

## Stack

- **Backend** : Python · FastAPI · yfinance
- **Frontend** : HTML / CSS / Vanilla JS (aucun framework)
- **Données** : yfinance, Finnhub (gratuit), CoinGecko (public)

## Installation

### 1. Cloner / télécharger le projet

```bash
cd traderar
```

### 2. Créer un environnement virtuel

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer la clé Finnhub (actualités)

1. Rendez-vous sur **https://finnhub.io** et créez un compte gratuit (< 1 minute).
2. Copiez votre clé API depuis le tableau de bord.
3. Créez un fichier `.env` à la racine du projet :

```env
FINNHUB_API_KEY=votre_cle_ici
```

> Sans cette clé, les sections Actions / Crypto fonctionnent normalement.  
> Seule la section Actualités affichera un message d'invite.

### 5. Lancer le serveur

```bash
uvicorn main:app --reload
```

Ouvrez ensuite **http://localhost:8000** dans votre navigateur.

## Endpoints API

| Méthode | Route                    | Description                          |
|---------|--------------------------|--------------------------------------|
| GET     | `/api/trending-stocks`   | Actions haussières (yfinance)        |
| GET     | `/api/news`              | Actualités marchés (Finnhub)         |
| GET     | `/api/emerging`          | Entreprises émergentes (yfinance)    |
| GET     | `/api/crypto`            | Prix crypto en EUR (CoinGecko)       |

Toutes les réponses sont mises en cache côté serveur **5 minutes** pour éviter les limites de taux.

## Personnalisation des watchlists

Modifiez directement les listes Python dans `services/stocks.py` :

```python
TRENDING_WATCHLIST = ["AAPL", "MSFT", ...]   # Tickers yfinance
EMERGING_WATCHLIST = ["PLTR", "ASML.AS", ...]
```

## Notes

- Les données sont récupérées en direct à chaque actualisation (hors cache).
- Les prix sont indicatifs — pas un conseil en investissement.
- Limites Finnhub free tier : 60 req/min · CoinGecko public : 10–30 req/min.
