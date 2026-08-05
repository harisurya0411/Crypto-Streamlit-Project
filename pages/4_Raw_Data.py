"""
Raw Data page - search, filter, and export the full holdings dataset.
"""

import streamlit as st

from auth import check_login, show_logout_button
from utils import load_holdings

st.set_page_config(page_title="Raw Data", page_icon="📄", layout="wide")
check_login()
show_logout_button()

st.title("📄 Raw data")

holdings = load_holdings()
if holdings.empty:
    st.info("Add some holdings first on the 'Add Holding' page.")
    st.stop()

st.sidebar.header("📊 Filters")
search_term = st.sidebar.text_input("Search asset name")
sort_by = st.sidebar.selectbox("Sort by", options=["Asset", "Exchange", "Quantity", "BuyPrice"])

filtered = holdings.copy()
if search_term:
    filtered = filtered[filtered["Asset"].str.contains(search_term, case=False, na=False)]
filtered = filtered.sort_values(sort_by)

st.caption(f"Showing {len(filtered)} of {len(holdings)} holdings")
st.dataframe(filtered, use_container_width=True, hide_index=True)

csv_bytes = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download this view as CSV",
    data=csv_bytes,
    file_name="holdings_raw.csv",
    mime="text/csv",
)
