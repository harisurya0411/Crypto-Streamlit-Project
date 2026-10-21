"""
Investment Simulator - monthly SIP (dollar-cost averaging) vs investing a
lump sum, replayed on real historical prices, in rupees or dollars, with
India's crypto tax applied.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analysis import drawdown, load_benchmarks, load_closes, pct
from auth import show_logout_button
from ui import COIN_COLORS, PLOT_LAYOUT, insight, question, reading, sources, takeaway

st.set_page_config(page_title="Investment Simulator", page_icon="🧮", layout="wide")
show_logout_button()

st.title("🧮 Investment Simulator")
question("For an ordinary investor, is it better to invest a fixed amount every month (a SIP) or everything at "
         "once, and what is actually left after India's 30% crypto tax?")

INDIA_TAX = 0.30 * 1.04   # Section 115BBH: flat 30% on gains + 4% health & education cess

closes = load_closes()
usdinr = load_benchmarks()["USDINR"].dropna().reindex(closes.index).ffill().bfill()

# ----------------------------------------------------------------------
# Inputs
# ----------------------------------------------------------------------
st.sidebar.header("📊 Simulation settings")
coin = st.sidebar.selectbox("Coin", list(closes.columns), index=list(closes.columns).index("Bitcoin"))
currency = st.sidebar.radio("Currency", ["INR (₹)", "USD ($)"], horizontal=True)
inr = currency.startswith("INR")
sym = "₹" if inr else "$"
monthly = st.sidebar.number_input(f"Monthly amount ({sym})", min_value=100, value=5000 if inr else 100,
                                  step=500 if inr else 10)
first_day = closes[coin].first_valid_index()
start = st.sidebar.date_input("Start investing", value=max(pd.Timestamp("2021-01-01"), first_day),
                              min_value=first_day, max_value=closes.index.max() - pd.Timedelta(days=60))
end = st.sidebar.date_input("Value on", value=closes.index.max(), min_value=pd.Timestamp(start) + pd.Timedelta(days=60),
                            max_value=closes.index.max())
apply_tax = st.sidebar.toggle("Apply Indian crypto tax (31.2% on gains)", value=inr)

start, end = pd.Timestamp(start), pd.Timestamp(end)


def simulate(prices: pd.Series, fx: pd.Series, start, end, amount, in_inr):
    """Replay a monthly SIP and a same-size lump sum. Returns daily values and buy log."""
    p = prices.loc[start:end].dropna()
    rate = fx.loc[p.index] if in_inr else pd.Series(1.0, index=p.index)
    buy_days = p.groupby([p.index.year, p.index.month]).head(1).index   # first trading day each month
    units_bought = pd.Series(0.0, index=p.index)
    units_bought.loc[buy_days] = (amount / rate.loc[buy_days]) / p.loc[buy_days]
    invested = pd.Series(0.0, index=p.index)
    invested.loc[buy_days] = amount
    sip_value = units_bought.cumsum() * p * rate
    total = amount * len(buy_days)
    lump_units = (total / rate.iloc[0]) / p.iloc[0]
    lump_value = lump_units * p * rate
    return pd.DataFrame({"Invested": invested.cumsum(), "SIP value": sip_value, "Lump sum value": lump_value}), len(buy_days)


sim, n_months = simulate(closes[coin], usdinr, start, end, monthly, inr)
total_in = sim["Invested"].iloc[-1]
sip_final, lump_final = sim["SIP value"].iloc[-1], sim["Lump sum value"].iloc[-1]


def after_tax(value, invested):
    gain = value - invested
    return value - INDIA_TAX * gain if (apply_tax and gain > 0) else value


sip_net, lump_net = after_tax(sip_final, total_in), after_tax(lump_final, total_in)

# ----------------------------------------------------------------------
# 1. Result of the chosen plan
# ----------------------------------------------------------------------
st.subheader(f"1. {sym}{monthly:,.0f} a month into {coin}, {start:%b %Y} to {end:%b %Y}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total invested", f"{sym}{total_in:,.0f}", f"{n_months} monthly buys", delta_color="off")
c2.metric("SIP value" + (" after tax" if apply_tax else ""), f"{sym}{sip_net:,.0f}", pct(sip_net / total_in - 1, 1, True))
c3.metric("Lump-sum value" + (" after tax" if apply_tax else ""), f"{sym}{lump_net:,.0f}", pct(lump_net / total_in - 1, 1, True))
worst = (sim["SIP value"] / sim["Invested"] - 1).loc[sim["Invested"] > 0]
c4.metric("SIP's worst point", pct(worst.min(), 0), f"on {worst.idxmin():%d %b %Y}", delta_color="off")

reading("Grey = money put in so far. Gold = what the monthly SIP was worth on each day. Purple = what you'd have "
        "if the same total had been invested on day one.")
fig = go.Figure()
fig.add_trace(go.Scatter(x=sim.index, y=sim["Invested"], name="Invested", line=dict(color="#888", dash="dot")))
fig.add_trace(go.Scatter(x=sim.index, y=sim["SIP value"], name="Monthly SIP", line=dict(color="#f0b90b")))
fig.add_trace(go.Scatter(x=sim.index, y=sim["Lump sum value"], name="Lump sum", line=dict(color="#8c8cff")))
fig.update_layout(**PLOT_LAYOUT, height=420, yaxis_title=f"Value ({sym})")
st.plotly_chart(fig, width="stretch")

in_loss = (sim["SIP value"] < sim["Invested"]).loc[sim["Invested"] > 0].mean()
winner = "SIP" if sip_final > lump_final else "lump sum"
points = [
    f"The SIP turned **{sym}{total_in:,.0f}** into **{sym}{sip_final:,.0f}** before tax "
    f"({pct(sip_final / total_in - 1, 1, True)}). The **{winner}** came out ahead in this window "
    f"(lump sum: {sym}{lump_final:,.0f}).",
    f"The SIP was showing a loss on **{in_loss * 100:.0f}%** of days, and at its worst was "
    f"**{pct(worst.min(), 0)}** below the money put in. Sitting through that without selling is the hard part.",
]
if apply_tax:
    tax_paid = sip_final - sip_net
    points.append(f"India taxes crypto gains at a flat 30% + 4% cess, with no deduction for losses on other coins. "
                  f"Here that takes **{sym}{tax_paid:,.0f}**, cutting the SIP's profit from "
                  f"{pct(sip_final / total_in - 1, 1, True)} to **{pct(sip_net / total_in - 1, 1, True)}**. "
                  "(The 1% TDS deducted on each sale is credited against this tax, not charged extra.)")
if inr:
    fx0, fx1 = usdinr.loc[start:].iloc[0], usdinr.loc[:end].iloc[-1]
    points.append(f"The rupee moved from **₹{fx0:.2f}** to **₹{fx1:.2f}** per dollar over this period. Because crypto is "
                  f"priced in dollars, that alone {'added' if fx1 > fx0 else 'removed'} about "
                  f"**{pct(abs(fx1 / fx0 - 1), 0)}** to a rupee investor's return on any coin bought at the start.")
insight(points)

st.divider()

# ----------------------------------------------------------------------
# 2. Same SIP, every coin
# ----------------------------------------------------------------------
st.subheader("2. The same SIP in every coin")
reading(f"The same {sym}{monthly:,.0f}/month plan, same dates, run on each coin that was trading at the start date.")
rows = []
for c in closes.columns:
    if closes[c].first_valid_index() > start:
        continue
    s, _ = simulate(closes[c], usdinr, start, end, monthly, inr)
    rows.append({"Coin": c, "Final value": s["SIP value"].iloc[-1], "Invested": s["Invested"].iloc[-1],
                 "Worst point": (s["SIP value"] / s["Invested"] - 1).loc[s["Invested"] > 0].min()})
every = pd.DataFrame(rows).set_index("Coin")
every["Return"] = every["Final value"] / every["Invested"] - 1
every = every.sort_values("Return", ascending=False)
fig = px.bar(every, x=every.index, y=every["Return"] * 100, color=every.index, color_discrete_map=COIN_COLORS,
             text=(every["Return"] * 100).round(0).astype(int).astype(str) + "%",
             labels={"y": "SIP return %", "x": ""})
fig.add_hline(y=0, line_color="grey")
fig.update_layout(**PLOT_LAYOUT, height=360, showlegend=False)
fig.update_layout(hovermode="closest")
st.plotly_chart(fig, width="stretch")

losers = every[every["Return"] < 0]
insight([
    f"Best: **{every.index[0]}** ({pct(every['Return'].iloc[0], 0, True)}). Worst: **{every.index[-1]}** "
    f"({pct(every['Return'].iloc[-1], 0, True)}).",
    f"**{len(losers)} of {len(every)}** coins lost money even with steady monthly buying"
    + (f" ({', '.join(losers.index)})." if len(losers) else "."),
    "A SIP smooths out *when* you buy, but it cannot rescue a coin that keeps falling. What you buy still matters "
    "more than how you buy it.",
])

st.divider()

# ----------------------------------------------------------------------
# 3. SIP vs lump sum across every possible start month
# ----------------------------------------------------------------------
st.subheader("3. Was the result luck? SIP vs lump sum for every start month")
months = st.slider("Investment period (months)", 6, 48, 24, step=6)
reading(f"For every possible start month, we compare investing over {months} months (SIP) with investing "
        f"the same total on day one (lump sum), both valued at the end of the {months} months. Above 1.0x = profit.")
monthly_px = closes[coin].dropna().resample("MS").first()
rows = []
for i in range(len(monthly_px) - months):
    seg, end_px = monthly_px.iloc[i:i + months], monthly_px.iloc[i + months]
    rows.append({"Start": monthly_px.index[i],
                 "SIP": (1 / seg).sum() * end_px / months,
                 "Lump sum": end_px / seg.iloc[0]})
roll = pd.DataFrame(rows).set_index("Start")

if roll.empty:
    st.info("Not enough history for this period length.")
else:
    fig = px.line(roll, labels={"value": "Money multiple at the end", "variable": ""},
                  color_discrete_sequence=["#f0b90b", "#8c8cff"])
    fig.add_hline(y=1, line_dash="dash", line_color="grey")
    fig.update_yaxes(type="log")
    fig.update_layout(**PLOT_LAYOUT, height=380)
    st.plotly_chart(fig, width="stretch")

    lump_wins = (roll["Lump sum"] > roll["SIP"]).mean()
    insight([
        f"Out of **{len(roll)}** possible start months, the lump sum finished ahead **{lump_wins * 100:.0f}%** of the "
        f"time. Typical outcome: lump sum **{roll['Lump sum'].median():.2f}x**, SIP **{roll['SIP'].median():.2f}x**.",
        f"Chance of ending at a loss: lump sum **{(roll['Lump sum'] < 1).mean() * 100:.0f}%**, SIP "
        f"**{(roll['SIP'] < 1).mean() * 100:.0f}%**. Worst case: lump sum **{roll['Lump sum'].min():.2f}x**, "
        f"SIP **{roll['SIP'].min():.2f}x**.",
        "Because crypto has risen over the long run, money invested earlier usually had more time to grow, so the "
        "lump sum tends to win. The SIP's real benefit is behavioural: it avoids putting everything in at a peak "
        "and makes the worst outcomes a little less painful.",
    ])

takeaway("A monthly SIP doesn't beat a lump sum on average, but it protects against terrible timing. For an "
         "Indian investor, rupee depreciation has quietly boosted returns while the 31.2% tax takes a large share of "
         "any gain, and no investing method rescues a coin that keeps falling.")
sources("Binance daily closes, Yahoo Finance USD/INR. Tax rule: Section 115BBH of the Income Tax Act (30% + 4% cess, "
        "no loss set-off) and Section 194S (1% TDS).")
