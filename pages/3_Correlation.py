"""
Correlation and Diversification - do coins move together, and does
holding several of them (or mixing crypto with stocks) reduce risk?
"""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from analysis import CRYPTO_DAYS_PER_YEAR, drawdown, load_benchmarks, load_closes, pct, weekly_returns
from auth import show_logout_button
from ui import COIN_COLORS, PLOT_LAYOUT, insight, question, reading, sources, takeaway

st.set_page_config(page_title="Correlation", page_icon="🔗", layout="wide")
show_logout_button()

st.title("🔗 Correlation and Diversification")
question("If I buy several different coins, am I actually spreading my risk? And does crypto behave like "
         "'digital gold' or like a risky stock?")

closes = load_closes()
bench = load_benchmarks()

# ----------------------------------------------------------------------
# Sidebar filters
# ----------------------------------------------------------------------
st.sidebar.header("📊 Filters")
coins = st.sidebar.multiselect("Coins", list(closes.columns), default=list(closes.columns))
start = st.sidebar.date_input("Analyse from", value=pd.Timestamp("2020-09-01"),
                              min_value=closes.index.min(), max_value=closes.index.max() - pd.Timedelta(days=200))
window = st.sidebar.select_slider("Rolling window (days)", options=[30, 60, 90, 180], value=90)

if len(coins) < 2 or "Bitcoin" not in coins:
    st.warning("Pick Bitcoin plus at least one other coin in the sidebar.")
    st.stop()

returns = closes.loc[pd.Timestamp(start):, coins].pct_change(fill_method=None).dropna()
st.caption(f"Using {len(returns):,} days where all {len(coins)} selected coins traded "
           f"({returns.index[0]:%d %b %Y} to {returns.index[-1]:%d %b %Y}).")

# ----------------------------------------------------------------------
# 1. Correlation matrix
# ----------------------------------------------------------------------
st.subheader("1. How closely do coins move together?")
reading("Correlation of daily returns. 1.0 = always move together, 0 = unrelated, negative = move opposite. "
        "For diversification you want low numbers; anything above 0.5 is a strong link.")
corr = returns.corr()
fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1, aspect="auto")
fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=520)
st.plotly_chart(fig, width="stretch")

pairs = corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1)).stack()
hi, lo = pairs.idxmax(), pairs.idxmin()
btc_corr = corr["Bitcoin"].drop("Bitcoin").sort_values()
sp_gold = bench[["SP500", "Gold"]].dropna().pct_change().loc[pd.Timestamp(start):].corr().iloc[0, 1]
insight([
    f"The average correlation between two coins is **{pairs.mean():.2f}**, and **{(pairs > 0.5).mean() * 100:.0f}%** "
    f"of all pairs are above 0.5. For comparison, stocks (S&P 500) and gold correlated at just **{sp_gold:.2f}** "
    "over the same period, which is why they work well together in a portfolio.",
    f"Most linked pair: **{hi[0]} & {hi[1]} ({pairs.max():.2f})**. Least linked: **{lo[0]} & {lo[1]} ({pairs.min():.2f})**.",
    f"**{btc_corr.index[0]}** is the most independent of Bitcoin ({btc_corr.iloc[0]:.2f}); "
    f"**{btc_corr.index[-1]}** is closest to it ({btc_corr.iloc[-1]:.2f}). Even the most independent coin "
    "still follows Bitcoin a lot of the time.",
])

st.divider()

# ----------------------------------------------------------------------
# 2. Bitcoin's bad days
# ----------------------------------------------------------------------
st.subheader("2. When Bitcoin has a bad day, does anything hold up?")
reading("Only the days when Bitcoin fell more than 5%. Bars show how often each other coin also fell "
        "on those days, and its average move.")
bad = returns[returns["Bitcoin"] < -0.05]
others = bad.drop(columns="Bitcoin")
fell_share = (others < 0).mean().sort_values()
avg_move = others.mean()
summary = pd.DataFrame({"Also fell (% of days)": fell_share * 100, "Average move %": avg_move[fell_share.index] * 100})
fig = px.bar(summary, x=summary.index, y="Also fell (% of days)", color="Average move %",
             color_continuous_scale="Reds_r", text_auto=".0f")
fig.update_layout(**PLOT_LAYOUT, height=360, xaxis_title="")
fig.update_layout(hovermode="closest")
st.plotly_chart(fig, width="stretch")

