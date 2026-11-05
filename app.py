"""Stock Trading Companion - Streamlit app by Aafan Khan.

Run locally:  streamlit run app.py
Type a company name or ticker and your AI companion builds a one-page research briefing.
"""

import plotly.graph_objects as go
import streamlit as st

from briefing import data
from briefing.demo import demo_history, demo_stock
from briefing.report import DISCLAIMER, RATING_LABELS, ai_summary, build_markdown, money

MINT, AMBER, RED, MUTED, GRID = "#3DDC97", "#F5B841", "#FF6B6B", "#8A9BB8", "rgba(138,155,184,0.15)"

st.set_page_config(page_title="Stock Trading Companion", page_icon="📈", layout="centered")

st.markdown(f"""
<style>
  .hero {{
    background: linear-gradient(135deg, #12304F 0%, #0E3B3A 100%);
    border: 1px solid rgba(61,220,151,0.25);
    border-radius: 18px; padding: 26px 28px; margin-bottom: 18px;
  }}
  .hero .tag {{ color:{MINT}; font-size:13px; font-weight:700; letter-spacing:2px; text-transform:uppercase; }}
  .hero h1 {{ color:#FFFFFF; font-size:38px; margin:6px 0 6px; padding:0; line-height:1.15; }}
  .hero p {{ color:#C5D3EA; font-size:16px; margin:0; }}
  .hero .by {{ color:{MUTED}; font-size:13px; margin-top:10px; }}
  div[data-testid="stMetric"] {{
    background:#152238; border:1px solid rgba(138,155,184,0.18);
    border-radius:14px; padding:14px 16px;
  }}
  div[data-testid="stMetricLabel"] p {{ color:{MUTED}; }}
  h2 {{ color:{MINT} !important; font-size:22px !important; margin-top:18px !important; }}
  .footer {{ color:{MUTED}; font-size:13px; text-align:center; margin-top:30px; }}
  .footer a {{ color:{MINT}; text-decoration:none; }}
</style>
<div class="hero">
  <div class="tag">AI research companion</div>
  <h1>📈 Stock Trading Companion</h1>
  <p>Type any company and your companion pulls live prices, explains what moves the stock,
     what to watch and what Wall Street expects, all on one page.</p>
  <div class="by">Built by Aafan Khan</div>
</div>
""", unsafe_allow_html=True)

query = st.text_input("Which company are you looking at?", placeholder="e.g. ASML, Apple, Adyen, NVDA")
demo = st.toggle("Demo mode (fictional company, works offline)", value=False)


@st.cache_data(ttl=300, show_spinner=False)
def search(q):
    return data.resolve(q)


@st.cache_data(ttl=300, show_spinner=False)
def load(symbol):
    return data.fetch(symbol), data.history(symbol)


def style(fig, title, height):
    fig.update_layout(
        title=dict(text=title, font=dict(color="#E6EDF7", size=16)), height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=MUTED), margin=dict(l=10, r=10, t=44, b=10),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


stock = hist = None
if demo:
    stock, hist = demo_stock(), demo_history()
elif query:
    try:
        matches = search(query)
    except Exception as e:
        st.error(f"Your companion could not reach the market data service: {e}")
        matches = []
    if not matches:
        st.warning("No matching stock found. Try the ticker symbol instead.")
    else:
        labels = [f"{m['name']} ({m['symbol']}, {m['exchange']})" for m in matches]
        choice = st.selectbox("Pick the listing", labels)
        symbol = matches[labels.index(choice)]["symbol"]
        with st.spinner(f"Your companion is researching {symbol}..."):
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
        up = hist.iloc[-1] >= hist.iloc[0]
        line = MINT if up else RED
        fill = "rgba(61,220,151,0.12)" if up else "rgba(255,107,107,0.12)"
        fig = go.Figure(go.Scatter(x=hist.index, y=hist.values, mode="lines",
                                   line=dict(width=2.5, color=line), fill="tozeroy", fillcolor=fill))
        lo, hi = float(hist.min()), float(hist.max())
        if stock.analyst.target_mean:
            hi = max(hi, stock.analyst.target_mean)
            fig.add_hline(y=stock.analyst.target_mean, line_dash="dash", line_color=AMBER,
                          annotation_text="Avg analyst target", annotation_font_color=AMBER,
                          annotation_position="top left")
        pad = (hi - lo) * 0.08 or 1
        fig.update_yaxes(range=[lo - pad, hi + pad], title=stock.currency)
        st.plotly_chart(style(fig, "Price over the last year", 330), use_container_width=True)

    b = stock.analyst.breakdown
    if b:
        names = {"strongBuy": "Strong buy", "buy": "Buy", "hold": "Hold", "sell": "Sell", "strongSell": "Strong sell"}
        colors = {"strongBuy": "#22C55E", "buy": MINT, "hold": AMBER, "sell": "#FF8A65", "strongSell": RED}
        keys = list(b)
        fig2 = go.Figure(go.Bar(x=[b[k] for k in keys], y=[names.get(k, k) for k in keys], orientation="h",
                                marker_color=[colors.get(k, MUTED) for k in keys],
                                text=[b[k] for k in keys], textposition="outside"))
        fig2.update_yaxes(autorange="reversed")
        st.plotly_chart(style(fig2, "What analysts are saying", 250), use_container_width=True)

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

st.markdown(
    '<div class="footer">Stock Trading Companion · built by Aafan Khan · '
    '<a href="https://github.com/aafankhan4796-eng/stock-briefing">GitHub</a> · '
    '<a href="https://www.linkedin.com/in/aafan-khan">LinkedIn</a><br>'
    'Research tool only, not financial advice.</div>',
    unsafe_allow_html=True,
)
