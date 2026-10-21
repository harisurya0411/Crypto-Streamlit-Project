"""
My Portfolio - live value of your holdings, where they are held, how they
have performed, and how risky the mix is according to historical data.
"""

import folium
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

from analysis import CRYPTO_DAYS_PER_YEAR, drawdown, load_closes, pct, usd
from auth import check_login, show_logout_button
from ui import COIN_COLORS, PLOT_LAYOUT, insight, reading
from utils import EXCHANGE_LOCATIONS, INDIAN_EXCHANGES, live_prices, load_holdings

st.set_page_config(page_title="My Portfolio", page_icon="💼", layout="wide")
check_login()
show_logout_button()

st.title("💼 My Portfolio")
st.caption("Live value of your holdings, where they are custodied, and how risky the mix has been historically")

holdings = load_holdings()
if holdings.empty:
    st.info("Your portfolio is empty. Go to **Add Holding** in the sidebar to add your first crypto asset, "
            "or bulk-upload a CSV.")
    st.stop()
if st.session_state.get("username") == "guest":
    st.info("You're viewing the **demo portfolio**. Its buy prices are the real closing prices on each buy date, "
            "so the gains and losses below are what these trades actually would have made.")

prices, change_24h, price_source = live_prices(holdings["Asset"].unique())
st.caption(f"Prices: {price_source}")

holdings["CurrentPrice"] = holdings["Asset"].map(prices)
holdings["CostBasis"] = holdings["Quantity"] * holdings["BuyPrice"]
holdings["CurrentValue"] = holdings["Quantity"] * holdings["CurrentPrice"]
holdings["GainLoss"] = holdings["CurrentValue"] - holdings["CostBasis"]
holdings["GainLossPct"] = (holdings["GainLoss"] / holdings["CostBasis"] * 100).round(1)

# ----------------------------------------------------------------------
# SIDEBAR FILTERS
# ----------------------------------------------------------------------
st.sidebar.header("📊 Filters")
assets = sorted(holdings["Asset"].unique())
selected_assets = st.sidebar.multiselect("Asset", options=assets, default=assets)
exchanges = sorted(holdings["Exchange"].unique())
selected_exchanges = st.sidebar.multiselect("Exchange", options=exchanges, default=exchanges)
val_min, val_max = float(holdings["CurrentValue"].min()), float(holdings["CurrentValue"].max())
if val_min == val_max:
    val_max += 1  # avoid a zero-width slider when there's only one holding
value_range = st.sidebar.slider("Current value range ($)", val_min, val_max, (val_min, val_max))

filtered = holdings[
    holdings["Asset"].isin(selected_assets)
    & holdings["Exchange"].isin(selected_exchanges)
    & holdings["CurrentValue"].between(*value_range)
]
if filtered.empty:
    st.warning("No holdings match these filters.")
    st.stop()

# ----------------------------------------------------------------------
# KPI ROW
# ----------------------------------------------------------------------
total_value = filtered["CurrentValue"].sum()
total_cost = filtered["CostBasis"].sum()
total_gain = filtered["GainLoss"].sum()
best = filtered.loc[filtered["GainLossPct"].idxmax()]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Portfolio Value", f"${total_value:,.2f}")
col2.metric("Total Gain / Loss", f"${total_gain:,.2f}", pct(total_gain / total_cost, 1, True))
col3.metric("Best Performer", f"{best['Asset']} ({best['GainLossPct']:+.1f}%)")
col4.metric("Holdings", len(filtered))

tab_overview, tab_perf, tab_risk = st.tabs(["🗺️ Where it's held", "📈 Performance", "⚠️ Risk check"])

