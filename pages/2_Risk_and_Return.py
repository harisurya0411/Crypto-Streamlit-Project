"""
Risk and Return - how volatile crypto is, how deep it falls, and whether
the extra risk has been rewarded compared with stocks and gold.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analysis import (CRYPTO_DAYS_PER_YEAR, MARKET_DAYS_PER_YEAR, drawdown, load_benchmarks,
                      load_closes, max_drawdown_info, pct, risk_return_table)
from auth import show_logout_button
from ui import COIN_COLORS, PLOT_LAYOUT, insight, question, reading, sources, takeaway

st.set_page_config(page_title="Risk and Return", page_icon="⚖️", layout="wide")
show_logout_button()

st.title("⚖️ Risk and Return")
question("How risky is crypto compared with stocks and gold, and has that extra risk actually been rewarded?")

closes = load_closes()
bench = load_benchmarks()[["SP500", "Gold"]].rename(columns={"SP500": "S&P 500"})

# ----------------------------------------------------------------------
# Sidebar filters
# ----------------------------------------------------------------------
st.sidebar.header("📊 Filters")
coins = st.sidebar.multiselect("Coins", list(closes.columns), default=list(closes.columns))
period = st.sidebar.radio("Period", ["Full history (since 2018)", "Last 3 years", "Last 1 year"])
show_bench = st.sidebar.toggle("Compare with S&P 500 and gold", value=True)

if not coins:
    st.warning("Pick at least one coin in the sidebar.")
    st.stop()

end = closes.index.max()
start = {"Last 3 years": end - pd.DateOffset(years=3),
         "Last 1 year": end - pd.DateOffset(years=1)}.get(period, closes.index.min())
c = closes.loc[start:, coins]
b = bench.loc[start:end]

table = risk_return_table(c, CRYPTO_DAYS_PER_YEAR)
if show_bench:
    table = pd.concat([table, risk_return_table(b, MARKET_DAYS_PER_YEAR)])
table = table.sort_values("Sharpe", ascending=False)

# ----------------------------------------------------------------------
# 1. Risk vs return scatter
# ----------------------------------------------------------------------
st.subheader("1. Return vs risk")
reading("Each dot is one asset. Further right = more volatile (bigger price swings). Higher up = more growth "
        "per year (CAGR). The ideal asset sits top-left: high return for little risk.")
plot = table.reset_index()
plot["CAGR %"] = plot["CAGR"] * 100
plot["Volatility %"] = plot["Volatility"] * 100
fig = px.scatter(plot, x="Volatility %", y="CAGR %", text="Asset", color="Asset",
                 color_discrete_map=COIN_COLORS, size=np.clip(plot["Sharpe"].fillna(0), 0.1, None) + 0.3,
                 hover_data={"Sharpe": ":.2f", "Volatility %": ":.0f", "CAGR %": ":.0f"})
fig.update_traces(textposition="top center")
fig.for_each_trace(lambda t: t.update(textposition="bottom center") if t.name == "S&P 500" else None)
fig.add_hline(y=0, line_dash="dash", line_color="grey")
fig.update_layout(**PLOT_LAYOUT, height=460, showlegend=False)
fig.update_layout(hovermode="closest")
st.plotly_chart(fig, width="stretch")

crypto_tbl = table.loc[[a for a in table.index if a in coins]]
best_sharpe = crypto_tbl["Sharpe"].idxmax()
points = [
    f"Crypto volatility ranges from **{pct(crypto_tbl['Volatility'].min(), 0)}** "
    f"({crypto_tbl['Volatility'].idxmin()}) to **{pct(crypto_tbl['Volatility'].max(), 0)}** "
    f"({crypto_tbl['Volatility'].idxmax()}) a year.",
    f"Best return per unit of risk among the coins (Sharpe ratio): **{best_sharpe}** "
    f"({crypto_tbl.loc[best_sharpe, 'Sharpe']:.2f}).",
]
if show_bench and "S&P 500" in table.index:
    sp_vol = table.loc["S&P 500", "Volatility"]
    btc_vol = table.loc["Bitcoin", "Volatility"] if "Bitcoin" in table.index else crypto_tbl["Volatility"].median()
    points.append(f"The S&P 500's volatility was **{pct(sp_vol, 0)}** and gold's **{pct(table.loc['Gold', 'Volatility'], 0)}**. "
                  f"Bitcoin swings about **{btc_vol / sp_vol:.1f}x** as much as the US stock market.")
    beat_sp = crypto_tbl[crypto_tbl["Sharpe"] > table.loc["S&P 500", "Sharpe"]].index.tolist()
    points.append(f"Only **{len(beat_sp)} of {len(crypto_tbl)}** coins gave a better risk-adjusted return than the "
                  f"S&P 500 in this period" + (f" ({', '.join(beat_sp)})." if beat_sp else "."))
rho = crypto_tbl[["Volatility", "CAGR"]].corr(method="spearman").iloc[0, 1]
if "Bitcoin" in crypto_tbl.index:
    btc_row = crypto_tbl.loc["Bitcoin"]
    worse = crypto_tbl[(crypto_tbl["Volatility"] > btc_row["Volatility"]) & (crypto_tbl["CAGR"] < btc_row["CAGR"])]
    points.append(f"Within crypto, extra volatility was only loosely linked to extra return (rank correlation {rho:+.2f}). "
                  f"**{len(worse)}** coins ({', '.join(worse.index) or 'none'}) were more volatile than Bitcoin "
                  "*and* grew more slowly: more risk with less reward.")
else:
    points.append(f"Within crypto, extra volatility was only loosely linked to extra return (rank correlation {rho:+.2f}).")
insight(points)

with st.expander("Full statistics table"):
    show = table.copy()
    for col in ["CAGR", "Volatility", "Max drawdown", "Below ATH now", "Best day", "Worst day", "% of days up"]:
        show[col] = show[col] * 100
    st.dataframe(show, width="stretch", column_config={
        col: st.column_config.NumberColumn(format="%.1f%%")
        for col in ["CAGR", "Volatility", "Max drawdown", "Below ATH now", "Best day", "Worst day", "% of days up"]
    } | {"Sharpe": st.column_config.NumberColumn(format="%.2f")})
    st.caption("CAGR = compound annual growth rate. Volatility = annualised standard deviation of daily returns. "
               "Sharpe = annualised mean return / volatility (risk-free rate taken as 0). "
               "Crypto is annualised over 365 days, stocks and gold over 252 trading days.")

st.divider()

# ----------------------------------------------------------------------
# 2. Drawdowns
# ----------------------------------------------------------------------
st.subheader("2. How far below its peak (drawdown)")
reading("0% means the asset is at an all-time high. -60% means it is 60% below its previous high. "
        "The deeper and longer the 'underwater' shape, the more painful it was to hold.")
dd_assets = [a for a in ["Bitcoin", "Ethereum"] if a in coins] + (["S&P 500", "Gold"] if show_bench else [])
dd_frame = pd.DataFrame({a: drawdown(c[a] if a in c else b[a]) for a in dd_assets}) * 100
fig = px.line(dd_frame, color_discrete_map=COIN_COLORS, labels={"value": "Drawdown %", "variable": ""})
fig.update_layout(**PLOT_LAYOUT, height=380)
st.plotly_chart(fig, width="stretch")

points = []
for a in dd_assets:
    s = c[a] if a in c else b[a]
    d = max_drawdown_info(s)
    rec = (f"took **{d['days_to_recover']} days** to get back to its old high" if d["days_to_recover"]
           else "**has not yet recovered** its old high")
    points.append(f"**{a}**: worst fall **{pct(d['max_drawdown'])}** ({d['peak_date']:%b %Y} to "
                  f"{d['trough_date']:%b %Y}) and {rec}.")
points.append("A 75% fall needs a **300% gain** just to break even. That maths, not just the size of the drop, "
              "is why deep drawdowns destroy long-term wealth.")
insight(points)

st.divider()

# ----------------------------------------------------------------------
# 3. Daily moves
# ----------------------------------------------------------------------
st.subheader("3. How big are normal daily moves?")
reading("Distribution of daily percentage changes. A tall, narrow shape means calm prices; a wide shape with "
        "long tails means frequent large jumps in both directions.")
dist_assets = [a for a in ["Bitcoin", "Dogecoin"] if a in coins] + (["S&P 500"] if show_bench else [])
dist = pd.concat([((c[a] if a in c else b[a]).dropna().pct_change().dropna() * 100).rename(a).to_frame()
                  .melt(var_name="Asset", value_name="Daily change %") for a in dist_assets])
fig = px.histogram(dist, x="Daily change %", color="Asset", barmode="overlay", histnorm="percent",
                   nbins=200, color_discrete_map=COIN_COLORS, opacity=0.6)
fig.update_xaxes(range=[-20, 20])
fig.update_layout(**PLOT_LAYOUT, height=360, yaxis_title="% of days")
fig.update_layout(hovermode="closest")
st.plotly_chart(fig, width="stretch")

points = []
per_year = {}
for a in dist_assets:
    s = (c[a] if a in c else b[a]).dropna()
    r = s.pct_change().dropna()
    per_year[a] = (r.abs() > 0.05).sum() / ((s.index[-1] - s.index[0]).days / 365.25)
    points.append(f"**{a}**: moved more than 5% in a day on **{(r.abs() > 0.05).mean() * 100:.1f}%** of days "
                  f"({(r.abs() > 0.05).sum()} days); worst day **{pct(r.min())}**, best day **{pct(r.max(), 1, True)}**.")
if "S&P 500" in per_year and len(per_year) > 1:
    crypto_a = [a for a in per_year if a != "S&P 500"][0]
    points.append(f"A 5% day happens about **{per_year['S&P 500']:.1f} times a year** for the S&P 500 (mostly in "
                  f"crises) but about **{per_year[crypto_a]:.0f} times a year** for {crypto_a}. Position size has to "
                  "be small enough to sit through those days without panic-selling.")
insight(points)

st.divider()

# ----------------------------------------------------------------------
# 4. Is Bitcoin getting calmer?
# ----------------------------------------------------------------------
st.subheader("4. Is Bitcoin becoming less volatile as it matures?")
reading("Volatility measured over a rolling 90-day window (63 trading days for the S&P 500), annualised. "
        "Spikes show crisis periods.")
roll_assets = [a for a in ["Bitcoin", "Ethereum"] if a in coins]
roll = pd.DataFrame({a: closes[a].pct_change().rolling(90).std() * np.sqrt(CRYPTO_DAYS_PER_YEAR) * 100
                     for a in roll_assets})
if show_bench:
    sp = bench["S&P 500"].dropna()
    roll["S&P 500"] = sp.pct_change().rolling(63).std() * np.sqrt(MARKET_DAYS_PER_YEAR) * 100
roll = roll.dropna(how="all")
fig = px.line(roll, color_discrete_map=COIN_COLORS, labels={"value": "Annualised volatility %", "variable": ""})
fig.update_layout(**PLOT_LAYOUT, height=360)
st.plotly_chart(fig, width="stretch")

if "Bitcoin" in closes:
    btc_r = closes["Bitcoin"].pct_change()
    by_year = btc_r.groupby(btc_r.index.year).std() * np.sqrt(CRYPTO_DAYS_PER_YEAR)
    first_y, last_y = by_year.index[0], by_year.index[-1]
    calm = by_year.idxmin()
    insight([
        f"Bitcoin's volatility was **{pct(by_year.iloc[0], 0)} in {first_y}** and **{pct(by_year.iloc[-1], 0)} "
        f"in {last_y}**. Its calmest year so far was **{calm} ({pct(by_year.min(), 0)})**.",
        "The long-run trend is downward: as Bitcoin's market grew and spot ETFs brought in large, slower-moving "
        "investors, each dollar of news moved the price less.",
        "Even 'calm' Bitcoin is still well above the stock market's typical 15-20%, so it remains a high-risk asset.",
    ])

takeaway("Bitcoin is roughly 3x as volatile as the US stock market and most altcoins 5x or more, and nearly every "
         "coin has fallen 80%+ from a peak. Only a few coins rewarded that risk better than the S&P 500, so most "
         "holders took on far more risk without being paid more for it.")
sources()
