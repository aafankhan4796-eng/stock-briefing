"""Market data layer, built on yfinance (free Yahoo Finance data).

Every field is optional: Yahoo's coverage differs by company and exchange,
so missing values are returned as None instead of raising errors.
Note: free data can be delayed (often ~15 minutes) and is for personal,
educational use.
"""

from datetime import datetime, timezone
from typing import Optional

from .models import AnalystView, NewsItem, StockData


def _yf():
    import yfinance as yf  # imported lazily so tests can run without network
    return yf


def resolve(query: str) -> list[dict]:
    """Turn a company name or ticker into candidate tickers.

    Returns a list of {"symbol", "name", "exchange", "type"} dicts, best match first.
    """
    query = query.strip()
    if not query:
        return []
    results = _yf().Search(query, max_results=8).quotes
    out = []
    for q in results:
        if q.get("quoteType") not in ("EQUITY", "ETF"):
            continue
        out.append({
            "symbol": q.get("symbol"),
            "name": q.get("shortname") or q.get("longname") or q.get("symbol"),
            "exchange": q.get("exchDisp") or q.get("exchange", ""),
            "type": q.get("quoteType"),
        })
    return out


def _num(d: dict, key: str) -> Optional[float]:
    v = d.get(key)
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def parse_news(raw: list) -> list[NewsItem]:
    """Normalise yfinance news (handles both the old flat and the new nested format)."""
    items = []
    for n in raw or []:
        c = n.get("content", n)
        title = c.get("title")
        if not title:
            continue
        publisher = (c.get("provider") or {}).get("displayName") or c.get("publisher", "")
        link = (c.get("canonicalUrl") or {}).get("url") or c.get("link", "")
        published = c.get("pubDate", "")
        if not published and n.get("providerPublishTime"):
            published = datetime.fromtimestamp(n["providerPublishTime"], tz=timezone.utc).isoformat()
        items.append(NewsItem(title=title, publisher=publisher, link=link, published=published[:10]))
    return items


def _next_earnings(ticker) -> Optional[str]:
    try:
        cal = ticker.calendar
        dates = cal.get("Earnings Date") if isinstance(cal, dict) else None
        if dates:
            d = dates[0]
            return d.isoformat() if hasattr(d, "isoformat") else str(d)
    except Exception:
        pass
    return None


def _breakdown(ticker) -> dict:
    try:
        df = ticker.recommendations_summary
        if df is not None and not df.empty:
            row = df.iloc[0]  # current month
            return {k: int(row[k]) for k in ("strongBuy", "buy", "hold", "sell", "strongSell") if k in row}
    except Exception:
        pass
    return {}


def fetch(symbol: str) -> StockData:
    """Fetch everything needed for the briefing for one ticker."""
    t = _yf().Ticker(symbol)
    info = t.info or {}

    analyst = AnalystView(
        recommendation=info.get("recommendationKey"),
        num_analysts=info.get("numberOfAnalystOpinions"),
        target_mean=_num(info, "targetMeanPrice"),
        target_median=_num(info, "targetMedianPrice"),
        target_high=_num(info, "targetHighPrice"),
        target_low=_num(info, "targetLowPrice"),
        breakdown=_breakdown(t),
    )

    price = _num(info, "currentPrice") or _num(info, "regularMarketPrice")
    if price is None:
        try:
            price = float(t.fast_info["last_price"])
        except Exception:
            price = None

    return StockData(
        ticker=symbol.upper(),
        name=info.get("longName") or info.get("shortName") or symbol.upper(),
        currency=info.get("currency") or "USD",
        exchange=info.get("fullExchangeName") or info.get("exchange", ""),
        price=price,
        previous_close=_num(info, "regularMarketPreviousClose") or _num(info, "previousClose"),
        day_low=_num(info, "dayLow"),
        day_high=_num(info, "dayHigh"),
        week52_low=_num(info, "fiftyTwoWeekLow"),
        week52_high=_num(info, "fiftyTwoWeekHigh"),
        market_cap=_num(info, "marketCap"),
        trailing_pe=_num(info, "trailingPE"),
        forward_pe=_num(info, "forwardPE"),
        dividend_yield=_normalise_yield(_num(info, "dividendYield")),
        beta=_num(info, "beta"),
        sector=info.get("sector", ""),
        industry=info.get("industry", ""),
        country=info.get("country", ""),
        summary=info.get("longBusinessSummary", ""),
        next_earnings=_next_earnings(t),
        analyst=analyst,
        news=parse_news(getattr(t, "news", []))[:6],
    )


def _normalise_yield(v: Optional[float]) -> Optional[float]:
    """yfinance has reported dividend yield both as a fraction (0.012) and a percent (1.2)."""
    if v is None:
        return None
    return v / 100 if v > 0.25 else v


def history(symbol: str, period: str = "1y"):
    """Daily closing prices as a pandas Series."""
    df = _yf().Ticker(symbol).history(period=period)
    return df["Close"] if not df.empty else df
