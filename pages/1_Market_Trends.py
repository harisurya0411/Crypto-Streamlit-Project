"""
Market Trends - long-run price history, growth comparison, yearly returns
and the Bitcoin halving cycle.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analysis import (EVENTS, HALVINGS, bear_markets, calendar_year_returns, drawdown, load_closes,
                      load_volumes, max_drawdown_info, pct, usd)
from auth import show_logout_button
from ui import COIN_COLORS, PLOT_LAYOUT, insight, question, reading, sources, takeaway

st.set_page_config(page_title="Market Trends", page_icon="📈", layout="wide")
show_logout_button()

st.title("📈 Market Trends")
question("How have the major cryptocurrencies performed since 2018, and do prices move in repeatable cycles?")

closes = load_closes()
coins = list(closes.columns)

# ----------------------------------------------------------------------
# Sidebar filters
# ----------------------------------------------------------------------
st.sidebar.header("📊 Filters")
default = [c for c in ["Bitcoin", "Ethereum", "Solana", "BNB", "XRP", "Dogecoin"] if c in coins]
selected = st.sidebar.multiselect("Coins", coins, default=default)
min_d, max_d = closes.index.min().date(), closes.index.max().date()
start, end = st.sidebar.slider("Date range", min_d, max_d, (pd.Timestamp("2020-09-01").date(), max_d),
                               format="MMM YYYY")
log_scale = st.sidebar.toggle("Logarithmic price axis", value=True)

if not selected:
    st.warning("Pick at least one coin in the sidebar.")
    st.stop()

window = closes.loc[pd.Timestamp(start):pd.Timestamp(end), selected]

# ----------------------------------------------------------------------
# 1. Bitcoin's full history with events
# ----------------------------------------------------------------------
st.subheader("1. Bitcoin since 2018: big booms, deep crashes")
reading("Each vertical line marks a real-world event. On a logarithmic axis an equal vertical distance "
        "means an equal percentage move, so a fall from $60k to $30k looks the same size as $20k to $10k.")

btc = closes["Bitcoin"].dropna()
fig = go.Figure(go.Scatter(x=btc.index, y=btc, name="Bitcoin", line=dict(color=COIN_COLORS["Bitcoin"], width=1.6)))
for date, label in EVENTS:
    fig.add_vline(x=pd.Timestamp(date), line_dash="dot", line_color="rgba(255,255,255,0.35)")
    fig.add_annotation(x=pd.Timestamp(date), y=1, yref="paper", text=label, showarrow=False,
                       textangle=-90, xanchor="right", yanchor="top", font=dict(size=10, color="#bbb"))
fig.add_trace(go.Scatter(x=[btc.idxmax()], y=[btc.max()], mode="markers+text", name="All-time high",
                         text=[f"ATH {usd(btc.max())}"], textposition="middle left",
                         marker=dict(size=9, color="#ffffff", symbol="star")))
fig.update_layout(**PLOT_LAYOUT, height=430, yaxis_title="Price (USD)")
fig.update_yaxes(type="log" if log_scale else "linear")
st.plotly_chart(fig, width="stretch")

btc_dd = drawdown(btc)
ath_date = btc.idxmax()
bears = bear_markets(btc, -0.5)
info = max_drawdown_info(btc)
bear_list = "; ".join(f"{b['peak_date']:%b %Y} to {b['trough_date']:%b %Y} ({pct(b['depth'], 0)})" for b in bears)
insight([
    f"Bitcoin went from **{usd(btc.iloc[0])}** on {btc.index[0]:%d %b %Y} to **{usd(btc.iloc[-1])}** on "
    f"{btc.index[-1]:%d %b %Y}, about **{btc.iloc[-1] / btc.iloc[0]:.1f}x**, but the path was anything but smooth.",
    f"It fell more than 50% from its high in **{len(bears)} separate bear markets**: {bear_list}. "
    f"The worst was **{pct(info['max_drawdown'])}**.",
    f"The all-time high in this data is **{usd(btc.max())}** on {ath_date:%d %b %Y}. "
    f"As of the last data point it is **{pct(-btc_dd.iloc[-1])} below** that peak.",
    "Several of the sharpest single drops line up with specific shocks (the COVID panic, the Terra/LUNA and FTX "
    "collapses), when trust in the system or its big players was hit. The bear markets themselves dragged on for "
    "many months, so recovering took patience, not just nerve.",
])

st.divider()

# ----------------------------------------------------------------------
# 2. Growth of $100
# ----------------------------------------------------------------------
st.subheader("2. What $100 became in each coin")
common = window.dropna()
if common.empty:
    st.info("The selected coins have no dates in common in this range. Widen the date range.")
else:
    reading(f"Every line starts at $100 on {common.index[0]:%d %b %Y} (the first day all selected coins "
            "have data), so the lines compare growth directly regardless of each coin's price.")
    growth = common / common.iloc[0] * 100
    fig = px.line(growth, color_discrete_map=COIN_COLORS, labels={"value": "Value of $100", "variable": "Coin"})
    fig.add_hline(y=100, line_dash="dash", line_color="grey")
    fig.update_layout(**PLOT_LAYOUT, height=420)
    fig.update_yaxes(type="log" if log_scale else "linear")
    st.plotly_chart(fig, width="stretch")

    final = growth.iloc[-1].sort_values(ascending=False)
    peak = growth.max()
    losers = final[final < 100]
    points = [
        f"Best: **{final.index[0]}** turned $100 into **${final.iloc[0]:,.0f}**. "
        f"Worst: **{final.index[-1]}** ended at **${final.iloc[-1]:,.0f}**.",
        f"**{len(losers)} of {len(final)}** selected coins are worth less than they started with"
        + (f" ({', '.join(losers.index)})." if len(losers) else "."),
    ]
    gave_back = ((peak - final) / peak).sort_values(ascending=False)
    points.append(f"**{gave_back.index[0]}** gave back the most: it peaked at ${peak[gave_back.index[0]]:,.0f} "
                  f"but now sits at ${final[gave_back.index[0]]:,.0f} ({pct(gave_back.iloc[0])} below its peak "
                  "in this window). Paper gains are not real gains until you sell.")
    if "Bitcoin" in final.index:
        beat = [c for c in final.index if c != "Bitcoin" and final[c] > final["Bitcoin"]]
        points.append(f"Only **{len(beat)}** of the other coins beat simply holding Bitcoin over this period"
                      + (f" ({', '.join(beat)})." if beat else "."))
    insight(points)

st.divider()

# ----------------------------------------------------------------------
# 3. Calendar-year returns
# ----------------------------------------------------------------------
st.subheader("3. Year-by-year returns")
reading("Green cells are years the coin rose, red cells are years it fell. A blank cell means the coin "
        "was not trading on Binance yet (or only listed part-way through that year). The current year is year-to-date.")
yearly = calendar_year_returns(closes[selected]).dropna(how="all")
fig = px.imshow(yearly.T * 100, text_auto=".0f", aspect="auto", color_continuous_scale="RdYlGn",
                color_continuous_midpoint=0, labels=dict(color="Return %", x="Year", y=""))
fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=60 + 38 * len(selected))
fig.update_xaxes(dtick=1)
st.plotly_chart(fig, width="stretch")

full_years = yearly.loc[yearly.index < closes.index.max().year]
all_up, all_down = [], []
for year, row in full_years.iterrows():
    row = row.dropna()
    if len(row) >= 2 and (row > 0).all():
        all_up.append(str(year))
    elif len(row) >= 2 and (row < 0).all():
        all_down.append(str(year))
cells = yearly.stack()
best_cell, worst_cell = cells.idxmax(), cells.idxmin()
points = [
    f"Years where **every** selected coin rose: **{', '.join(all_up) or 'none'}**. "
    f"Years where every one fell: **{', '.join(all_down) or 'none'}**. "
    f"That is {len(all_up) + len(all_down)} of {len(full_years)} full years in which all coins moved the same "
    "way: the whole market has good and bad years together.",
    f"Best single year: **{best_cell[1]} in {best_cell[0]} ({pct(cells.max(), 0, True)})**. "
    f"Worst: **{worst_cell[1]} in {worst_cell[0]} ({pct(cells.min(), 0, True)})**.",
]
if "Bitcoin" in yearly:
    b = yearly["Bitcoin"].dropna()
    points.append(f"Bitcoin had **{(b > 0).sum()} up-years and {(b < 0).sum()} down-years** "
                  f"(including {b.index[-1]} so far). Big up-years tend to be followed by down-years "
                  "(2021 then 2022, 2024 then 2025), so buying after a great year has often meant buying near a top.")
insight(points)

st.divider()

# ----------------------------------------------------------------------
# 4. Halving cycle
# ----------------------------------------------------------------------
st.subheader("4. The Bitcoin halving cycle")
reading("Every ~4 years the number of new bitcoins created per block is cut in half. Each line shows Bitcoin's "
        "price relative to its price on halving day (= 100), plotted against days since that halving.")
fig = go.Figure()
cycle_rows = []
for label, h_date in HALVINGS.items():
    seg = btc.loc[h_date:h_date + pd.Timedelta(days=1000)]
    if seg.empty:
        continue
    idx = seg / seg.iloc[0] * 100
    days = (seg.index - h_date).days
    fig.add_trace(go.Scatter(x=days, y=idx, name=label, mode="lines"))
    cycle_rows.append({"Cycle": label, "Peak day": int((idx.idxmax() - h_date).days),
                       "Peak date": idx.idxmax(), "Peak multiple": idx.max() / 100,
                       "Days so far": int(days[-1])})
fig.add_hline(y=100, line_dash="dash", line_color="grey")
fig.update_layout(**PLOT_LAYOUT, height=400, xaxis_title="Days since halving", yaxis_title="Price index (halving day = 100)")
fig.update_layout(hovermode="x")
st.plotly_chart(fig, width="stretch")

cyc = pd.DataFrame(cycle_rows)
points = []
for _, r in cyc.iterrows():
    points.append(f"**{r['Cycle']}**: price peaked **{r['Peak day']} days** later ({r['Peak date']:%b %Y}) at "
                  f"**{r['Peak multiple']:.1f}x** the halving-day price.")
if len(cyc) == 2:
    diff = abs(cyc["Peak day"].iloc[0] - cyc["Peak day"].iloc[1])
    points.append(f"Both peaks came roughly 1.5 years after the halving, only **{diff} days apart** in timing. "
                  f"The second cycle's peak multiple was much smaller ({cyc['Peak multiple'].iloc[1]:.1f}x vs "
                  f"{cyc['Peak multiple'].iloc[0]:.1f}x): each cycle has produced smaller gains as Bitcoin got bigger.")
points.append("Two cycles are only two data points. The pattern is real in this data, but it is not a law: "
              "ETFs and institutional buyers may change how future cycles behave.")
insight(points)

st.divider()

# ----------------------------------------------------------------------
# 5. Trading activity
# ----------------------------------------------------------------------
st.subheader("5. Trading activity on Binance")
reading("Total US-dollar value traded each month across the selected coins on Binance spot markets.")
vol = load_volumes().loc[pd.Timestamp(start):pd.Timestamp(end), selected].resample("ME").sum()
fig = px.bar(vol / 1e9, color_discrete_map=COIN_COLORS, labels={"value": "Traded value (USD bn)", "variable": "Coin"})
fig.update_layout(**PLOT_LAYOUT, height=380, barmode="stack")
st.plotly_chart(fig, width="stretch")

monthly_total = vol.sum(axis=1)
top_month = monthly_total.idxmax()
share = vol.sum() / vol.sum().sum()
points = [
    f"The busiest month in this range was **{top_month:%B %Y}** with **{usd(monthly_total.max())}** traded.",
    f"**{share.idxmax()}** accounts for **{pct(share.max())}** of all trading in the selected coins.",
    "Volume spikes during both manias and crashes: people trade most when prices move fastest, which is "
    "also when emotional decisions are most likely.",
]
if "Bitcoin" in selected and pd.Timestamp(start) <= pd.Timestamp("2023-03-22") and pd.Timestamp(end) >= pd.Timestamp("2022-07-08"):
    points.append("Data caveat: Binance removed trading fees on Bitcoin pairs from July 2022 to March 2023, which "
                  "inflated Bitcoin's volume in that window without reflecting extra real demand.")
insight(points)

takeaway("Crypto has delivered large long-run gains, but in short bursts separated by 50-80% crashes, and "
         "half of these 10 coins never got back above their 2021 peak. Surviving the crashes mattered more than "
         "finding the next hot coin.")
sources()
