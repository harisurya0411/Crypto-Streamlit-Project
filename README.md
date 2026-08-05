# 🪙 Crypto Portfolio Tracker

A Streamlit web app for tracking crypto holdings across exchanges, with
live prices, gain/loss analysis, and a map of where your assets are held.

## What it does
- Sign up / log in (accounts stored locally, hashed passwords)
- Add holdings manually or bulk-import a CSV
- Live prices from CoinGecko merged with your holdings
- KPI row: total portfolio value, total gain/loss, best performer, holdings count
- Map: bubble size shows value held at each exchange
- Performance page: allocation pie chart, gain/loss bar chart, top movers
- Watchlist: track coins you don't own yet
- Filter by asset, exchange, value range
- Export your holdings as CSV

## Who it's for
Retail crypto investors who hold assets across multiple exchanges and
want one place to see total value and performance, without connecting
API keys to their actual exchange accounts.

## Data & APIs used
- [CoinGecko API](https://www.coingecko.com/en/api) — free, no key
  required, live crypto prices
- Static exchange HQ coordinates (reference data for the map)
- Your own holdings (added manually or uploaded) — no bundled sample
  data, every account starts empty like a real app

## Login
- **Demo account** — Username: `guest`  Password: `crypto123`
- Or click "Sign Up" to create your own account.

Note: on Streamlit Community Cloud the filesystem resets on redeploy,
so accounts and holdings aren't permanent — expected for a capstone demo.
A production version would use a real database instead.

## Running it locally
```
pip install -r requirements.txt
streamlit run Dashboard.py
```
Log in with the demo account, then go to "Add Holding" to add your first
crypto position (e.g. 0.5 Bitcoin on Coinbase, bought at $40,000).

## Project structure
```
crypto-portfolio/
├── Dashboard.py              # Main page: map, KPIs, filters, table
├── auth.py                   # Sign up / log in
├── utils.py                  # Shared data loading + reference constants
├── pages/
│   ├── 1_Add_Holding.py      # Manual entry + CSV bulk upload
│   ├── 2_Performance.py      # Allocation & gain/loss charts
│   ├── 3_Watchlist.py        # Live prices for coins you don't own
│   └── 4_Raw_Data.py         # Full table, search, CSV export
├── data/                     # users.json + per-user holdings (empty at start)
├── requirements.txt
└── .streamlit/config.toml    # Gold/dark theme
```

## Deploying to get a public link
1. Create a GitHub repo, upload every file/folder here (keep the structure).
2. Go to https://share.streamlit.io → sign in with GitHub → "New app"
3. Select your repo, branch `main`, main file path `Dashboard.py` → Deploy
4. You'll get a public URL like `https://your-app-name.streamlit.app/`
