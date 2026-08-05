"""
Add Holding page - manual entry form, plus bulk CSV upload
(mandatory element #4: file upload).
"""

import streamlit as st
import pandas as pd

from auth import check_login, show_logout_button
from utils import load_holdings, save_holdings, ASSET_IDS, EXCHANGE_LOCATIONS, COLUMNS

st.set_page_config(page_title="Add Holding", page_icon="➕", layout="wide")
check_login()
show_logout_button()

st.title("➕ Add a holding")

holdings = load_holdings()

# ----------------------------------------------------------------------
# Manual entry form
# ----------------------------------------------------------------------
st.subheader("✍️ Add a single holding")

with st.form("add_holding_form"):
    c1, c2 = st.columns(2)
    asset = c1.selectbox("Asset", options=list(ASSET_IDS.keys()))
    exchange = c2.selectbox("Exchange", options=list(EXCHANGE_LOCATIONS.keys()))

    c3, c4 = st.columns(2)
    quantity = c3.number_input("Quantity", min_value=0.0, step=0.01, format="%.4f")
    buy_price = c4.number_input("Buy price per unit ($)", min_value=0.0, step=0.01)

    submitted = st.form_submit_button("Add holding")

    if submitted:
        if quantity <= 0 or buy_price <= 0:
            st.error("Quantity and buy price must be greater than zero.")
        else:
            new_row = pd.DataFrame([{
                "Asset": asset, "Exchange": exchange,
                "Quantity": quantity, "BuyPrice": buy_price,
            }])
            holdings = pd.concat([holdings, new_row], ignore_index=True)
            save_holdings(holdings)
            st.success(f"Added {quantity} {asset} on {exchange}. Check the Dashboard.")

st.divider()

# ----------------------------------------------------------------------
# FILE UPLOAD (mandatory element #4)
# ----------------------------------------------------------------------
st.subheader("📁 Bulk import from a CSV or Excel file")
st.caption(f"Expected columns: {', '.join(COLUMNS)}")

uploaded_file = st.file_uploader("Upload file", type=["csv", "xlsx"])

if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        new_df = pd.read_csv(uploaded_file)
    else:
        new_df = pd.read_excel(uploaded_file)

    if not set(COLUMNS).issubset(new_df.columns):
        st.error(f"Your file is missing columns: {set(COLUMNS) - set(new_df.columns)}")
    else:
        st.dataframe(new_df, use_container_width=True)
        if st.button("Import these rows into my portfolio"):
            holdings = pd.concat([holdings, new_df[COLUMNS]], ignore_index=True)
            save_holdings(holdings)
            st.success(f"Imported {len(new_df)} holdings. Check the Dashboard.")

st.divider()

# ----------------------------------------------------------------------
# Current holdings + ability to delete rows
# ----------------------------------------------------------------------
st.subheader("Your current holdings")
if holdings.empty:
    st.caption("Nothing added yet.")
else:
    st.dataframe(holdings, use_container_width=True, hide_index=True)
    row_to_delete = st.number_input(
        "Row index to remove (see table above, 0 = first row)",
        min_value=0, max_value=max(len(holdings) - 1, 0), step=1,
    )
    if st.button("🗑️ Remove this row"):
        holdings = holdings.drop(index=row_to_delete).reset_index(drop=True)
        save_holdings(holdings)
        st.success("Removed. Refresh the page to see the updated table.")
