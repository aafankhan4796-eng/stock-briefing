"""AI Stock Briefing - Streamlit app.

Run locally:  streamlit run app.py
Type a company name or ticker and get a one-page research briefing.
"""

import plotly.graph_objects as go
import streamlit as st

from briefing import data
from briefing.demo import demo_history, demo_stock
from briefing.report import DISCLAIMER, RATING_LABELS, ai_summary, build_markdown, money

st.set_page_config(page_title="AI Stock Briefing", page_icon="📈", layout="centered")
st.title("📈 AI Stock Briefing")
st.caption("Type a company name or ticker for a one-page research briefing: price, drivers, "
           "what to watch, analyst forecasts and news.")

query = st.text_input("Company or ticker", placeholder="e.g. ASML, Apple, Adyen, NVDA")
demo = st.toggle("Demo mode (fictional company, works offline)", value=False)


@st.cache_data(ttl=300, show_spinner=False)
def search(q):
    return data.resolve(q)


@st.cache_data(ttl=300, show_spinner=False)
def load(symbol):
    return data.fetch(symbol), data.history(symbol)


stock = hist = None
if demo:
    stock, hist = demo_stock(), demo_history()
elif query:
    try:
        matches = search(query)
    except Exception as e:
        st.error(f"Could not reach the market data service: {e}")
        matches = []
    if not matches:
        st.warning("No matching stock found. Try the ticker symbol instead.")
    else:
        labels = [f"{m['name']} ({m['symbol']}, {m['exchange']})" for m in matches]
        choice = st.selectbox("Pick the listing", labels)
        symbol = matches[labels.index(choice)]["symbol"]
        with st.spinner(f"Loading {symbol}..."):
            try:
                stock, hist = load(symbol)
            except Exception as e:
                st.error(f"Could not load data for {symbol}: {e}")

if stock:
    c1, c2, c3 = st.columns(3)
    c1.metric("Price", money(stock.price, stock.currency),
              f"{stock.change_pct:+.2f}%" if stock.change_pct is not None else None)
    c2.metric("Market cap", money(stock.market_cap, stock.currency))
    rating = RATING_LABELS.get((stock.analyst.recommendation or "none").lower(), "n/a")
    c3.metric("Analyst consensus", rating,
              f"{stock.upside_to_target_pct:+.0f}% to target" if stock.upside_to_target_pct is not None else None)

    if hist is not None and len(hist):
        fig = go.Figure(go.Scatter(x=hist.index, y=hist.values, mode="lines", line=dict(width=2)))
        if stock.analyst.target_mean:
            fig.add_hline(y=stock.analyst.target_mean, line_dash="dash",
                          annotation_text="Avg analyst target", annotation_position="top left")
        fig.update_layout(title="Price over the last year", height=320, margin=dict(l=10, r=10, t=40, b=10),
                          yaxis_title=stock.currency)
        st.plotly_chart(fig, use_container_width=True)

    b = stock.analyst.breakdown
    if b:
        names = {"strongBuy": "Strong buy", "buy": "Buy", "hold": "Hold", "sell": "Sell", "strongSell": "Strong sell"}
        fig2 = go.Figure(go.Bar(x=list(b.values()), y=[names.get(k, k) for k in b], orientation="h"))
        fig2.update_layout(title="Analyst ratings", height=240, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        api_key = None
    summary = ai_summary(stock, api_key) if not stock.is_demo else None

    report = build_markdown(stock, summary)
    st.markdown(report)
    st.download_button("Download briefing (Markdown)", report, file_name=f"{stock.ticker}_briefing.md")
else:
    st.info(DISCLAIMER)
