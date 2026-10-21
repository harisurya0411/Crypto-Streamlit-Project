"""
Crypto Market Insights - home page.

Explains the purpose of the app, summarises the dataset and today's market,
and lists the headline findings from each analysis page.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from analysis import (bear_markets, drawdown, load_benchmarks, load_closes, load_crypto, load_fear_greed,
                      load_snapshot, pct, usd)
from auth import show_logout_button
from ui import COIN_COLORS, insight, reading

st.set_page_config(page_title="Crypto Market Insights", page_icon="🪙", layout="wide")
show_logout_button()

st.title("🪙 Crypto Market Insights & Portfolio Tracker")
st.markdown("#### What eight years of real market data says about investing in cryptocurrency")

crypto = load_crypto()
closes = load_closes()
fng = load_fear_greed()
bench = load_benchmarks()
snap = load_snapshot().set_index("Asset")
btc = closes["Bitcoin"].dropna()
end = closes.index.max()

# ----------------------------------------------------------------------
# Purpose
# ----------------------------------------------------------------------
with st.container(border=True):
    st.markdown(f"""
**Purpose.** Crypto is heavily marketed to young investors in India, usually with stories of 100x gains. This app
tests those stories against **{len(crypto):,} daily price records** for the 10 best-known cryptocurrencies
({btc.index[0]:%b %Y} to {end:%b %Y}), compared with the S&P 500 and gold, so that a first-time investor can see
how crypto actually behaves before putting money in.

**Who it's for.** A student or young professional deciding whether to buy crypto, how much, and how, plus anyone
already holding coins who wants to understand their risk (log in to the portfolio tracker with the demo account).

