"""
Shared helpers used across pages: per-user holdings storage, live prices,
and static reference data (which coin IDs the API uses, and exchange
locations for the map).
"""

import os

import pandas as pd
import requests
import streamlit as st

from analysis import DATA_DIR, load_closes

COLUMNS = ["Asset", "Exchange", "Quantity", "BuyPrice"]   # required
OPTIONAL_COLUMNS = ["BuyDate"]                             # enables holding-period analysis

# Maps a friendly name to the ID CoinGecko's API expects.
# Polygon migrated MATIC -> POL in Sept 2024; "matic-network" now returns a
# stale price with zero market cap, so the new token ID is used.
ASSET_IDS = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Solana": "solana",
    "Cardano": "cardano",
    "Dogecoin": "dogecoin",
    "Litecoin": "litecoin",
    "Polkadot": "polkadot",
    "Polygon": "polygon-ecosystem-token",
    "BNB": "binancecoin",
    "XRP": "ripple",
}

# Static reference data for the map: (lat, lon) of each exchange's HQ
EXCHANGE_LOCATIONS = {
    "Binance": (35.9375, 14.3754),     # Malta
    "Coinbase": (37.7749, -122.4194),  # San Francisco
    "Kraken": (47.6062, -122.3321),    # Seattle
    "WazirX": (19.0760, 72.8777),      # Mumbai
    "CoinDCX": (12.9716, 77.5946),     # Bengaluru
    "Bybit": (25.2048, 55.2708),       # Dubai
    "KuCoin": (-4.6796, 55.4920),      # Seychelles
    "OKX": (35.8997, 14.5146),         # Malta
    "Gemini": (40.7128, -74.0060),     # New York
}
INDIAN_EXCHANGES = {"WazirX", "CoinDCX"}

# The demo account gets a realistic starting portfolio so the dashboard is
# never empty. Buy prices are NOT made up: they are looked up from the real
# closing price on each buy date in data/crypto_daily.csv.
DEMO_PORTFOLIO = [
    # Asset,     Exchange,   Quantity, BuyDate
    ("Bitcoin",  "WazirX",   0.010,    "2021-11-10"),  # bought at the 2021 peak
    ("Bitcoin",  "CoinDCX",  0.015,    "2023-01-15"),  # bought near the 2022 bottom
    ("Ethereum", "Binance",  0.40,     "2022-06-18"),
    ("Solana",   "Coinbase", 5.0,      "2024-03-01"),
    ("Dogecoin", "WazirX",   1500.0,   "2021-05-08"),  # meme-coin hype top
    ("Cardano",  "Kraken",   300.0,    "2023-06-10"),
    ("XRP",      "Bybit",    400.0,    "2024-11-20"),
    ("Polygon",  "CoinDCX",  250.0,    "2022-12-01"),
    ("BNB",      "Binance",  1.0,      "2023-10-01"),
]


def _user_file() -> str:
    username = st.session_state.get("username", "anonymous")
    return os.path.join(DATA_DIR, f"holdings_{username}.csv")


def historical_close(asset: str, date) -> float | None:
    """Real closing price of `asset` on `date` (or the nearest earlier day)."""
    closes = load_closes()
    if asset not in closes:
        return None
    series = closes[asset].dropna().loc[: pd.Timestamp(date)]
    return float(series.iloc[-1]) if not series.empty else None


def demo_holdings() -> pd.DataFrame:
    rows = []
    for asset, exchange, qty, buy_date in DEMO_PORTFOLIO:
        rows.append({
            "Asset": asset, "Exchange": exchange, "Quantity": qty,
            "BuyPrice": round(historical_close(asset, buy_date), 6), "BuyDate": buy_date,
        })
    return pd.DataFrame(rows)


def load_holdings() -> pd.DataFrame:
    path = _user_file()
    if os.path.exists(path):
        return pd.read_csv(path)
    if st.session_state.get("username") == "guest":
        df = demo_holdings()
        save_holdings(df)
        return df
    return pd.DataFrame(columns=COLUMNS + OPTIONAL_COLUMNS)


def save_holdings(df: pd.DataFrame) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(_user_file(), index=False)


# ----------------------------------------------------------------------
# LIVE API - CoinGecko simple price endpoint, no key required
# ----------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner="Fetching live prices...")
def _fetch_coingecko(asset_ids: tuple) -> dict:
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": ",".join(asset_ids), "vs_currencies": "usd", "include_24hr_change": "true"}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def live_prices(assets) -> tuple[dict, dict, str]:
    """
    Returns (price, change_24h, source) keyed by asset name.
    If CoinGecko is down or rate-limited, falls back to the latest close in
    the bundled dataset so the app never shows empty values.
    """
    assets = [a for a in assets if a in ASSET_IDS]
    try:
        data = _fetch_coingecko(tuple(sorted(ASSET_IDS[a] for a in assets)))
        price = {a: data[ASSET_IDS[a]]["usd"] for a in assets if ASSET_IDS[a] in data}
        change = {a: data[ASSET_IDS[a]].get("usd_24h_change") for a in assets if ASSET_IDS[a] in data}
        if len(price) == len(assets):
            return price, change, "live (CoinGecko)"
    except Exception:
        pass
    closes = load_closes()
    last = closes.ffill().iloc[-1]
    prev = closes.ffill().iloc[-2]
    price = {a: float(last[a]) for a in assets}
    change = {a: float((last[a] / prev[a] - 1) * 100) for a in assets}
    return price, change, f"last close in dataset ({closes.index[-1].date()})"