n_fell = (others < 0).sum(axis=1)
beta = returns.drop(columns="Bitcoin").apply(lambda s: s.cov(returns["Bitcoin"]) / returns["Bitcoin"].var())
insight([
    f"Bitcoin fell more than 5% on **{len(bad)} days**. On **{(n_fell == others.shape[1]).mean() * 100:.0f}%** of "
    f"those days **every** other selected coin fell too, and on **{(n_fell >= others.shape[1] - 1).mean() * 100:.0f}%** "
    "all but one did.",
    f"On those days Bitcoin dropped **{pct(bad['Bitcoin'].mean())}** on average, while the other coins dropped "
    f"**{pct(avg_move.mean())}** on average: altcoins usually fall *harder* than Bitcoin.",
    f"Sensitivity to Bitcoin (beta): **{(beta > 1).sum()} of {len(beta)}** coins have a beta above 1, meaning a 1% "
    f"Bitcoin move comes with a bigger move in that coin. Highest: **{beta.idxmax()} ({beta.max():.2f})**.",
    "Diversification is supposed to help most in a crash. Inside crypto it does the opposite: correlations are "
    "highest exactly when prices are falling.",
])

st.divider()

# ----------------------------------------------------------------------
# 3. Rolling correlation with Bitcoin
# ----------------------------------------------------------------------
st.subheader(f"3. Correlation with Bitcoin over time ({window}-day rolling)")
reading("Each line is one coin's correlation with Bitcoin, recalculated every day over the previous "
        f"{window} days. Dips show periods when a coin briefly went its own way.")
roll = returns.drop(columns="Bitcoin").rolling(window).corr(returns["Bitcoin"]).dropna(how="all")
fig = px.line(roll, color_discrete_map=COIN_COLORS, labels={"value": "Correlation with Bitcoin", "variable": "Coin"})
fig.add_hline(y=0.5, line_dash="dash", line_color="grey")
fig.update_layout(**PLOT_LAYOUT, height=380)
st.plotly_chart(fig, width="stretch")

above = (roll > 0.5).mean().sort_values()
low_points = roll.mean(axis=1)
insight([
    f"Averaged over all coins, the rolling correlation stayed above 0.5 **{(roll > 0.5).stack().mean() * 100:.0f}%** of the time.",
    f"**{above.index[0]}** spent the most time decoupled from Bitcoin (correlation above 0.5 only "
    f"{above.iloc[0] * 100:.0f}% of the time), usually during its own hype cycles.",
    f"The lowest average correlation came around **{low_points.idxmin():%b %Y}**, when coin-specific stories "
    "briefly mattered more than the overall market. Those windows are short and do not last.",
])

st.divider()

# ----------------------------------------------------------------------
# 4. Does owning more coins reduce risk?
# ----------------------------------------------------------------------
st.subheader("4. Does owning more coins reduce risk?")
reading("Compares Bitcoin alone with an equal-weight basket of all selected coins (rebalanced daily), "
        "and with the average risk of holding a single coin.")
basket = returns.mean(axis=1)
vol = pd.Series({
    "Bitcoin only": returns["Bitcoin"].std(),
    "Equal-weight basket": basket.std(),
    "Average single coin": returns.std().mean(),
}) * np.sqrt(CRYPTO_DAYS_PER_YEAR) * 100
growth = pd.DataFrame({"Bitcoin only": (1 + returns["Bitcoin"]).cumprod(), "Equal-weight basket": (1 + basket).cumprod()})
mdd = growth.apply(lambda s: drawdown(s).min())

c1, c2 = st.columns(2)
fig = px.bar(vol, text_auto=".0f", labels={"value": "Annual volatility %", "index": ""},
             color=vol.index, color_discrete_sequence=["#f7931a", "#8c8cff", "#9aa4b1"])
fig.update_layout(margin=dict(t=30, b=10, l=10, r=10), height=340, showlegend=False, title="Volatility")
c1.plotly_chart(fig, width="stretch")
fig = px.line(growth * 100, labels={"value": "Value of $100", "variable": ""},
              color_discrete_sequence=["#f7931a", "#8c8cff"])
fig.update_layout(**PLOT_LAYOUT, height=340, title="Growth of $100")
fig.update_yaxes(type="log")
c2.plotly_chart(fig, width="stretch")

diversified = vol["Equal-weight basket"] < vol["Bitcoin only"]
insight([
    f"Spreading money equally across {len(coins)} coins gave a volatility of **{vol['Equal-weight basket']:.0f}%**, "
    f"versus **{vol['Bitcoin only']:.0f}%** for Bitcoin alone. "
    + ("The basket was calmer, but only slightly." if diversified else
       "**The basket was riskier than just holding Bitcoin.**"),
    f"Compared with picking one coin at random (average volatility {vol['Average single coin']:.0f}%), the basket "
    f"did reduce risk by **{(1 - vol['Equal-weight basket'] / vol['Average single coin']) * 100:.0f}%**, so mixing "
    "coins mainly protects you from picking the single worst one.",
    f"Worst fall: basket **{pct(mdd['Equal-weight basket'])}** vs Bitcoin **{pct(mdd['Bitcoin only'])}**.",
    "Because the coins are so correlated, buying more of them is not real diversification. Real diversification "
    "has to come from outside crypto (see below).",
])

