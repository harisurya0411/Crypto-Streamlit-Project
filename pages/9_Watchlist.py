"""
Watchlist page - live prices of coins you're considering, with the
historical context needed to judge them (trend, risk, distance from peak).
"""

import numpy as np
import pandas as pd
import streamlit as st

from analysis import CRYPTO_DAYS_PER_YEAR, drawdown, load_closes, load_snapshot, pct
from auth import show_logout_button
from ui import insight, question, reading
from utils import ASSET_IDS, live_prices

st.set_page_config(page_title="Watchlist", page_icon="👀", layout="wide")
show_logout_button()

st.title("👀 Watchlist")
question("Before buying a coin: how has it been trending, how risky is it, and is it 'cheap' only because it crashed?")

if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = ["Ethereum", "Solana", "XRP", "Cardano"]

c1, c2 = st.columns([3, 1])
new_coin = c1.selectbox("Add a coin to your watchlist", options=[c for c in ASSET_IDS if c not in st.session_state["watchlist"]] or ["—"])
c2.write("")
c2.write("")
if c2.button("➕ Add to watchlist") and new_coin != "—":
    st.session_state["watchlist"].append(new_coin)
    st.rerun()

watch = st.session_state["watchlist"]
if not watch:
    st.info("Your watchlist is empty. Add a coin above.")
    st.stop()

closes = load_closes()
snap = load_snapshot().set_index("Asset")
prices, change_24h, price_source = live_prices(watch)
last = closes.index.max()

rows = []
for coin in watch:
    s = closes[coin].dropna()
    r1y = s.loc[last - pd.DateOffset(years=1):].pct_change().dropna()
    btc_r = closes["Bitcoin"].loc[r1y.index].pct_change()
    rows.append({
        "Coin": coin,
        "Price (USD)": prices.get(coin),
        "24h %": change_24h.get(coin),
        "30d %": (s.iloc[-1] / s.loc[:last - pd.Timedelta(days=30)].iloc[-1] - 1) * 100,
        "1y %": (s.iloc[-1] / s.loc[:last - pd.DateOffset(years=1)].iloc[-1] - 1) * 100,
        "1y volatility %": r1y.std() * np.sqrt(CRYPTO_DAYS_PER_YEAR) * 100,
        "Corr. with BTC": r1y.corr(btc_r),
        "Below ATH %": drawdown(s).iloc[-1] * 100,
        "Market cap": snap.loc[coin, "market_cap"] if coin in snap.index else None,
        "Last 90 days": s.iloc[-90:].round(6).tolist(),
    })
df = pd.DataFrame(rows)

st.caption(f"Live prices: {price_source}. Trend and risk columns use daily closes up to {last:%d %b %Y}.")
reading("ATH = all-time high in the dataset. Volatility is the size of a typical year's swings. "
        "Correlation with BTC near 1 means the coin mostly just follows Bitcoin.")
st.dataframe(df, width="stretch", hide_index=True, column_config={
    "Price (USD)": st.column_config.NumberColumn(format="$%.4g"),
    "24h %": st.column_config.NumberColumn(format="%+.1f%%"),
    "30d %": st.column_config.NumberColumn(format="%+.1f%%"),
    "1y %": st.column_config.NumberColumn(format="%+.1f%%"),
    "1y volatility %": st.column_config.NumberColumn(format="%.0f%%"),
    "Corr. with BTC": st.column_config.NumberColumn(format="%.2f"),
    "Below ATH %": st.column_config.ProgressColumn(format="%.0f%%", min_value=-100, max_value=0),
    "Market cap": st.column_config.NumberColumn(format="compact"),
    "Last 90 days": st.column_config.LineChartColumn(),
})

best = df.loc[df["1y %"].idxmax()]
calm = df.loc[df["1y volatility %"].idxmin()]
deepest = df.loc[df["Below ATH %"].idxmin()]
# How often have coins that fell this far from their peak gone on to regain it?
recovered = []
for c in closes.columns:
    pre = closes[c].loc[:"2021-12-31"].max()
    recovered.append(closes[c].loc["2022-01-01":].max() >= pre)
insight([
    f"Best 1-year performance on this list: **{best['Coin']}** ({best['1y %']:+.0f}%)"
    + (", so every coin here is down over the past year" if best["1y %"] < 0 else "")
    + f". Calmest: **{calm['Coin']}** ({calm['1y volatility %']:.0f}% volatility).",
    f"**{deepest['Coin']}** is **{abs(deepest['Below ATH %']):.0f}%** below its all-time high. A big fall can look "
    f"like a bargain, but of the 10 coins in this dataset only **{sum(recovered)}** ever got back above their 2021 "
    "peak. A crashed price is not proof of value.",
    f"Average correlation with Bitcoin on this list: **{df['Corr. with BTC'].mean():.2f}**. Adding these coins "
    "mainly adds more Bitcoin-like risk, not something different.",
], "What to look at before buying")

remove_coin = st.selectbox("Remove a coin", options=["—"] + watch)
if remove_coin != "—" and st.button("🗑️ Remove"):
    st.session_state["watchlist"].remove(remove_coin)
    st.rerun()
