import httpx
import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

_cache: dict = {}
CACHE_TTL = 300

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

POSITIVE_WORDS = {
    "gain", "rise", "jump", "surge", "soar", "beat", "record", "high",
    "rally", "bull", "growth", "profit", "strong", "boost", "up",
    "recover", "rebound", "outperform", "upgrade", "buy",
}
NEGATIVE_WORDS = {
    "fall", "drop", "crash", "decline", "lose", "miss", "low", "bear",
    "loss", "cut", "fear", "risk", "warn", "weak", "down", "sell",
    "downgrade", "recession", "debt", "layoff", "bankrupt",
}
# Mots-clés "crise" — déclenchent un mode défensif sur tous les scores
CRISIS_WORDS = {
    "war", "crisis", "crash", "collapse", "default", "bankruptcy",
    "recession", "plunge", "selloff", "sell-off", "panic", "contagion",
    "sanction", "sanctions", "conflict", "tariff", "tariffs", "shutdown",
    "lockdown", "pandemic", "outbreak", "attack", "invasion", "missile",
    "strike", "stagflation", "inflation", "hike",
}


def _time_ago(ts: int) -> str:
    now = datetime.now(timezone.utc).timestamp()
    diff = now - ts
    if diff < 60:
        return "À l'instant"
    if diff < 3600:
        return f"Il y a {int(diff / 60)} min"
    if diff < 86400:
        return f"Il y a {int(diff / 3600)} h"
    return f"Il y a {int(diff / 86400)} j"


def _sentiment(headline: str) -> str:
    words = headline.lower().split()
    pos = sum(1 for w in words if w.strip(".,!?") in POSITIVE_WORDS)
    neg = sum(1 for w in words if w.strip(".,!?") in NEGATIVE_WORDS)
    if pos > neg:
        return "positif"
    if neg > pos:
        return "négatif"
    return "neutre"


async def get_macro_context() -> dict:
    """Analyse globale du flux d'actualités générales :
    - Sentiment global (positif/négatif sur 50 derniers titres)
    - Intensité de crise (% de titres contenant des mots-clés "crise")
    Cache 10 minutes.
    """
    key = "macro_context"
    if key in _cache and time.time() - _cache[key]["ts"] < 600:
        return _cache[key]["data"]

    default = {"sentiment": 0.0, "crisis_intensity": 0.0, "crisis_keywords": [], "total_articles": 0}
    if not FINNHUB_API_KEY:
        return default

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://finnhub.io/api/v1/news",
                params={"category": "general", "token": FINNHUB_API_KEY},
            )
            if r.status_code != 200:
                return default
            articles = r.json() or []

        if not articles:
            return default

        pos = neg = 0
        crisis_hits = 0
        crisis_found: dict[str, int] = {}
        total = min(len(articles), 50)

        for a in articles[:50]:
            h = (a.get("headline") or "").lower()
            words = [w.strip(".,!?:;-'\"()[]") for w in h.split()]
            p = sum(1 for w in words if w in POSITIVE_WORDS)
            n = sum(1 for w in words if w in NEGATIVE_WORDS)
            if p > n: pos += 1
            elif n > p: neg += 1
            for w in words:
                if w in CRISIS_WORDS:
                    crisis_hits += 1
                    crisis_found[w] = crisis_found.get(w, 0) + 1

        sentiment = (pos - neg) / total if total else 0
        crisis_intensity = crisis_hits / total if total else 0
        # Top mots crises trouvés
        top_crisis = sorted(crisis_found.items(), key=lambda x: -x[1])[:5]

        data = {
            "sentiment":         round(sentiment, 3),
            "crisis_intensity":  round(crisis_intensity, 3),
            "crisis_keywords":   [w for w, _ in top_crisis],
            "positive_articles": pos,
            "negative_articles": neg,
            "total_articles":    total,
        }
        _cache[key] = {"data": data, "ts": time.time()}
        return data
    except Exception as exc:
        print(f"[news] macro error: {exc}")
        return default


async def get_market_news() -> list[dict]:
    key = "news"
    if key in _cache and time.time() - _cache[key]["ts"] < CACHE_TTL:
        return _cache[key]["data"]

    articles: list[dict] = []
    fail_reason = None  # None = ok, sinon raison de l'echec

    if FINNHUB_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://finnhub.io/api/v1/news",
                    params={"category": "general", "token": FINNHUB_API_KEY},
                )
                if resp.status_code == 200:
                    for item in resp.json()[:50]:
                        headline = item.get("headline", "").strip()
                        if not headline:
                            continue
                        articles.append({
                            "headline": headline,
                            "source": item.get("source", ""),
                            "url": item.get("url", "#"),
                            "time_ago": _time_ago(item.get("datetime", 0)),
                            "sentiment": _sentiment(headline),
                            "summary": (item.get("summary") or "")[:200],
                            "image": item.get("image", ""),
                        })
                elif resp.status_code == 429:
                    fail_reason = ("Limite de l'API Finnhub atteinte (60 req/min en gratuit). "
                                   "Les actualités reviendront automatiquement dans 1-2 minutes.")
                    print("[news] Finnhub 429 rate limit")
                else:
                    fail_reason = f"Finnhub a répondu {resp.status_code} — réessayez dans une minute."
                    print(f"[news] Finnhub HTTP {resp.status_code}")
        except Exception as exc:
            fail_reason = "Erreur réseau vers Finnhub — réessayez dans une minute."
            print(f"[news] Finnhub error: {exc!r}")
    else:
        fail_reason = ("Ajoutez votre clé gratuite dans le fichier .env sous "
                       "FINNHUB_API_KEY pour afficher les actualités financières en temps réel.")

    if not articles:
        placeholder_title = ("Clé API Finnhub non configurée" if not FINNHUB_API_KEY
                             else "Actualités temporairement indisponibles")
        # PAS de mise en cache du placeholder : la prochaine requete retentera
        return [{
            "headline": placeholder_title,
            "source": "TradeRadar",
            "url": "https://finnhub.io",
            "time_ago": "À l'instant",
            "sentiment": "neutre",
            "summary": fail_reason or "",
            "image": "",
        }]

    _cache[key] = {"data": articles, "ts": time.time()}
    return articles
