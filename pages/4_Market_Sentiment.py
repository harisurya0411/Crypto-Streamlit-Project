"""
Market Sentiment - does the Crypto Fear & Greed Index tell us anything
useful about what Bitcoin will do next?
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from analysis import SENTIMENT_ORDER, forward_return, load_closes, load_fear_greed, pct
from auth import show_logout_button
from ui import PLOT_LAYOUT, insight, question, reading, sources, takeaway

st.set_page_config(page_title="Market Sentiment", page_icon="🧠", layout="wide")
show_logout_button()

st.title("🧠 Market Sentiment")
question("Investors are told to 'be greedy when others are fearful'. Does buying Bitcoin when the market is "
         "scared actually pay off better than buying when everyone is excited?")

SENT_COLORS = {"Extreme Fear": "#c0392b", "Fear": "#e67e22", "Neutral": "#95a5a6",
               "Greed": "#7dcea0", "Extreme Greed": "#1e8449"}

fng = load_fear_greed()
btc = load_closes()["Bitcoin"].dropna()
df = fng.join(btc.rename("BTC"), how="inner")

st.markdown("The **Crypto Fear & Greed Index** (alternative.me) scores market mood every day from 0 (extreme fear) "
            "to 100 (extreme greed), combining price volatility, momentum, trading volume, social media activity and "
            "Bitcoin's share of the crypto market.")

# ----------------------------------------------------------------------
# Sidebar filters
# ----------------------------------------------------------------------
st.sidebar.header("📊 Filters")
horizon = st.sidebar.select_slider("Holding period after buying", options=[7, 30, 90, 180, 365], value=90,
                                   format_func=lambda d: f"{d} days")
years = sorted(df.index.year.unique())
year_range = st.sidebar.slider("Years", years[0], years[-1], (years[0], years[-1]))
df = df[(df.index.year >= year_range[0]) & (df.index.year <= year_range[1])].copy()
df["Forward"] = forward_return(btc, horizon).reindex(df.index)

# ----------------------------------------------------------------------
# 1. Sentiment vs price
# ----------------------------------------------------------------------
st.subheader("1. Bitcoin's price coloured by market mood")
reading("Each dot is one day's Bitcoin price, coloured by that day's Fear & Greed reading. "
        "The bottom panel shows the raw index value.")
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.04)
for s in SENTIMENT_ORDER:
    part = df[df["Sentiment"] == s]
    fig.add_trace(go.Scattergl(x=part.index, y=part["BTC"], mode="markers", name=s,
                               marker=dict(size=3, color=SENT_COLORS[s])), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["FearGreed"], name="Index", line=dict(color="#aaa", width=1),
                         showlegend=False), row=2, col=1)
fig.add_hrect(y0=0, y1=25, fillcolor="#c0392b", opacity=0.15, line_width=0, row=2, col=1)
fig.add_hrect(y0=75, y1=100, fillcolor="#1e8449", opacity=0.15, line_width=0, row=2, col=1)
fig.update_yaxes(type="log", title_text="BTC price (USD)", row=1, col=1)
fig.update_yaxes(title_text="Fear & Greed", range=[0, 100], row=2, col=1)
fig.update_layout(**PLOT_LAYOUT, height=520)
fig.update_layout(hovermode="closest")
st.plotly_chart(fig, width="stretch")

past30 = btc.pct_change(30).reindex(df.index)
by_mood_past = past30.groupby(df["Sentiment"]).mean()
ext_fear = df[df["Sentiment"] == "Extreme Fear"]
ext_greed = df[df["Sentiment"] == "Extreme Greed"]
top_fear_years = ext_fear.index.year.value_counts().head(3).index.sort_values()
top_greed_years = ext_greed.index.year.value_counts().head(3).index.sort_values()
points = []
if {"Extreme Fear", "Extreme Greed"} <= set(by_mood_past.index):
    points.append(f"Mood follows price. In the 30 days *before* an extreme-greed reading Bitcoin had risen "
                  f"**{pct(by_mood_past['Extreme Greed'], 0, True)}** on average; before an extreme-fear reading it had "
                  f"moved **{pct(by_mood_past['Extreme Fear'], 0, True)}**. The index is partly built from recent "
                  "price momentum, so it largely describes what has already happened.")
points.append(f"Extreme fear appeared on **{len(ext_fear)} days**, mostly in **{', '.join(map(str, top_fear_years))}**: "
              "the years of deep price falls.")
points.append(f"Extreme greed appeared on **{len(ext_greed)} days**, mostly in **{', '.join(map(str, top_greed_years))}**: "
              "the bull-market run-ups.")
insight(points)

st.divider()

# ----------------------------------------------------------------------
# 2. Forward returns by sentiment
# ----------------------------------------------------------------------
st.subheader(f"2. What happened {horizon} days after buying in each mood?")
reading(f"For every day, we measure the Bitcoin return you would have made by buying that day and holding "
        f"{horizon} days, then group the days by sentiment. The median is the 'typical' outcome; the average "
        "is pulled up by a few huge winners.")
stats = (df.dropna(subset=["Forward"]).groupby("Sentiment")["Forward"]
         .agg(Average="mean", Median="median", Win_rate=lambda x: (x > 0).mean(), Days="count")
         .reindex(SENTIMENT_ORDER).dropna(subset=["Days"]))
plot = stats[["Average", "Median"]].mul(100).reset_index().melt(id_vars="Sentiment", var_name="Measure",
                                                               value_name="Return %")
fig = px.bar(plot, x="Sentiment", y="Return %", color="Measure", barmode="group", text_auto=".1f",
             color_discrete_sequence=["#f0b90b", "#8c8cff"])
fig.update_layout(**PLOT_LAYOUT, height=380)
fig.update_layout(hovermode="closest")
st.plotly_chart(fig, width="stretch")

show = stats.copy()
show["Average"] *= 100
show["Median"] *= 100
show["Win_rate"] *= 100
st.dataframe(show.rename(columns={"Win_rate": "% of times profitable", "Days": "Days in sample"}),
             width="stretch", column_config={
                 c: st.column_config.NumberColumn(format="%.1f%%") for c in ["Average", "Median", "% of times profitable"]})

best_med, worst_med = stats["Median"].idxmax(), stats["Median"].idxmin()
best_win = stats["Win_rate"].idxmax()
rho = df[["FearGreed", "Forward"]].dropna().corr(method="spearman").iloc[0, 1]
points = [
    f"Best typical (median) {horizon}-day result: buying in **{best_med}** ({pct(stats.loc[best_med, 'Median'], 1, True)}). "
    f"Worst: **{worst_med}** ({pct(stats.loc[worst_med, 'Median'], 1, True)}).",
    f"Highest chance of being in profit: **{best_win}** ({pct(stats.loc[best_win, 'Win_rate'], 0)} of the time).",
]
if "Extreme Fear" in stats.index:
    ef = stats.loc["Extreme Fear"]
    points.append(f"Buying in extreme fear: average **{pct(ef['Average'], 1, True)}** but median **{pct(ef['Median'], 1, True)}**. "
                  "The gap shows a few spectacular rebounds (like March 2020) make 'buy the fear' look better on "
                  "average than it usually feels: fear often got deeper before it ended (2018, 2022).")
points.append(f"The rank correlation between the index and the next {horizon}-day return is only **{rho:+.2f}**. "
              "Sentiment is a weak predictor on its own; it is not a buy/sell signal.")
insight(points)

st.divider()

# ----------------------------------------------------------------------
# 3. Mood by year
# ----------------------------------------------------------------------
st.subheader("3. How the market's mood changed year by year")
reading("Share of days in each sentiment band, per calendar year.")
mood = df.groupby([df.index.year, "Sentiment"]).size().unstack(fill_value=0).reindex(columns=SENTIMENT_ORDER, fill_value=0)
mood_pct = mood.div(mood.sum(axis=1), axis=0) * 100
fig = px.bar(mood_pct, color_discrete_map=SENT_COLORS, labels={"value": "% of days", "Date": "Year", "variable": ""})
fig.update_layout(**PLOT_LAYOUT, height=360, barmode="stack")
fig.update_xaxes(dtick=1)
fig.update_layout(hovermode="closest")
st.plotly_chart(fig, width="stretch")

fearful = (mood_pct["Extreme Fear"] + mood_pct["Fear"])
greedy = (mood_pct["Greed"] + mood_pct["Extreme Greed"])
yearly_btc = btc.groupby(btc.index.year).agg(["first", "last"])
yearly_btc = (yearly_btc["last"] / yearly_btc["first"] - 1).reindex(mood_pct.index)
link = pd.concat([greedy.rename("greedy"), yearly_btc.rename("ret")], axis=1).corr().iloc[0, 1]
insight([
    f"Most fearful year: **{fearful.idxmax()}** ({fearful.max():.0f}% of days in fear or extreme fear). "
    f"Most greedy: **{greedy.idxmax()}** ({greedy.max():.0f}% of days in greed).",
    f"Across years, the share of 'greedy' days and Bitcoin's return for that year have a correlation of **{link:.2f}**: "
    "the index is mostly a mirror of the year's price action.",
    "The same index level means different things in different cycles, which is another reason not to trade on it alone.",
])

takeaway("The Fear & Greed Index describes the market's mood well but predicts it poorly. 'Buy when others are "
         "fearful' only worked for patient buyers who could wait out further falls; for short holding periods, "
         "momentum (buying in greed) did just as well or better.")
sources("alternative.me Crypto Fear & Greed Index (daily since Feb 2018), Binance BTC/USDT daily closes.")
