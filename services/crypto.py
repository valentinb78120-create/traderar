import asyncio
import httpx
import time


async def get_crypto_detail(coin_id: str, period: str = "30") -> dict | None:
    """Détail d'une crypto pour modal : prix, history, ATH/ATL, description, links."""
    # period en jours : 1, 7, 30, 90, 365, max
    cache_key = f"cryptodet_{coin_id}_{period}"
    if cache_key in _cache and time.time() - _cache[cache_key]["ts"] < 600:
        return _cache[cache_key]["data"]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            info_task = client.get(
                f"https://api.coingecko.com/api/v3/coins/{coin_id}",
                params={"localization": "false", "tickers": "false",
                        "community_data": "false", "developer_data": "false",
                        "sparkline": "false"},
            )
            chart_task = client.get(
                f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
                params={"vs_currency": "eur", "days": period},
            )
            info_r, chart_r = await asyncio.gather(info_task, chart_task)

        if info_r.status_code != 200:
            return None
        info = info_r.json()
        md = info.get("market_data", {})
        chart = chart_r.json() if chart_r.status_code == 200 else {}

        prices = chart.get("prices", [])
        history = [{"t": int(p[0] / 1000), "c": round(float(p[1]), 6)} for p in prices if len(p) == 2]

        data = {
            "id":           info.get("id"),
            "symbol":       info.get("symbol", "").upper(),
            "name":         info.get("name"),
            "image":        (info.get("image") or {}).get("large") or (info.get("image") or {}).get("small", ""),
            "price":        (md.get("current_price") or {}).get("eur"),
            "change_24h":   round((md.get("price_change_percentage_24h") or 0), 2),
            "change_7d":    round((md.get("price_change_percentage_7d") or 0), 2),
            "change_30d":   round((md.get("price_change_percentage_30d") or 0), 2),
            "change_1y":    round((md.get("price_change_percentage_1y") or 0), 2),
            "market_cap":   (md.get("market_cap") or {}).get("eur"),
            "volume_24h":   (md.get("total_volume") or {}).get("eur"),
            "high_24h":     (md.get("high_24h") or {}).get("eur"),
            "low_24h":      (md.get("low_24h") or {}).get("eur"),
            "ath":          (md.get("ath") or {}).get("eur"),
            "ath_change":   round((md.get("ath_change_percentage") or {}).get("eur", 0), 2),
            "ath_date":     (md.get("ath_date") or {}).get("eur"),
            "atl":          (md.get("atl") or {}).get("eur"),
            "atl_change":   round((md.get("atl_change_percentage") or {}).get("eur", 0), 2),
            "circulating":  md.get("circulating_supply"),
            "total_supply": md.get("total_supply"),
            "max_supply":   md.get("max_supply"),
            "rank":         md.get("market_cap_rank"),
            "description":  ((info.get("description") or {}).get("en") or "")[:600],
            "homepage":     ((info.get("links") or {}).get("homepage") or [""])[0],
            "tr":           coin_id in TR_CRYPTO_IDS,
            "period":       period,
            "history":      history,
        }
        _cache[cache_key] = {"data": data, "ts": time.time()}
        return data
    except Exception as exc:
        print(f"[crypto-detail] {coin_id}: {exc}")
        return None


async def get_crypto_global() -> dict:
    """Statistiques globales crypto : dominance BTC, market cap totale."""
    key = "crypto_global"
    if key in _cache and time.time() - _cache[key]["ts"] < 600:  # cache 10 min
        return _cache[key]["data"]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.coingecko.com/api/v3/global")
            if r.status_code != 200:
                return {}
            d = r.json().get("data", {})
            mcap_eur = (d.get("total_market_cap") or {}).get("eur", 0)
            vol_eur  = (d.get("total_volume") or {}).get("eur", 0)
            dominance = d.get("market_cap_percentage", {})
            change = d.get("market_cap_change_percentage_24h_usd", 0)
            data = {
                "total_market_cap_eur": mcap_eur,
                "total_volume_eur":     vol_eur,
                "market_cap_change_24h": round(change, 2),
                "btc_dominance":  round(dominance.get("btc", 0), 2),
                "eth_dominance":  round(dominance.get("eth", 0), 2),
                "active_cryptos": d.get("active_cryptocurrencies"),
            }
            _cache[key] = {"data": data, "ts": time.time()}
            return data
    except Exception as exc:
        print(f"[crypto-global] error: {exc}")
        return {}


