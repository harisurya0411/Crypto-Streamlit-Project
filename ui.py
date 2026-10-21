"""
Small layout helpers so every page explains its charts the same way:

    question()  - the question the page sets out to answer
    reading()   - "how to read this chart", shown above a chart
    insight()   - what we conclude from it, shown below a chart
    sources()   - where the numbers came from
"""

import streamlit as st

PLOT_LAYOUT = dict(
    margin=dict(t=40, b=10, l=10, r=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    hovermode="x unified",
)

# One fixed colour per coin so a coin looks the same on every page
COIN_COLORS = {
    "Bitcoin": "#f7931a",
    "Ethereum": "#627eea",
    "BNB": "#f0d43a",
    "XRP": "#e8e8e8",
    "Solana": "#14f195",
    "Cardano": "#00b3c7",
    "Dogecoin": "#ff6f61",
    "Litecoin": "#7d8ca3",
    "Polkadot": "#e6007a",
    "Polygon": "#a46bff",
    "S&P 500": "#4fc3f7",
    "Gold": "#ffd54f",
}


def _escape(text: str) -> str:
    """Streamlit renders $...$ as LaTeX maths, so '$100 to $300' would be garbled."""
    return text.replace("$", r"\$")


def question(text: str) -> None:
    st.markdown(f"> **Question this page answers:** {_escape(text)}")


def reading(text: str) -> None:
    st.caption(f"📖 **How to read this:** {_escape(text)}")


def insight(points: list, title: str = "What the data shows") -> None:
    with st.container(border=True):
        st.markdown(f"**💡 {title}**")
        st.markdown("\n".join(f"- {_escape(p)}" for p in points))


def takeaway(text: str) -> None:
    st.success(f"**Takeaway:** {_escape(text)}")


def sources(text: str = "Binance daily candles (USDT pairs), alternative.me Fear & Greed Index, "
                          "Yahoo Finance (S&P 500, gold, USD/INR), CoinGecko market snapshot.") -> None:
    st.divider()
    st.caption(f"Data: {text} See **Data and Methodology** for details.")
