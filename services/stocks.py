"""Service stocks — combine Yahoo (prix + fondamentaux) + Finnhub (fondamentaux US, sentiment).

Sources :
- Yahoo Finance v8 chart : prix, history 1 an, 52S, devise (tous marchés, gratuit, sans clé)
- Finnhub /stock/profile2 + /stock/metric : marketCap, P/E, dividende, croissance
  (US uniquement sur le plan gratuit ; EU/Asie renverra 403)
- Yahoo Finance quoteSummary : mêmes fondamentaux que Finnhub, en repli — gratuit,
  sans clé, TOUS marchés. Utilisé quand Finnhub est absent/indisponible/hors US,
  ce qui couvre le cas d'un utilisateur qui vient de cloner le projet sans clé API.
"""
import asyncio
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

_cache: dict = {}
_fundamentals_cache: dict = {}
_sentiment_cache: dict = {}
_market_context = {"vix": None, "ts": 0}
_fetch_lock = asyncio.Lock()  # évite que plusieurs endpoints fetchent en parallèle
CACHE_TTL = 300           # 5 min pour les prix
FUNDAMENTALS_TTL = 86400  # 24 h pour les fondamentaux
SENTIMENT_TTL = 3600      # 1 h pour sentiment news + analystes

# Valeurs "gabarit" presentes dans .env.example : si l'utilisateur n'a pas
# encore remplace le texte, la cle est consideree comme ABSENTE. Sans ca,
# l'API repond 401 et l'app affiche "Finnhub a repondu 401" au lieu du message
# clair "ajoutez votre cle dans .env".
_PLACEHOLDERS = {"votre_cle_ici", "your_key_here", "changeme", "xxx", "none"}


def _clean_key(name: str) -> str:
    """Lit une variable d'environnement, en ignorant les valeurs gabarit."""
    val = (os.getenv(name) or "").strip().strip('"').strip("'")
    return "" if val.lower() in _PLACEHOLDERS else val
FINNHUB_API_KEY = _clean_key("FINNHUB_API_KEY")
FINNHUB_BASE    = "https://finnhub.io/api/v1"

# Rate limiting Finnhub (free tier = 60 req/min).
# Sans garde-fou, un demarrage a froid (~300 tickers x 3 appels) explose le quota
# → timeouts en cascade + 429 sur les news. Semaphore + cooldown global.
_finnhub_sem = asyncio.Semaphore(3)
_finnhub_cooldown_until = 0.0


async def _finnhub_get(client: httpx.AsyncClient, path: str, params: dict) -> httpx.Response | None:
    """GET Finnhub avec limitation de concurrence et cooldown global sur 429.
    Retourne None si indisponible (cooldown actif, rate limit, erreur reseau)."""
    global _finnhub_cooldown_until
    if not FINNHUB_API_KEY or time.time() < _finnhub_cooldown_until:
        return None
    async with _finnhub_sem:
        if time.time() < _finnhub_cooldown_until:
            return None
        try:
            r = await client.get(f"{FINNHUB_BASE}{path}",
                                 params={**params, "token": FINNHUB_API_KEY},
                                 timeout=8)
        except Exception as exc:
            print(f"[stocks] Finnhub {path} erreur reseau: {exc!r}")
            return None
        if r.status_code == 429:
            _finnhub_cooldown_until = time.time() + 90
            print("[stocks] Finnhub rate limit (429) - pause 90s, les donnees se rempliront progressivement")
            return None
        return r
YAHOO_BASE      = "https://query1.finance.yahoo.com/v8/finance/chart"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


