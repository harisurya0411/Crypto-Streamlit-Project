"""
Shared helpers used across pages: per-user holdings storage, and static
reference data (which coin IDs the API uses, and exchange locations for
the map).
"""

import streamlit as st
import pandas as pd
import os

DATA_DIR = "data"
COLUMNS = ["Asset", "Exchange", "Quantity", "BuyPrice"]

# Maps a friendly name to the ID CoinGecko's API expects
ASSET_IDS = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Solana": "solana",
    "Cardano": "cardano",
    "Dogecoin": "dogecoin",
    "Litecoin": "litecoin",
    "Polkadot": "polkadot",
    "Polygon": "matic-network",
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


def _user_file() -> str:
    username = st.session_state.get("username", "anonymous")
    return os.path.join(DATA_DIR, f"holdings_{username}.csv")


def load_holdings() -> pd.DataFrame:
    """Every user starts with an EMPTY portfolio - no shared sample data."""
    path = _user_file()
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame(columns=COLUMNS)


def save_holdings(df: pd.DataFrame) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(_user_file(), index=False)
