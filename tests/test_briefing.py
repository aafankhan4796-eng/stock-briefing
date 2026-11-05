from briefing.data import _normalise_yield, parse_news
from briefing.demo import demo_stock
from briefing.drivers import GENERIC, sector_view, signals
from briefing.report import build_markdown, money


def test_derived_metrics():
    s = demo_stock()
    assert round(s.change_pct, 2) == round((104.20 / 102.50 - 1) * 100, 2)
    assert round(s.upside_to_target_pct, 1) == round((118 / 104.20 - 1) * 100, 1)
    assert 0 <= s.position_in_52w_range <= 1


def test_briefing_has_all_six_sections():
    md = build_markdown(demo_stock())
    for heading in ["1. Snapshot", "2. What moves this stock", "3. What to watch",
                    "4. Wall Street view", "5. Key signals", "6. Recent news"]:
        assert heading in md
    assert "not financial advice" in md
    assert "Demo mode" in md


def test_signals_describe_volatility_and_target():
    out = " ".join(signals(demo_stock()))
    assert "Volatile" in out
    assert "price target" in out
    assert "expect earnings to grow" in out


def test_unknown_sector_uses_generic_drivers():
    s = demo_stock()
    s.sector = "Something new"
    assert sector_view(s) == GENERIC


def test_missing_data_does_not_crash():
    s = demo_stock()
    s.price = None
    s.beta = None
    s.analyst.num_analysts = None
    md = build_markdown(s)
    assert "n/a" in md
    assert "No analyst coverage" in md


def test_parse_news_handles_both_formats():
    old = [{"title": "Old style", "publisher": "Reuters", "link": "https://x", "providerPublishTime": 1700000000}]
    new = [{"content": {"title": "New style", "provider": {"displayName": "Bloomberg"},
                        "canonicalUrl": {"url": "https://y"}, "pubDate": "2026-11-01T10:00:00Z"}}]
    items = parse_news(old + new)
    assert [i.title for i in items] == ["Old style", "New style"]
    assert items[1].publisher == "Bloomberg" and items[1].published == "2026-11-01"


def test_yield_and_money_formatting():
    assert _normalise_yield(1.2) == 0.012
    assert _normalise_yield(0.012) == 0.012
    assert money(48.2e9, "USD") == "USD 48.2B"
    assert money(None) == "n/a"


def test_fetch_with_fake_yfinance(monkeypatch):
    """fetch() maps Yahoo-style fields correctly (no network needed)."""
    import datetime
    import pandas as pd
    from briefing import data

    class FakeTicker:
        info = {"longName": "Fake Inc", "currency": "EUR", "currentPrice": 50.0,
                "regularMarketPreviousClose": 48.0, "fiftyTwoWeekLow": 30.0, "fiftyTwoWeekHigh": 60.0,
                "marketCap": 2e10, "trailingPE": 20.0, "forwardPE": 18.0, "dividendYield": 1.5,
                "beta": 0.6, "sector": "Utilities", "recommendationKey": "hold",
                "numberOfAnalystOpinions": 9, "targetMeanPrice": 55.0, "targetHighPrice": 70.0,
                "targetLowPrice": 40.0}
        calendar = {"Earnings Date": [datetime.date(2027, 2, 1)]}
        recommendations_summary = pd.DataFrame([{"period": "0m", "strongBuy": 1, "buy": 3, "hold": 4,
                                                 "sell": 1, "strongSell": 0}])
        news = [{"content": {"title": "Fake news", "provider": {"displayName": "Wire"}}}]

        def __init__(self, symbol):
            pass

    class FakeYF:
        Ticker = FakeTicker

    monkeypatch.setattr(data, "_yf", lambda: FakeYF)
    s = data.fetch("fake")
    assert s.name == "Fake Inc" and s.ticker == "FAKE"
    assert s.dividend_yield == 0.015
    assert s.next_earnings == "2027-02-01"
    assert s.analyst.breakdown["hold"] == 4
    assert "Defensive" in " ".join(__import__("briefing.drivers", fromlist=["signals"]).signals(s))