TRENDING_WATCHLIST = [
    # ═══════════ CAC 40 (FR) — sur TR ═══════════
    {"symbol": "AI.PA",   "name": "Air Liquide",        "sector": "Industrie",         "currency": "EUR", "tr": True},
    {"symbol": "AIR.PA",  "name": "Airbus",             "sector": "Aérospatial",       "currency": "EUR", "tr": True},
    {"symbol": "BN.PA",   "name": "Danone",             "sector": "Consommation",      "currency": "EUR", "tr": True},
    {"symbol": "BNP.PA",  "name": "BNP Paribas",        "sector": "Finance",           "currency": "EUR", "tr": True},
    {"symbol": "BVI.PA",  "name": "Bureau Veritas",     "sector": "Services",          "currency": "EUR", "tr": True},
    {"symbol": "CA.PA",   "name": "Carrefour",          "sector": "Distribution",      "currency": "EUR", "tr": True},
    {"symbol": "CAP.PA",  "name": "Capgemini",          "sector": "Tech",              "currency": "EUR", "tr": True},
    {"symbol": "DG.PA",   "name": "Vinci",              "sector": "Construction",      "currency": "EUR", "tr": True},
    {"symbol": "EL.PA",   "name": "EssilorLuxottica",   "sector": "Consommation",      "currency": "EUR", "tr": True},
    {"symbol": "EN.PA",   "name": "Bouygues",           "sector": "Construction",      "currency": "EUR", "tr": True},
    {"symbol": "ENGI.PA", "name": "Engie",              "sector": "Énergie",           "currency": "EUR", "tr": True},
    {"symbol": "GLE.PA",  "name": "Société Générale",   "sector": "Finance",           "currency": "EUR", "tr": True},
    {"symbol": "HO.PA",   "name": "Thales",             "sector": "Aérospatial",       "currency": "EUR", "tr": True},
    {"symbol": "KER.PA",  "name": "Kering",             "sector": "Luxe",              "currency": "EUR", "tr": True},
    {"symbol": "LR.PA",   "name": "Legrand",            "sector": "Industrie",         "currency": "EUR", "tr": True},
    {"symbol": "MC.PA",   "name": "LVMH",               "sector": "Luxe",              "currency": "EUR", "tr": True},
    {"symbol": "ML.PA",   "name": "Michelin",           "sector": "Industrie",         "currency": "EUR", "tr": True},
    {"symbol": "OR.PA",   "name": "L'Oréal",            "sector": "Consommation",      "currency": "EUR", "tr": True},
    {"symbol": "ORA.PA",  "name": "Orange",             "sector": "Télécoms",          "currency": "EUR", "tr": True},
    {"symbol": "RI.PA",   "name": "Pernod Ricard",      "sector": "Consommation",      "currency": "EUR", "tr": True},
    {"symbol": "RMS.PA",  "name": "Hermès",             "sector": "Luxe",              "currency": "EUR", "tr": True},
    {"symbol": "SAF.PA",  "name": "Safran",             "sector": "Aérospatial",       "currency": "EUR", "tr": True},
    {"symbol": "SAN.PA",  "name": "Sanofi",             "sector": "Pharma",            "currency": "EUR", "tr": True},
    {"symbol": "SU.PA",   "name": "Schneider Electric", "sector": "Industrie",         "currency": "EUR", "tr": True},
    {"symbol": "TTE.PA",  "name": "TotalEnergies",      "sector": "Énergie",           "currency": "EUR", "tr": True},
    {"symbol": "PUB.PA",  "name": "Publicis",           "sector": "Communication",     "currency": "EUR", "tr": True},
    {"symbol": "VIE.PA",  "name": "Veolia",             "sector": "Services",          "currency": "EUR", "tr": True},
    {"symbol": "ACA.PA",  "name": "Crédit Agricole",    "sector": "Finance",           "currency": "EUR", "tr": True},
    {"symbol": "STMPA.PA","name": "STMicroelectronics", "sector": "Semi-conducteurs",  "currency": "EUR", "tr": True},

    # ═══════════ S&P 500 / NASDAQ — top 40 ═══════════
    {"symbol": "AAPL",    "name": "Apple Inc.",         "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "MSFT",    "name": "Microsoft",          "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "NVDA",    "name": "NVIDIA",             "sector": "Semi-conducteurs",  "currency": "USD", "tr": True},
    {"symbol": "GOOGL",   "name": "Alphabet (A)",       "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "META",    "name": "Meta Platforms",     "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "AMZN",    "name": "Amazon",             "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "TSLA",    "name": "Tesla",              "sector": "Automobile",        "currency": "USD", "tr": True},
    {"symbol": "BRK-B",   "name": "Berkshire Hathaway", "sector": "Finance",           "currency": "USD", "tr": True},
    {"symbol": "LLY",     "name": "Eli Lilly",          "sector": "Pharma",            "currency": "USD", "tr": True},
    {"symbol": "JPM",     "name": "JPMorgan Chase",     "sector": "Finance",           "currency": "USD", "tr": True},
    {"symbol": "V",       "name": "Visa Inc.",          "sector": "Finance",           "currency": "USD", "tr": True},
    {"symbol": "MA",      "name": "Mastercard",         "sector": "Finance",           "currency": "USD", "tr": True},
    {"symbol": "COST",    "name": "Costco",             "sector": "Distribution",      "currency": "USD", "tr": True},
    {"symbol": "WMT",     "name": "Walmart",            "sector": "Distribution",      "currency": "USD", "tr": True},
    {"symbol": "HD",      "name": "Home Depot",         "sector": "Distribution",      "currency": "USD", "tr": True},
    {"symbol": "JNJ",     "name": "Johnson & Johnson",  "sector": "Pharma",            "currency": "USD", "tr": True},
    {"symbol": "PG",      "name": "Procter & Gamble",   "sector": "Consommation",      "currency": "USD", "tr": True},
    {"symbol": "UNH",     "name": "UnitedHealth",       "sector": "Santé",             "currency": "USD", "tr": True},
    {"symbol": "ABBV",    "name": "AbbVie",             "sector": "Pharma",            "currency": "USD", "tr": True},
    {"symbol": "MRK",     "name": "Merck",              "sector": "Pharma",            "currency": "USD", "tr": True},
    {"symbol": "PFE",     "name": "Pfizer",             "sector": "Pharma",            "currency": "USD", "tr": True},
    {"symbol": "KO",      "name": "Coca-Cola",          "sector": "Consommation",      "currency": "USD", "tr": True},
    {"symbol": "PEP",     "name": "PepsiCo",            "sector": "Consommation",      "currency": "USD", "tr": True},
    {"symbol": "MCD",     "name": "McDonald's",         "sector": "Consommation",      "currency": "USD", "tr": True},
    {"symbol": "SBUX",    "name": "Starbucks",          "sector": "Consommation",      "currency": "USD", "tr": True},
    {"symbol": "NKE",     "name": "Nike",               "sector": "Consommation",      "currency": "USD", "tr": True},
    {"symbol": "DIS",     "name": "Disney",             "sector": "Communication",     "currency": "USD", "tr": True},
    {"symbol": "NFLX",    "name": "Netflix",            "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "ORCL",    "name": "Oracle",             "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "CSCO",    "name": "Cisco",              "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "ADBE",    "name": "Adobe",              "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "INTC",    "name": "Intel",              "sector": "Semi-conducteurs",  "currency": "USD", "tr": True},
    {"symbol": "QCOM",    "name": "Qualcomm",           "sector": "Semi-conducteurs",  "currency": "USD", "tr": True},
    {"symbol": "AVGO",    "name": "Broadcom",           "sector": "Semi-conducteurs",  "currency": "USD", "tr": True},
    {"symbol": "TXN",     "name": "Texas Instruments",  "sector": "Semi-conducteurs",  "currency": "USD", "tr": True},
    {"symbol": "BAC",     "name": "Bank of America",    "sector": "Finance",           "currency": "USD", "tr": True},
    {"symbol": "GS",      "name": "Goldman Sachs",      "sector": "Finance",           "currency": "USD", "tr": True},
    {"symbol": "MS",      "name": "Morgan Stanley",     "sector": "Finance",           "currency": "USD", "tr": True},
    {"symbol": "C",       "name": "Citigroup",          "sector": "Finance",           "currency": "USD", "tr": True},
    {"symbol": "WFC",     "name": "Wells Fargo",        "sector": "Finance",           "currency": "USD", "tr": True},
    {"symbol": "XOM",     "name": "ExxonMobil",         "sector": "Énergie",           "currency": "USD", "tr": True},
    {"symbol": "CVX",     "name": "Chevron",            "sector": "Énergie",           "currency": "USD", "tr": True},
    {"symbol": "BA",      "name": "Boeing",             "sector": "Aérospatial",       "currency": "USD", "tr": True},
    {"symbol": "CAT",     "name": "Caterpillar",        "sector": "Industrie",         "currency": "USD", "tr": True},
    {"symbol": "GE",      "name": "General Electric",   "sector": "Industrie",         "currency": "USD", "tr": True},
    {"symbol": "MMM",     "name": "3M",                 "sector": "Industrie",         "currency": "USD", "tr": True},
    {"symbol": "IBM",     "name": "IBM",                "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "GM",      "name": "General Motors",     "sector": "Automobile",        "currency": "USD", "tr": True},
    {"symbol": "F",       "name": "Ford",               "sector": "Automobile",        "currency": "USD", "tr": True},

    # ═══════════ DAX (DE) ═══════════
    {"symbol": "SAP.DE",  "name": "SAP SE",             "sector": "Tech",              "currency": "EUR", "tr": True},
    {"symbol": "SIE.DE",  "name": "Siemens",            "sector": "Industrie",         "currency": "EUR", "tr": True},
    {"symbol": "ALV.DE",  "name": "Allianz",            "sector": "Assurance",         "currency": "EUR", "tr": True},
    {"symbol": "ADS.DE",  "name": "Adidas",             "sector": "Consommation",      "currency": "EUR", "tr": True},
    {"symbol": "DBK.DE",  "name": "Deutsche Bank",      "sector": "Finance",           "currency": "EUR", "tr": True},
    {"symbol": "BMW.DE",  "name": "BMW",                "sector": "Automobile",        "currency": "EUR", "tr": True},
    {"symbol": "MBG.DE",  "name": "Mercedes-Benz",      "sector": "Automobile",        "currency": "EUR", "tr": True},
    {"symbol": "VOW3.DE", "name": "Volkswagen",         "sector": "Automobile",        "currency": "EUR", "tr": True},
    {"symbol": "BAS.DE",  "name": "BASF",               "sector": "Chimie",            "currency": "EUR", "tr": True},
    {"symbol": "BAYN.DE", "name": "Bayer",              "sector": "Pharma",            "currency": "EUR", "tr": True},
    {"symbol": "DTE.DE",  "name": "Deutsche Telekom",   "sector": "Télécoms",          "currency": "EUR", "tr": True},
    {"symbol": "DPW.DE",  "name": "DHL Group",          "sector": "Logistique",        "currency": "EUR", "tr": True},
    {"symbol": "MUV2.DE", "name": "Munich Re",          "sector": "Assurance",         "currency": "EUR", "tr": True},
    {"symbol": "IFX.DE",  "name": "Infineon",           "sector": "Semi-conducteurs",  "currency": "EUR", "tr": True},
    {"symbol": "RWE.DE",  "name": "RWE",                "sector": "Énergie",           "currency": "EUR", "tr": True},
    {"symbol": "EOAN.DE", "name": "E.ON",               "sector": "Énergie",           "currency": "EUR", "tr": True},

    # ═══════════ FTSE 100 (UK) ═══════════
    {"symbol": "AZN.L",   "name": "AstraZeneca",        "sector": "Pharma",            "currency": "GBP", "tr": True},
    {"symbol": "SHEL.L",  "name": "Shell",              "sector": "Énergie",           "currency": "GBP", "tr": True},
    {"symbol": "HSBA.L",  "name": "HSBC Holdings",      "sector": "Finance",           "currency": "GBP", "tr": True},
    {"symbol": "BP.L",    "name": "BP",                 "sector": "Énergie",           "currency": "GBP", "tr": True},
    {"symbol": "ULVR.L",  "name": "Unilever",           "sector": "Consommation",      "currency": "GBP", "tr": True},
    {"symbol": "GSK.L",   "name": "GSK",                "sector": "Pharma",            "currency": "GBP", "tr": True},
    {"symbol": "RIO.L",   "name": "Rio Tinto",          "sector": "Mines",             "currency": "GBP", "tr": True},
    {"symbol": "BARC.L",  "name": "Barclays",           "sector": "Finance",           "currency": "GBP", "tr": True},
    {"symbol": "VOD.L",   "name": "Vodafone",           "sector": "Télécoms",          "currency": "GBP", "tr": True},

    # ═══════════ SMI (CH) ═══════════
    {"symbol": "ROG.SW",  "name": "Roche",              "sector": "Pharma",            "currency": "CHF", "tr": True},
    {"symbol": "NESN.SW", "name": "Nestlé",             "sector": "Consommation",      "currency": "CHF", "tr": True},
    {"symbol": "NOVN.SW", "name": "Novartis",           "sector": "Pharma",            "currency": "CHF", "tr": True},
    {"symbol": "UBSG.SW", "name": "UBS",                "sector": "Finance",           "currency": "CHF", "tr": True},

    # ═══════════ Pays-Bas / Espagne / Italie ═══════════
    {"symbol": "ASML.AS", "name": "ASML Holding",       "sector": "Semi-conducteurs",  "currency": "EUR", "tr": True},
    {"symbol": "INGA.AS", "name": "ING Groep",          "sector": "Finance",           "currency": "EUR", "tr": True},
    {"symbol": "PHIA.AS", "name": "Philips",            "sector": "Santé",             "currency": "EUR", "tr": True},
    {"symbol": "AD.AS",   "name": "Ahold Delhaize",     "sector": "Distribution",      "currency": "EUR", "tr": True},
    {"symbol": "SAN.MC",  "name": "Santander",          "sector": "Finance",           "currency": "EUR", "tr": True},
    {"symbol": "BBVA.MC", "name": "BBVA",               "sector": "Finance",           "currency": "EUR", "tr": True},
    {"symbol": "IBE.MC",  "name": "Iberdrola",          "sector": "Énergie",           "currency": "EUR", "tr": True},
    {"symbol": "ITX.MC",  "name": "Inditex (Zara)",     "sector": "Consommation",      "currency": "EUR", "tr": True},
    {"symbol": "ENI.MI",  "name": "ENI",                "sector": "Énergie",           "currency": "EUR", "tr": True},
    {"symbol": "ISP.MI",  "name": "Intesa Sanpaolo",    "sector": "Finance",           "currency": "EUR", "tr": True},
    {"symbol": "STLA.MI", "name": "Stellantis",         "sector": "Automobile",        "currency": "EUR", "tr": True},
    {"symbol": "NOVO-B.CO","name": "Novo Nordisk",      "sector": "Pharma",            "currency": "DKK", "tr": True},
    {"symbol": "MAERSK-B.CO","name": "Maersk",          "sector": "Logistique",        "currency": "DKK", "tr": True},

    # ═══════════ Japon (TSE) — PAS sur TR ═══════════
    {"symbol": "7203.T",  "name": "Toyota Motor",       "sector": "Automobile",        "currency": "JPY", "tr": False},
    {"symbol": "6758.T",  "name": "Sony Group",         "sector": "Tech",              "currency": "JPY", "tr": False},
    {"symbol": "9984.T",  "name": "SoftBank Group",     "sector": "Tech",              "currency": "JPY", "tr": False},
    {"symbol": "7974.T",  "name": "Nintendo",           "sector": "Tech",              "currency": "JPY", "tr": False},
    {"symbol": "8306.T",  "name": "Mitsubishi UFJ",     "sector": "Finance",           "currency": "JPY", "tr": False},
    {"symbol": "6861.T",  "name": "Keyence",            "sector": "Tech",              "currency": "JPY", "tr": False},
    {"symbol": "6098.T",  "name": "Recruit Holdings",   "sector": "Services",          "currency": "JPY", "tr": False},

    # ═══════════ Hong Kong / Chine — PAS sur TR ═══════════
    {"symbol": "0700.HK", "name": "Tencent",            "sector": "Tech",              "currency": "HKD", "tr": False},
    {"symbol": "9988.HK", "name": "Alibaba (HK)",       "sector": "Tech",              "currency": "HKD", "tr": False},
    {"symbol": "3690.HK", "name": "Meituan",            "sector": "Tech",              "currency": "HKD", "tr": False},
    {"symbol": "1299.HK", "name": "AIA Group",          "sector": "Assurance",         "currency": "HKD", "tr": False},

    # ═══════════ US Mid Caps / Tech additionnels ═══════════
    {"symbol": "T",       "name": "AT&T",               "sector": "Télécoms",          "currency": "USD", "tr": True},
    {"symbol": "VZ",      "name": "Verizon",            "sector": "Télécoms",          "currency": "USD", "tr": True},
    {"symbol": "TMUS",    "name": "T-Mobile",           "sector": "Télécoms",          "currency": "USD", "tr": True},
    {"symbol": "CMCSA",   "name": "Comcast",            "sector": "Communication",     "currency": "USD", "tr": True},
    {"symbol": "PYPL",    "name": "PayPal",             "sector": "Fintech",           "currency": "USD", "tr": True},
    {"symbol": "BLK",     "name": "BlackRock",          "sector": "Finance",           "currency": "USD", "tr": True},
    {"symbol": "AXP",     "name": "American Express",   "sector": "Finance",           "currency": "USD", "tr": True},
    {"symbol": "SCHW",    "name": "Charles Schwab",     "sector": "Finance",           "currency": "USD", "tr": True},
    {"symbol": "USB",     "name": "US Bancorp",         "sector": "Finance",           "currency": "USD", "tr": True},
    {"symbol": "PNC",     "name": "PNC Financial",      "sector": "Finance",           "currency": "USD", "tr": True},
    {"symbol": "TGT",     "name": "Target",             "sector": "Distribution",      "currency": "USD", "tr": True},
    {"symbol": "LOW",     "name": "Lowe's",             "sector": "Distribution",      "currency": "USD", "tr": True},
    {"symbol": "CVS",     "name": "CVS Health",         "sector": "Santé",             "currency": "USD", "tr": True},
    {"symbol": "WBA",     "name": "Walgreens",          "sector": "Santé",             "currency": "USD", "tr": True},
    {"symbol": "ABT",     "name": "Abbott Labs",        "sector": "Santé",             "currency": "USD", "tr": True},
    {"symbol": "TMO",     "name": "Thermo Fisher",      "sector": "Santé",             "currency": "USD", "tr": True},
    {"symbol": "DHR",     "name": "Danaher",            "sector": "Santé",             "currency": "USD", "tr": True},
    {"symbol": "BMY",     "name": "Bristol-Myers Squibb","sector": "Pharma",           "currency": "USD", "tr": True},
    {"symbol": "AMGN",    "name": "Amgen",              "sector": "Biotech",           "currency": "USD", "tr": True},
    {"symbol": "GILD",    "name": "Gilead Sciences",    "sector": "Biotech",           "currency": "USD", "tr": True},
    {"symbol": "CI",      "name": "Cigna",              "sector": "Santé",             "currency": "USD", "tr": True},
    {"symbol": "HUM",     "name": "Humana",             "sector": "Santé",             "currency": "USD", "tr": True},
    {"symbol": "LMT",     "name": "Lockheed Martin",    "sector": "Aérospatial",       "currency": "USD", "tr": True},
    {"symbol": "RTX",     "name": "RTX (Raytheon)",     "sector": "Aérospatial",       "currency": "USD", "tr": True},
    {"symbol": "NOC",     "name": "Northrop Grumman",   "sector": "Aérospatial",       "currency": "USD", "tr": True},
    {"symbol": "GD",      "name": "General Dynamics",   "sector": "Aérospatial",       "currency": "USD", "tr": True},
    {"symbol": "HON",     "name": "Honeywell",          "sector": "Industrie",         "currency": "USD", "tr": True},
    {"symbol": "DE",      "name": "John Deere",         "sector": "Industrie",         "currency": "USD", "tr": True},
    {"symbol": "UPS",     "name": "UPS",                "sector": "Logistique",        "currency": "USD", "tr": True},
    {"symbol": "FDX",     "name": "FedEx",              "sector": "Logistique",        "currency": "USD", "tr": True},
    {"symbol": "UNP",     "name": "Union Pacific",      "sector": "Transport",         "currency": "USD", "tr": True},
    {"symbol": "CSX",     "name": "CSX",                "sector": "Transport",         "currency": "USD", "tr": True},
    {"symbol": "DAL",     "name": "Delta Air Lines",    "sector": "Transport",         "currency": "USD", "tr": True},
    {"symbol": "AAL",     "name": "American Airlines",  "sector": "Transport",         "currency": "USD", "tr": True},
    {"symbol": "UAL",     "name": "United Airlines",    "sector": "Transport",         "currency": "USD", "tr": True},
    {"symbol": "LUV",     "name": "Southwest Airlines", "sector": "Transport",         "currency": "USD", "tr": True},
    {"symbol": "MAR",     "name": "Marriott",           "sector": "Hospitalité",       "currency": "USD", "tr": True},
    {"symbol": "HLT",     "name": "Hilton",             "sector": "Hospitalité",       "currency": "USD", "tr": True},
    {"symbol": "ABNB",    "name": "Airbnb",             "sector": "Hospitalité",       "currency": "USD", "tr": True},
    {"symbol": "BKNG",    "name": "Booking Holdings",   "sector": "Voyage",            "currency": "USD", "tr": True},
    {"symbol": "UBER",    "name": "Uber",               "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "LYFT",    "name": "Lyft",               "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "DASH",    "name": "DoorDash",           "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "SPOT",    "name": "Spotify",            "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "MELI",    "name": "MercadoLibre",       "sector": "E-commerce",        "currency": "USD", "tr": True},
    {"symbol": "EBAY",    "name": "eBay",               "sector": "E-commerce",        "currency": "USD", "tr": True},
    {"symbol": "ETSY",    "name": "Etsy",               "sector": "E-commerce",        "currency": "USD", "tr": True},
    {"symbol": "F",       "name": "Ford",               "sector": "Automobile",        "currency": "USD", "tr": True},
    # REITs (Real Estate)
    {"symbol": "AMT",     "name": "American Tower",     "sector": "REIT",              "currency": "USD", "tr": True},
    {"symbol": "PLD",     "name": "Prologis",           "sector": "REIT",              "currency": "USD", "tr": True},
    {"symbol": "EQIX",    "name": "Equinix",            "sector": "REIT",              "currency": "USD", "tr": True},
    {"symbol": "PSA",     "name": "Public Storage",     "sector": "REIT",              "currency": "USD", "tr": True},
    # Commodities & utilities
    {"symbol": "NEM",     "name": "Newmont (Gold)",     "sector": "Mines",             "currency": "USD", "tr": True},
    {"symbol": "FCX",     "name": "Freeport-McMoRan",   "sector": "Mines",             "currency": "USD", "tr": True},
    {"symbol": "DUK",     "name": "Duke Energy",        "sector": "Énergie",           "currency": "USD", "tr": True},
    {"symbol": "SO",      "name": "Southern Co",        "sector": "Énergie",           "currency": "USD", "tr": True},
    {"symbol": "NEE",     "name": "NextEra Energy",     "sector": "Énergie",           "currency": "USD", "tr": True},
]

EMERGING_WATCHLIST = [
    # ═══════════ EU Tech / Fintech ═══════════
    {"symbol": "ADYEN.AS","name": "Adyen",              "sector": "Fintech",           "currency": "EUR", "tr": True},
    {"symbol": "DSY.PA",  "name": "Dassault Systèmes",  "sector": "Logiciel",          "currency": "EUR", "tr": True},
    {"symbol": "WLN.PA",  "name": "Worldline",          "sector": "Fintech",           "currency": "EUR", "tr": True},
    {"symbol": "MT.AS",   "name": "ArcelorMittal",      "sector": "Métaux",            "currency": "EUR", "tr": True},
    {"symbol": "RNO.PA",  "name": "Renault",            "sector": "Automobile",        "currency": "EUR", "tr": True},

    # ═══════════ US High-Growth Software ═══════════
    {"symbol": "PLTR",    "name": "Palantir",           "sector": "Logiciel",          "currency": "USD", "tr": True},
    {"symbol": "NET",     "name": "Cloudflare",         "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "CRWD",    "name": "CrowdStrike",        "sector": "Cybersécurité",     "currency": "USD", "tr": True},
    {"symbol": "SNOW",    "name": "Snowflake",          "sector": "Data",              "currency": "USD", "tr": True},
    {"symbol": "MDB",     "name": "MongoDB",            "sector": "Data",              "currency": "USD", "tr": True},
    {"symbol": "DDOG",    "name": "Datadog",            "sector": "DevOps",            "currency": "USD", "tr": True},
    {"symbol": "ZS",      "name": "Zscaler",            "sector": "Cybersécurité",     "currency": "USD", "tr": True},
    {"symbol": "OKTA",    "name": "Okta",               "sector": "Cybersécurité",     "currency": "USD", "tr": True},
    {"symbol": "TEAM",    "name": "Atlassian",          "sector": "Logiciel",          "currency": "USD", "tr": True},
    {"symbol": "BILL",    "name": "Bill.com",           "sector": "Fintech",           "currency": "USD", "tr": True},
    {"symbol": "U",       "name": "Unity Software",     "sector": "Logiciel",          "currency": "USD", "tr": True},
    {"symbol": "RBLX",    "name": "Roblox",             "sector": "Gaming",            "currency": "USD", "tr": True},
    {"symbol": "SHOP",    "name": "Shopify",            "sector": "E-commerce",        "currency": "USD", "tr": True},
    {"symbol": "SQ",      "name": "Block (Square)",     "sector": "Fintech",           "currency": "USD", "tr": True},
    {"symbol": "PYPL",    "name": "PayPal",             "sector": "Fintech",           "currency": "USD", "tr": True},
    {"symbol": "COIN",    "name": "Coinbase",           "sector": "Crypto",            "currency": "USD", "tr": True},
    {"symbol": "RIVN",    "name": "Rivian",             "sector": "Automobile",        "currency": "USD", "tr": True},
    {"symbol": "LCID",    "name": "Lucid Group",        "sector": "Automobile",        "currency": "USD", "tr": True},

    # ═══════════ Semi-conducteurs & IA ═══════════
    {"symbol": "AMD",     "name": "AMD",                "sector": "Semi-conducteurs",  "currency": "USD", "tr": True},
    {"symbol": "ARM",     "name": "Arm Holdings",       "sector": "Semi-conducteurs",  "currency": "USD", "tr": True},
    {"symbol": "MRVL",    "name": "Marvell",            "sector": "Semi-conducteurs",  "currency": "USD", "tr": True},
    {"symbol": "MU",      "name": "Micron",             "sector": "Semi-conducteurs",  "currency": "USD", "tr": True},
    {"symbol": "SMCI",    "name": "Super Micro",        "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "ANET",    "name": "Arista Networks",    "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "TSM",     "name": "TSMC (ADR)",         "sector": "Semi-conducteurs",  "currency": "USD", "tr": True},
    {"symbol": "ASML",    "name": "ASML (ADR)",         "sector": "Semi-conducteurs",  "currency": "USD", "tr": True},

    # ═══════════ Énergie verte / cleantech ═══════════
    {"symbol": "ENPH",    "name": "Enphase Energy",     "sector": "Énergie verte",     "currency": "USD", "tr": True},
    {"symbol": "FSLR",    "name": "First Solar",        "sector": "Énergie verte",     "currency": "USD", "tr": True},
    {"symbol": "PLUG",    "name": "Plug Power",         "sector": "Hydrogène",         "currency": "USD", "tr": True},
    {"symbol": "BE",      "name": "Bloom Energy",       "sector": "Énergie",           "currency": "USD", "tr": True},

    # ═══════════ Santé / Biotech ═══════════
    {"symbol": "DXCM",    "name": "Dexcom",             "sector": "Santé",             "currency": "USD", "tr": True},
    {"symbol": "ISRG",    "name": "Intuitive Surgical", "sector": "Santé",             "currency": "USD", "tr": True},
    {"symbol": "MRNA",    "name": "Moderna",            "sector": "Biotech",           "currency": "USD", "tr": True},
    {"symbol": "BNTX",    "name": "BioNTech",           "sector": "Biotech",           "currency": "USD", "tr": True},
    {"symbol": "REGN",    "name": "Regeneron",          "sector": "Biotech",           "currency": "USD", "tr": True},
    {"symbol": "VRTX",    "name": "Vertex Pharma",      "sector": "Biotech",           "currency": "USD", "tr": True},
    {"symbol": "HIMS",    "name": "Hims & Hers",        "sector": "Santé",             "currency": "USD", "tr": True},

    # ═══════════ Chine via ADR ═══════════
    {"symbol": "BABA",    "name": "Alibaba (ADR)",      "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "JD",      "name": "JD.com (ADR)",       "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "PDD",     "name": "Pinduoduo",          "sector": "E-commerce",        "currency": "USD", "tr": True},
    {"symbol": "NIO",     "name": "NIO",                "sector": "Automobile",        "currency": "USD", "tr": True},
    {"symbol": "BIDU",    "name": "Baidu",              "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "LI",      "name": "Li Auto",            "sector": "Automobile",        "currency": "USD", "tr": True},
    {"symbol": "XPEV",    "name": "XPeng",              "sector": "Automobile",        "currency": "USD", "tr": True},

    # ═══════════ ETFs thématiques ═══════════
    {"symbol": "SOXX",    "name": "iShares Semi ETF",   "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "ICLN",    "name": "iShares Clean Energy ETF","sector": "ETF",          "currency": "USD", "tr": True},
    {"symbol": "AIQ",     "name": "Global X AI ETF",    "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "ROBO",    "name": "ROBO Robotics ETF",  "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "ARKK",    "name": "ARK Innovation ETF", "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "ARKG",    "name": "ARK Genomics ETF",   "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "QQQ",     "name": "Invesco QQQ (Nasdaq)","sector": "ETF",              "currency": "USD", "tr": True},
    {"symbol": "SPY",     "name": "SPDR S&P 500",       "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "XLK",     "name": "Technology Select",  "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "XLV",     "name": "Health Care Select", "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "XLE",     "name": "Energy Select",      "sector": "ETF",               "currency": "USD", "tr": True},

    # ═══════════ Marchés exotiques — PAS sur TR ═══════════
    {"symbol": "1211.HK", "name": "BYD (HK)",           "sector": "Automobile",        "currency": "HKD", "tr": False},
    {"symbol": "9618.HK", "name": "JD.com (HK)",        "sector": "Tech",              "currency": "HKD", "tr": False},
    {"symbol": "1810.HK", "name": "Xiaomi",             "sector": "Tech",              "currency": "HKD", "tr": False},
    {"symbol": "0992.HK", "name": "Lenovo",             "sector": "Tech",              "currency": "HKD", "tr": False},
    {"symbol": "RELIANCE.NS","name": "Reliance Industries","sector": "Énergie",        "currency": "INR", "tr": False},
    {"symbol": "INFY.NS", "name": "Infosys",            "sector": "Tech",              "currency": "INR", "tr": False},
    {"symbol": "TCS.NS",  "name": "Tata Consultancy",   "sector": "Tech",              "currency": "INR", "tr": False},
    {"symbol": "HDFCBANK.NS","name": "HDFC Bank",       "sector": "Finance",           "currency": "INR", "tr": False},

    # ═══════════ Small/Mid Caps US Growth additionnels ═══════════
    {"symbol": "AFRM",    "name": "Affirm",             "sector": "Fintech",           "currency": "USD", "tr": True},
    {"symbol": "SOFI",    "name": "SoFi Technologies",  "sector": "Fintech",           "currency": "USD", "tr": True},
    {"symbol": "UPST",    "name": "Upstart",            "sector": "Fintech",           "currency": "USD", "tr": True},
    {"symbol": "HOOD",    "name": "Robinhood",          "sector": "Fintech",           "currency": "USD", "tr": True},
    {"symbol": "ROKU",    "name": "Roku",               "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "PINS",    "name": "Pinterest",          "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "SNAP",    "name": "Snap",               "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "TWLO",    "name": "Twilio",             "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "DOCN",    "name": "DigitalOcean",       "sector": "Cloud",             "currency": "USD", "tr": True},
    {"symbol": "FSLY",    "name": "Fastly",             "sector": "Tech",              "currency": "USD", "tr": True},
    {"symbol": "S",       "name": "SentinelOne",        "sector": "Cybersécurité",     "currency": "USD", "tr": True},
    {"symbol": "PANW",    "name": "Palo Alto Networks", "sector": "Cybersécurité",     "currency": "USD", "tr": True},
    {"symbol": "FTNT",    "name": "Fortinet",           "sector": "Cybersécurité",     "currency": "USD", "tr": True},
    {"symbol": "WDAY",    "name": "Workday",            "sector": "Logiciel",          "currency": "USD", "tr": True},
    {"symbol": "NOW",     "name": "ServiceNow",         "sector": "Logiciel",          "currency": "USD", "tr": True},
    {"symbol": "INTU",    "name": "Intuit",             "sector": "Logiciel",          "currency": "USD", "tr": True},
    {"symbol": "CRM",     "name": "Salesforce",         "sector": "Logiciel",          "currency": "USD", "tr": True},

    # ═══════════ Biotech / Innovation médicale ═══════════
    {"symbol": "CRSP",    "name": "CRISPR Therapeutics","sector": "Biotech",           "currency": "USD", "tr": True},
    {"symbol": "EDIT",    "name": "Editas Medicine",    "sector": "Biotech",           "currency": "USD", "tr": True},
    {"symbol": "NTLA",    "name": "Intellia",           "sector": "Biotech",           "currency": "USD", "tr": True},
    {"symbol": "BEAM",    "name": "Beam Therapeutics",  "sector": "Biotech",           "currency": "USD", "tr": True},
    {"symbol": "ILMN",    "name": "Illumina",           "sector": "Biotech",           "currency": "USD", "tr": True},
    {"symbol": "RXRX",    "name": "Recursion Pharma",   "sector": "Biotech IA",        "currency": "USD", "tr": True},

    # ═══════════ Espace / nouveau monde ═══════════
    {"symbol": "RKLB",    "name": "Rocket Lab",         "sector": "Aérospatial",       "currency": "USD", "tr": True},
    {"symbol": "ASTS",    "name": "AST SpaceMobile",    "sector": "Aérospatial",       "currency": "USD", "tr": True},
    {"symbol": "IONQ",    "name": "IonQ (Quantum)",     "sector": "Quantum",           "currency": "USD", "tr": True},
    {"symbol": "RGTI",    "name": "Rigetti Computing",  "sector": "Quantum",           "currency": "USD", "tr": True},

    # ═══════════ Méta-univers / Gaming ═══════════
    {"symbol": "EA",      "name": "Electronic Arts",    "sector": "Gaming",            "currency": "USD", "tr": True},
    {"symbol": "TTWO",    "name": "Take-Two",           "sector": "Gaming",            "currency": "USD", "tr": True},
    {"symbol": "ATVI",    "name": "Activision Blizzard","sector": "Gaming",            "currency": "USD", "tr": True},

    # ═══════════ ETFs additionnels ═══════════
    {"symbol": "VTI",     "name": "Vanguard Total US",  "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "VWO",     "name": "Vanguard Emerging",  "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "EFA",     "name": "iShares MSCI EAFE",  "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "EEM",     "name": "iShares Emerging",   "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "GLD",     "name": "SPDR Gold",          "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "SLV",     "name": "iShares Silver",     "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "USO",     "name": "United States Oil",  "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "TLT",     "name": "iShares 20Y Treasury","sector": "ETF",              "currency": "USD", "tr": True},
    {"symbol": "VYM",     "name": "Vanguard High Dividend","sector": "ETF",            "currency": "USD", "tr": True},
    {"symbol": "SCHD",    "name": "Schwab Dividend",    "sector": "ETF",               "currency": "USD", "tr": True},
    {"symbol": "JEPI",    "name": "JPMorgan Equity Premium","sector": "ETF",           "currency": "USD", "tr": True},
]


# ── Cloture de la veille (variation du jour) ──────────────────────────

def _previous_close(meta_yh: dict, closes: list[float], current: float) -> float | None:
    """Retourne la cloture de la SEANCE PRECEDENTE, pour calculer la variation du jour.

    PIEGE YAHOO : `meta.chartPreviousClose` n'est PAS la cloture de la veille,
    c'est la cloture juste AVANT la fenetre demandee. Avec range=1y il renvoie
    donc le prix d'il y a un an (ex. MU : 116 au lieu de 910) → la variation
    "du jour" affichait +700%. On ne s'en sert jamais ici.

    Ordre de priorite :
      1. meta.previousClose        → valeur officielle Yahoo (souvent absente sur range=1y)
      2. closes[-2]                → le dernier bar correspond a la seance en cours
      3. closes[-1]                → le prix live est plus recent que le dernier bar
    """
    prev = meta_yh.get("previousClose")
    if prev:
        return float(prev)
    if len(closes) < 2:
        return None
    # Tolerance 0.01 % : le dernier close et le prix live sont la meme seance
    # (Yahoo arrondit differemment les deux champs).
    if closes[-1] and abs(current - closes[-1]) / closes[-1] < 1e-4:
        return float(closes[-2])
    return float(closes[-1])


# ── Yahoo Finance v8 chart : prix + history ───────────────────────────

async def _fetch_yahoo(meta: dict, client: httpx.AsyncClient) -> dict | None:
    symbol = meta["symbol"]
    try:
        # On demande 1 an avec un peu de marge pour avoir MM200 + ROC 6 mois
        resp = await client.get(
            f"{YAHOO_BASE}/{symbol}",
            params={"range": "1y", "interval": "1d"},
            headers=HEADERS,
            timeout=8,
        )
        if resp.status_code != 200:
            print(f"[stocks] {symbol} - Yahoo HTTP {resp.status_code}")
            return None
        data = resp.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return None

        chart = result[0]
        meta_yh = chart.get("meta", {})
        quote_arr = chart.get("indicators", {}).get("quote", [{}])
        if not quote_arr:
            return None

        quote = quote_arr[0]
        closes_raw  = quote.get("close",  []) or []
        highs_raw   = quote.get("high",   []) or []
        lows_raw    = quote.get("low",    []) or []
        volumes_raw = quote.get("volume", []) or []

        # Series alignees : on ne garde que les jours ou le close existe,
        # high/low/volume retombent sur le close (ou 0) si absents ce jour-la.
        closes, highs, lows, volumes = [], [], [], []
        for i, c in enumerate(closes_raw):
            if c is None:
                continue
            c = float(c)
            closes.append(c)
            h = highs_raw[i] if i < len(highs_raw) else None
            l = lows_raw[i]  if i < len(lows_raw)  else None
            v = volumes_raw[i] if i < len(volumes_raw) else None
            highs.append(float(h) if h is not None else c)
            lows.append(float(l) if l is not None else c)
            volumes.append(float(v) if v is not None else 0.0)
        if len(closes) < 2:
            return None

        current = float(meta_yh.get("regularMarketPrice") or closes[-1])
        prev    = _previous_close(meta_yh, closes, current)
        if not prev:
            return None

        change_pct = ((current - prev) / prev) * 100
        week_low   = float(meta_yh.get("fiftyTwoWeekLow")  or min(closes))
        week_high  = float(meta_yh.get("fiftyTwoWeekHigh") or max(closes))

        if week_high != week_low:
            position_52w = ((current - week_low) / (week_high - week_low)) * 100
            position_52w = max(0.0, min(100.0, position_52w))
        else:
            position_52w = 50.0

        sparkline = [round(c, 4) for c in closes[-30:]]

        perf_1m = 0.0
        if len(sparkline) >= 2 and sparkline[0] != 0:
            perf_1m = ((sparkline[-1] - sparkline[0]) / sparkline[0]) * 100

        # Calcul des indicateurs techniques (RSI, MACD, MM, Bollinger, ATR, ADX,
        # OBV, MFI, CMF, divergences...) depuis la serie OHLCV 1 an
        indicators = compute_indicators(closes, highs=highs, lows=lows, volumes=volumes)

        return {
            "ticker":         symbol,
            "name":           meta["name"],
            "price":          round(current, 4),
            "change_pct":     round(change_pct, 2),
            "week_low":       round(week_low, 4),
            "week_high":      round(week_high, 4),
            "position_52w":   round(position_52w, 1),
            "sector":         meta["sector"],
            "market_cap":     None,
            "pe_ratio":       None,
            "dividend_yield": None,
            "revenue_growth": None,
            "currency":       meta_yh.get("currency") or meta.get("currency", "USD"),
            "sparkline":      sparkline,
            "perf_1m":        round(perf_1m, 2),
            "near_52w_low":   position_52w < 15,
            "tr":             meta.get("tr", False),
            "indicators":     indicators,
        }
    except Exception as exc:
        print(f"[stocks] Yahoo error {symbol}: {exc}")
        return None


# ── Finnhub : fondamentaux (US uniquement en gratuit, needs FINNHUB_API_KEY)

async def _fetch_finnhub_fundamentals(symbol: str, client: httpx.AsyncClient) -> dict | None:
    """Retourne marketCap, P/E, dividende, croissance via Finnhub — ou None
    si indisponible (pas de cle, ticker non-US, rate limit). Ne met RIEN en
    cache lui-meme : c'est _fetch_fundamentals() qui gere le cache, pour
    pouvoir essayer la source Yahoo en repli sans etre bloque par un None
    deja cache par cette fonction."""
    if not FINNHUB_API_KEY:
        return None

    # Skip non-US tickers (Finnhub free = 403)
    if "." in symbol:
        return None

    try:
        profile_resp, metric_resp = await asyncio.gather(
            _finnhub_get(client, "/stock/profile2", {"symbol": symbol}),
            _finnhub_get(client, "/stock/metric",   {"symbol": symbol, "metric": "all"}),
        )

        if profile_resp is None or profile_resp.status_code != 200:
            return None

        pj = profile_resp.json() or {}
        market_cap_m = pj.get("marketCapitalization")
        if not market_cap_m:
            return None

        metric_data = {}
        if metric_resp is not None and metric_resp.status_code == 200:
            mj = metric_resp.json() or {}
            metric_data = mj.get("metric", {}) or {}

        pe = metric_data.get("peNormalizedAnnual") or metric_data.get("peTTM") or metric_data.get("peExclExtraTTM")
        div_yield = metric_data.get("dividendYieldIndicatedAnnual") or metric_data.get("currentDividendYieldTTM")
        rev_growth_pct = metric_data.get("revenueGrowthTTMYoy")  # déjà en %

        return {
            "market_cap":     market_cap_m * 1_000_000,  # Finnhub renvoie en millions
            "pe_ratio":       round(pe, 2) if pe else None,
            "dividend_yield": round(div_yield, 2) if div_yield else None,
            "revenue_growth": round(rev_growth_pct / 100, 4) if rev_growth_pct else None,  # en fraction (0.1276 = 12.76%)
        }
    except Exception as exc:
        print(f"[stocks] Finnhub fundamentals error {symbol}: {exc!r}")
        return None


# ── Yahoo Finance : fondamentaux de repli (aucune cle requise) ────────
#
# Sans FINNHUB_API_KEY (cas de tout utilisateur qui vient de cloner le
# projet), la section "Fondamentaux" etait vide pour la quasi-totalite des
# titres, et meme AVEC une cle, seuls les tickers US fonctionnent (403 sur
# le plan gratuit pour l'Europe/l'Asie). Yahoo expose les memes chiffres
# (cap. boursiere, P/E, dividende, croissance du CA) pour N'IMPORTE QUEL
# marche, gratuitement — mais l'endpoint quoteSummary exige un cookie +
# "crumb" anti-bot (contrairement au endpoint /chart utilise pour les prix).
# On recupere ce crumb une seule fois et on le reutilise pour tous les
# tickers, avec le MEME client HTTP (le crumb est lie au cookie de session).

_yahoo_fundamentals_client: httpx.AsyncClient | None = None
_yahoo_crumb: str | None = None
_yahoo_crumb_ts = 0.0
_yahoo_crumb_lock = asyncio.Lock()
YAHOO_CRUMB_TTL = 3600  # 1h : marge de securite, Yahoo n'invalide pas si souvent


def _get_yahoo_fundamentals_client() -> httpx.AsyncClient:
    """Client HTTP persistant (jamais ferme) : le crumb Yahoo est valide
    uniquement avec les cookies du client qui l'a obtenu.
    Sans le header Accept: application/json de HEADERS : l'endpoint
    /getcrumb repond en texte brut et renvoie 406 Not Acceptable si on
    exige du JSON."""
    global _yahoo_fundamentals_client
    if _yahoo_fundamentals_client is None:
        _yahoo_fundamentals_client = httpx.AsyncClient(
            headers={"User-Agent": HEADERS["User-Agent"]}, timeout=10, follow_redirects=True,
        )
    return _yahoo_fundamentals_client


async def _get_yahoo_crumb() -> str | None:
    global _yahoo_crumb, _yahoo_crumb_ts
    if _yahoo_crumb and time.time() - _yahoo_crumb_ts < YAHOO_CRUMB_TTL:
        return _yahoo_crumb
    async with _yahoo_crumb_lock:
        if _yahoo_crumb and time.time() - _yahoo_crumb_ts < YAHOO_CRUMB_TTL:
            return _yahoo_crumb  # deja rafraichi par une autre requete concurrente
        try:
            client = _get_yahoo_fundamentals_client()
            await client.get("https://fc.yahoo.com")  # pose le cookie de session
            r = await client.get("https://query2.finance.yahoo.com/v1/test/getcrumb")
            crumb = r.text.strip()
            if r.status_code == 200 and crumb and len(crumb) < 30:
                _yahoo_crumb = crumb
                _yahoo_crumb_ts = time.time()
                return crumb
        except Exception as exc:
            print(f"[stocks] Yahoo crumb error: {exc!r}")
        return None


async def _fetch_yahoo_fundamentals(symbol: str) -> dict | None:
    """Repli sans cle API : mêmes champs que Finnhub, pour tous les marches."""
    crumb = await _get_yahoo_crumb()
    if not crumb:
        return None
    try:
        client = _get_yahoo_fundamentals_client()
        r = await client.get(
            f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}",
            params={"modules": "price,summaryDetail,financialData", "crumb": crumb},
        )
        if r.status_code == 401:
            # Le crumb a ete invalide cote serveur -> on en redemandera un neuf
            global _yahoo_crumb
            _yahoo_crumb = None
            return None
        if r.status_code != 200:
            return None

        results = ((r.json().get("quoteSummary") or {}).get("result")) or []
        if not results:
            return None
        res = results[0]
        price_mod = res.get("price", {}) or {}
        summary   = res.get("summaryDetail", {}) or {}
        financial = res.get("financialData", {}) or {}

        market_cap = (price_mod.get("marketCap") or {}).get("raw")
        if not market_cap:
            return None
        pe         = (summary.get("trailingPE") or {}).get("raw")
        div_yield  = (summary.get("dividendYield") or {}).get("raw")      # fraction (0.0287 = 2.87%)
        rev_growth = (financial.get("revenueGrowth") or {}).get("raw")   # deja en fraction

        return {
            "market_cap":     market_cap,
            "pe_ratio":       round(pe, 2) if pe else None,
            "dividend_yield": round(div_yield * 100, 2) if div_yield else None,
            "revenue_growth": round(rev_growth, 4) if rev_growth is not None else None,
        }
    except Exception as exc:
        print(f"[stocks] Yahoo fundamentals error {symbol}: {exc!r}")
        return None


async def _fetch_fundamentals(symbol: str, client: httpx.AsyncClient) -> dict | None:
    """Finnhub d'abord (si une cle est configuree et le ticker est US),
    sinon Yahoo (fonctionne partout, sans cle). Cache unique ici : les deux
    sous-fonctions ne cachent rien elles-memes pour ne jamais bloquer le
    repli sur un None mis en cache trop tot par l'autre source."""
    cached = _fundamentals_cache.get(symbol)
    if cached and time.time() - cached["ts"] < FUNDAMENTALS_TTL:
        return cached["data"]

    data = await _fetch_finnhub_fundamentals(symbol, client)
    if not data:
        data = await _fetch_yahoo_fundamentals(symbol)

    if data:
        _fundamentals_cache[symbol] = {"data": data, "ts": time.time()}
    return data


# ── Finnhub : sentiment news + recommandations analystes ─────────────

async def _fetch_finnhub_sentiment(symbol: str, client: httpx.AsyncClient) -> dict | None:
    """Récupère sentiment des news + consensus analystes + earnings surprise.
    US uniquement (Finnhub free renvoie 403 pour EU/Asie)."""
    if not FINNHUB_API_KEY or "." in symbol:
        return None

    cached = _sentiment_cache.get(symbol)
    if cached and time.time() - cached["ts"] < SENTIMENT_TTL:
        return cached["data"]

    from datetime import date, timedelta
    from services.news import POSITIVE_WORDS, NEGATIVE_WORDS

    today = date.today()
    fr = today - timedelta(days=14)

    try:
        news_resp, rec_resp, earn_resp = await asyncio.gather(
            _finnhub_get(client, "/company-news",
                         {"symbol": symbol, "from": fr.isoformat(), "to": today.isoformat()}),
            _finnhub_get(client, "/stock/recommendation", {"symbol": symbol}),
            _finnhub_get(client, "/stock/earnings",       {"symbol": symbol}),
        )

        # Tout en rate limit / erreur reseau → pas de cache, retentera plus tard
        if news_resp is None and rec_resp is None and earn_resp is None:
            return None

        # ── Sentiment des news (analyse lexicale des titres) ──
        news_sent = None
        news_count = 0
        if news_resp is not None and news_resp.status_code == 200:
            articles = news_resp.json() or []
            news_count = len(articles)
            if articles:
                pos = neg = 0
                for a in articles[:25]:
                    h = (a.get("headline") or "").lower()
                    words = [w.strip(".,!?:;-'\"") for w in h.split()]
                    p = sum(1 for w in words if w in POSITIVE_WORDS)
                    n = sum(1 for w in words if w in NEGATIVE_WORDS)
                    if p > n: pos += 1
                    elif n > p: neg += 1
                total = pos + neg
                if total > 0:
                    news_sent = round((pos - neg) / total, 3)  # -1 à +1

        # ── Consensus analystes ──
        analyst = None
        upgrade_trend = None
        if rec_resp is not None and rec_resp.status_code == 200:
            recs = rec_resp.json() or []
            if recs:
                latest = recs[0]
                total = (latest.get("strongBuy", 0) + latest.get("buy", 0) +
                         latest.get("hold", 0) + latest.get("sell", 0) + latest.get("strongSell", 0))
                if total > 0:
                    bullish = (latest.get("strongBuy", 0) * 2 + latest.get("buy", 0)) / (total * 2)
                    bearish = (latest.get("strongSell", 0) * 2 + latest.get("sell", 0)) / (total * 2)
                    analyst = {
                        "bullish_ratio": round(bullish, 3),
                        "bearish_ratio": round(bearish, 3),
                        "total":         total,
                        "strong_buy":    latest.get("strongBuy", 0),
                        "buy":           latest.get("buy", 0),
                        "hold":          latest.get("hold", 0),
                        "sell":          latest.get("sell", 0),
                        "strong_sell":   latest.get("strongSell", 0),
                    }
                    # Tendance des recommandations (comparaison mois actuel vs ~3 mois avant)
                    if len(recs) >= 4:
                        old = recs[3]
                        old_total = (old.get("strongBuy", 0) + old.get("buy", 0) +
                                     old.get("hold", 0) + old.get("sell", 0) + old.get("strongSell", 0))
                        if old_total > 0:
                            old_bullish = (old.get("strongBuy", 0) * 2 + old.get("buy", 0)) / (old_total * 2)
                            upgrade_trend = round(bullish - old_bullish, 3)  # +0.1 = upgrades

        # ── Earnings surprises (sur derniers trimestres) ──
        earnings_surprise = None
        beats = misses = 0
        if earn_resp is not None and earn_resp.status_code == 200:
            earnings = earn_resp.json() or []
            for e in earnings[:4]:  # 4 derniers trimestres
                actual = e.get("actual")
                est = e.get("estimate")
                if actual is not None and est is not None:
                    if actual > est: beats += 1
                    elif actual < est: misses += 1
            if beats + misses > 0:
                earnings_surprise = round((beats - misses) / (beats + misses), 3)

        data = {
            "news_sentiment":    news_sent,
            "news_count":        news_count,
            "analyst":           analyst,
            "analyst_upgrade":   upgrade_trend,
            "earnings_surprise": earnings_surprise,
            "earnings_beats":    beats,
            "earnings_misses":   misses,
        }
        _sentiment_cache[symbol] = {"data": data, "ts": time.time()}
        return data
    except Exception as exc:
        print(f"[stocks] Finnhub sentiment error {symbol}: {exc!r}")
        return None


# ── Macro : VIX (peur sur les marchés) ───────────────────────────────

async def _set_macro_news():
    """Fetche le sentiment macro + détection de crise depuis le service news."""
    from services.news import get_macro_context
    try:
        ctx = await get_macro_context()
        _market_context["macro_sentiment"]    = ctx.get("sentiment", 0)
        _market_context["crisis_intensity"]   = ctx.get("crisis_intensity", 0)
        _market_context["crisis_keywords"]    = ctx.get("crisis_keywords", [])
    except Exception as exc:
        print(f"[stocks] macro news error: {exc}")


async def _get_vix() -> float | None:
    """Récupère le VIX (Volatility Index) — cache 10 min."""
    if time.time() - _market_context["ts"] < 600 and _market_context["vix"] is not None:
        return _market_context["vix"]
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{YAHOO_BASE}/^VIX",
                                 params={"range": "5d", "interval": "1d"},
                                 headers=HEADERS)
            if r.status_code == 200:
                result = r.json().get("chart", {}).get("result", [])
                if result:
                    m = result[0].get("meta", {})
                    closes = [c for c in (result[0].get("indicators", {}).get("quote", [{}])[0].get("close") or []) if c is not None]
                    vix = float(m.get("regularMarketPrice") or (closes[-1] if closes else 20))
                    _market_context["vix"] = vix
                    _market_context["ts"] = time.time()
                    return vix
    except Exception as exc:
        print(f"[stocks] VIX error: {exc}")
    return _market_context.get("vix")


# ── Combinaison ───────────────────────────────────────────────────────

async def _fetch_full(meta: dict, client: httpx.AsyncClient) -> dict | None:
    yahoo_data, fundamentals, sentiment = await asyncio.gather(
        _fetch_yahoo(meta, client),
        _fetch_fundamentals(meta["symbol"], client),
        _fetch_finnhub_sentiment(meta["symbol"], client),
    )
    if not yahoo_data:
        return None

    if fundamentals:
        yahoo_data["market_cap"]     = fundamentals["market_cap"]
        yahoo_data["pe_ratio"]       = fundamentals["pe_ratio"]
        yahoo_data["dividend_yield"] = fundamentals["dividend_yield"]
        yahoo_data["revenue_growth"] = fundamentals["revenue_growth"]

    if sentiment:
        yahoo_data["sentiment"] = sentiment

    # Score d'opportunité ENRICHI : technique + fondamentaux + sentiment + macro
    yahoo_data["opportunity"] = compute_opportunity_score(
        yahoo_data,
        yahoo_data.get("indicators"),
        sentiment=sentiment,
        vix=_market_context.get("vix"),
        macro_sentiment=_market_context.get("macro_sentiment"),
        crisis_intensity=_market_context.get("crisis_intensity"),
    )

    return yahoo_data


async def _fetch_watchlist(watchlist: list[dict]) -> list[dict]:
    # Sémaphore : 80 simultanés — assez pour ~250 tickers en 3-4 vagues
    sem = asyncio.Semaphore(80)

    async def one(meta, client):
        async with sem:
            return await _fetch_full(meta, client)

    async with httpx.AsyncClient(timeout=20) as client:
        results = await asyncio.gather(*[one(m, client) for m in watchlist])
    return [r for r in results if r is not None]


# ── Cache partagé ─────────────────────────────────────────────────────

async def _get_all_stocks() -> list[dict]:
    """Récupère TOUS les tickers (trending + emerging) avec lock pour
    éviter les fetchs parallèles redondants. Cache 5 min."""
    key = "all_stocks"
    cached = _cache.get(key)
    if cached and time.time() - cached["ts"] < CACHE_TTL:
        return cached["data"]

    async with _fetch_lock:
        # Re-check après le lock : un autre coroutine a peut-être déjà fetché
        cached = _cache.get(key)
        if cached and time.time() - cached["ts"] < CACHE_TTL:
            return cached["data"]

        # Récupère le VIX + le contexte macro news avant les watchlists
        from services.news import get_macro_context
        await asyncio.gather(_get_vix(), _set_macro_news())
        # _set_macro_news appelle get_macro_context et stocke dans _market_context

        # Dédoublonne les watchlists par ticker
        all_meta: dict[str, dict] = {}
        for m in TRENDING_WATCHLIST + EMERGING_WATCHLIST:
            all_meta[m["symbol"]] = m

        data = await _fetch_watchlist(list(all_meta.values()))
        if data:
            _cache[key] = {"data": data, "ts": time.time()}
        return data


# ── Endpoints publics ─────────────────────────────────────────────────

async def get_trending_stocks() -> list[dict]:
    all_stocks = await _get_all_stocks()
    trending_tickers = {m["symbol"] for m in TRENDING_WATCHLIST}
    trending = [s for s in all_stocks if s["ticker"] in trending_tickers]
    trending.sort(key=lambda x: x["change_pct"], reverse=True)
    return trending[:40]  # Top 40


async def get_emerging_companies() -> list[dict]:
    all_stocks = await _get_all_stocks()
    emerging_tickers = {m["symbol"] for m in EMERGING_WATCHLIST}
    emerging = [s for s in all_stocks if s["ticker"] in emerging_tickers]
    emerging.sort(key=lambda x: x["perf_1m"], reverse=True)
    return emerging[:40]  # Top 40


async def get_all_universe() -> list[dict]:
    """Renvoie TOUS les tickers (trending + emerging fusionnés) — pour la section "Tout voir"."""
    return await _get_all_stocks()


async def get_top_movers(top_n: int = 5) -> dict:
    """Top gainers/losers du jour parmi TOUS les tickers suivis."""
    all_stocks = await _get_all_stocks()
    sorted_asc = sorted(all_stocks, key=lambda x: x["change_pct"])
    return {
        "gainers": list(reversed(sorted_asc[-top_n:])),
        "losers":  sorted_asc[:top_n],
    }


# ── Détail d'une action (modal) ───────────────────────────────────────

# Mapping période → (range Yahoo, interval Yahoo)
PERIOD_PARAMS = {
    "1d":  ("1d",  "5m"),
    "5d":  ("5d",  "30m"),
    "1mo": ("1mo", "1d"),
    "3mo": ("3mo", "1d"),
    "1y":  ("1y",  "1d"),
    "5y":  ("5y",  "1wk"),
    "max": ("max", "1mo"),
}


async def _fetch_yahoo_history(symbol: str, period: str, client: httpx.AsyncClient) -> list[dict]:
    """Récupère l'historique avec timestamps pour le graphique du modal."""
    rng, interval = PERIOD_PARAMS.get(period, ("1y", "1d"))
    try:
        resp = await client.get(
            f"{YAHOO_BASE}/{symbol}",
            params={"range": rng, "interval": interval},
            headers=HEADERS,
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return []
        chart = result[0]
        timestamps = chart.get("timestamp", []) or []
        closes = chart.get("indicators", {}).get("quote", [{}])[0].get("close", []) or []

        out = []
        for t, c in zip(timestamps, closes):
            if c is not None:
                out.append({"t": int(t), "c": round(float(c), 4)})
        return out
    except Exception as exc:
        print(f"[stocks] history error {symbol} {period}: {exc}")
        return []


async def _fetch_company_news(symbol: str, client: httpx.AsyncClient) -> list[dict]:
    """Récupère les news d'une entreprise depuis Finnhub (US uniquement en gratuit)."""
    if not FINNHUB_API_KEY:
        return []
    from datetime import date, timedelta
    today = date.today()
    fr = today - timedelta(days=30)
    try:
        resp = await _finnhub_get(client, "/company-news",
                                  {"symbol": symbol, "from": fr.isoformat(), "to": today.isoformat()})
        if resp is None or resp.status_code != 200:
            return []
        articles = resp.json()
        return [{
            "headline": a.get("headline", ""),
            "source":   a.get("source", ""),
            "url":      a.get("url", ""),
            "datetime": a.get("datetime", 0),
            "summary":  (a.get("summary") or "")[:240],
            "image":    a.get("image", ""),
        } for a in articles[:10] if a.get("headline")]
    except Exception as exc:
        print(f"[stocks] company-news error {symbol}: {exc}")
        return []


def compute_opportunity_score(s: dict, indicators: dict | None = None,
                              sentiment: dict | None = None, vix: float | None = None,
                              macro_sentiment: float | None = None,
                              crisis_intensity: float | None = None) -> dict:
    """Score d'opportunite v6 — architecture en 4 piliers + overlay risque/macro.

    Piliers (chacun 0-100, base 50) :
      - trend     : la tendance de fond est-elle haussiere et confirmee ?
      - timing    : est-ce un bon point d'entree MAINTENANT ? (survente, pullback, divergences)
      - quality   : l'entreprise/l'action est-elle saine ? (fondamentaux + stats risque/rendement)
      - sentiment : que disent les news et les analystes ?

    Score final = moyenne ponderee des piliers disponibles, avec poids ADAPTATIFS
    selon le regime detecte (bull → momentum prime ; bear → qualite et timing priment),
    puis multiplicateur de risque, overlay macro (VIX/crise) et plafonds regime baissier.

    Retourne aussi : pillars, regime, confidence (0-100, couverture des donnees),
    risk_mult, et un breakdown detaille par signal. Heuristique — pas un conseil.
    """
    breakdown: dict[str, float] = {}
    pillars_raw = {"trend": 0.0, "timing": 0.0, "quality": 0.0, "sentiment": 0.0}
    ind = indicators or {}

    def add(pillar: str, key: str, pts: float):
        if pts:
            pillars_raw[pillar] += pts
            breakdown[key] = round(breakdown.get(key, 0.0) + pts, 1)

    cp_day = s.get("change_pct") or 0
    pos    = s.get("position_52w")
    perf1m = s.get("perf_1m")

    # ════════════════════ DETECTION DU REGIME ════════════════════
    bull_votes = bear_votes = 0
    if ind.get("above_sma_200") is True:    bull_votes += 1
    elif ind.get("above_sma_200") is False: bear_votes += 1
    if ind.get("golden_cross") is True:     bull_votes += 1
    elif ind.get("golden_cross") is False:  bear_votes += 1
    roc3 = ind.get("roc_3m")
    if roc3 is not None:
        if roc3 > 5:    bull_votes += 1
        elif roc3 < -5: bear_votes += 1
    if ind.get("structure") == "HH_HL":     bull_votes += 1
    elif ind.get("structure") == "LH_LL":   bear_votes += 1
    adx, di_p, di_m = ind.get("adx"), ind.get("di_plus"), ind.get("di_minus")
    if adx is not None and adx > 20 and di_p is not None and di_m is not None:
        if di_p > di_m:  bull_votes += 1
        else:            bear_votes += 1

    if bull_votes - bear_votes >= 2:
        regime = "bull"
    elif bear_votes - bull_votes >= 2:
        regime = "bear"
    else:
        regime = "neutral"

    # ════════════════════ PILIER TREND ════════════════════
    if ind:
        if ind.get("above_sma_200") is True:
            add("trend", "above_sma200", 6.0)
        elif ind.get("above_sma_200") is False:
            add("trend", "below_sma200", -6.0)

        if ind.get("golden_cross") is True:
            add("trend", "golden_cross", 5.0)
        elif ind.get("golden_cross") is False:
            add("trend", "death_cross", -5.0)

        # Alignement multi-timeframes
        rocs = [ind.get(k) for k in ("roc_1w", "roc_1m", "roc_3m", "roc_6m")]
        valid = [r for r in rocs if r is not None]
        if len(valid) >= 3:
            n_pos = sum(1 for r in valid if r > 0)
            if n_pos == len(valid):
                add("trend", "trend_aligned_up", 8.0)
            elif n_pos == 0:
                add("trend", "trend_aligned_down", -8.0)
            elif n_pos >= len(valid) - 1:
                add("trend", "trend_mostly_up", 3.0)

        # Force du trend (regression 90j)
        r2, slope_pct = ind.get("trend_r2"), ind.get("trend_slope_pct")
        if r2 is not None and slope_pct is not None and r2 > 0.5:
            if slope_pct > 0.1:
                add("trend", "strong_uptrend", min(r2 * 7, 7))
            elif slope_pct < -0.1:
                add("trend", "strong_downtrend", -min(r2 * 7, 7))

        # MACD + inflexion de momentum
        macd = ind.get("macd")
        if macd:
            if macd.get("bullish"):
                add("trend", "macd_bullish", 4.0 + min(abs(macd.get("histogram", 0)) * 0.5, 2))
                hs = macd.get("hist_slope")
                if hs is not None and hs < 0:
                    add("trend", "macd_momentum_down", -2.0)  # toujours bullish mais s'essouffle
            else:
                add("trend", "macd_bearish", -4.0)
                hs = macd.get("hist_slope")
                if hs is not None and hs > 0:
                    add("trend", "macd_momentum_up", 2.0)     # encore bearish mais ca remonte

        # ADX : force directionnelle confirmee
        if adx is not None and di_p is not None and di_m is not None:
            if adx > 40:
                add("trend", "adx_trend", 7.0 if di_p > di_m else -7.0)
            elif adx > 25:
                add("trend", "adx_trend", 5.0 if di_p > di_m else -5.0)

        # Structure HH/HL
        if ind.get("structure") == "HH_HL":
            add("trend", "structure_hh_hl", 6.0)
        elif ind.get("structure") == "LH_LL":
            add("trend", "structure_lh_ll", -6.0)

        # Volume : OBV confirme ou contredit le prix
        obv_t, roc1m = ind.get("obv_trend"), ind.get("roc_1m")
        if obv_t is not None and roc1m is not None:
            if obv_t > 2 and roc1m > 0:
                add("trend", "obv_confirm", 4.0)        # hausse soutenue par le volume
            elif obv_t < -2 and roc1m > 0:
                add("trend", "obv_diverge", -4.0)       # hausse SANS volume = suspecte
            elif obv_t < -2 and roc1m < 0:
                add("trend", "obv_confirm_down", -3.0)  # baisse confirmee par le volume

        # Chaikin Money Flow : accumulation / distribution institutionnelle
        cmf = ind.get("cmf")
        if cmf is not None:
            if cmf > 0.15:
                add("trend", "cmf_accumulation", 4.0)
            elif cmf < -0.15:
                add("trend", "cmf_distribution", -4.0)

        # Pic 52S recent / momentum essouffle
        dh = ind.get("days_since_high")
        if dh is not None:
            if dh < 10 and cp_day > 0:
                add("trend", "near_52w_high", 3.0)
            elif dh > 200:
                add("trend", "faded_momentum", -2.0)

    # Performance 1 mois (momentum sain vs faiblesse)
    if perf1m is not None:
        if 0 <= perf1m <= 20:
            add("trend", "perf_1m", perf1m / 20 * 5)
        elif perf1m < 0:
            add("trend", "perf_1m", max(perf1m * 0.5, -6))

    # ════════════════════ PILIER TIMING ════════════════════
    if ind:
        # Consensus survente/surachat — 6 votants (MFI inclus desormais)
        os_votes = ob_votes = 0
        rsi = ind.get("rsi")
        if rsi is not None:
            if rsi < 30: os_votes += 1
            elif rsi > 70: ob_votes += 1
        wr = ind.get("williams_r")
        if wr is not None:
            if wr < -80: os_votes += 1
            elif wr > -20: ob_votes += 1
        cci = ind.get("cci")
        if cci is not None:
            if cci < -100: os_votes += 1
            elif cci > 100: ob_votes += 1
        stoch = ind.get("stochastic")
        if stoch is not None:
            if stoch < 20: os_votes += 1
            elif stoch > 80: ob_votes += 1
        bb = ind.get("bb_position")
        if bb is not None:
            if bb < 0.15: os_votes += 1
            elif bb > 0.85: ob_votes += 1
        mfi = ind.get("mfi")
        if mfi is not None:
            if mfi < 20: os_votes += 1
            elif mfi > 80: ob_votes += 1

        if os_votes >= 4:   v = 14.0
        elif os_votes == 3: v = 9.0
        elif os_votes == 2: v = 4.0
        else:               v = 0.0
        if v and cp_day <= -7:
            v *= 0.5  # garde-fou couteau qui tombe : survente pendant une chute panique
        if v:
            add("timing", "consensus_oversold", v)

        if ob_votes >= 4:   add("timing", "consensus_overbought", -12.0)
        elif ob_votes == 3: add("timing", "consensus_overbought", -7.0)
        elif ob_votes == 2: add("timing", "consensus_overbought", -3.0)

        # Divergence RSI — un des signaux de retournement les plus fiables
        div = ind.get("rsi_divergence")
        if div == "bullish":
            add("timing", "rsi_divergence_bull", 8.0)
        elif div == "bearish":
            add("timing", "rsi_divergence_bear", -8.0)

        # Z-score (extremes statistiques)
        z = ind.get("z_score_50")
        if z is not None:
            if z < -2:     add("timing", "z_score", 5.0)
            elif z < -1.5: add("timing", "z_score", 2.5)
            elif z > 2:    add("timing", "z_score", -5.0)
            elif z > 1.5:  add("timing", "z_score", -2.5)

        # Pullback vers supports (MM200, EMA21)
        d200 = ind.get("dist_sma200")
        if d200 is not None:
            if -8 < d200 < -2:
                add("timing", "pullback_to_sma200", 4.0)
            elif d200 > 30:
                add("timing", "far_from_sma200", -4.0)
        d21 = ind.get("dist_ema21")
        if d21 is not None and -6 < d21 < -1 and regime == "bull":
            add("timing", "pullback_to_ema21", 3.0)  # repli vers l'EMA21 en tendance haussiere

        # Rebond frais depuis le plus bas
        dl = ind.get("days_since_low")
        if dl is not None and dl < 15 and cp_day > 0.5:
            add("timing", "fresh_bounce", 5.0)

        # Evenements de volume
        vr = ind.get("volume_ratio")
        if vr is not None and vr > 2.5:
            if cp_day > 1:
                add("timing", "volume_breakout", 4.0)        # cassure confirmee par le volume
            elif cp_day < -3 and pos is not None and pos < 30:
                add("timing", "volume_capitulation", 3.0)    # climax vendeur pres du bas = fond probable
            elif cp_day < -3 and pos is not None and pos > 50:
                add("timing", "volume_distribution", -4.0)   # grosse vente en haut de cycle

        # Canal de Donchian 55j
        dc = ind.get("donchian_pos")
        if dc is not None:
            if dc > 0.98 and cp_day > 0:
                add("timing", "donchian_breakout", 3.0)
            elif dc < 0.10 and cp_day >= 0:
                add("timing", "donchian_low", 3.0)

        # Acceleration
        acc = ind.get("acceleration")
        if acc is not None:
            if acc > 5:    add("timing", "acceleration", 3.0)
            elif acc < -5: add("timing", "acceleration", -3.0)

    # Position 52 semaines (logique anti falling-knife conservee)
    if pos is not None:
        if pos < 5:
            if cp_day < -5:   v = -5.0
            elif cp_day < -2: v = 0.0
            else:             v = 6.0
        elif pos < 30:
            v = (30 - pos) / 30 * 8
            if cp_day < -5:
                v *= 0.4
        else:
            v = -(pos - 30) / 70 * 4
        add("timing", "position_52w", round(v, 1))

    # Variation du jour : pullback sain / panique / surchauffe
    if cp_day:
        if -7 < cp_day <= -2:
            add("timing", "pullback", round(abs(cp_day) / 7 * 4, 1))
        elif cp_day <= -7:
            add("timing", "panic_drop", round(-min((abs(cp_day) - 7) / 10 * 8 + 3, 10), 1))
        elif cp_day >= 7:
            add("timing", "overheated", round(-min((cp_day - 7) / 7 * 4, 5), 1))
    if perf1m is not None and perf1m > 25:
        add("timing", "overheated", -3.0)

    # ════════════════════ PILIER QUALITY ════════════════════
    has_fundamentals = any(s.get(k) is not None for k in
                           ("pe_ratio", "revenue_growth", "dividend_yield", "market_cap"))

    rg = s.get("revenue_growth")
    if rg is not None:
        rg_pct = rg * 100
        if rg_pct > 0:
            add("quality", "revenue_growth", round(min(rg_pct / 30, 1) * 10, 1))
        else:
            add("quality", "revenue_growth", round(max(rg_pct / 3, -8), 1))

    pe = s.get("pe_ratio")
    if pe is not None and pe > 0:
        if pe < 12:   v = 6.0
        elif pe < 25: v = 3.0
        elif pe < 40: v = 0.0
        else:
            # P/E eleve excusable si forte croissance (logique PEG)
            v = -1.0 if (rg is not None and rg * 100 > 30) else -5.0
        add("quality", "pe_ratio", v)

    dy = s.get("dividend_yield")
    if dy is not None:
        if 1.5 <= dy <= 6:
            add("quality", "dividend", 3.0)
        elif dy > 9:
            add("quality", "dividend_trap", -2.0)  # rendement anormal = signal de detresse

    mcap = s.get("market_cap")
    if mcap is not None:
        if mcap > 200_000_000_000:
            add("quality", "megacap_stability", 2.0)
        elif mcap < 2_000_000_000:
            add("quality", "smallcap_risk", -2.0)

    if ind:
        # Sortino (fallback Sharpe) : qualite du rendement ajuste du risque baissier
        sortino = ind.get("sortino")
        ratio = sortino if sortino is not None else ind.get("sharpe_like")
        if ratio is not None:
            key = "sortino" if sortino is not None else "sharpe"
            if ratio > 2:    add("quality", key, 6.0)
            elif ratio > 1:  add("quality", key, 4.0)
            elif ratio > 0:  add("quality", key, 1.0)
            elif ratio < -1: add("quality", key, -5.0)

        mdd = ind.get("max_drawdown")
        if mdd is not None:
            if mdd < 15:   add("quality", "max_drawdown", 4.0)
            elif mdd >= 50: add("quality", "max_drawdown", -6.0)
            elif mdd >= 30: add("quality", "max_drawdown", -3.0)

        vol = ind.get("volatility")
        if vol is not None:
            if vol > 80:  add("quality", "volatility", -5.0)
            elif vol > 50: add("quality", "volatility", -2.0)
            elif vol < 15: add("quality", "volatility", 2.0)

        udr = ind.get("up_day_ratio")
        if udr is not None:
            if udr > 0.60:  add("quality", "consistency", 3.0)
            elif udr < 0.40: add("quality", "consistency", -3.0)

    sent_data = sentiment or {}
    es = sent_data.get("earnings_surprise")
    if es is not None:
        if es >= 0.75:    add("quality", "earnings_surprise", 6.0)
        elif es >= 0.25:  add("quality", "earnings_surprise", 3.0)
        elif es <= -0.5:  add("quality", "earnings_surprise", -5.0)
        elif es <= -0.25: add("quality", "earnings_surprise", -2.5)

    # ════════════════════ PILIER SENTIMENT ════════════════════
    has_sentiment = False
    ns, nc = sent_data.get("news_sentiment"), sent_data.get("news_count", 0)
    if ns is not None and nc >= 3:
        has_sentiment = True
        mult = 1.25 if nc >= 10 else 1.0  # plus d'articles = signal plus fiable
        if ns > 0.5:    add("sentiment", "news_sentiment", 8.0 * mult)
        elif ns > 0.2:  add("sentiment", "news_sentiment", 4.0 * mult)
        elif ns < -0.5: add("sentiment", "news_sentiment", -10.0 * mult)
        elif ns < -0.2: add("sentiment", "news_sentiment", -5.0 * mult)

    analyst = sent_data.get("analyst")
    if analyst and analyst.get("total", 0) >= 3:
        has_sentiment = True
        bull = analyst["bullish_ratio"]
        if bull > 0.75:   add("sentiment", "analyst_consensus", 9.0)
        elif bull > 0.6:  add("sentiment", "analyst_consensus", 5.0)
        elif bull > 0.5:  add("sentiment", "analyst_consensus", 1.0)
        elif bull < 0.25: add("sentiment", "analyst_consensus", -9.0)
        elif bull < 0.4:  add("sentiment", "analyst_consensus", -5.0)

    ut = sent_data.get("analyst_upgrade")
    if ut is not None:
        has_sentiment = True
        if ut > 0.15:    add("sentiment", "analyst_trend", 5.0)
        elif ut > 0.05:  add("sentiment", "analyst_trend", 2.5)
        elif ut < -0.15: add("sentiment", "analyst_trend", -5.0)
        elif ut < -0.05: add("sentiment", "analyst_trend", -2.5)

    # ════════════════════ COMBINAISON PONDEREE ════════════════════
    pillars = {p: max(0.0, min(100.0, 50.0 + raw)) for p, raw in pillars_raw.items()}

    weights_by_regime = {
        "bull":    {"trend": 0.40, "timing": 0.20, "quality": 0.25, "sentiment": 0.15},
        "neutral": {"trend": 0.30, "timing": 0.30, "quality": 0.25, "sentiment": 0.15},
        "bear":    {"trend": 0.15, "timing": 0.35, "quality": 0.35, "sentiment": 0.15},
    }
    weights = dict(weights_by_regime[regime])

    # Piliers indisponibles → poids redistribues sur les autres
    available = {"trend": bool(ind), "timing": bool(ind) or pos is not None,
                 "quality": has_fundamentals or bool(ind),
                 "sentiment": has_sentiment}
    active = {p: w for p, w in weights.items() if available[p]}
    if not active:
        # Fallback minimal (quasi impossible) : neutre
        return {"score": 50, "tag": "neutral", "breakdown": {}, "pillars": pillars,
                "regime": regime, "confidence": 0, "risk_mult": 1.0, "version": 6,
                "weights": weights}
    w_total = sum(active.values())
    score = sum(pillars[p] * (w / w_total) for p, w in active.items())

    # ════════════════════ MULTIPLICATEUR DE RISQUE ════════════════════
    risk_mult = 1.0
    atr_pct = ind.get("atr_pct")
    if atr_pct is not None:
        if atr_pct > 6:   risk_mult -= 0.12
        elif atr_pct > 4: risk_mult -= 0.06
    vol = ind.get("volatility")
    if vol is not None:
        if vol > 80:  risk_mult -= 0.10
        elif vol > 60: risk_mult -= 0.05
    mdd = ind.get("max_drawdown")
    if mdd is not None and mdd > 60:
        risk_mult -= 0.08
    if adx is not None and adx > 30 and di_m is not None and di_p is not None and di_m > di_p:
        risk_mult -= 0.08  # downtrend puissant et en cours
    risk_mult = max(0.65, risk_mult)
    if score > 50 and risk_mult < 1.0:
        adjusted = 50 + (score - 50) * risk_mult
        breakdown["risk_adjustment"] = round(adjusted - score, 1)
        score = adjusted

    # ════════════════════ OVERLAY MACRO ════════════════════
    if macro_sentiment is not None:
        if macro_sentiment < -0.3:
            score -= 4; breakdown["macro_news_negative"] = -4.0
        elif macro_sentiment < -0.15:
            score -= 2; breakdown["macro_news_negative"] = -2.0
        elif macro_sentiment > 0.3:
            score += 3; breakdown["macro_news_positive"] = 3.0
        elif macro_sentiment > 0.15:
            score += 1.5; breakdown["macro_news_positive"] = 1.5

    if crisis_intensity is not None and crisis_intensity > 0.0:
        if crisis_intensity > 0.30 and score > 50:
            penalty = (score - 50) * 0.30
            score -= penalty
            breakdown["crisis_mode_strong"] = round(-penalty, 1)
        elif crisis_intensity > 0.15 and score > 60:
            penalty = (score - 60) * 0.20
            score -= penalty
            breakdown["crisis_mode"] = round(-penalty, 1)

    if vix is not None:
        if vix > 35 and score > 50:
            penalty = (score - 50) * 0.25
            score -= penalty
            breakdown["macro_fear_regime"] = round(-penalty, 1)
        elif vix > 25 and score > 60:
            penalty = (score - 60) * 0.15
            score -= penalty
            breakdown["macro_stress"] = round(-penalty, 1)
        elif vix < 13 and score > 75:
            penalty = (score - 75) * 0.15
            score -= penalty
            breakdown["macro_complacency"] = round(-penalty, 1)

    # ════════════════════ PLAFONDS REGIME BAISSIER ════════════════════
    if ind:
        bearish_signals = 0
        if ind.get("above_sma_200") is False: bearish_signals += 1
        if ind.get("above_sma_50")  is False: bearish_signals += 1
        if ind.get("golden_cross")  is False: bearish_signals += 1
        if ind.get("macd") and not ind["macd"].get("bullish"): bearish_signals += 1
        if ind.get("structure") == "LH_LL": bearish_signals += 1
        if adx is not None and adx > 25 and di_m is not None and di_p is not None and di_m > di_p:
            bearish_signals += 1
        rocs = [ind.get(k) for k in ("roc_1m", "roc_3m", "roc_6m")]
        valid = [r for r in rocs if r is not None]
        if valid and all(r <= 0 for r in valid):
            bearish_signals += 2

        # Preuve de retournement (divergence bull + survente forte) → plafond assoupli
        bottoming = (ind.get("rsi_divergence") == "bullish"
                     and breakdown.get("consensus_oversold", 0) >= 9)
        if bearish_signals >= 6:
            cap = 50 if bottoming else 40
        elif bearish_signals >= 4:
            cap = 60 if bottoming else 50
        elif bearish_signals >= 3:
            cap = 70 if bottoming else 65
        else:
            cap = None
        if cap is not None and score > cap:
            breakdown["bearish_regime_cap"] = round(cap - score, 1)
            score = cap

    score = max(0, min(100, score))

    # ════════════════════ CONFIANCE (couverture des donnees) ════════════════════
    confidence = 0
    if ind:
        confidence += 25
        if ind.get("sma_200") is not None:  confidence += 10  # historique >= 200j
        if ind.get("obv_trend") is not None or ind.get("mfi") is not None: confidence += 10
        if ind.get("adx") is not None:      confidence += 10
    if has_fundamentals:
        confidence += 15
    if has_sentiment:
        confidence += 15
        if nc >= 5: confidence += 7
        if analyst and analyst.get("total", 0) >= 5: confidence += 8
    confidence = min(100, confidence)

    if score >= 75:   tag = "hot"
    elif score >= 60: tag = "good"
    elif score >= 40: tag = "neutral"
    elif score >= 25: tag = "weak"
    else:             tag = "avoid"

    return {
        "score":      round(score),
        "tag":        tag,
        "breakdown":  breakdown,
        "pillars":    {p: round(v) for p, v in pillars.items()},
        "weights":    {p: round(active.get(p, 0) / w_total, 3) if p in active else 0
                       for p in weights},
        "regime":     regime,
        "confidence": confidence,
        "risk_mult":  round(risk_mult, 2),
        "version":    6,
    }


def compute_opportunity_score_v5(s: dict, indicators: dict | None = None,
                                 sentiment: dict | None = None, vix: float | None = None,
                                 macro_sentiment: float | None = None,
                                 crisis_intensity: float | None = None) -> dict:
    """LEGACY v5 — conserve pour comparaison dans le futur backtest (P9.1).
    Score additif 0-100. Remplace en prod par compute_opportunity_score (v6).
    """
    score = 50.0
    breakdown: dict[str, float] = {}

    # ── Position dans la fourchette 52 semaines ──
    # ATTENTION : "près du bas" ≠ opportunité si l'action chute encore fort.
    # On combine avec la variation du jour pour détecter les "couteaux qui tombent".
    pos = s.get("position_52w")
    cp_day = s.get("change_pct") or 0
    if pos is not None:
        if pos < 5:
            # Très près du plus bas annuel
            if cp_day < -5:
                v = -4.0   # toujours en chute libre = falling knife
            elif cp_day < -2:
                v = 0.0    # pas de signal clair
            else:
                v = 5.0    # stabilisation possible = vraie opportunité
        elif pos < 30:
            # Zone basse "saine" : bonus modéré
            v = (30 - pos) / 30 * 10
            # Réduit le bonus si l'action chute fort aujourd'hui
            if cp_day < -5:
                v *= 0.4
        else:
            v = -(pos - 30) / 70 * 5
        score += v
        breakdown["position_52w"] = round(v, 1)

    # ── Performance 1 mois ──
    perf = s.get("perf_1m")
    if perf is not None:
        if perf >= 0 and perf <= 20:
            v = perf / 20 * 8       # bonus jusqu'à 8 si momentum sain
        elif perf > 20:
            v = 8 - (perf - 20) / 30 * 5  # malus si surchauffe
            v = max(v, 0)
        else:  # perf négative
            v = max(perf * 0.6, -10)
        score += v
        breakdown["perf_1m"] = round(v, 1)

    # ── Croissance du revenu ──
    rg = s.get("revenue_growth")
    if rg is not None:
        rg_pct = rg * 100
        if rg_pct > 0:
            v = min(rg_pct / 30, 1) * 12  # max 12 si croissance >= 30%
        else:
            v = max(rg_pct / 3, -10)
        score += v
        breakdown["revenue_growth"] = round(v, 1)

    # ── P/E ratio ──
    pe = s.get("pe_ratio")
    if pe is not None and pe > 0:
        if pe < 12:
            v = 6.0    # sous-évalué
        elif pe < 25:
            v = 3.0    # valorisation correcte
        elif pe < 40:
            v = 0.0    # cher mais OK pour growth
        else:
            v = -5.0   # très cher
        score += v
        breakdown["pe_ratio"] = v

    # ── Dividende ──
    dy = s.get("dividend_yield")
    if dy is not None and 1.5 <= dy <= 6:
        score += 3
        breakdown["dividend"] = 3.0

    # ── Variation du jour : pullback sain vs panique vs surchauffe ──
    cp = s.get("change_pct")
    if cp is not None:
        if -7 < cp <= -2:
            # Pullback sain (-2% à -7%) : opportunité d'entrée raisonnable
            v = abs(cp) / 7 * 3.5
            breakdown["pullback"] = round(v, 1)
            score += v
        elif cp <= -7:
            # PANIQUE — chute violente du jour. Quasi toujours mauvaise nouvelle.
            v = -min((abs(cp) - 7) / 10 * 8 + 3, 10)
            breakdown["panic_drop"] = round(v, 1)
            score += v
        elif cp >= 7:
            # Surchauffe (FOMO / squeeze)
            v = -min((cp - 7) / 7 * 4, 5)
            breakdown["overheated"] = round(v, 1)
            score += v

    # ── Indicateurs techniques (si disponibles) ──
    if indicators:
        # ═══ CONSENSUS multi-indicateurs survente/surachat ═══
        # Plus de votes alignés = signal plus fiable
        oversold_votes = 0
        overbought_votes = 0
        rsi = indicators.get("rsi")
        if rsi is not None:
            if rsi < 30: oversold_votes += 1
            elif rsi > 70: overbought_votes += 1
        wr = indicators.get("williams_r")
        if wr is not None:
            if wr < -80: oversold_votes += 1
            elif wr > -20: overbought_votes += 1
        cci = indicators.get("cci")
        if cci is not None:
            if cci < -100: oversold_votes += 1
            elif cci > 100: overbought_votes += 1
        stoch = indicators.get("stochastic")
        if stoch is not None:
            if stoch < 20: oversold_votes += 1
            elif stoch > 80: overbought_votes += 1
        bb_pos = indicators.get("bb_position")
        if bb_pos is not None:
            if bb_pos < 0.15: oversold_votes += 1
            elif bb_pos > 0.85: overbought_votes += 1

        # Bonus/malus selon le consensus
        if oversold_votes >= 4:
            v = 12.0  # consensus FORT : survente confirmée
            breakdown["consensus_oversold"] = v
            score += v
        elif oversold_votes >= 3:
            v = 7.0
            breakdown["consensus_oversold"] = v
            score += v
        elif oversold_votes >= 2:
            v = 3.0
            breakdown["consensus_oversold"] = v
            score += v

        if overbought_votes >= 4:
            v = -10.0  # consensus FORT : surachat confirmé
            breakdown["consensus_overbought"] = v
            score += v
        elif overbought_votes >= 3:
            v = -6.0
            breakdown["consensus_overbought"] = v
            score += v
        elif overbought_votes >= 2:
            v = -3.0
            breakdown["consensus_overbought"] = v
            score += v

        # RSI seul (sans consensus) — petits ajustements
        if rsi is not None and oversold_votes < 2 and overbought_votes < 2:
            if rsi < 30:   v = 3.0
            elif rsi > 70: v = -3.0
            else:          v = 0.0
            if v:
                breakdown["rsi"] = v
                score += v

        # ═══ MACD ═══
        macd = indicators.get("macd")
        if macd:
            if macd.get("bullish"):
                hist = macd.get("histogram", 0)
                v = 5.0 + min(abs(hist) * 0.5, 3)
                breakdown["macd_bullish"] = round(v, 1)
            else:
                v = -3.0
                breakdown["macd_bearish"] = -3.0
            score += v

        # ═══ Golden / Death cross ═══
        if indicators.get("golden_cross"):
            score += 4
            breakdown["golden_cross"] = 4.0
        elif indicators.get("golden_cross") is False:
            score -= 3
            breakdown["death_cross"] = -3.0

        # ═══ Alignement multi-timeframes (ROC 1S, 1M, 3M, 6M) ═══
        rocs = [indicators.get(k) for k in ("roc_1w", "roc_1m", "roc_3m", "roc_6m")]
        valid = [r for r in rocs if r is not None]
        if len(valid) >= 3:
            positive = sum(1 for r in valid if r > 0)
            if positive == len(valid):
                score += 8
                breakdown["trend_aligned_up"] = 8.0
            elif positive == 0:
                score -= 8
                breakdown["trend_aligned_down"] = -8.0
            elif positive >= len(valid) - 1:
                score += 3
                breakdown["trend_mostly_up"] = 3.0

        # ═══ Force du trend (R² de la régression linéaire 90j) ═══
        # Trend persistent et bien établi = bonus si haussier, malus si baissier
        r2 = indicators.get("trend_r2")
        slope_pct = indicators.get("trend_slope_pct")
        if r2 is not None and slope_pct is not None and r2 > 0.5:
            # Tendance bien établie (R² > 0.5)
            if slope_pct > 0.1:
                v = min(r2 * 6, 6)
                breakdown["strong_uptrend"] = round(v, 1)
                score += v
            elif slope_pct < -0.1:
                v = -min(r2 * 6, 6)
                breakdown["strong_downtrend"] = round(v, 1)
                score += v

        # ═══ Volatilité ═══
        vol = indicators.get("volatility")
        if vol is not None:
            if vol > 80:       v = -5.0
            elif vol > 50:     v = -2.0
            elif vol < 15:     v = 2.0
            else:              v = 0.0
            if v:
                score += v
                breakdown["volatility"] = v

        # ═══ Maximum Drawdown (résilience) ═══
        mdd = indicators.get("max_drawdown")
        if mdd is not None:
            if mdd < 15:        v = 3.0    # très résilient
            elif mdd < 30:      v = 0.0
            elif mdd < 50:      v = -3.0
            else:               v = -6.0   # forte chute = vulnérable
            if v:
                score += v
                breakdown["max_drawdown"] = v

        # ═══ Sharpe-like (rendement ajusté du risque) ═══
        sharpe = indicators.get("sharpe_like")
        if sharpe is not None:
            if sharpe > 2:      v = 5.0    # excellent risk/reward
            elif sharpe > 1:    v = 3.0
            elif sharpe > 0:    v = 1.0
            elif sharpe < -1:   v = -4.0
            else:               v = 0.0
            if v:
                score += v
                breakdown["sharpe"] = v

        # ═══ Distance MM200 et MM50 ═══
        dist200 = indicators.get("dist_sma200")
        if dist200 is not None:
            if -8 < dist200 < -2:
                v = 4.0
                breakdown["pullback_to_sma200"] = v
                score += v
            elif dist200 > 30:
                v = -4.0
                breakdown["far_from_sma200"] = v
                score += v

        # ═══ Z-score : extrême de prix vs moyenne 50j ═══
        z = indicators.get("z_score_50")
        if z is not None:
            if z < -2:           v = 4.0   # 2 écarts-types sous moyenne = rebond probable
            elif z < -1.5:       v = 2.0
            elif z > 2:          v = -4.0  # 2 écarts-types au-dessus = correction probable
            elif z > 1.5:        v = -2.0
            else:                v = 0.0
            if v:
                score += v
                breakdown["z_score"] = v

        # ═══ Rebond depuis le plus bas 52 semaines ═══
        days_low = indicators.get("days_since_low")
        cp_day = s.get("change_pct") or 0
        if days_low is not None and days_low < 15 and cp_day > 0.5:
            # Plus bas récent + jour positif = vrai rebond
            v = 5.0
            breakdown["fresh_bounce"] = v
            score += v

        # ═══ Accélération du prix ═══
        accel = indicators.get("acceleration")
        if accel is not None:
            if accel > 5:        v = 4.0   # forte accélération haussière
            elif accel > 2:      v = 2.0
            elif accel < -5:     v = -3.0  # décélération marquée
            else:                v = 0.0
            if v:
                score += v
                breakdown["acceleration"] = v

        # ═══ Pic récent : pic 52w très récent = momentum continu ═══
        days_high = indicators.get("days_since_high")
        if days_high is not None:
            if days_high < 10 and cp_day > 0:
                v = 3.0
                breakdown["near_52w_high"] = v
                score += v
            elif days_high > 200:
                # Pic très ancien = perte de momentum
                v = -2.0
                breakdown["faded_momentum"] = v
                score += v

    # ═══════════════════════════════════════════════════════════════
    # ═══ SENTIMENT NEWS & RECOMMANDATIONS ANALYSTES ═══
    # ═══════════════════════════════════════════════════════════════
    if sentiment:
        # ── Sentiment des news ──
        ns = sentiment.get("news_sentiment")
        nc = sentiment.get("news_count", 0)
        if ns is not None and nc >= 3:
            # Seuils ajustés en fonction du nombre d'articles (plus = plus fiable)
            if ns > 0.5:       v = 5.0
            elif ns > 0.2:     v = 2.5
            elif ns < -0.5:    v = -6.0  # mauvaises news = signal très négatif
            elif ns < -0.2:    v = -3.0
            else:              v = 0.0
            if v:
                breakdown["news_sentiment"] = v
                score += v

        # ── Consensus analystes ──
        analyst = sentiment.get("analyst")
        if analyst and analyst.get("total", 0) >= 3:
            bull = analyst["bullish_ratio"]
            if bull > 0.75:    v = 7.0   # consensus achat très fort
            elif bull > 0.6:   v = 4.0
            elif bull > 0.5:   v = 1.0
            elif bull < 0.25:  v = -7.0
            elif bull < 0.4:   v = -4.0
            else:              v = 0.0
            if v:
                breakdown["analyst_consensus"] = v
                score += v

        # ── Tendance des recommandations (upgrades/downgrades) ──
        ut = sentiment.get("analyst_upgrade")
        if ut is not None:
            if ut > 0.15:      v = 4.0   # upgrade significatif sur 3 mois
            elif ut > 0.05:    v = 2.0
            elif ut < -0.15:   v = -4.0  # downgrade significatif
            elif ut < -0.05:   v = -2.0
            else:              v = 0.0
            if v:
                breakdown["analyst_trend"] = v
                score += v

        # ── Earnings surprise (beats vs misses sur 4 trimestres) ──
        es = sentiment.get("earnings_surprise")
        if es is not None:
            if es >= 0.75:     v = 5.0   # bat les estimations à répétition
            elif es >= 0.25:   v = 2.5
            elif es <= -0.5:   v = -4.0  # rate constamment
            elif es <= -0.25:  v = -2.0
            else:              v = 0.0
            if v:
                breakdown["earnings_surprise"] = v
                score += v

    # ═══ SENTIMENT MACRO DES NEWS (climat général du marché) ═══
    if macro_sentiment is not None:
        if macro_sentiment < -0.3:
            v = -4.0   # actu globale très négative
            breakdown["macro_news_negative"] = v
            score += v
        elif macro_sentiment < -0.15:
            v = -2.0
            breakdown["macro_news_negative"] = v
            score += v
        elif macro_sentiment > 0.3:
            v = 3.0
            breakdown["macro_news_positive"] = v
            score += v
        elif macro_sentiment > 0.15:
            v = 1.5
            breakdown["macro_news_positive"] = v
            score += v

    # ═══ MODE CRISE DÉTECTÉ (mots-clés guerre/krach/récession dans les news) ═══
    if crisis_intensity is not None and crisis_intensity > 0.0:
        if crisis_intensity > 0.30:
            # Très forte présence de mots-crises → mode défensif fort
            if score > 50:
                penalty = (score - 50) * 0.30
                score -= penalty
                breakdown["crisis_mode_strong"] = round(-penalty, 1)
        elif crisis_intensity > 0.15:
            # Présence notable → léger mode défensif
            if score > 60:
                penalty = (score - 60) * 0.20
                score -= penalty
                breakdown["crisis_mode"] = round(-penalty, 1)

    # ═══ CONTEXTE MACRO (VIX) ═══
    # Le VIX est l'indice de la peur. Quand le VIX est très élevé,
    # les signaux haussiers individuels sont moins fiables (panique générale).
    if vix is not None:
        if vix > 35:
            # Panique générale — beaucoup de faux signaux. Pénalise les scores > 50.
            if score > 50:
                penalty = (score - 50) * 0.25
                score -= penalty
                breakdown["macro_fear_regime"] = round(-penalty, 1)
        elif vix > 25:
            # Stress de marché
            if score > 60:
                penalty = (score - 60) * 0.15
                score -= penalty
                breakdown["macro_stress"] = round(-penalty, 1)
        elif vix < 13:
            # Complaisance — méfier des bullish trop forts
            if score > 75:
                penalty = (score - 75) * 0.15
                score -= penalty
                breakdown["macro_complacency"] = round(-penalty, 1)

    # ── Détection régime baissier confirmé ──
    # Si plusieurs signaux baissiers s'alignent, on PLAFONNE le score à 50
    # pour éviter les "couteaux qui tombent" (falling knives)
    if indicators:
        bearish_signals = 0
        if indicators.get("above_sma_200") is False:                bearish_signals += 1
        if indicators.get("above_sma_50")  is False:                bearish_signals += 1
        if indicators.get("golden_cross")  is False:                bearish_signals += 1
        if indicators.get("macd") and not indicators["macd"].get("bullish"): bearish_signals += 1
        rocs = [indicators.get(k) for k in ("roc_1m", "roc_3m", "roc_6m")]
        valid = [r for r in rocs if r is not None]
        if valid and sum(1 for r in valid if r > 0) == 0:
            bearish_signals += 2   # tous les timeframes en baisse = très bearish

        if bearish_signals >= 4:
            # Régime baissier confirmé : on plafonne à 50 (= "NEUTRE" max)
            if score > 50:
                breakdown["bearish_regime_cap"] = round(50 - score, 1)
            score = min(score, 50)
        elif bearish_signals >= 3:
            # Régime baissier partiel : plafond à 65 (= "GOOD" max)
            if score > 65:
                breakdown["bearish_regime_cap"] = round(65 - score, 1)
            score = min(score, 65)

    # Clamp 0-100
    score = max(0, min(100, score))

    # Tag synthétique
    if score >= 75:
        tag = "hot"
    elif score >= 60:
        tag = "good"
    elif score >= 40:
        tag = "neutral"
    elif score >= 25:
        tag = "weak"
    else:
        tag = "avoid"

    return {"score": round(score), "tag": tag, "breakdown": breakdown}


def _ema_series(prices: list[float], period: int) -> list[float]:
    """Série EMA (Exponential Moving Average). Retourne 1 valeur par close à partir de l'indice `period-1`."""
    if len(prices) < period:
        return []
    k = 2 / (period + 1)
    out = []
    ema = sum(prices[:period]) / period
    out.append(ema)
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
        out.append(ema)
    return out


def _rsi_series(closes: list[float], period: int = 14) -> list[float]:
    """Serie RSI Wilder complete (une valeur par close a partir de l'indice period)."""
    if len(closes) < period + 1:
        return []
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out = []
    rs = avg_gain / avg_loss if avg_loss else float("inf")
    out.append(100 - 100 / (1 + rs) if avg_loss else 100.0)
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            out.append(100.0)
        else:
            rs = avg_gain / avg_loss
            out.append(100 - 100 / (1 + rs))
    return out


def _linreg_slope(ys: list[float]) -> float:
    """Pente d'une regression lineaire simple sur ys (x = 0..n-1)."""
    n = len(ys)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = sum(ys) / n
    num = sum((i - x_mean) * (ys[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n)) or 1
    return num / den


def compute_indicators(closes: list[float], highs: list[float] | None = None,
                       lows: list[float] | None = None,
                       volumes: list[float] | None = None) -> dict:
    """Calcule un set complet d'indicateurs techniques a partir des series OHLCV :
    RSI, MACD, MM 50/200, EMA21, Bollinger, Stochastic, ROC multi-TF, Volatilite,
    ATR, ADX/DI, OBV, MFI, CMF, volume ratio, divergence RSI, Donchian,
    structure HH/HL, Sortino, up-day ratio.
    Highs/lows/volumes optionnels : les indicateurs qui en dependent sont
    simplement omis s'ils manquent (compat anciennes series closes-only).
    """
    if not closes or len(closes) < 30:
        return {}

    current = closes[-1]
    out: dict = {}

    has_hl  = bool(highs and lows and len(highs) == len(closes) and len(lows) == len(closes))
    has_vol = bool(volumes and len(volumes) == len(closes) and any(v > 0 for v in volumes[-30:]))

    # ── SMA ──
    if len(closes) >= 50:
        out["sma_50"] = round(sum(closes[-50:]) / 50, 4)
    if len(closes) >= 200:
        out["sma_200"] = round(sum(closes[-200:]) / 200, 4)

    # ── EMA 21 (tendance court terme, tres suivie par les swing traders) ──
    ema21 = _ema_series(closes, 21)
    if ema21:
        out["ema_21"] = round(ema21[-1], 4)
        out["dist_ema21"] = round((current / ema21[-1] - 1) * 100, 2) if ema21[-1] else None

    # ── RSI 14 (Wilder) ──
    if len(closes) >= 15:
        gains, losses = [], []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(diff, 0))
            losses.append(abs(min(diff, 0)))
        period = 14
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        out["rsi"] = round(rsi, 1)

    # ── MACD (12, 26, 9) ──
    if len(closes) >= 35:
        ema12 = _ema_series(closes, 12)
        ema26 = _ema_series(closes, 26)
        offset12 = len(closes) - len(ema12)
        offset26 = len(closes) - len(ema26)
        start = max(offset12, offset26)
        macd_line = [ema12[i - offset12] - ema26[i - offset26] for i in range(start, len(closes))]
        signal = _ema_series(macd_line, 9)
        if signal:
            macd_now = macd_line[-1]
            sig_now = signal[-1]
            hist_now = macd_now - sig_now
            # Pente de l'histogramme : le momentum accelere ou s'essouffle ?
            # (signal precoce de retournement, avant le croisement lui-meme)
            hist_slope = None
            if len(signal) >= 4:
                off = len(macd_line) - len(signal)
                hist_prev = macd_line[off + len(signal) - 4] - signal[-4]
                hist_slope = hist_now - hist_prev
            out["macd"] = {
                "macd":       round(macd_now, 4),
                "signal":     round(sig_now, 4),
                "histogram":  round(hist_now, 4),
                "bullish":    macd_now > sig_now,
                "hist_slope": round(hist_slope, 4) if hist_slope is not None else None,
            }

    # ── Bollinger Bands (20, 2σ) ──
    if len(closes) >= 20:
        recent = closes[-20:]
        mean = sum(recent) / 20
        var = sum((p - mean) ** 2 for p in recent) / 20
        std = var ** 0.5
        upper = mean + 2 * std
        lower = mean - 2 * std
        out["bb_upper"]  = round(upper, 4)
        out["bb_lower"]  = round(lower, 4)
        out["bb_middle"] = round(mean, 4)
        if upper != lower:
            out["bb_position"] = round((current - lower) / (upper - lower), 3)

    # ── Stochastic Oscillator (%K, 14 jours) ──
    if len(closes) >= 14:
        rec = closes[-14:]
        lo, hi = min(rec), max(rec)
        if hi != lo:
            out["stochastic"] = round((current - lo) / (hi - lo) * 100, 1)

    # ── Rate of Change multi-timeframes ──
    if len(closes) >= 6 and closes[-6]:
        out["roc_1w"] = round((current / closes[-6] - 1) * 100, 2)
    if len(closes) >= 22 and closes[-22]:
        out["roc_1m"] = round((current / closes[-22] - 1) * 100, 2)
    if len(closes) >= 66 and closes[-66]:
        out["roc_3m"] = round((current / closes[-66] - 1) * 100, 2)
    if len(closes) >= 132 and closes[-132]:
        out["roc_6m"] = round((current / closes[-132] - 1) * 100, 2)

    # ── Volatilité annualisée (21 jours) ──
    if len(closes) >= 22:
        rets = []
        for i in range(-21, 0):
            if closes[i - 1]:
                rets.append(closes[i] / closes[i - 1] - 1)
        if rets:
            mean_r = sum(rets) / len(rets)
            var_r = sum((r - mean_r) ** 2 for r in rets) / len(rets)
            out["volatility"] = round((var_r ** 0.5) * (252 ** 0.5) * 100, 2)

    # ── Distance par rapport à la MM200 (en %) ──
    if "sma_200" in out and out["sma_200"]:
        out["dist_sma200"] = round((current / out["sma_200"] - 1) * 100, 2)
    if "sma_50" in out and out["sma_50"]:
        out["dist_sma50"] = round((current / out["sma_50"] - 1) * 100, 2)

    # ── CCI (Commodity Channel Index, 20 jours) ──
    if len(closes) >= 20:
        rec = closes[-20:]
        mean20 = sum(rec) / 20
        mean_dev = sum(abs(p - mean20) for p in rec) / 20
        if mean_dev:
            cci = (current - mean20) / (0.015 * mean_dev)
            out["cci"] = round(cci, 1)

    # ── Williams %R (14 jours) ──
    if len(closes) >= 14:
        rec = closes[-14:]
        hi, lo = max(rec), min(rec)
        if hi != lo:
            out["williams_r"] = round((hi - current) / (hi - lo) * -100, 1)

    # ── Maximum Drawdown sur la période ──
    if len(closes) >= 50:
        peak = closes[0]
        max_dd = 0
        for p in closes:
            if p > peak:
                peak = p
            dd = (peak - p) / peak * 100 if peak else 0
            if dd > max_dd:
                max_dd = dd
        out["max_drawdown"] = round(max_dd, 1)

    # ── Jours depuis le plus haut / plus bas 52 semaines ──
    if len(closes) >= 50:
        recent_year = closes[-252:] if len(closes) > 252 else closes
        hi_idx = max(range(len(recent_year)), key=lambda i: recent_year[i])
        lo_idx = min(range(len(recent_year)), key=lambda i: recent_year[i])
        out["days_since_high"] = len(recent_year) - 1 - hi_idx
        out["days_since_low"]  = len(recent_year) - 1 - lo_idx

    # ── Régression linéaire 90 jours : pente + R² (force du trend) ──
    if len(closes) >= 90:
        n = 90
        ys = closes[-n:]
        xs = list(range(n))
        x_mean = (n - 1) / 2
        y_mean = sum(ys) / n
        num = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
        den = sum((x - x_mean) ** 2 for x in xs) or 1
        slope = num / den
        # R² : qualité du fit linéaire
        y_pred = [y_mean + slope * (x - x_mean) for x in xs]
        ss_res = sum((ys[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y - y_mean) ** 2 for y in ys) or 1
        r2 = 1 - ss_res / ss_tot
        # Pente normalisée en % par jour
        slope_pct = (slope / y_mean) * 100 if y_mean else 0
        out["trend_slope_pct"] = round(slope_pct, 3)
        out["trend_r2"]        = round(max(0, min(1, r2)), 3)

    # ── Z-score : écart par rapport à la moyenne 50 jours ──
    if len(closes) >= 50:
        rec = closes[-50:]
        mean50 = sum(rec) / 50
        var50 = sum((p - mean50) ** 2 for p in rec) / 50
        std50 = var50 ** 0.5
        if std50:
            out["z_score_50"] = round((current - mean50) / std50, 2)

    # ── Sharpe & Sortino (sur ~6 mois, methode coherente) ──
    if len(closes) >= 60:
        window = closes[-126:] if len(closes) > 126 else closes
        rets = [window[i] / window[i - 1] - 1 for i in range(1, len(window)) if window[i - 1]]
        if len(rets) >= 30:
            mean_r = sum(rets) / len(rets)
            var_r = sum((r - mean_r) ** 2 for r in rets) / len(rets)
            std_r = var_r ** 0.5
            if std_r > 0:
                out["sharpe_like"] = round(mean_r / std_r * (252 ** 0.5), 2)
            # Sortino : ne penalise que la volatilite BAISSIERE
            downside = [min(r, 0) ** 2 for r in rets]
            dd = (sum(downside) / len(downside)) ** 0.5
            if dd > 0:
                out["sortino"] = round(mean_r / dd * (252 ** 0.5), 2)
            # Ratio de jours haussiers (qualite/regularite du trend)
            out["up_day_ratio"] = round(sum(1 for r in rets[-50:] if r > 0) / min(len(rets), 50), 3)

    # ── Accélération du prix : ROC court vs ROC moyen ──
    if "roc_1w" in out and "roc_1m" in out:
        # Acceleration = momentum court terme - momentum moyen terme
        # > 0 : ça accélère, < 0 : ça décélère
        out["acceleration"] = round(out["roc_1w"] * 4 - out["roc_1m"], 2)

    # ── Distance au plus haut 52 semaines (en %, toujours <= 0) ──
    year = closes[-252:] if len(closes) > 252 else closes
    hi_52 = max(year)
    if hi_52:
        out["dist_52w_high"] = round((current / hi_52 - 1) * 100, 2)

    # ── Donchian position (canal 55 jours — breakout/breakdown) ──
    if len(closes) >= 55:
        ch = (highs[-55:] if has_hl else closes[-55:])
        cl = (lows[-55:]  if has_hl else closes[-55:])
        d_hi, d_lo = max(ch), min(cl)
        if d_hi != d_lo:
            out["donchian_pos"] = round((current - d_lo) / (d_hi - d_lo), 3)

    # ── Structure de tendance HH/HL vs LH/LL (3 fenetres de 40 jours) ──
    if len(closes) >= 120:
        w1, w2, w3 = closes[-120:-80], closes[-80:-40], closes[-40:]
        if max(w1) < max(w2) < max(w3) and min(w1) < min(w2) < min(w3):
            out["structure"] = "HH_HL"   # plus hauts + plus bas ascendants = uptrend sain
        elif max(w1) > max(w2) > max(w3) and min(w1) > min(w2) > min(w3):
            out["structure"] = "LH_LL"   # tout descend = downtrend confirme
        else:
            out["structure"] = None

    # ── Divergence RSI (signal de retournement puissant) ──
    rsi_ser = _rsi_series(closes)
    if len(rsi_ser) >= 40:
        # Compare le plus bas prix des 12 derniers jours au plus bas des 13-40 jours
        off = len(closes) - len(rsi_ser)
        rec_n = 12
        old_lo_i = min(range(len(closes) - 40, len(closes) - rec_n), key=lambda i: closes[i])
        rec_lo_i = min(range(len(closes) - rec_n, len(closes)),      key=lambda i: closes[i])
        old_hi_i = max(range(len(closes) - 40, len(closes) - rec_n), key=lambda i: closes[i])
        rec_hi_i = max(range(len(closes) - rec_n, len(closes)),      key=lambda i: closes[i])
        div = None
        if (closes[rec_lo_i] < closes[old_lo_i] and rec_lo_i - off >= 0 and old_lo_i - off >= 0
                and rsi_ser[rec_lo_i - off] > rsi_ser[old_lo_i - off] + 3):
            div = "bullish"   # prix fait un plus bas, RSI refuse de suivre → vendeurs s'epuisent
        elif (closes[rec_hi_i] > closes[old_hi_i] and rec_hi_i - off >= 0 and old_hi_i - off >= 0
                and rsi_ser[rec_hi_i - off] < rsi_ser[old_hi_i - off] - 3):
            div = "bearish"   # prix fait un plus haut, RSI s'essouffle → acheteurs s'epuisent
        out["rsi_divergence"] = div

    # ═══════════ Indicateurs High/Low (ATR, ADX) ═══════════
    if has_hl and len(closes) >= 29:
        # ── ATR 14 (volatilite "vraie", gaps inclus) en % du prix ──
        trs = []
        for i in range(1, len(closes)):
            tr = max(highs[i] - lows[i],
                     abs(highs[i] - closes[i - 1]),
                     abs(lows[i]  - closes[i - 1]))
            trs.append(tr)
        period = 14
        atr = sum(trs[:period]) / period
        for t in trs[period:]:
            atr = (atr * (period - 1) + t) / period
        if current:
            out["atr_pct"] = round(atr / current * 100, 2)

        # ── ADX 14 + DI+ / DI- (force et direction du trend) ──
        plus_dm, minus_dm = [], []
        for i in range(1, len(closes)):
            up = highs[i] - highs[i - 1]
            dn = lows[i - 1] - lows[i]
            plus_dm.append(up if (up > dn and up > 0) else 0.0)
            minus_dm.append(dn if (dn > up and dn > 0) else 0.0)
        # Lissage Wilder
        sm_tr   = sum(trs[:period])
        sm_pdm  = sum(plus_dm[:period])
        sm_mdm  = sum(minus_dm[:period])
        dxs = []
        for i in range(period, len(trs)):
            sm_tr  = sm_tr  - sm_tr / period  + trs[i]
            sm_pdm = sm_pdm - sm_pdm / period + plus_dm[i]
            sm_mdm = sm_mdm - sm_mdm / period + minus_dm[i]
            if sm_tr:
                di_p = sm_pdm / sm_tr * 100
                di_m = sm_mdm / sm_tr * 100
                if di_p + di_m:
                    dxs.append(abs(di_p - di_m) / (di_p + di_m) * 100)
        if len(dxs) >= period:
            adx = sum(dxs[:period]) / period
            for d in dxs[period:]:
                adx = (adx * (period - 1) + d) / period
            out["adx"] = round(adx, 1)
            if sm_tr:
                out["di_plus"]  = round(sm_pdm / sm_tr * 100, 1)
                out["di_minus"] = round(sm_mdm / sm_tr * 100, 1)

    # ═══════════ Indicateurs Volume (OBV, MFI, CMF, spike) ═══════════
    if has_vol:
        # ── Volume ratio : volume du jour vs moyenne 20j (spike detection) ──
        if len(volumes) >= 21:
            avg_vol20 = sum(volumes[-21:-1]) / 20
            if avg_vol20 > 0:
                out["volume_ratio"] = round(volumes[-1] / avg_vol20, 2)

        # ── OBV (On-Balance Volume) : le volume confirme-t-il le prix ? ──
        if len(closes) >= 21:
            obv = 0.0
            obv_ser = [0.0]
            for i in range(1, len(closes)):
                if closes[i] > closes[i - 1]:
                    obv += volumes[i]
                elif closes[i] < closes[i - 1]:
                    obv -= volumes[i]
                obv_ser.append(obv)
            avg_vol = sum(volumes[-20:]) / 20
            if avg_vol > 0:
                # Variation OBV sur 20j normalisee par le volume moyen → [-20, +20] env.
                out["obv_trend"] = round((obv_ser[-1] - obv_ser[-21]) / avg_vol, 2)

        # ── MFI 14 (RSI pondere par le volume) ──
        if has_hl and len(closes) >= 15:
            tps = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(len(closes))]
            pos_mf = neg_mf = 0.0
            for i in range(len(tps) - 14, len(tps)):
                mf = tps[i] * volumes[i]
                if tps[i] > tps[i - 1]:
                    pos_mf += mf
                elif tps[i] < tps[i - 1]:
                    neg_mf += mf
            if pos_mf + neg_mf > 0:
                out["mfi"] = round(100 * pos_mf / (pos_mf + neg_mf), 1)

        # ── Chaikin Money Flow 20j (accumulation vs distribution) ──
        if has_hl and len(closes) >= 20:
            mfv_sum = vol_sum = 0.0
            for i in range(len(closes) - 20, len(closes)):
                hl = highs[i] - lows[i]
                if hl > 0:
                    mult = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / hl
                    mfv_sum += mult * volumes[i]
                vol_sum += volumes[i]
            if vol_sum > 0:
                out["cmf"] = round(mfv_sum / vol_sum, 3)

    # ── Indicateurs synthétiques ──
    if "sma_50" in out:
        out["above_sma_50"] = current > out["sma_50"]
    if "sma_200" in out:
        out["above_sma_200"] = current > out["sma_200"]
    if "sma_50" in out and "sma_200" in out:
        out["golden_cross"] = out["sma_50"] > out["sma_200"]

    return out


async def get_stock_detail(symbol: str, period: str = "1y") -> dict | None:
    """Renvoie tout ce qu'il faut pour le modal détail d'une action.
    Fonctionne pour les tickers de la watchlist OU n'importe quel ticker Yahoo."""
    all_stocks = await _get_all_stocks()
    base = next((s for s in all_stocks if s["ticker"] == symbol), None)

    async with httpx.AsyncClient(timeout=15) as client:
        if not base:
            # Ticker hors watchlist : fetch à la volée
            meta = {"symbol": symbol, "name": symbol, "sector": "—", "currency": "USD", "tr": True}
            fetched = await _fetch_full(meta, client)
            if not fetched:
                return None
            base = fetched

        history, news = await asyncio.gather(
            _fetch_yahoo_history(symbol, period, client),
            _fetch_company_news(symbol, client),
        )

    # Indicateurs + score sont déjà dans `base` (calculés au fetch initial)
    return {**base, "period": period, "history": history, "news": news}


# ── Recherche de tickers ──────────────────────────────────────────────

async def get_custom_watchlist(symbols: list[str]) -> list[dict]:
    """Fetch arbitrary tickers (utilisateur). Réutilise le cache global si dispo."""
    if not symbols:
        return []
    all_stocks = await _get_all_stocks()
    cached_by_ticker = {s["ticker"]: s for s in all_stocks}

    to_fetch = []
    results = []
    for sym in symbols:
        if sym in cached_by_ticker:
            results.append(cached_by_ticker[sym])
        else:
            to_fetch.append({"symbol": sym, "name": sym, "sector": "—", "currency": "USD", "tr": True})

    if to_fetch:
        async with httpx.AsyncClient(timeout=20) as client:
            fetched = await asyncio.gather(*[_fetch_full(m, client) for m in to_fetch])
        results.extend([r for r in fetched if r])
    return results


INDICES = [
    # ── Indices boursiers mondiaux ──
    {"symbol": "^FCHI",     "name": "CAC 40",         "category": "index"},
    {"symbol": "^GSPC",     "name": "S&P 500",        "category": "index"},
    {"symbol": "^IXIC",     "name": "Nasdaq",         "category": "index"},
    {"symbol": "^DJI",      "name": "Dow Jones",      "category": "index"},
    {"symbol": "^RUT",      "name": "Russell 2000",   "category": "index"},
    {"symbol": "^GDAXI",    "name": "DAX",            "category": "index"},
    {"symbol": "^FTSE",     "name": "FTSE 100",       "category": "index"},
    {"symbol": "^N225",     "name": "Nikkei",         "category": "index"},
    {"symbol": "^STOXX50E", "name": "Euro Stoxx 50",  "category": "index"},
    {"symbol": "^HSI",      "name": "Hang Seng",      "category": "index"},
    {"symbol": "^BSESN",    "name": "BSE Sensex",     "category": "index"},
    {"symbol": "^KS11",     "name": "KOSPI",          "category": "index"},
    {"symbol": "^AXJO",     "name": "ASX 200",        "category": "index"},
    {"symbol": "^GSPTSE",   "name": "TSX (Canada)",   "category": "index"},
    {"symbol": "^BVSP",     "name": "Bovespa",        "category": "index"},
    {"symbol": "^MXX",      "name": "IPC Mexico",     "category": "index"},
    {"symbol": "^IBEX",     "name": "IBEX 35",        "category": "index"},
    {"symbol": "FTSEMIB.MI","name": "FTSE MIB",       "category": "index"},
    {"symbol": "^AEX",      "name": "AEX",            "category": "index"},
    {"symbol": "^SSMI",     "name": "SMI Suisse",     "category": "index"},
    {"symbol": "^VIX",      "name": "VIX (volatilité)","category": "index"},

    # ── Forex majeurs ──
    {"symbol": "EURUSD=X", "name": "EUR/USD", "category": "forex"},
    {"symbol": "EURGBP=X", "name": "EUR/GBP", "category": "forex"},
    {"symbol": "EURJPY=X", "name": "EUR/JPY", "category": "forex"},
    {"symbol": "EURCHF=X", "name": "EUR/CHF", "category": "forex"},
    {"symbol": "GBPUSD=X", "name": "GBP/USD", "category": "forex"},
    {"symbol": "USDJPY=X", "name": "USD/JPY", "category": "forex"},
    {"symbol": "USDCHF=X", "name": "USD/CHF", "category": "forex"},
    {"symbol": "AUDUSD=X", "name": "AUD/USD", "category": "forex"},
    {"symbol": "USDCAD=X", "name": "USD/CAD", "category": "forex"},
    {"symbol": "USDCNY=X", "name": "USD/CNY", "category": "forex"},
    {"symbol": "DX-Y.NYB", "name": "DXY (Dollar Index)","category": "forex"},

    # ── Matières premières ──
    {"symbol": "GC=F",     "name": "Or",          "category": "commodity"},
    {"symbol": "SI=F",     "name": "Argent",      "category": "commodity"},
    {"symbol": "PL=F",     "name": "Platine",     "category": "commodity"},
    {"symbol": "PA=F",     "name": "Palladium",   "category": "commodity"},
    {"symbol": "HG=F",     "name": "Cuivre",      "category": "commodity"},
    {"symbol": "CL=F",     "name": "Pétrole WTI", "category": "commodity"},
    {"symbol": "BZ=F",     "name": "Brent",       "category": "commodity"},
    {"symbol": "NG=F",     "name": "Gaz nat.",    "category": "commodity"},
    {"symbol": "HO=F",     "name": "Fioul",       "category": "commodity"},
    {"symbol": "RB=F",     "name": "Essence",     "category": "commodity"},
    {"symbol": "ZW=F",     "name": "Blé",         "category": "commodity"},
    {"symbol": "ZC=F",     "name": "Maïs",        "category": "commodity"},
    {"symbol": "ZS=F",     "name": "Soja",        "category": "commodity"},
    {"symbol": "KC=F",     "name": "Café",        "category": "commodity"},
    {"symbol": "SB=F",     "name": "Sucre",       "category": "commodity"},
    {"symbol": "CC=F",     "name": "Cacao",       "category": "commodity"},
]


async def get_calendar() -> dict:
    """Calendrier économique + earnings via Finnhub (7 jours à venir)."""
    key = "calendar"
    if key in _cache and time.time() - _cache[key]["ts"] < 3600:  # cache 1h
        return _cache[key]["data"]

    if not FINNHUB_API_KEY:
        return {"economic": [], "earnings": []}

    from datetime import date, timedelta
    today = date.today()
    end = today + timedelta(days=7)
    params = {"from": today.isoformat(), "to": end.isoformat(), "token": FINNHUB_API_KEY}

    async def fetch_eco(client):
        try:
            r = await client.get(f"{FINNHUB_BASE}/calendar/economic", params=params, timeout=8)
            if r.status_code != 200: return []
            events = r.json().get("economicCalendar", []) or []
            return [{
                "time":     e.get("time"),
                "country":  e.get("country"),
                "event":    e.get("event"),
                "impact":   e.get("impact"),
                "actual":   e.get("actual"),
                "estimate": e.get("estimate"),
                "prev":     e.get("prev"),
                "unit":     e.get("unit"),
            } for e in events[:150]]
        except Exception as exc:
            print(f"[calendar] eco error: {exc}")
            return []

    async def fetch_earnings(client):
        try:
            r = await client.get(f"{FINNHUB_BASE}/calendar/earnings", params=params, timeout=8)
            if r.status_code != 200: return []
            events = r.json().get("earningsCalendar", []) or []
            return [{
                "date":      e.get("date"),
                "symbol":    e.get("symbol"),
                "hour":      e.get("hour"),
                "epsEst":    e.get("epsEstimate"),
                "revEst":    e.get("revenueEstimate"),
                "year":      e.get("year"),
                "quarter":   e.get("quarter"),
            } for e in events if e.get("symbol")][:150]
        except Exception as exc:
            print(f"[calendar] earnings error: {exc}")
            return []

    async with httpx.AsyncClient() as client:
        eco, earn = await asyncio.gather(fetch_eco(client), fetch_earnings(client))

    data = {"economic": eco, "earnings": earn}
    if eco or earn:
        _cache[key] = {"data": data, "ts": time.time()}
    return data


async def get_indices() -> list[dict]:
    key = "indices"
    if key in _cache and time.time() - _cache[key]["ts"] < CACHE_TTL:
        return _cache[key]["data"]

    async def fetch(idx, client):
        symbol = idx["symbol"]
        try:
            resp = await client.get(
                f"{YAHOO_BASE}/{symbol}",
                params={"range": "5d", "interval": "1d"},
                headers=HEADERS, timeout=8,
            )
            if resp.status_code != 200:
                return None
            result = resp.json().get("chart", {}).get("result", [])
            if not result:
                return None
            m = result[0].get("meta", {})
            closes = [c for c in (result[0].get("indicators", {}).get("quote", [{}])[0].get("close") or []) if c is not None]
            if len(closes) < 2:
                return None
            current = float(m.get("regularMarketPrice") or closes[-1])
            prev    = _previous_close(m, closes, current)
            change_pct = ((current - prev) / prev * 100) if prev else 0
            return {
                "symbol":     symbol,
                "name":       idx["name"],
                "category":   idx["category"],
                "value":      round(current, 4 if idx["category"] == "forex" else 2),
                "change_pct": round(change_pct, 2),
                "currency":   m.get("currency", ""),
            }
        except Exception:
            return None

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[fetch(i, client) for i in INDICES])
    data = [r for r in results if r]
    if data:
        _cache[key] = {"data": data, "ts": time.time()}
    return data


async def search_tickers(query: str, limit: int = 10) -> list[dict]:
    """Recherche via Yahoo Finance — actions, ETFs, indices, crypto."""
    if not query or len(query) < 1:
        return []
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                "https://query1.finance.yahoo.com/v1/finance/search",
                params={"q": query, "quotesCount": limit, "newsCount": 0},
                headers=HEADERS,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            quotes = data.get("quotes", [])
            return [{
                "symbol":   q.get("symbol", ""),
                "name":     q.get("longname") or q.get("shortname") or q.get("symbol", ""),
                "exchange": q.get("exchDisp") or q.get("exchange", ""),
                "type":     q.get("quoteType", ""),
            } for q in quotes if q.get("symbol")][:limit]
    except Exception as exc:
        print(f"[stocks] search error {query}: {exc}")
        return []
