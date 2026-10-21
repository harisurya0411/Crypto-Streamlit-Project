"""
Add Holding page - manual entry (with the real historical price filled in
for the chosen date), plus bulk CSV / Excel upload.
"""

import pandas as pd
import streamlit as st

from analysis import drawdown, load_closes, load_fear_greed, pct, usd
from auth import check_login, show_logout_button
from ui import insight
from utils import ASSET_IDS, COLUMNS, EXCHANGE_LOCATIONS, OPTIONAL_COLUMNS, historical_close, load_holdings, save_holdings

st.set_page_config(page_title="Add Holding", page_icon="➕", layout="wide")
check_login()
show_logout_button()

st.title("➕ Add a holding")

holdings = load_holdings()
closes = load_closes()

# ----------------------------------------------------------------------
# Manual entry
# ----------------------------------------------------------------------
st.subheader("✍️ Add a single holding")
c1, c2, c3 = st.columns(3)
asset = c1.selectbox("Asset", options=list(ASSET_IDS.keys()))
exchange = c2.selectbox("Exchange", options=list(EXCHANGE_LOCATIONS.keys()))
first = closes[asset].first_valid_index().date()
buy_date = c3.date_input("Buy date", value=closes.index.max().date(), min_value=first,
                         max_value=closes.index.max().date())

ref_price = historical_close(asset, buy_date)
c4, c5 = st.columns(2)
quantity = c4.number_input("Quantity", min_value=0.0, step=0.01, format="%.4f")
use_hist = c5.toggle(f"Use the real closing price on that date ({usd(ref_price)})", value=True)
buy_price = ref_price if use_hist else c5.number_input("Buy price per unit ($)", min_value=0.0, step=0.01,
                                                       value=float(ref_price or 0.0))

# Context for the chosen date, so the user sees what kind of moment they bought into
series = closes[asset].dropna()
dd_then = drawdown(series.loc[:pd.Timestamp(buy_date)]).iloc[-1]
since = series.iloc[-1] / ref_price - 1 if ref_price else float("nan")
fng = load_fear_greed()
mood = fng.loc[:pd.Timestamp(buy_date)].iloc[-1] if not fng.loc[:pd.Timestamp(buy_date)].empty else None
points = [
    f"On {buy_date:%d %b %Y}, {asset} closed at **{usd(ref_price)}**, which was **{pct(-dd_then, 0)} below** its "
    "all-time high up to that day." if dd_then < -0.005 else
    f"On {buy_date:%d %b %Y}, {asset} closed at **{usd(ref_price)}**, at or near its all-time high.",
]
if pd.Timestamp(buy_date) < series.index[-1]:
    points.append(f"From that close to the latest price in the dataset ({series.index[-1]:%d %b %Y}) it has moved "
                  f"**{pct(since, 0, True)}**.")
if mood is not None:
    points.append(f"Market mood that day: **{mood['Sentiment']}** (Fear & Greed {mood['FearGreed']}).")
insight(points, "Context for this purchase")

if st.button("Add holding", type="primary"):
    if quantity <= 0 or not buy_price or buy_price <= 0:
        st.error("Quantity and buy price must be greater than zero.")
    else:
        new_row = pd.DataFrame([{"Asset": asset, "Exchange": exchange, "Quantity": quantity,
                                 "BuyPrice": round(buy_price, 6), "BuyDate": str(buy_date)}])
        holdings = pd.concat([holdings, new_row], ignore_index=True)
        save_holdings(holdings)
        st.success(f"Added {quantity} {asset} on {exchange}. Check **My Portfolio**.")

st.divider()

# ----------------------------------------------------------------------
# FILE UPLOAD
# ----------------------------------------------------------------------
st.subheader("📁 Bulk import from a CSV or Excel file")
st.caption(f"Required columns: {', '.join(COLUMNS)}. Optional: {', '.join(OPTIONAL_COLUMNS)} (YYYY-MM-DD). "
           f"Asset must be one of: {', '.join(ASSET_IDS)}.")

uploaded_file = st.file_uploader("Upload file", type=["csv", "xlsx"])
if uploaded_file is not None:
    new_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
    missing = set(COLUMNS) - set(new_df.columns)
    unknown = set(new_df.get("Asset", pd.Series(dtype=str))) - set(ASSET_IDS)
    if missing:
        st.error(f"Your file is missing columns: {missing}")
    elif unknown:
        st.error(f"Unknown assets in your file: {unknown}")
    else:
        keep = COLUMNS + [c for c in OPTIONAL_COLUMNS if c in new_df.columns]
        st.dataframe(new_df[keep], width="stretch")
        if st.button("Import these rows into my portfolio"):
            holdings = pd.concat([holdings, new_df[keep]], ignore_index=True)
            save_holdings(holdings)
            st.success(f"Imported {len(new_df)} holdings. Check **My Portfolio**.")

st.divider()

# ----------------------------------------------------------------------
# Current holdings + ability to delete rows
# ----------------------------------------------------------------------
st.subheader("Your current holdings")
if holdings.empty:
    st.caption("Nothing added yet.")
else:
    st.dataframe(holdings, width="stretch")
    row_to_delete = st.number_input("Row index to remove (see table above, 0 = first row)",
                                    min_value=0, max_value=max(len(holdings) - 1, 0), step=1)
    if st.button("🗑️ Remove this row"):
        holdings = holdings.drop(index=row_to_delete).reset_index(drop=True)
        save_holdings(holdings)
        st.rerun()