async def get_forex_rates() -> dict:
    """Taux de change vers EUR (cache 24h). open.er-api.com — gratuit, sans clé,
    couvre 160+ devises (USD, GBP, JPY, HKD, CHF, INR, DKK, etc.)."""
    if "forex" in _cache and time.time() - _cache["forex"]["ts"] < 86400:
        return _cache["forex"]["data"]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://open.er-api.com/v6/latest/EUR")
            if r.status_code != 200:
                return {"EUR": 1.0}
            data = r.json()
            # data["rates"] : 1 EUR vers chaque devise. On veut chaque devise → EUR (inverse).
            rates = {"EUR": 1.0}
            for cur, val in (data.get("rates") or {}).items():
                if val:
                    rates[cur] = round(1.0 / val, 6)
            if len(rates) > 1:
                _cache["forex"] = {"data": rates, "ts": time.time()}
            return rates
    except Exception as exc:
        print(f"[forex] error: {exc}")
        return {"EUR": 1.0}

_cache: dict = {}
CACHE_TTL = 300

# Set des IDs CoinGecko disponibles sur Trade Republic (mai 2026)
# Source : catalogue TR crypto. Mettre à jour si TR ajoute/retire.
TR_CRYPTO_IDS = {
    "bitcoin", "ethereum", "solana", "ripple", "cardano",
    "polkadot", "chainlink", "matic-network", "avalanche-2", "dogecoin",
    "litecoin", "bitcoin-cash", "uniswap", "aave", "stellar",
    "cosmos", "tezos", "the-graph", "decentraland", "the-sandbox",
    "shiba-inu", "tron", "monero", "filecoin",
}

# Top crypto par cap (CoinGecko IDs) — top 50
CRYPTO_IDS = [
    # ── Top 10 — toutes sur TR ──
    "bitcoin", "ethereum", "solana", "ripple", "cardano",
    "polkadot", "chainlink", "matic-network", "avalanche-2", "dogecoin",
    # ── 11-30 mix TR / hors TR ──
    "litecoin", "bitcoin-cash", "uniswap", "aave", "stellar",
    "cosmos", "shiba-inu", "tron", "monero", "filecoin",
    "the-open-network", "near", "arbitrum", "optimism", "injective-protocol",
    "sui", "aptos", "celestia", "sei-network", "tezos",
    # ── 31-50 DeFi / L1 / écosystèmes / GameFi ──
    "ethereum-classic", "vechain", "algorand", "the-graph", "render-token",
    "fantom", "decentraland", "the-sandbox", "elrond-erd-2", "kava",
    "kusama", "internet-computer", "chiliz", "axie-infinity", "mantle",
    "starknet", "pyth-network", "jupiter-exchange-solana", "worldcoin-wld", "thorchain",
    # ── 51-75 stablecoins, memecoins, niches ──
    "tether", "usd-coin", "dai", "first-digital-usd",
    "wrapped-bitcoin", "bittensor", "kaspa", "hedera-hashgraph",
    "stacks", "flow", "theta-token", "iota", "neo", "qtum",
    "pepe", "bonk", "floki", "dogwifcoin", "ondo-finance",
    "fetch-ai", "singularitynet", "ocean-protocol", "akash-network",
    "helium",
]

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"


async def get_crypto_prices() -> list[dict]:
    key = "crypto"
    if key in _cache and time.time() - _cache[key]["ts"] < CACHE_TTL:
        return _cache[key]["data"]

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                COINGECKO_URL,
                params={
                    "vs_currency": "eur",
                    "ids": ",".join(CRYPTO_IDS),
                    "order": "market_cap_desc",
                    "per_page": 75,
                    "page": 1,
                    "sparkline": "true",
                    "price_change_percentage": "24h,7d",
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            raw = resp.json()

        data = []
        for item in raw:
            price = item.get("current_price") or 0
            data.append({
                "id": item["id"],
                "symbol": item["symbol"].upper(),
                "name": item["name"],
                "price": price,
                "change_24h": round(item.get("price_change_percentage_24h") or 0, 2),
                "change_7d": round(
                    item.get("price_change_percentage_7d_in_currency") or 0, 2
                ),
                "high_24h": item.get("high_24h"),
                "low_24h": item.get("low_24h"),
                "market_cap": item.get("market_cap"),
                "image": item.get("image", ""),
                "tr": item["id"] in TR_CRYPTO_IDS,
                "sparkline_7d": (item.get("sparkline_in_7d") or {}).get("price", []),
            })

        _cache[key] = {"data": data, "ts": time.time()}
        return data

    except Exception as exc:
        print(f"[crypto] CoinGecko error: {exc}")
        return []
