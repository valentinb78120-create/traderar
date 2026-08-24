"""Test rapide du scoring v6 avec des series synthetiques (a supprimer apres)."""
import math
import random

from services.stocks import compute_indicators, compute_opportunity_score

random.seed(42)


def make_series(kind: str, n: int = 252):
    closes, highs, lows, volumes = [], [], [], []
    price = 100.0
    for i in range(n):
        if kind == "bull":
            drift = 0.0030
        elif kind == "bear":
            drift = -0.0030
        elif kind == "crash":
            drift = 0.0020 if i < n - 30 else -0.025
        elif kind == "recovery":
            drift = -0.0030 if i < n - 40 else 0.006
        else:  # range
            drift = 0.0010 * math.sin(i / 10)
        price *= 1 + drift + random.gauss(0, 0.008)
        price = max(price, 1)
        closes.append(price)
        spread = price * abs(random.gauss(0, 0.008))
        highs.append(price + spread)
        lows.append(max(price - spread, 0.5))
        volumes.append(1_000_000 * (1 + abs(random.gauss(0, 0.4))))
    return closes, highs, lows, volumes


for kind in ("bull", "bear", "crash", "recovery", "range"):
    closes, highs, lows, volumes = make_series(kind)
    ind = compute_indicators(closes, highs=highs, lows=lows, volumes=volumes)
    week_low, week_high = min(closes), max(closes)
    pos = (closes[-1] - week_low) / (week_high - week_low) * 100 if week_high != week_low else 50
    s = {
        "position_52w": pos,
        "change_pct": (closes[-1] / closes[-2] - 1) * 100,
        "perf_1m": (closes[-1] / closes[-22] - 1) * 100,
        "pe_ratio": 18.0,
        "revenue_growth": 0.12,
        "dividend_yield": 2.5,
        "market_cap": 50_000_000_000,
    }
    sentiment = {
        "news_sentiment": 0.3, "news_count": 8,
        "analyst": {"bullish_ratio": 0.7, "total": 12},
        "analyst_upgrade": 0.08, "earnings_surprise": 0.5,
    }
    r = compute_opportunity_score(s, ind, sentiment=sentiment, vix=18)
    assert 0 <= r["score"] <= 100, f"score hors bornes: {r['score']}"
    assert all(0 <= v <= 100 for v in r["pillars"].values()), "pilier hors bornes"
    assert 0 <= r["confidence"] <= 100
    path_pct = (closes[-1] / closes[0] - 1) * 100
    print(f"{kind:9s} path={path_pct:+7.1f}% score={r['score']:3d} tag={r['tag']:8s} "
          f"regime={r['regime']:8s} conf={r['confidence']:3d} risk={r['risk_mult']:.2f} "
          f"pillars={r['pillars']}")

# Cas EU : pas de fondamentaux ni sentiment
closes, highs, lows, volumes = make_series("bull")
ind = compute_indicators(closes, highs=highs, lows=lows, volumes=volumes)
s_eu = {"position_52w": 60.0, "change_pct": 0.5, "perf_1m": 3.0,
        "pe_ratio": None, "revenue_growth": None, "dividend_yield": None, "market_cap": None}
r = compute_opportunity_score(s_eu, ind)
print(f"{'EU-nofund':9s} score={r['score']:3d} tag={r['tag']:8s} regime={r['regime']:8s} "
      f"conf={r['confidence']:3d} weights={r['weights']}")
assert r["weights"]["sentiment"] == 0, "sentiment devrait etre exclu"

# Cas minimal : closes-only, peu d'historique
short = [100 + i * 0.1 + random.gauss(0, 1) for i in range(60)]
ind_min = compute_indicators(short)
r = compute_opportunity_score({"position_52w": 50, "change_pct": 0.2, "perf_1m": 1.5}, ind_min)
print(f"{'minimal':9s} score={r['score']:3d} conf={r['confidence']:3d}")

# Crash + VIX panique + crise
closes, highs, lows, volumes = make_series("crash")
ind = compute_indicators(closes, highs=highs, lows=lows, volumes=volumes)
r = compute_opportunity_score({"position_52w": 5, "change_pct": -8, "perf_1m": -25},
                              ind, vix=42, crisis_intensity=0.4, macro_sentiment=-0.5)
print(f"{'panic-mac':9s} score={r['score']:3d} tag={r['tag']:8s} (attendu: tres bas)")
assert r["score"] <= 45, f"crash+VIX devrait donner un score bas, obtenu {r['score']}"

print("\nOK - tous les tests passent")