# ----------------------------------------------------------------------
# TAB 1: map + table
# ----------------------------------------------------------------------
with tab_overview:
    st.subheader("Holdings by exchange")
    reading("Bubble size = value held at each exchange's headquarters location. Click a bubble for the amount.")
    exchange_value = filtered.groupby("Exchange")["CurrentValue"].sum().reset_index()
    biggest = exchange_value["CurrentValue"].max()

    m = folium.Map(location=[20, 10], zoom_start=2, tiles="CartoDB dark_matter")
    for _, row in exchange_value.iterrows():
        coords = EXCHANGE_LOCATIONS.get(row["Exchange"])
        if coords:
            folium.CircleMarker(
                location=coords,
                radius=6 + 29 * np.sqrt(row["CurrentValue"] / biggest),
                color="#f0b90b", fill=True, fill_color="#f0b90b", fill_opacity=0.7,
                popup=folium.Popup(f"<b>{row['Exchange']}</b><br>${row['CurrentValue']:,.2f}", max_width=200),
                tooltip=row["Exchange"],
            ).add_to(m)
    st_folium(m, height=420, use_container_width=True, returned_objects=[])

    share = (exchange_value.set_index("Exchange")["CurrentValue"] / total_value).sort_values(ascending=False)
    indian = share[share.index.isin(INDIAN_EXCHANGES)].sum()
    points = [
        f"**{pct(share.iloc[0], 0)}** of this portfolio sits on a single exchange (**{share.index[0]}**). "
        f"Spread across {len(share)} exchanges in total.",
        "Coins left on an exchange are only as safe as that exchange. FTX's collapse (Nov 2022) froze customer funds "
        "worldwide, and India's WazirX lost about $230M to a hack in July 2024 and froze withdrawals.",
    ]
    if indian > 0:
        points.append(f"**{pct(indian, 0)}** is on Indian exchanges (WazirX / CoinDCX). These are convenient for "
                      "rupee deposits and handle the 1% TDS automatically, but carry the same custody risk.")
    points.append("Long-term holdings are safer in a personal wallet you control; keep on exchanges only what you trade.")
    insight(points, "What this tells us about custody risk")

    st.subheader("📋 Your holdings")
    cols = ["Asset", "Exchange", "Quantity", "BuyPrice", "CurrentPrice", "CurrentValue", "GainLoss", "GainLossPct"]
    if "BuyDate" in filtered:
        cols.insert(2, "BuyDate")
    st.dataframe(filtered[cols], width="stretch", hide_index=True)
    st.download_button("⬇️ Download holdings as CSV", data=filtered.to_csv(index=False).encode("utf-8"),
                       file_name="crypto_holdings.csv", mime="text/csv")

# ----------------------------------------------------------------------
# TAB 2: allocation, gain/loss, buy timing
# ----------------------------------------------------------------------
with tab_perf:
    c1, c2 = st.columns(2)
    alloc = filtered.groupby("Asset")["CurrentValue"].sum().sort_values(ascending=False)
    with c1:
        st.subheader("Allocation")
        fig = px.pie(alloc.reset_index(), names="Asset", values="CurrentValue", hole=0.45,
                     color="Asset", color_discrete_map=COIN_COLORS)
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=330)
        st.plotly_chart(fig, width="stretch")
    gl = filtered.groupby("Asset")[["GainLoss", "CostBasis"]].sum()
    gl["Return %"] = gl["GainLoss"] / gl["CostBasis"] * 100
    gl = gl.sort_values("GainLoss")
    with c2:
        st.subheader("Gain / loss by asset")
        fig = px.bar(gl, x=gl.index, y="GainLoss", color="GainLoss", color_continuous_scale=["#e74c3c", "#2ecc71"],
                     color_continuous_midpoint=0, hover_data={"Return %": ":.1f"}, labels={"x": "", "GainLoss": "Gain/loss ($)"})
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=330, coloraxis_showscale=False)
        st.plotly_chart(fig, width="stretch")

    weights = alloc / alloc.sum()
    effective_n = 1 / (weights ** 2).sum()
    winners = (gl["GainLoss"] > 0).sum()
    insight([
        f"Largest position: **{weights.index[0]}** at **{pct(weights.iloc[0], 0)}** of the portfolio. Although you hold "
        f"{len(weights)} coins, the weights make it behave like **{effective_n:.1f} equally-sized positions** "
        "(effective number of holdings = 1 / sum of squared weights).",
        f"**{winners} of {len(gl)}** coins are in profit. Biggest gain: **{gl['GainLoss'].idxmax()}** "
        f"({usd(gl['GainLoss'].max())}); biggest loss: **{gl['GainLoss'].idxmin()}** ({usd(gl['GainLoss'].min())}).",
    ])

    if "BuyDate" in filtered and filtered["BuyDate"].notna().any():
        st.subheader("Did buy timing matter?")
        reading("For each purchase: how far below its all-time high the coin was on the day you bought it, "
                "against the return since. Points further left were bought nearer a peak.")
        closes = load_closes()
        timed = filtered.dropna(subset=["BuyDate"]).copy()
        timed["BuyDate"] = pd.to_datetime(timed["BuyDate"])
        timed["Below ATH at buy %"] = [
            drawdown(closes[a].loc[:d]).iloc[-1] * 100 if a in closes else np.nan
            for a, d in zip(timed["Asset"], timed["BuyDate"])]
        fig = px.scatter(timed, x="Below ATH at buy %", y="GainLossPct", color="Asset", size="CostBasis",
                         color_discrete_map=COIN_COLORS, hover_data=["BuyDate", "Exchange"],
                         labels={"GainLossPct": "Return since buying %"})
        fig.add_hline(y=0, line_dash="dash", line_color="grey")
        fig.update_layout(**PLOT_LAYOUT, height=380)
        fig.update_layout(hovermode="closest")
        st.plotly_chart(fig, width="stretch")
        near_peak = timed[timed["Below ATH at buy %"] > -20]
        far = timed[timed["Below ATH at buy %"] <= -50]
        pts = []
        if len(near_peak):
            pts.append(f"Purchases made within 20% of an all-time high: **{len(near_peak)}**, average return "
                       f"**{near_peak['GainLossPct'].mean():+.0f}%**.")
        if len(far):
            pts.append(f"Purchases made 50%+ below the high (after a crash): **{len(far)}**, average return "
                       f"**{far['GainLossPct'].mean():+.0f}%**.")
        pts.append("Buying after a crash, when it feels worst, has historically worked out far better than buying "
                   "during the excitement near a peak.")
        insight(pts)

