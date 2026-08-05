"""
Performance page - portfolio allocation and gain/loss breakdown.
"""

import streamlit as st
import requests
import plotly.express as px

from auth import check_login, show_logout_button
from utils import load_holdings, ASSET_IDS

st.set_page_config(page_title="Performance", page_icon="📈", layout="wide")
check_login()
show_logout_button()

st.title("📈 Performance")

holdings = load_holdings()
if holdings.empty:
    st.info("Add some holdings first on the 'Add Holding' page.")
    st.stop()


@st.cache_data(ttl=300, show_spinner="Fetching live prices...")
def fetch_prices(asset_ids):
    ids_param = ",".join(asset_ids)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_param}&vs_currencies=usd"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


coin_ids = [ASSET_IDS[a] for a in holdings["Asset"].unique() if a in ASSET_IDS]
try:
    prices = fetch_prices(coin_ids)
except Exception as e:
    st.error(f"Couldn't fetch live prices ({e}).")
    prices = {}

holdings["CurrentPrice"] = holdings["Asset"].apply(lambda a: prices.get(ASSET_IDS.get(a), {}).get("usd"))
holdings["CurrentValue"] = holdings["Quantity"] * holdings["CurrentPrice"]
holdings["CostBasis"] = holdings["Quantity"] * holdings["BuyPrice"]
holdings["GainLoss"] = holdings["CurrentValue"] - holdings["CostBasis"]

# ----------------------------------------------------------------------
# Allocation pie chart
# ----------------------------------------------------------------------
st.subheader("Portfolio allocation")
alloc = holdings.groupby("Asset")["CurrentValue"].sum().reset_index()
fig_pie = px.pie(alloc, names="Asset", values="CurrentValue", hole=0.4)
fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10))
st.plotly_chart(fig_pie, use_container_width=True)

# ----------------------------------------------------------------------
# Gain/loss bar chart
# ----------------------------------------------------------------------
st.subheader("Gain / loss by asset")
gl = holdings.groupby("Asset")["GainLoss"].sum().reset_index()
fig_bar = px.bar(gl, x="Asset", y="GainLoss", color="GainLoss", color_continuous_scale=["#e74c3c", "#2ecc71"])
fig_bar.update_layout(margin=dict(t=10, b=10, l=10, r=10))
st.plotly_chart(fig_bar, use_container_width=True)

# ----------------------------------------------------------------------
# Top movers table
# ----------------------------------------------------------------------
st.subheader("Best & worst positions")
c1, c2 = st.columns(2)
c1.write("**Top gainers**")
c1.dataframe(holdings.sort_values("GainLoss", ascending=False).head(3)[["Asset", "GainLoss"]], hide_index=True)
c2.write("**Top losers**")
c2.dataframe(holdings.sort_values("GainLoss").head(3)[["Asset", "GainLoss"]], hide_index=True)
