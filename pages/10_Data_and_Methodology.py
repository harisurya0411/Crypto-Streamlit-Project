"""
Data and Methodology - where every number comes from, how it was cleaned,
the formulas used, known limitations, and a raw-data explorer with export.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from analysis import load_benchmarks, load_crypto, load_fear_greed, load_snapshot
from auth import show_logout_button
from ui import insight, question

st.set_page_config(page_title="Data and Methodology", page_icon="📄", layout="wide")
show_logout_button()

st.title("📄 Data and Methodology")
question("Where does the data come from, how reliable is it, and how were the numbers in this app calculated?")

crypto = load_crypto()
fng = load_fear_greed()
bench = load_benchmarks()
snap = load_snapshot()

# ----------------------------------------------------------------------
# Sources
# ----------------------------------------------------------------------
st.subheader("1. Datasets")
sources = pd.DataFrame([
    {"File": "crypto_daily.csv", "Source": "Binance public API (/api/v3/klines)",
     "Contents": "Daily open, high, low, close, volume, traded value and trade count for 10 coins (USDT pairs)",
     "From": crypto["Date"].min().date(), "To": crypto["Date"].max().date(), "Rows": len(crypto)},
    {"File": "fear_greed.csv", "Source": "alternative.me Fear & Greed API",
     "Contents": "Daily sentiment score 0-100 and its label",
     "From": fng.index.min().date(), "To": fng.index.max().date(), "Rows": len(fng)},
    {"File": "benchmarks.csv", "Source": "Yahoo Finance chart API",
     "Contents": "Daily closes: S&P 500 index (^GSPC), gold futures (GC=F), USD/INR exchange rate (INR=X)",
     "From": bench.index.min().date(), "To": bench.index.max().date(), "Rows": len(bench)},
    {"File": "market_snapshot.csv", "Source": "CoinGecko /coins/markets",
     "Contents": "Market cap, circulating/max supply and all-time high per coin",
     "From": snap["SnapshotDate"].iloc[0], "To": snap["SnapshotDate"].iloc[0], "Rows": len(snap)},
])
sources[["From", "To"]] = sources[["From", "To"]].astype(str)
st.dataframe(sources, width="stretch", hide_index=True)
st.caption("All four are free and need no API key. `scripts/build_dataset.py` downloads them again, so every chart "
           "in this app can be reproduced or updated with one command.")

# ----------------------------------------------------------------------
# Coverage + quality
# ----------------------------------------------------------------------
st.subheader("2. Coverage and data quality")
cov = crypto.groupby("Asset").agg(Start=("Date", "min"), End=("Date", "max"), Days=("Date", "count")).reset_index()
cov["Expected days"] = (cov["End"] - cov["Start"]).dt.days + 1
cov["Missing days"] = cov["Expected days"] - cov["Days"]
fig = px.timeline(cov.sort_values("Start", ascending=False), x_start="Start", x_end="End", y="Asset",
                  color_discrete_sequence=["#f0b90b"])
fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=330)
st.plotly_chart(fig, width="stretch")

late = cov[cov["Start"] > crypto["Date"].min()].sort_values("Start")
bench_rows = bench.notna().sum()
insight([
    f"**{len(crypto):,} daily price rows** across {crypto['Asset'].nunique()} coins, with only "
    f"**{int(cov['Missing days'].sum())} missing day(s)** in total "
    f"({', '.join(cov.loc[cov['Missing days'] > 0, 'Asset']) or 'none'}).",
    "Coins listed later have shorter histories: " + ", ".join(f"{r.Asset} from {r.Start:%b %Y}" for r in late.itertuples())
    + ". Comparisons across all 10 coins therefore start from September 2020, just after the last of them was listed.",
    f"The S&P 500 has **{bench_rows['SP500']:,}** rows versus **{cov['Days'].max():,}** for Bitcoin, because stock "
    "markets close at weekends and on holidays. Crypto-vs-stock comparisons use weekly returns to line the two up.",
], "Data quality checks")

st.subheader("3. Cleaning steps")
st.markdown("""
1. **Only completed days.** Today's still-open daily candle is dropped so the last day's close is final.
2. **Polygon's token migration.** Polygon replaced MATIC with POL in September 2024 at a 1:1 swap. Binance's
   MATICUSDT series (to 12 Sep 2024) and POLUSDT series (from 13 Sep 2024) are joined into one continuous
   "Polygon" series. The two days of the swap have no trading and are left as gaps, not invented.
3. **Live prices fixed.** The original app asked CoinGecko for `matic-network`, which now returns a stale price
   with zero market cap; it now uses `polygon-ecosystem-token`.
