"""Stock Trading Companion - personal watchlist edition (private, password protected).

Run locally:  streamlit run personal.py
Deploy as a second Streamlit app with these secrets:
    APP_PASSWORD = "choose-your-own"
    WATCHLIST = "NVDA, MU, ASML.AS"   # optional: replaces the default groups below
"""

import hmac
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from briefing import data
from briefing.demo import demo_history, demo_stock
from briefing.report import DISCLAIMER, RATING_LABELS, build_markdown

MINT, AMBER, RED, MUTED, GRID = "#3DDC97", "#F5B841", "#FF6B6B", "#8A9BB8", "rgba(138,155,184,0.15)"
GROUPS = {
    "Market": ["^GSPC", "^IXIC"],
    "AI & chips": ["NVDA", "AMD", "AVGO", "TSM", "ARM", "ASML.AS", "QCOM"],
    "Memory": ["MU", "000660.KS", "005930.KS", "SNDK"],
    "Big tech / AI": ["MSFT", "GOOGL", "META", "AMZN", "AAPL"],
    "Other": ["ADYEN.AS"],
}
INDEX_NAMES = {"^GSPC": "S&P 500", "^IXIC": "Nasdaq Composite"}
SHORT = {"000660.KS": "SK hynix", "005930.KS": "Samsung", "ASML.AS": "ASML", "ADYEN.AS": "Adyen"}
GROUP_OF = {t: g for g, ts in GROUPS.items() for t in ts}

st.set_page_config(page_title="My Trading Companion", page_icon="📈", layout="wide")


def secret(key, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


# ---------- password gate ----------
def unlocked() -> bool:
    pw = secret("APP_PASSWORD")
    if not pw:
        st.warning("No APP_PASSWORD set, so this page is open. Add one in the app's secrets to make it private.")
        return True
    if st.session_state.get("ok"):
        return True
    st.markdown("### 🔒 My Trading Companion")
    entered = st.text_input("Password", type="password")
    if entered:
        if hmac.compare_digest(entered, str(pw)):
            st.session_state.ok = True
            st.rerun()
        st.error("Wrong password.")
    return False


if not unlocked():
    st.stop()

# ---------- styling ----------
st.markdown(f"""
<style>
  .hero {{ background: linear-gradient(135deg, #12304F 0%, #0E3B3A 100%);
          border: 1px solid rgba(61,220,151,0.25); border-radius: 18px; padding: 22px 26px; margin-bottom: 14px; }}
  .hero .tag {{ color:{MINT}; font-size:13px; font-weight:700; letter-spacing:2px; text-transform:uppercase; }}
  .hero h1 {{ color:#FFFFFF; font-size:32px; margin:6px 0 4px; padding:0; }}
  .hero p {{ color:#C5D3EA; font-size:15px; margin:0; }}
  div[data-testid="stMetric"] {{ background:#152238; border:1px solid rgba(138,155,184,0.18);
          border-radius:14px; padding:14px 16px; }}
  div[data-testid="stMetricLabel"] p {{ color:{MUTED}; }}
  h2 {{ color:{MINT} !important; font-size:22px !important; }}
</style>
<div class="hero">
  <div class="tag">Personal edition</div>
  <h1>📈 My Trading Companion</h1>
  <p>Aafan's watchlist: the market, AI &amp; chip stocks, memory makers and big tech, on one screen.</p>
</div>
""", unsafe_allow_html=True)

# ---------- watchlist state ----------
if "watchlist" not in st.session_state:
    raw = secret("WATCHLIST")
    if raw:
        st.session_state.watchlist = [t.strip().upper() for t in str(raw).split(",") if t.strip()]
    else:
        st.session_state.watchlist = [t for ts in GROUPS.values() for t in ts]

with st.sidebar:
    st.header("Watchlist")
    demo = st.toggle("Demo mode (offline, fictional data)", value=False)
    add = st.text_input("Add a company or ticker", placeholder="e.g. Shell, ING, TSLA")
    if add:
        try:
            matches = data.resolve(add)
        except Exception:
            matches = []
        if matches:
            sym = matches[0]["symbol"].upper()
            if st.button(f"Add {matches[0]['name']} ({sym})"):
                if sym not in st.session_state.watchlist:
                    st.session_state.watchlist.append(sym)
                st.rerun()
        else:
            st.caption("No match found. Try the exact ticker, e.g. INGA.AS.")
    keep = st.multiselect("Your stocks", st.session_state.watchlist, default=st.session_state.watchlist)
    if keep != st.session_state.watchlist:
        st.session_state.watchlist = keep
        st.rerun()
    st.caption("Changes last for this visit. To save a custom list, paste this into the app's secrets as WATCHLIST:")
    st.code(", ".join(st.session_state.watchlist) or "-", language=None)
    if st.button("Refresh prices"):
        st.cache_data.clear()
        st.rerun()


def _load_one(symbol):
    try:
        return symbol, data.fetch(symbol), data.history(symbol, "3mo"), None
    except Exception as e:
        return symbol, None, None, str(e)


@st.cache_data(ttl=300, show_spinner=False)
def load_all(symbols):
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(_load_one, symbols))