# ----------------------------------------------------------------------
# TAB 3: historical risk of this exact mix
# ----------------------------------------------------------------------
with tab_risk:
    st.subheader("How risky is this mix?")
    lookback = st.radio("History used", ["1 year", "3 years"], horizontal=True, index=1)
    years = 1 if lookback == "1 year" else 3
    closes = load_closes()
    hist = closes.loc[closes.index.max() - pd.DateOffset(years=years):, weights.index]
    rets = hist.pct_change(fill_method=None).dropna()
    port = (rets * weights[rets.columns]).sum(axis=1)
    port_vol = port.std() * np.sqrt(CRYPTO_DAYS_PER_YEAR)
    btc_vol = closes["Bitcoin"].loc[rets.index[0]:].pct_change().std() * np.sqrt(CRYPTO_DAYS_PER_YEAR)
    weighted_avg_vol = (rets.std() * np.sqrt(CRYPTO_DAYS_PER_YEAR) * weights[rets.columns]).sum()
    value_path = (1 + port).cumprod()
    var95 = -np.percentile(port, 5)

    reading(f"Replays the last {lookback} of real daily price moves on your *current* weights, to show how this "
            "mix would have behaved. It is a backtest, not a forecast.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Annual volatility", pct(port_vol, 0), f"Bitcoin alone: {pct(btc_vol, 0)}", delta_color="off")
    c2.metric("Worst fall of this mix", pct(drawdown(value_path).min(), 0))
    c3.metric("Bad day (1 in 20)", f"-${var95 * total_value:,.0f}", f"-{var95 * 100:.1f}% of value", delta_color="off")

    fig = px.line((value_path * total_value).rename("Portfolio"), labels={"value": "Value ($)", "index": ""},
                  color_discrete_sequence=["#f0b90b"])
    fig.update_layout(**PLOT_LAYOUT, height=320, showlegend=False)
    st.plotly_chart(fig, width="stretch")

    diversification = 1 - port_vol / weighted_avg_vol
    insight([
        f"With today's weights this portfolio would have swung **{pct(port_vol, 0)}** a year, "
        f"{'more' if port_vol > btc_vol else 'less'} than Bitcoin alone ({pct(btc_vol, 0)}).",
        f"Holding several coins cut risk by only **{pct(diversification, 0)}** compared with the average of the "
        "individual coins, because they move together (see the Correlation page).",
        f"On 1 day in 20 you should expect to lose at least **${var95 * total_value:,.0f}** "
        f"({var95 * 100:.1f}% of the portfolio). If that number would make you panic-sell, the position is too large.",
    ], "What the history of this mix tells us")
