"""
Conclusions - the answer to each research question, recomputed from the
data every time the page loads, plus what it means for an investor.
"""

import numpy as np
import pandas as pd
import streamlit as st

from analysis import (bear_markets, forward_return, load_benchmarks, load_closes, load_fear_greed, pct,
                      risk_return_table, weekly_returns, MARKET_DAYS_PER_YEAR)
from auth import show_logout_button
from ui import sources

st.set_page_config(page_title="Conclusions", page_icon="✅", layout="wide")
show_logout_button()

st.title("✅ Conclusions")
st.markdown("Each answer below is recalculated from the dataset when this page loads, so the numbers always "
            "match the charts on the analysis pages.")

closes = load_closes()
bench = load_benchmarks()
btc = closes["Bitcoin"].dropna()
end = closes.index.max()

# --- Q1: trends ---------------------------------------------------------
bears = bear_markets(btc, -0.5)
pre = closes.loc[:"2021-12-31"].max()
post = closes.loc["2022-01-01":].max()
not_recovered = [c for c in closes if post[c] < pre[c]]

# --- Q2: risk ------------------------------------------------------------
crypto_stats = risk_return_table(closes)
bench_stats = risk_return_table(bench[["SP500", "Gold"]], MARKET_DAYS_PER_YEAR)
sp_sharpe = bench_stats.loc["SP500", "Sharpe"]
beat_sp = crypto_stats[crypto_stats["Sharpe"] > sp_sharpe].index.tolist()

# --- Q3: diversification ------------------------------------------------
rets = closes.loc["2020-09-01":].pct_change(fill_method=None).dropna()
corr = rets.corr().values[np.triu_indices(rets.shape[1], 1)]
basket_vol = rets.mean(axis=1).std() * np.sqrt(365)
btc_vol = rets["Bitcoin"].std() * np.sqrt(365)
wk = weekly_returns(pd.concat([btc, bench["SP500"].dropna()], axis=1).ffill()).dropna()
sp_corr_late = wk.loc["2020-01-01":].corr().iloc[0, 1]
sp_corr_early = wk.loc[:"2019-12-31"].corr().iloc[0, 1]

# --- Q4: sentiment -------------------------------------------------------
fng = load_fear_greed().join(forward_return(btc, 90).rename("f90"), how="inner").dropna()
med = fng.groupby("Sentiment")["f90"].median()
win = fng.groupby("Sentiment")["f90"].apply(lambda x: (x > 0).mean())

# --- Q5: SIP vs lump sum --------------------------------------------------
m = btc.resample("MS").first()
lump_wins, sip_worst, lump_worst = [], [], []
for i in range(len(m) - 24):
    seg, end_px = m.iloc[i:i + 24], m.iloc[i + 24]
    sip, lump = (1 / seg).sum() * end_px / 24, end_px / seg.iloc[0]
    lump_wins.append(lump > sip)
    sip_worst.append(sip)
    lump_worst.append(lump)
usdinr = bench["USDINR"].dropna()

st.subheader("Answers to the research questions")

with st.container(border=True):
    st.markdown("#### 1. How have major cryptocurrencies performed, and are there cycles?")
    st.markdown(f"""
- Bitcoin grew **{btc.iloc[-1] / btc.iloc[0]:.1f}x** from {btc.index[0]:%b %Y} to {end:%b %Y}, but went through
  **{len(bears)} bear markets of more than 50%**, the worst **{pct(min(b['depth'] for b in bears), 0)}**.
- **{len(not_recovered)} of 10** coins never got back above their 2021 peak ({', '.join(not_recovered)}).
- Bitcoin's price peaked about 1.5 years after each of the last two halvings, but the second peak was a much
  smaller multiple. The cycle is visible, with only two examples to go on.
""")
    st.page_link("pages/1_Market_Trends.py", label="See the evidence: Market Trends", icon="📈")

with st.container(border=True):
    st.markdown("#### 2. How risky is crypto, and was the risk rewarded?")
    st.markdown(f"""
- Bitcoin's volatility was **{pct(crypto_stats.loc['Bitcoin', 'Volatility'], 0)}** a year versus
  **{pct(bench_stats.loc['SP500', 'Volatility'], 0)}** for the S&P 500, about
  **{crypto_stats.loc['Bitcoin', 'Volatility'] / bench_stats.loc['SP500', 'Volatility']:.1f}x** as much. Most altcoins
  were riskier still (median **{pct(crypto_stats['Volatility'].median(), 0)}**).
- Over the full period only **{len(beat_sp)} of 10** coins ({', '.join(beat_sp) or 'none'}) gave a better
  return per unit of risk than the S&P 500 (Sharpe {sp_sharpe:.2f}). **Bitcoin did not**
  ({crypto_stats.loc['Bitcoin', 'Sharpe']:.2f}) in this window, which starts near the 2017 peak.
""" if "Bitcoin" not in beat_sp else f"""
- Bitcoin's volatility was **{pct(crypto_stats.loc['Bitcoin', 'Volatility'], 0)}** a year versus
  **{pct(bench_stats.loc['SP500', 'Volatility'], 0)}** for the S&P 500.
- Over the full period **{len(beat_sp)} of 10** coins ({', '.join(beat_sp)}) beat the S&P 500's return per unit of risk.
""")
    st.page_link("pages/2_Risk_and_Return.py", label="See the evidence: Risk and Return", icon="⚖️")

