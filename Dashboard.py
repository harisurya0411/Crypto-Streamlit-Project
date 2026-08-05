"""
Crypto Portfolio Tracker - Dashboard (home) page.
"""

import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium

from auth import check_login, show_logout_button
from utils import load_holdings, ASSET_IDS, EXCHANGE_LOCATIONS

st.set_page_config(page_title="Crypto Portfolio Tracker", page_icon="🪙", layout="wide")

check_login()
show_logout_button()

st.title("🪙 Crypto Portfolio Tracker")
st.caption("Live prices, gains/losses, and where your holdings are custodied")

# ----------------------------------------------------------------------
# LIVE API - CoinGecko simple price endpoint, no key required
# ----------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner="Fetching live prices...")
def fetch_prices(asset_ids: list) -> dict:
    ids_param = ",".join(asset_ids)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_param}&vs_currencies=usd"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


holdings = load_holdings()

if holdings.empty:
    st.info(
        "Your portfolio is empty. Go to **Add Holding** in the sidebar to add your "
        "first crypto asset, or bulk-upload a CSV."
    )
    st.stop()

# ----------------------------------------------------------------------
# Merge live prices into holdings
# ----------------------------------------------------------------------
coin_ids = [ASSET_IDS[a] for a in holdings["Asset"].unique() if a in ASSET_IDS]

try:
    prices = fetch_prices(coin_ids)
except Exception as e:
    st.error(f"Couldn't fetch live prices right now ({e}).")
    prices = {}

def current_price(asset):
    coin_id = ASSET_IDS.get(asset)
    return prices.get(coin_id, {}).get("usd", None)

holdings["CurrentPrice"] = holdings["Asset"].apply(current_price)
holdings["CostBasis"] = holdings["Quantity"] * holdings["BuyPrice"]
holdings["CurrentValue"] = holdings["Quantity"] * holdings["CurrentPrice"]
holdings["GainLoss"] = holdings["CurrentValue"] - holdings["CostBasis"]
holdings["GainLossPct"] = (holdings["GainLoss"] / holdings["CostBasis"] * 100).round(1)

# ----------------------------------------------------------------------
# SIDEBAR FILTERS (mandatory element #5: at least 3 filters)
# ----------------------------------------------------------------------
st.sidebar.header("📊 Filters")

assets = sorted(holdings["Asset"].unique())
selected_assets = st.sidebar.multiselect("Asset", options=assets, default=assets)

exchanges = sorted(holdings["Exchange"].unique())
selected_exchanges = st.sidebar.multiselect("Exchange", options=exchanges, default=exchanges)

val_min, val_max = float(holdings["CurrentValue"].min()), float(holdings["CurrentValue"].max())
if val_min == val_max:
    val_max += 1  # avoid a zero-width slider when there's only one holding
value_range = st.sidebar.slider("Current value range ($)", val_min, val_max, (val_min, val_max))

filtered = holdings[
    (holdings["Asset"].isin(selected_assets))
    & (holdings["Exchange"].isin(selected_exchanges))
    & (holdings["CurrentValue"].between(*value_range))
]

# ----------------------------------------------------------------------
# KPI ROW (mandatory element #6: at least 3 st.metric cards)
# ----------------------------------------------------------------------
total_value = filtered["CurrentValue"].sum()
total_gain = filtered["GainLoss"].sum()

if not filtered.empty:
    best = filtered.loc[filtered["GainLossPct"].idxmax()]
    best_label = f"{best['Asset']} ({best['GainLossPct']:+.1f}%)"
else:
    best_label = "—"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Portfolio Value", f"${total_value:,.2f}")
col2.metric("Total Gain / Loss", f"${total_gain:,.2f}")
col3.metric("Best Performer", best_label)
col4.metric("Holdings", len(filtered))

st.divider()

# ----------------------------------------------------------------------
# INTERACTIVE MAP (mandatory element #2)
# Bubble size = value held at that exchange
# ----------------------------------------------------------------------
st.subheader("🗺️ Holdings by exchange")

exchange_value = filtered.groupby("Exchange")["CurrentValue"].sum().reset_index()

m = folium.Map(location=[20, 10], zoom_start=2, tiles="CartoDB dark_matter")

for _, row in exchange_value.iterrows():
    coords = EXCHANGE_LOCATIONS.get(row["Exchange"])
    if coords:
        folium.CircleMarker(
            location=coords,
            radius=max(6, min(35, row["CurrentValue"] / 200)),
            color="#f0b90b",
            fill=True,
            fill_color="#f0b90b",
            fill_opacity=0.7,
            popup=folium.Popup(f"<b>{row['Exchange']}</b><br>${row['CurrentValue']:,.2f}", max_width=200),
            tooltip=row["Exchange"],
        ).add_to(m)

st_folium(m, width=1200, height=450)

# ----------------------------------------------------------------------
# TABLE + CSV DOWNLOAD (mandatory element #7)
# ----------------------------------------------------------------------
st.subheader("📋 Your holdings")
st.dataframe(
    filtered[["Asset", "Exchange", "Quantity", "BuyPrice", "CurrentPrice", "CurrentValue", "GainLoss", "GainLossPct"]],
    use_container_width=True,
    hide_index=True,
)

csv_bytes = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download holdings as CSV",
    data=csv_bytes,
    file_name="crypto_holdings.csv",
    mime="text/csv",
)
