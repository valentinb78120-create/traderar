from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from services.stocks import get_trending_stocks, get_emerging_companies, get_top_movers, get_stock_detail, search_tickers, get_custom_watchlist, get_indices, get_calendar, get_all_universe
from services.news import get_market_news
from services.crypto import get_crypto_prices, get_forex_rates, get_crypto_global, get_crypto_detail

app = FastAPI(title="TradeRadar API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/trending-stocks")
async def trending_stocks():
    try:
        data = await get_trending_stocks()
        return JSONResponse({"status": "ok", "data": data})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.get("/api/news")
async def market_news():
    try:
        data = await get_market_news()
        return JSONResponse({"status": "ok", "data": data})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.get("/api/market-context")
async def market_context_endpoint():
    """Retourne le contexte macro courant (VIX + sentiment + crise)."""
    from services.stocks import _market_context
    from services.news import get_macro_context
    macro = await get_macro_context()
    return JSONResponse({"status": "ok", "data": {
        "vix":              _market_context.get("vix"),
        "macro_sentiment":  macro.get("sentiment"),
        "crisis_intensity": macro.get("crisis_intensity"),
        "crisis_keywords":  macro.get("crisis_keywords", []),
        "total_articles":   macro.get("total_articles", 0),
    }})


@app.get("/api/all-universe")
async def all_universe():
    try:
        data = await get_all_universe()
        return JSONResponse({"status": "ok", "data": data})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.get("/api/top-movers")
async def top_movers():
    try:
        data = await get_top_movers(top_n=10)
        return JSONResponse({"status": "ok", "data": data})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.get("/api/watchlist")
async def custom_watchlist(symbols: str = ""):
    try:
        syms = [s.strip() for s in symbols.split(",") if s.strip()]
        data = await get_custom_watchlist(syms)
        return JSONResponse({"status": "ok", "data": data})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.get("/api/search")
async def search(q: str = ""):
    try:
        data = await search_tickers(q.strip())
        return JSONResponse({"status": "ok", "data": data})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.get("/api/stock-detail/{symbol}")
async def stock_detail(symbol: str, period: str = "1y"):
    try:
        data = await get_stock_detail(symbol, period)
        if not data:
            return JSONResponse({"status": "error", "message": "ticker introuvable"}, status_code=404)
        return JSONResponse({"status": "ok", "data": data})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.get("/api/emerging")
async def emerging_companies():
    try:
        data = await get_emerging_companies()
        return JSONResponse({"status": "ok", "data": data})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.get("/api/calendar")
async def calendar():
    try:
        data = await get_calendar()
        return JSONResponse({"status": "ok", "data": data})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.get("/api/indices")
async def indices():
    try:
        data = await get_indices()
        return JSONResponse({"status": "ok", "data": data})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.get("/api/forex")
async def forex_rates():
    try:
        data = await get_forex_rates()
        return JSONResponse({"status": "ok", "data": data})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.get("/api/crypto-detail/{coin_id}")
async def crypto_detail(coin_id: str, period: str = "30"):
    try:
        data = await get_crypto_detail(coin_id, period)
        if not data:
            return JSONResponse({"status": "error", "message": "crypto introuvable"}, status_code=404)
        return JSONResponse({"status": "ok", "data": data})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.get("/api/crypto-global")
async def crypto_global():
    try:
        data = await get_crypto_global()
        return JSONResponse({"status": "ok", "data": data})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@app.get("/api/crypto")
async def crypto_prices():
    try:
        data = await get_crypto_prices()
        return JSONResponse({"status": "ok", "data": data})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


# Static files and SPA fallback — must be declared after API routes
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/sw.js")
async def service_worker():
    # Servi a la racine pour que le scope du Service Worker couvre toute l'app.
    return FileResponse(
        "static/sw.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"},
    )


@app.get("/manifest.webmanifest")
async def manifest():
    return FileResponse(
        "static/manifest.webmanifest",
        media_type="application/manifest+json",
    )