def load_demo(symbol, i):
    base = demo_stock()
    shift = [1.0, 0.62, 1.35, 0.88, 1.12, 0.7, 1.2][i % 7]
    s = replace(base, ticker=symbol, name=f"{symbol} (demo)", price=round(base.price * shift, 2),
                previous_close=round(base.previous_close * shift * (1 + (i % 3 - 1) * 0.02), 2),
                week52_low=base.week52_low * shift, week52_high=base.week52_high * shift,
                analyst=replace(base.analyst, target_mean=round(base.analyst.target_mean * shift, 2)))
    return s, demo_history(65) * shift


rows, stocks, errors = [], {}, []
with st.spinner("Your companion is checking your watchlist..."):
    syms = tuple(st.session_state.watchlist)
    results = [(t, *load_demo(t, i), None) for i, t in enumerate(syms)] if demo else load_all(syms)
    for sym, s, h, err in results:
        if err or s is None:
            errors.append(f"{sym}: {err}")
            continue
        if sym in INDEX_NAMES:
            s = replace(s, name=INDEX_NAMES[sym])
        stocks[sym] = (s, h)
        a = s.analyst
        rows.append({
            "Group": GROUP_OF.get(sym, "Added"),
            "Ticker": sym,
            "Company": s.name,
            "Price": s.price,
            "Currency": s.currency,
            "Today %": s.change_pct,
            "3-month trend": [float(x) for x in h.values] if h is not None and len(h) else [],
            "52-week position %": None if s.position_in_52w_range is None else s.position_in_52w_range * 100,
            "Analyst view": RATING_LABELS.get((a.recommendation or "none").lower(), "n/a"),
            "Avg target": a.target_mean,
            "Upside to target %": s.upside_to_target_pct,
            "Next earnings": (s.next_earnings or "")[:10],
        })

for e in errors:
    st.warning(f"Couldn't load {e}")

if not rows:
    st.info("Add a stock in the sidebar to get started.")
    st.stop()

df = pd.DataFrame(rows)

# ---------- headline metrics ----------
idx = df[df["Ticker"].isin(list(INDEX_NAMES))]
stk = df[~df["Ticker"].isin(list(INDEX_NAMES))]
moves = stk.dropna(subset=["Today %"])
c1, c2, c3, c4, c5 = st.columns(5)
for col, (_, r) in zip((c1, c2), idx.iterrows()):
    col.metric(r["Company"], f"{r['Price']:,.0f}" if pd.notna(r["Price"]) else "n/a",
               f"{r['Today %']:+.2f}%" if pd.notna(r["Today %"]) else None)
c3.metric("Stocks up today", int((moves["Today %"] > 0).sum()), f"{int((moves['Today %'] < 0).sum())} down",
          delta_color="off")