4. **USDT treated as USD.** Binance quotes prices in Tether (USDT), a dollar-pegged stablecoin that has stayed
   very close to \\$1 for almost all of this period, apart from brief wobbles during market stress.
5. **Different calendars.** Crypto trades 365 days a year and stocks about 252. Volatility is annualised with the
   right number for each, and cross-asset correlations use Friday-to-Friday weekly returns.
6. **Part-year returns hidden.** A coin's listing year is excluded from calendar-year comparisons when it
   started trading after the first week of January.
7. **Demo portfolio from real prices.** The demo account's buy prices are looked up from the real close on each
   buy date rather than typed in.
""")

st.subheader("4. Formulas")
st.markdown(r"""
| Measure | Formula | Meaning |
|---|---|---|
| Daily return | $r_t = P_t / P_{t-1} - 1$ | % change from one close to the next |
| CAGR | $(P_{end}/P_{start})^{1/years} - 1$ | Smoothed yearly growth rate |
| Volatility | $\text{std}(r_t)\times\sqrt{365}$ ($\sqrt{252}$ for stocks) | Typical size of a year's swings |
| Sharpe ratio | $\dfrac{\text{mean}(r_t)\times 365}{\text{volatility}}$ (risk-free rate = 0) | Return per unit of risk |
| Drawdown | $P_t / \max_{s \le t} P_s - 1$ | How far below the previous peak |
| Correlation | Pearson correlation of returns | Whether two assets move together (-1 to 1) |
| Beta vs BTC | $\text{cov}(r_{coin}, r_{BTC}) / \text{var}(r_{BTC})$ | Move in a coin for a 1% Bitcoin move |
| Forward return | $P_{t+h} / P_t - 1$ | Return from buying on day $t$ and holding $h$ days |
| 1-in-20 bad day (VaR 95%) | 5th percentile of daily portfolio returns | Loss exceeded on about 1 day in 20 |
""")

st.subheader("5. Limitations")
st.markdown("""
- **Survivorship bias.** These 10 coins were chosen because they are still large today. Thousands of coins from
  2018 have since collapsed or vanished, so "crypto" as a whole did worse than this sample suggests.
- **One exchange.** Prices are Binance's. Other exchanges differ slightly, and Binance's own volume was inflated
  by a zero-fee promotion on Bitcoin pairs (July 2022 to March 2023).
- **Short history.** Eight years and two halving cycles is a small sample for statements about cycles.
- **Overlapping windows.** Forward-return and rolling-window statistics reuse overlapping periods, so they are
  less independent than their day counts suggest.
- **Simplified tax.** The simulator applies India's flat 30% + 4% cess to the final gain only. Real tax depends
  on when each sale happens, and TDS affects cash flow.
- **Past performance does not predict future returns.** This app describes what happened; it is not investment advice.
""")

st.divider()

# ----------------------------------------------------------------------
# Raw data explorer
# ----------------------------------------------------------------------
st.subheader("6. Explore and download the raw data")
st.sidebar.header("📊 Raw data filters")
dataset = st.sidebar.selectbox("Dataset", ["Crypto daily prices", "Fear & Greed", "Benchmarks", "Market snapshot"])

if dataset == "Crypto daily prices":
    coins = st.sidebar.multiselect("Coins", sorted(crypto["Asset"].unique()), default=["Bitcoin"])
    rng = st.sidebar.date_input("Date range", (crypto["Date"].max() - pd.Timedelta(days=90), crypto["Date"].max()))
    if len(rng) != 2:
        st.info("Pick a start and an end date.")
        st.stop()
    d0, d1 = rng
    view = crypto[crypto["Asset"].isin(coins) & crypto["Date"].between(pd.Timestamp(d0), pd.Timestamp(d1))]
elif dataset == "Fear & Greed":
    labels = st.sidebar.multiselect("Sentiment", sorted(fng["Sentiment"].unique()), default=sorted(fng["Sentiment"].unique()))
    view = fng[fng["Sentiment"].isin(labels)].reset_index()
elif dataset == "Benchmarks":
    view = bench.reset_index()
else:
    view = snap

sort_by = st.sidebar.selectbox("Sort by", list(view.columns))
descending = st.sidebar.toggle("Descending", value=True)
view = view.sort_values(sort_by, ascending=not descending)

st.caption(f"Showing {len(view):,} rows")
st.dataframe(view, width="stretch", hide_index=True)
with st.expander("Summary statistics for this selection"):
    st.dataframe(view.select_dtypes("number").describe(), width="stretch")
st.download_button("⬇️ Download this view as CSV", data=view.to_csv(index=False).encode("utf-8"),
                   file_name=f"{dataset.lower().replace(' ', '_').replace('&', 'and')}.csv", mime="text/csv")
