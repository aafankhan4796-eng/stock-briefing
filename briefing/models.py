"""Data model shared by the data layer, the analysis rules and the report."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NewsItem:
    title: str
    publisher: str = ""
    link: str = ""
    published: str = ""  # ISO date string, may be empty


@dataclass
class AnalystView:
    recommendation: Optional[str] = None      # e.g. "buy", "hold", "strong_buy"
    num_analysts: Optional[int] = None
    target_mean: Optional[float] = None
    target_median: Optional[float] = None
    target_high: Optional[float] = None
    target_low: Optional[float] = None
    # Counts of the latest ratings: strongBuy, buy, hold, sell, strongSell
    breakdown: dict = field(default_factory=dict)


@dataclass
class StockData:
    ticker: str
    name: str
    currency: str = "USD"
    exchange: str = ""
    price: Optional[float] = None
    previous_close: Optional[float] = None
    day_low: Optional[float] = None
    day_high: Optional[float] = None
    week52_low: Optional[float] = None
    week52_high: Optional[float] = None
    market_cap: Optional[float] = None
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    dividend_yield: Optional[float] = None    # as a fraction, e.g. 0.012 = 1.2%
    beta: Optional[float] = None
    sector: str = ""
    industry: str = ""
    country: str = ""
    summary: str = ""
    next_earnings: Optional[str] = None       # ISO date
    analyst: AnalystView = field(default_factory=AnalystView)
    news: list = field(default_factory=list)  # list[NewsItem]
    is_demo: bool = False

    @property
    def change_pct(self) -> Optional[float]:
        if self.price is None or not self.previous_close:
            return None
        return (self.price / self.previous_close - 1) * 100

    @property
    def upside_to_target_pct(self) -> Optional[float]:
        if self.price is None or not self.analyst.target_mean:
            return None
        return (self.analyst.target_mean / self.price - 1) * 100

    @property
    def position_in_52w_range(self) -> Optional[float]:
        """0 = at the 52-week low, 1 = at the 52-week high."""
        if None in (self.price, self.week52_low, self.week52_high):
            return None
        span = self.week52_high - self.week52_low
        return None if span <= 0 else (self.price - self.week52_low) / span
