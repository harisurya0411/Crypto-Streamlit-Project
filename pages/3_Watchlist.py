"""
Watchlist page - track live prices of coins you don't own yet.
"""

import streamlit as st
import requests
import pandas as pd

from auth import check_login, show_logout_button
from utils import ASSET_IDS

st.set_page_config(page_title="Watchlist", page_icon="👀", layout="wide")
check_login()
show_logout_button()

st.title("👀 Watchlist")
st.caption("Track live prices of coins you're thinking about buying")

if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = []

new_coin = st.selectbox("Add a coin to your watchlist", options=list(ASSET_IDS.keys()))
if st.button("➕ Add to watchlist"):
    if new_coin not in st.session_state["watchlist"]:
        st.session_state["watchlist"].append(new_coin)

if not st.session_state["watchlist"]:
    st.info("Your watchlist is empty. Add a coin above.")
    st.stop()


@st.cache_data(ttl=120, show_spinner="Fetching live prices...")
def fetch_prices(asset_ids):
    ids_param = ",".join(asset_ids)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_param}&vs_currencies=usd&include_24hr_change=true"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


coin_ids = [ASSET_IDS[c] for c in st.session_state["watchlist"]]
try:
    prices = fetch_prices(coin_ids)
except Exception as e:
    st.error(f"Couldn't fetch live prices ({e}).")
    prices = {}

rows = []
for coin in st.session_state["watchlist"]:
    cid = ASSET_IDS[coin]
    info = prices.get(cid, {})
    rows.append({
        "Coin": coin,
        "Price (USD)": info.get("usd"),
        "24h Change (%)": round(info.get("usd_24h_change", 0), 2),
    })

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, hide_index=True)

remove_coin = st.selectbox("Remove a coin", options=["—"] + st.session_state["watchlist"])
if remove_coin != "—" and st.button("🗑️ Remove"):
    st.session_state["watchlist"].remove(remove_coin)
    st.rerun()
