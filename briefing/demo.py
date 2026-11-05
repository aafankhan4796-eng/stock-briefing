"""Fictional demo company so the app (and tests) work offline. Not real data."""

import math

from .models import AnalystView, NewsItem, StockData


def demo_stock() -> StockData:
    return StockData(
        ticker="DEMO",
        name="Example Robotics Corp (fictional)",
        currency="USD",
        exchange="Demo Exchange",
        price=104.20,
        previous_close=102.50,
        day_low=101.90,
        day_high=105.10,
        week52_low=71.30,
        week52_high=112.80,
        market_cap=48.2e9,
        trailing_pe=34.0,
        forward_pe=26.5,
        dividend_yield=0.006,
        beta=1.42,
        sector="Technology",
        industry="Industrial automation software",
        country="Netherlands",
        summary=("Example Robotics Corp is a fictional company used to demonstrate this tool. "
                 "It sells software and robots that automate warehouses."),
        next_earnings="2027-01-28",
        analyst=AnalystView(recommendation="buy", num_analysts=18, target_mean=118.0, target_median=117.0,
                            target_high=140.0, target_low=90.0,
                            breakdown={"strongBuy": 5, "buy": 8, "hold": 4, "sell": 1, "strongSell": 0}),
        news=[
            NewsItem("Example Robotics wins large warehouse automation contract (fictional)", "Demo News", "", "2026-11-03"),
            NewsItem("Analysts raise targets after strong quarter (fictional)", "Demo Wire", "", "2026-10-29"),
        ],
        is_demo=True,
    )


def demo_history(days: int = 250):
    import pandas as pd
    idx = pd.bdate_range(end="2026-11-04", periods=days)
    values = [80 + 22 * (i / days) + 6 * math.sin(i / 14) for i in range(days)]
    shift = 104.20 - values[-1]  # end the series at the demo price
    values = [v + shift * (i / days) for i, v in enumerate(values)]
    return pd.Series(values, index=idx, name="Close")