**Questions it answers:**
1. How have major coins performed, and do prices move in cycles? → *Market Trends*
2. How risky is crypto, and has the risk been rewarded? → *Risk and Return*
3. Does owning several coins spread the risk? → *Correlation*
4. Does buying when the market is fearful pay off? → *Market Sentiment*
5. Is a monthly SIP better than a lump sum, after Indian tax? → *Investment Simulator*
""")

# ----------------------------------------------------------------------
# Dataset at a glance
# ----------------------------------------------------------------------
st.subheader("The data")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Daily price records", f"{len(crypto):,}")
c2.metric("Coins analysed", crypto["Asset"].nunique())
c3.metric("Years covered", f"{(end - btc.index[0]).days / 365.25:.1f}")
c4.metric("Data up to", f"{end:%d %b %Y}")
st.caption("Sources: Binance (daily prices and volume), alternative.me (Fear & Greed Index), Yahoo Finance "
           "(S&P 500, gold, USD/INR), CoinGecko (market caps). Details on the **Data and Methodology** page.")

# ----------------------------------------------------------------------
# Market today
# ----------------------------------------------------------------------
st.subheader("The market right now")
btc_30 = btc.iloc[-1] / btc.loc[:end - pd.Timedelta(days=30)].iloc[-1] - 1
total_cap = snap["market_cap"].sum()
btc_share = snap.loc["Bitcoin", "market_cap"] / total_cap
latest_mood = fng.iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Bitcoin price", usd(btc.iloc[-1]), f"{pct(btc_30, 1, True)} in 30 days")
c2.metric("Bitcoin below its peak", pct(drawdown(btc).iloc[-1], 0), f"peak {usd(btc.max())} on {btc.idxmax():%d %b %Y}",
          delta_color="off")
c3.metric("Market value of these 10 coins", usd(total_cap), f"Bitcoin = {pct(btc_share, 0)} of it", delta_color="off")
c4.metric("Fear & Greed Index", int(latest_mood["FearGreed"]), latest_mood["Sentiment"], delta_color="off")

left, right = st.columns([1, 1])
with left:
    reading("Share of the combined market value (market cap) of the 10 coins, from the CoinGecko snapshot.")
    fig = px.pie(snap.reset_index(), names="Asset", values="market_cap", hole=0.5, color="Asset",
                 color_discrete_map=COIN_COLORS)
    fig.update_traces(textinfo="percent+label", textposition="inside")
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=340, showlegend=False)
    st.plotly_chart(fig, width="stretch")
with right:
    reading("Bitcoin's price over the last year, with the Fear & Greed reading on each day as colour.")
    last_year = pd.concat([btc.loc[end - pd.DateOffset(years=1):].rename("Price"), fng["FearGreed"]], axis=1,
                          join="inner").reset_index()
    fig = px.scatter(last_year, x="Date", y="Price", color="FearGreed", color_continuous_scale="RdYlGn",
                     range_color=[0, 100])
    fig.update_traces(marker=dict(size=4))
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=340, coloraxis_colorbar=dict(title="F&G"))
    st.plotly_chart(fig, width="stretch")

top2 = (snap.loc["Bitcoin", "market_cap"] + snap.loc["Ethereum", "market_cap"]) / total_cap
yr = btc.loc[end - pd.DateOffset(years=1):]
insight([
    f"Bitcoin and Ethereum together make up **{pct(top2, 0)}** of the value of these 10 coins. The other eight, "
    "despite much of the hype, are a small part of the market.",
    f"Over the last 12 months Bitcoin ranged from **{usd(yr.min())}** to **{usd(yr.max())}**, a swing of "
    f"**{pct(yr.max() / yr.min() - 1, 0)}** between low and high, in a single year.",
    f"Current mood is **{latest_mood['Sentiment']}** ({int(latest_mood['FearGreed'])}/100). The Sentiment page "
    "tests whether readings like this have meant anything for future prices.",
], "Reading the market today")

# ----------------------------------------------------------------------
# Headline findings
# ----------------------------------------------------------------------
st.subheader("Headline findings")
rets = closes.loc["2020-09-01":].pct_change(fill_method=None).dropna()
basket_vol = rets.mean(axis=1).std() * np.sqrt(365)
btc_vol_common = rets["Bitcoin"].std() * np.sqrt(365)
sp = bench["SP500"].dropna()
sp_vol = sp.pct_change().std() * np.sqrt(252)
btc_vol = btc.pct_change().std() * np.sqrt(365)
pre = closes.loc[:"2021-12-31"].max()
post = closes.loc["2022-01-01":].max()
bears = bear_markets(btc, -0.5)

findings = [
    ("📈", f"Bitcoin rose **{btc.iloc[-1] / btc.iloc[0]:.1f}x** since {btc.index[0]:%Y}, but fell more than 50% in "
           f"**{len(bears)} separate bear markets** along the way.", "pages/1_Market_Trends.py"),
    ("⚖️", f"Bitcoin is about **{btc_vol / sp_vol:.1f}x as volatile** as the S&P 500, and altcoins are more volatile still.",
     "pages/2_Risk_and_Return.py"),
    ("🔗", f"An equal mix of all 10 coins was **{'more' if basket_vol > btc_vol_common else 'barely less'} volatile** "
           f"({pct(basket_vol, 0)}) than Bitcoin alone ({pct(btc_vol_common, 0)}): more coins is not diversification.",
     "pages/3_Correlation.py"),
    ("🧠", "The Fear & Greed Index mostly mirrors recent prices; on its own it is a weak predictor of what comes next.",
     "pages/4_Market_Sentiment.py"),
    ("🧮", f"**{int((post < pre).sum())} of 10** coins never regained their 2021 peak. A monthly SIP cannot rescue a coin "
           "that keeps falling.", "pages/5_Investment_Simulator.py"),
]
for icon, text, page in findings:
    c1, c2 = st.columns([5, 1])
    c1.markdown(f"{icon} {text}")
    c2.page_link(page, label="Evidence →")

st.page_link("pages/6_Conclusions.py", label="Read the full conclusions", icon="✅")

st.divider()
st.markdown("**Portfolio tracker.** Log in on **My Portfolio** (demo: `guest` / `crypto123`) to see live values, a "
            "map of where your coins are held, and a risk check of your own mix using the same historical data.")