with st.container(border=True):
    st.markdown("#### 3. Does holding several coins spread the risk?")
    st.markdown(f"""
- The average correlation between two coins is **{corr.mean():.2f}**, and on Bitcoin's worst days nearly every
  other coin fell too.
- An equal mix of all 10 coins had **{pct(basket_vol, 0)}** volatility, versus **{pct(btc_vol, 0)}** for Bitcoin alone:
  {'more coins meant *more* risk, not less' if basket_vol > btc_vol else 'only slightly less risk'}.
- Bitcoin's weekly correlation with the S&P 500 rose from **{sp_corr_early:.2f}** (2018-19) to **{sp_corr_late:.2f}**
  (2020 onward). It has behaved like a risky tech asset, not like gold.
""")
    st.page_link("pages/3_Correlation.py", label="See the evidence: Correlation", icon="🔗")

with st.container(border=True):
    st.markdown("#### 4. Does buying in 'fear' work?")
    st.markdown(f"""
- Typical (median) 90-day Bitcoin return after buying in **Extreme Fear**: **{pct(med.get('Extreme Fear'), 1, True)}**
  (profitable {pct(win.get('Extreme Fear'), 0)} of the time). After **Extreme Greed**:
  **{pct(med.get('Extreme Greed'), 1, True)}** (profitable {pct(win.get('Extreme Greed'), 0)} of the time).
- The index describes recent price moves more than it predicts the next ones. It is useful for keeping emotions in
  check, not as a trading signal.
""")
    st.page_link("pages/4_Market_Sentiment.py", label="See the evidence: Market Sentiment", icon="🧠")

with st.container(border=True):
    st.markdown("#### 5. SIP or lump sum, and what about tax?")
    st.markdown(f"""
- Across **{len(lump_wins)}** possible 2-year Bitcoin investment windows, a lump sum beat a monthly SIP
  **{np.mean(lump_wins) * 100:.0f}%** of the time, but the SIP's worst outcome ({min(sip_worst):.2f}x) was
  {'better' if min(sip_worst) > min(lump_worst) else 'no better'} than the lump sum's ({min(lump_worst):.2f}x).
- The rupee weakened from **₹{usdinr.iloc[0]:.0f}** to **₹{usdinr.iloc[-1]:.0f}** per dollar since {usdinr.index[0]:%Y},
  which by itself raised the rupee value of any dollar-priced asset by ~{(usdinr.iloc[-1] / usdinr.iloc[0] - 1) * 100:.0f}%.
  India's 31.2% tax on gains (no loss offset) then takes almost a third of any profit.
""")
    st.page_link("pages/5_Investment_Simulator.py", label="Try it yourself: Investment Simulator", icon="🧮")

st.subheader("What this means for a retail investor in India")
st.markdown("""
1. **Size it small.** Crypto has repeatedly lost more than half its value. Only invest an amount you could watch
   fall 70-80% without selling. The Correlation page shows that a 5% slice already changes a portfolio's results.
2. **Bitcoin first, altcoins with caution.** Most altcoins were riskier than Bitcoin, half never regained their 2021
   highs, and they fall harder than Bitcoin in crashes. Owning many coins is not diversification.
3. **Use a SIP for discipline, not for higher returns.** It will not beat a lump sum on average, but it prevents
   the worst timing mistakes, such as putting everything in at a peak.
4. **Ignore hype and fear headlines.** Sentiment mirrors recent prices. Buying in greed and selling in fear is the
   pattern the data punishes over longer horizons.
5. **Plan for tax and custody.** 31.2% of every gain goes to tax with no loss offset, and exchange failures (FTX,
   WazirX) show why long-term holdings belong in your own wallet.
""")

st.subheader("Limitations and further work")
st.markdown("""
- The sample has **survivorship bias** (coins that are still large today) and covers only two halving cycles.
- Prices come from one exchange (Binance); a multi-exchange average would be more robust.
- Further work: add on-chain data (active addresses, exchange flows), test a rules-based rebalancing strategy, and
  compare Indian exchange prices with global prices to measure the local premium caused by TDS.
""")
sources()
