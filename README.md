# 🪙 Crypto Market Insights & Portfolio Tracker

A Streamlit app that uses **8+ years of real daily market data** to answer one practical question:
*what does the evidence say about investing in cryptocurrency, especially for a first-time investor in India?*
It also includes a portfolio tracker that checks your own holdings against that evidence.

## Purpose
Crypto is marketed to young investors with stories of 100x gains. This app tests those stories against real
data for the 10 best-known coins (Bitcoin, Ethereum, BNB, XRP, Solana, Cardano, Dogecoin, Litecoin, Polkadot,
Polygon), compared with the S&P 500 and gold.

### Research questions (one analysis page each)
| # | Question | Page |
|---|---|---|
| 1 | How have major coins performed since 2018, and do prices move in cycles? | Market Trends |
| 2 | How risky is crypto compared with stocks and gold, and was the risk rewarded? | Risk and Return |
| 3 | Does owning several coins actually spread risk? Is Bitcoin "digital gold"? | Correlation |
| 4 | Does buying when the market is fearful pay off? | Market Sentiment |
| 5 | Monthly SIP or lump sum, and what is left after India's 31.2% crypto tax? | Investment Simulator |

Every chart has a **"How to read this"** note above it and a **"What the data shows"** box below it. The
insight text is calculated from the data (not hard-coded), so it stays correct when filters change or the
data is refreshed. The **Conclusions** page answers each question with numbers.

## Key findings (data to 20 Oct 2026)
- Bitcoin grew ~6x since Jan 2018 but fell more than 50% in four separate bear markets (worst: -81%).
- Bitcoin is ~3.4x as volatile as the S&P 500; most altcoins 5x or more. Only 4 of 10 coins beat the S&P 500
  on return per unit of risk over the full period.
- 5 of the 10 coins never got back above their 2021 peak.
- Coins are highly correlated (average 0.55). An equal mix of all 10 was *more* volatile (77%) than Bitcoin
  alone (57%), so holding many coins is not diversification.
- Since 2020 Bitcoin has moved with the stock market, not with gold.
- The Fear & Greed Index mostly mirrors recent prices; "buy in extreme fear" had a high average return but
  a weak typical (median) outcome.
- A lump sum beat a monthly SIP in ~70% of 2-year Bitcoin windows; the SIP's value is avoiding bad timing.

## Data
| File | Source (free, no API key) | Contents |
|---|---|---|
| `data/crypto_daily.csv` | Binance `/api/v3/klines` | 28,976 daily OHLCV rows, 10 coins, Jan 2018 to Oct 2026 |
| `data/fear_greed.csv` | alternative.me | Daily Crypto Fear & Greed Index since Feb 2018 |
| `data/benchmarks.csv` | Yahoo Finance | S&P 500, gold, USD/INR daily closes |
| `data/market_snapshot.csv` | CoinGecko | Market cap, supply, all-time high per coin |

Rebuild or update all datasets with:
```
python scripts/build_dataset.py
```
Cleaning steps, formulas and limitations are documented on the **Data and Methodology** page.

## Pages
| Page | What it does |
|---|---|
| Dashboard (home) | Purpose, dataset summary, market today, headline findings |
| 1 Market Trends | BTC history with events, growth of $100, yearly-returns heatmap, halving cycles, volume |
| 2 Risk and Return | Risk-return scatter vs S&P 500/gold, drawdowns, daily-move distribution, volatility trend |
| 3 Correlation | Correlation matrix, behaviour on BTC's worst days, rolling correlation, diversification test, BTC in a stock portfolio |
| 4 Market Sentiment | Price coloured by Fear & Greed, forward returns by mood, mood by year |
| 5 Investment Simulator | SIP vs lump sum in INR or USD with Indian tax, same SIP across all coins, every-start-month test |
| 6 Conclusions | Answers to the five questions and what they mean for an investor |
| 7 My Portfolio 🔒 | Live value, exchange map, allocation, gain/loss, buy-timing analysis, historical risk of your mix |
| 8 Add Holding 🔒 | Add by hand (real historical price auto-filled for the buy date) or bulk CSV/Excel upload |
| 9 Watchlist | Live prices plus 30d/1y trend, volatility, correlation with BTC, distance from peak, sparkline |
| 10 Data and Methodology | Sources, coverage, cleaning, formulas, limitations, raw-data explorer with CSV export |

🔒 = needs login. **Demo account:** username `guest`, password `crypto123`. It starts with a sample portfolio
whose buy prices are the real closing prices on each buy date. Analysis pages need no login.

## Running it locally
```
pip install -r requirements.txt
streamlit run Dashboard.py
```

## Project structure
```
├── Dashboard.py              # Home: purpose, data summary, headline findings
├── analysis.py               # Data loading + all calculations (returns, volatility, drawdowns, ...)
├── ui.py                     # Shared "how to read" / "insight" boxes and chart colours
├── auth.py                   # Sign up / log in for the portfolio pages
├── utils.py                  # Holdings storage, live prices (with offline fallback), reference data
├── pages/                    # One file per page (see table above)
├── scripts/build_dataset.py  # Downloads and cleans all datasets
├── data/                     # Bundled CSV datasets (+ per-user holdings created at runtime)
├── requirements.txt
└── .streamlit/config.toml    # Gold/dark theme
```

## Deploying
1. Push this folder to a GitHub repo (keep the structure, including `data/`).
2. On https://share.streamlit.io choose the repo, branch `main`, main file `Dashboard.py`, and deploy.

On Streamlit Community Cloud the filesystem resets on redeploy, so user accounts and holdings are not permanent.
The market datasets are bundled in the repo, so the analysis pages always work.

## Limitations
Survivorship bias (coins chosen because they are large today), prices from a single exchange, only two halving
cycles, overlapping windows in rolling statistics, and a simplified tax model. This is a data-analysis project,
not investment advice.
