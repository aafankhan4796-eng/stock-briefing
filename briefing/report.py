"""Builds the one-page briefing as Markdown, with an optional AI-written summary."""

import os
from datetime import date
from typing import Optional

from .drivers import sector_view, signals
from .models import StockData

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
DISCLAIMER = ("This companion is for research and education only. It is not financial advice "
              "and does not recommend buying or selling any security. Data may be delayed or incomplete.")

RATING_LABELS = {
    "strong_buy": "Strong buy", "buy": "Buy", "hold": "Hold",
    "underperform": "Underperform", "sell": "Sell", "strong_sell": "Strong sell", "none": "No rating",
}


def money(v: Optional[float], cur: str = "") -> str:
    if v is None:
        return "n/a"
    for div, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(v) >= div:
            return f"{cur} {v / div:,.1f}{suffix}".strip()
    return f"{cur} {v:,.2f}".strip()


def num(v: Optional[float], fmt: str = "{:.1f}") -> str:
    return "n/a" if v is None else fmt.format(v)


def build_markdown(s: StockData, ai_text: Optional[str] = None) -> str:
    a = s.analyst
    chg = s.change_pct
    lines = [
        f"# {s.name} ({s.ticker})",
        f"*{s.exchange} · {s.sector or 'n/a'} · {s.industry or 'n/a'} · Briefing date {date.today().isoformat()}*",
        "",
    ]
    if s.is_demo:
        lines += ["> **Demo mode:** fictional company and illustrative numbers.", ""]
    if ai_text:
        lines += ["## Summary", ai_text, ""]

    lines += [
        "## 1. Snapshot",
        "| Metric | Value |", "|---|---|",
        f"| Price | {money(s.price, s.currency)}" + (f" ({chg:+.2f}% today)" if chg is not None else "") + " |",
        f"| Day range | {num(s.day_low, '{:,.2f}')} – {num(s.day_high, '{:,.2f}')} |",
        f"| 52-week range | {num(s.week52_low, '{:,.2f}')} – {num(s.week52_high, '{:,.2f}')} |",
        f"| Market cap | {money(s.market_cap, s.currency)} |",
        f"| P/E (trailing / forward) | {num(s.trailing_pe)} / {num(s.forward_pe)} |",
        f"| Dividend yield | {num(s.dividend_yield * 100 if s.dividend_yield is not None else None, '{:.2f}%')} |",
        f"| Beta | {num(s.beta, '{:.2f}')} |",
        "",
        "## 2. What moves this stock",
    ]
    view = sector_view(s)
    lines += [f"- {d}" for d in view["drivers"]]

    lines += ["", "## 3. What to watch"]
    if s.next_earnings:
        lines.append(f"- **Next earnings date:** {s.next_earnings}")
    lines += [f"- {w}" for w in view["watch"]]

    lines += ["", "## 4. Wall Street view"]
    if a.num_analysts:
        rating = RATING_LABELS.get((a.recommendation or "none").lower(), a.recommendation)
        lines += [
            f"- **Consensus:** {rating} ({a.num_analysts} analysts)",
            f"- **Average price target:** {money(a.target_mean, s.currency)}"
            + (f" ({s.upside_to_target_pct:+.0f}% vs current price)" if s.upside_to_target_pct is not None else ""),
            f"- **Target range:** {money(a.target_low, s.currency)} – {money(a.target_high, s.currency)}",
        ]
        if a.breakdown:
            parts = [f"{k}: {v}" for k, v in a.breakdown.items()]
            lines.append(f"- **Latest ratings:** {', '.join(parts)}")
    else:
        lines.append("- No analyst coverage available for this ticker.")

    lines += ["", "## 5. Key signals"]
    lines += [f"- {x}" for x in signals(s)] or ["- Not enough data."]

    lines += ["", "## 6. Recent news"]
    if s.news:
        for n in s.news:
            meta = " · ".join(x for x in (n.publisher, n.published) if x)
            title = f"[{n.title}]({n.link})" if n.link else n.title
            lines.append(f"- {title}" + (f" *({meta})*" if meta else ""))
    else:
        lines.append("- No recent news found.")

    if s.summary:
        lines += ["", "## About the company", s.summary[:700] + ("..." if len(s.summary) > 700 else "")]

    lines += ["", "---", f"*{DISCLAIMER}*"]
    return "\n".join(lines)


def ai_summary(s: StockData, api_key: Optional[str] = None) -> Optional[str]:
    """Optional analyst-style summary from Claude. Returns None if no key or on error."""
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    facts = build_markdown(s)
    prompt = (
        "You are an equity research analyst writing for a smart non-expert. Using ONLY the facts below, "
        "write a 120-150 word summary: what the company does, what currently drives the stock, the main "
        "risks, and what analysts expect. Do not give buy/sell advice and do not invent numbers.\n\n" + facts
    )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(model=DEFAULT_MODEL, max_tokens=500,
                                     messages=[{"role": "user", "content": prompt}])
        return msg.content[0].text.strip()
    except Exception:
        return None