if len(moves):
    best = moves.loc[moves["Today %"].idxmax()]
    worst = moves.loc[moves["Today %"].idxmin()]
    c4.metric("Best today", SHORT.get(best["Ticker"], best["Ticker"]), f"{best['Today %']:+.2f}%")
    c5.metric("Worst today", SHORT.get(worst["Ticker"], worst["Ticker"]), f"{worst['Today %']:+.2f}%")

# ---------- sector averages ----------
sec = moves.groupby("Group")["Today %"].mean().dropna()
if len(sec) > 1:
    st.markdown("## How each group did today")
    sec = sec.sort_values()
    fig_s = go.Figure(go.Bar(x=sec.values, y=sec.index, orientation="h",
                             marker_color=[MINT if v >= 0 else RED for v in sec.values],
                             text=[f"{v:+.2f}%" for v in sec.values], textposition="outside"))
    fig_s.update_layout(height=60 + 40 * len(sec), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color=MUTED), margin=dict(l=10, r=40, t=10, b=10))
    fig_s.update_xaxes(gridcolor=GRID, zeroline=True, zerolinecolor=MUTED, ticksuffix="%")
    st.plotly_chart(fig_s, width="stretch")

# ---------- watchlist table ----------
st.markdown("## Your watchlist")
groups = ["All"] + [g for g in list(GROUPS) + ["Added"] if g in set(df["Group"])]
view = st.segmented_control("Show", groups, default="All") or "All"
shown = df if view == "All" else df[df["Group"] == view]
st.dataframe(
    shown, hide_index=True, width="stretch", height=min(38 * (len(shown) + 1) + 4, 760),
    column_config={
        "Price": st.column_config.NumberColumn(format="%.2f"),
        "Today %": st.column_config.NumberColumn(format="%+.2f%%"),
        "3-month trend": st.column_config.LineChartColumn(width="medium"),
        "52-week position %": st.column_config.ProgressColumn(
            min_value=0, max_value=100, format="%.0f%%",
            help="0% = at the 52-week low, 100% = at the 52-week high"),
        "Avg target": st.column_config.NumberColumn(format="%.2f"),
        "Upside to target %": st.column_config.NumberColumn(format="%+.0f%%"),
    },
)

# ---------- upcoming earnings ----------
today = date.today().isoformat()
upcoming = df[df["Next earnings"] >= today].sort_values("Next earnings")
if len(upcoming):
    st.markdown("## Coming up")
    for _, r in upcoming.head(8).iterrows():
        st.markdown(f"- **{r['Next earnings']}**: {r['Company']} ({r['Ticker']}) reports earnings")

# ---------- deep dive ----------
st.markdown("## Deep dive")
pick = st.selectbox("Open the full briefing for", list(stocks), format_func=lambda t: f"{stocks[t][0].name} ({t})")
s, h = stocks[pick]
if h is not None and len(h):
    up = h.iloc[-1] >= h.iloc[0]
    fig = go.Figure(go.Scatter(x=h.index, y=h.values, mode="lines", line=dict(width=2.5, color=MINT if up else RED),
                               fill="tozeroy", fillcolor="rgba(61,220,151,0.12)" if up else "rgba(255,107,107,0.12)"))
    lo, hi = float(h.min()), float(h.max())
    if s.analyst.target_mean:
        hi = max(hi, s.analyst.target_mean)
        fig.add_hline(y=s.analyst.target_mean, line_dash="dash", line_color=AMBER,
                      annotation_text="Avg analyst target", annotation_font_color=AMBER,
                      annotation_position="top left")
    pad = (hi - lo) * 0.08 or 1
    fig.update_layout(title=dict(text="Last 3 months", font=dict(color="#E6EDF7", size=16)), height=320,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=MUTED),
                      margin=dict(l=10, r=10, t=44, b=10))
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, range=[lo - pad, hi + pad], title=s.currency)
    st.plotly_chart(fig, width="stretch")

report = build_markdown(s)
with st.expander("Full briefing", expanded=True):
    st.markdown(report)
st.download_button("Download this briefing (Markdown)", report, file_name=f"{s.ticker}_briefing.md")

st.caption(DISCLAIMER)
