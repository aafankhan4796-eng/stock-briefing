"""Rule-based analysis: what typically moves a stock and what to watch.

These are general, sector-level patterns used to explain a stock, not
predictions. They make the tool useful even without an AI API key.
"""

from .models import StockData

SECTOR_DRIVERS = {
    "Technology": {
        "drivers": [
            "Revenue growth and demand for its products (e.g. cloud, chips, software subscriptions)",
            "Interest rates: higher rates usually weigh on high-growth tech valuations",
            "Investment cycles in AI, data centres and consumer electronics",
        ],
        "watch": ["Quarterly revenue and guidance", "Gross margin trend", "Export rules and trade tensions"],
    },
    "Financial Services": {
        "drivers": [
            "Interest rates and the gap between lending and deposit rates",
            "Credit quality: loan losses rise in a weak economy",
            "Transaction and trading volumes",
        ],
        "watch": ["Central bank rate decisions", "Net interest margin", "Loan-loss provisions"],
    },
    "Healthcare": {
        "drivers": [
            "Drug trial results and regulatory approvals",
            "Patent expiries on major products",
            "Drug pricing policy and reimbursement rules",
        ],
        "watch": ["Clinical trial readouts", "Approval decisions (FDA/EMA)", "Pipeline updates"],
    },
    "Consumer Cyclical": {
        "drivers": [
            "Consumer spending and confidence",
            "Inflation and input costs squeezing margins",
            "Brand strength and pricing power",
        ],
        "watch": ["Retail sales data", "Same-store sales growth", "Holiday-season trading"],
    },
    "Consumer Defensive": {
        "drivers": [
            "Pricing power against inflation in raw materials",
            "Volume trends as consumers trade down",
            "Currency effects on international sales",
        ],
        "watch": ["Organic sales growth (price vs volume)", "Input cost inflation", "Market share"],
    },
    "Energy": {
        "drivers": [
            "Oil and gas prices",
            "Production volumes and costs",
            "Energy transition policy and capital spending plans",
        ],
        "watch": ["OPEC+ decisions", "Oil price (Brent/WTI)", "Dividend and buyback plans"],
    },
    "Industrials": {
        "drivers": [
            "Economic growth and business investment",
            "Order backlog and supply chains",
            "Government infrastructure and defence spending",
        ],
        "watch": ["New orders and backlog", "Manufacturing PMI data", "Margin progress"],
    },
    "Utilities": {
        "drivers": [
            "Interest rates (utilities behave partly like bonds)",
            "Regulated returns allowed by authorities",
            "Energy prices and the renewable build-out",
        ],
        "watch": ["Bond yields", "Regulatory decisions", "Capital investment plans"],
    },
    "Communication Services": {
        "drivers": [
            "Advertising spend and user growth",
            "Subscriber numbers and pricing",
            "Regulation and competition",
        ],
        "watch": ["User / subscriber metrics", "Advertising market trends", "Regulatory cases"],
    },
    "Real Estate": {
        "drivers": [
            "Interest rates and financing costs",
            "Occupancy and rent growth",
            "Property valuations",
        ],
        "watch": ["Bond yields", "Occupancy rates", "Debt refinancing"],
    },
    "Basic Materials": {
        "drivers": [
            "Commodity prices (metals, chemicals)",
            "Demand from construction and manufacturing, especially in China",
            "Energy and production costs",
        ],
        "watch": ["Commodity prices", "China economic data", "Production volumes"],
    },
}

GENERIC = {
    "drivers": ["Revenue and profit growth vs expectations", "Overall market sentiment", "Interest rates"],
    "watch": ["Next earnings report", "Management guidance", "Major news and regulation"],
}


def sector_view(stock: StockData) -> dict:
    return SECTOR_DRIVERS.get(stock.sector, GENERIC)


def signals(stock: StockData) -> list[str]:
    """Plain-English observations from the numbers (descriptive, not advice)."""
    out = []
    if stock.beta is not None:
        if stock.beta >= 1.3:
            out.append(f"Volatile: beta of {stock.beta:.2f} means it has tended to move more than the overall market.")
        elif stock.beta <= 0.7:
            out.append(f"Defensive: beta of {stock.beta:.2f} means it has tended to move less than the overall market.")
        else:
            out.append(f"Moves roughly in line with the market (beta {stock.beta:.2f}).")

    pos = stock.position_in_52w_range
    if pos is not None:
        if pos >= 0.85:
            out.append("Trading near its 52-week high: momentum is strong, but expectations are high too.")
        elif pos <= 0.15:
            out.append("Trading near its 52-week low: worth checking what has gone wrong, or whether it is oversold.")

    if stock.trailing_pe and stock.forward_pe and stock.forward_pe > 0:
        if stock.forward_pe < stock.trailing_pe * 0.85:
            out.append("Forward P/E is well below trailing P/E: analysts expect earnings to grow.")
        elif stock.forward_pe > stock.trailing_pe * 1.15:
            out.append("Forward P/E is above trailing P/E: analysts expect earnings to fall.")

    up = stock.upside_to_target_pct
    if up is not None:
        direction = "above" if up >= 0 else "below"
        out.append(f"The average analyst price target is {abs(up):.0f}% {direction} the current price.")

    if stock.analyst.num_analysts is not None and stock.analyst.num_analysts < 5:
        out.append("Few analysts cover this stock, so the consensus is less reliable.")
    return out