st.divider()

# ----------------------------------------------------------------------
# 5. Bitcoin vs stocks and gold
# ----------------------------------------------------------------------
st.subheader("5. Is Bitcoin 'digital gold' or a risky tech stock?")
reading("Correlation of *weekly* returns (Friday to Friday) by calendar year. Weekly data is used because "
        "stock markets close at weekends and on holidays while crypto trades every day.")
mix = pd.concat([closes["Bitcoin"], bench["SP500"].dropna().rename("S&P 500"), bench["Gold"].dropna()], axis=1).ffill()
wk = weekly_returns(mix).dropna()
yearly_corr = wk.groupby(wk.index.year).apply(lambda g: g.corr().loc["Bitcoin", ["S&P 500", "Gold"]])
fig = px.bar(yearly_corr, barmode="group", color_discrete_map=COIN_COLORS,
             labels={"value": "Correlation with Bitcoin", "Date": "Year", "variable": ""})
fig.update_layout(**PLOT_LAYOUT, height=360)
fig.update_xaxes(dtick=1)
st.plotly_chart(fig, width="stretch")

early = yearly_corr.loc[yearly_corr.index <= 2019]
late = yearly_corr.loc[yearly_corr.index >= 2020]
insight([
    f"Bitcoin vs the S&P 500: average correlation **{early['S&P 500'].mean():.2f}** in 2018-19 but "
    f"**{late['S&P 500'].mean():.2f}** from 2020 onward (peak **{yearly_corr['S&P 500'].max():.2f}** in "
    f"{yearly_corr['S&P 500'].idxmax()}).",
    f"Bitcoin vs gold: average **{yearly_corr['Gold'].mean():.2f}**, close to no relationship in most years.",
    "Since 2020, when big institutions started trading it, Bitcoin has behaved more like a high-risk "
    "technology stock than a safe haven. It tends to fall with stocks when investors get nervous, which is the "
    "opposite of what gold is meant to do.",
])

st.divider()

# ----------------------------------------------------------------------
# 6. A small slice of Bitcoin in a stock portfolio
# ----------------------------------------------------------------------
st.subheader("6. What a small slice of Bitcoin does to a stock portfolio")
reading("Hypothetical portfolios of the S&P 500 plus 0-100% Bitcoin, rebalanced back to target every week, "
        f"from {wk.index[0]:%b %Y}. Shows what each Bitcoin weight would have done to growth and risk.")
rows = []
for w_btc in [0, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 1.0]:
    r = w_btc * wk["Bitcoin"] + (1 - w_btc) * wk["S&P 500"]
    value = (1 + r).cumprod()
    years = (wk.index[-1] - wk.index[0]).days / 365.25
    rows.append({"Bitcoin weight": f"{w_btc:.0%}", "CAGR %": (value.iloc[-1] ** (1 / years) - 1) * 100,
                 "Volatility %": r.std() * np.sqrt(52) * 100, "Worst fall %": drawdown(value).min() * 100,
                 "Return / risk": (r.mean() * 52) / (r.std() * np.sqrt(52))})
alloc = pd.DataFrame(rows).set_index("Bitcoin weight")
st.dataframe(alloc, width="stretch", column_config={
    c: st.column_config.NumberColumn(format="%.1f") for c in alloc.columns} | {
    "Return / risk": st.column_config.NumberColumn(format="%.2f")})

base, five = alloc.loc["0%"], alloc.loc["5%"]
insight([
    f"Adding just **5% Bitcoin** changed yearly growth from **{base['CAGR %']:.1f}%** to **{five['CAGR %']:.1f}%**, "
    f"while volatility moved from **{base['Volatility %']:.1f}%** to **{five['Volatility %']:.1f}%**.",
    f"Return per unit of risk peaked at **{alloc['Return / risk'].idxmax()} Bitcoin** "
    f"({alloc['Return / risk'].max():.2f}, vs {base['Return / risk']:.2f} for stocks alone). Above that, each extra "
    "slice of Bitcoin added more risk than reward.",
    f"The worst fall grew from **{base['Worst fall %']:.0f}%** (stocks only) to **{alloc.loc['20%', 'Worst fall %']:.0f}%** "
    f"at 20% Bitcoin, **{alloc.loc['50%', 'Worst fall %']:.0f}%** at 50% and **{alloc.loc['100%', 'Worst fall %']:.0f}%** "
    "all in Bitcoin. Small, regularly rebalanced positions captured much of crypto's upside without letting its "
    "crashes dominate.",
])

takeaway("Coins move as one market, especially in crashes, so holding ten coins is not diversification. "
         "The data supports a small Bitcoin position inside a wider portfolio rather than a portfolio of many coins.")
sources()
