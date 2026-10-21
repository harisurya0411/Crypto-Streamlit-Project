"""
Data loading and the analysis maths shared by every page.

All market data comes from the CSVs in data/ (built by
scripts/build_dataset.py from Binance, alternative.me, Yahoo Finance and
CoinGecko). Keeping the maths here means each page only decides what to
show and how to explain it.
"""

import os

import numpy as np
import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

CRYPTO_DAYS_PER_YEAR = 365   # crypto trades every day
MARKET_DAYS_PER_YEAR = 252   # stock / gold markets trade ~252 days a year

# Bitcoin's block reward halves every 210,000 blocks (~4 years)
HALVINGS = {
    "2020 halving": pd.Timestamp("2020-05-11"),
    "2024 halving": pd.Timestamp("2024-04-20"),
}

# Well-documented market events, used to annotate price charts
EVENTS = [
    ("2018-12-15", "2018 bear-market bottom"),
    ("2020-03-12", "COVID crash"),
    ("2020-05-11", "BTC halving"),
    ("2021-11-10", "2021 cycle peak"),
    ("2022-05-09", "Terra/LUNA collapse"),
    ("2022-11-08", "FTX collapse"),
    ("2024-01-10", "US spot BTC ETFs approved"),
    ("2024-04-20", "BTC halving"),
]

# Fear & Greed buckets as defined by alternative.me
SENTIMENT_ORDER = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]


# ----------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------
@st.cache_data
def load_crypto() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(DATA_DIR, "crypto_daily.csv"), parse_dates=["Date"])
    return df.sort_values(["Asset", "Date"])


@st.cache_data
def load_closes() -> pd.DataFrame:
    """Wide table: one row per day, one column per coin (daily close in USD)."""
    return load_crypto().pivot(index="Date", columns="Asset", values="Close").sort_index()


@st.cache_data
def load_volumes() -> pd.DataFrame:
    """Daily traded value in USD (Binance quote volume)."""
    return load_crypto().pivot(index="Date", columns="Asset", values="QuoteVolume").sort_index()


@st.cache_data
def load_fear_greed() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(DATA_DIR, "fear_greed.csv"), parse_dates=["Date"])
    return df.set_index("Date").sort_index()


@st.cache_data
def load_benchmarks() -> pd.DataFrame:
    """S&P 500, gold and USD/INR closes. Markets have different holidays, so
    each column has its own gaps: call .dropna() on a single column before use."""
    df = pd.read_csv(os.path.join(DATA_DIR, "benchmarks.csv"), parse_dates=["Date"])
    return df.set_index("Date").sort_index()


@st.cache_data
def load_snapshot() -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, "market_snapshot.csv"))


# ----------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------
def cagr(prices: pd.Series) -> float:
    """Compound annual growth rate between the first and last valid price."""
    p = prices.dropna()
    if len(p) < 2:
        return np.nan
    years = (p.index[-1] - p.index[0]).days / 365.25
    return (p.iloc[-1] / p.iloc[0]) ** (1 / years) - 1


def annual_volatility(returns: pd.Series, periods: int = CRYPTO_DAYS_PER_YEAR) -> float:
    return returns.dropna().std() * np.sqrt(periods)


def sharpe_ratio(returns: pd.Series, periods: int = CRYPTO_DAYS_PER_YEAR, risk_free: float = 0.0) -> float:
    r = returns.dropna()
    vol = r.std() * np.sqrt(periods)
    return (r.mean() * periods - risk_free) / vol if vol else np.nan


def drawdown(prices: pd.Series) -> pd.Series:
    """How far below its previous all-time high the price is on each day (0 to -1)."""
    p = prices.dropna()
    return p / p.cummax() - 1


def max_drawdown_info(prices: pd.Series) -> dict:
    """Worst peak-to-trough fall, when it happened and how long recovery took."""
    p = prices.dropna()
    dd = drawdown(p)
    trough = dd.idxmin()
    peak = p.loc[:trough].idxmax()
    after = p.loc[trough:]
    recovered = after[after >= p.loc[peak]]
    recovery_date = recovered.index[0] if not recovered.empty else None
    return {
        "max_drawdown": dd.min(),
        "peak_date": peak,
        "trough_date": trough,
        "recovery_date": recovery_date,
        "days_to_recover": (recovery_date - trough).days if recovery_date is not None else None,
        "current_drawdown": dd.iloc[-1],
    }


def risk_return_table(closes: pd.DataFrame, periods: int = CRYPTO_DAYS_PER_YEAR) -> pd.DataFrame:
    """One row of headline risk / return statistics per asset."""
    rows = []
    for asset in closes.columns:
        p = closes[asset].dropna()
        r = p.pct_change().dropna()
        dd = max_drawdown_info(p)
        rows.append({
            "Asset": asset,
            "Data from": p.index[0].date(),
            "CAGR": cagr(p),
            "Volatility": annual_volatility(r, periods),
            "Sharpe": sharpe_ratio(r, periods),
            "Max drawdown": dd["max_drawdown"],
            "Below ATH now": dd["current_drawdown"],
            "Best day": r.max(),
            "Worst day": r.min(),
            "Days moving >10%": int((r.abs() > 0.10).sum()),
            "% of days up": (r > 0).mean(),
        })
    return pd.DataFrame(rows).set_index("Asset")


def bear_markets(prices: pd.Series, threshold: float = -0.5) -> list[dict]:
    """
    Separate episodes where the price fell more than `threshold` below its
    all-time high before setting a new high. An episode runs from one
    all-time high to the next one (or to today if not yet recovered).
    """
    p = prices.dropna()
    dd = drawdown(p)
    episode_id = (dd == 0).cumsum()
    out = []
    for _, seg in dd.groupby(episode_id):
        if seg.min() < threshold:
            out.append({"peak_date": seg.index[0], "trough_date": seg.idxmin(), "depth": seg.min()})
    return out


def calendar_year_returns(closes: pd.DataFrame) -> pd.DataFrame:
    """
    Return for each calendar year (first to last close of the year).
    A coin's listing year is left blank when it started trading after the
    first week of January, because a part-year return is not comparable.
    """
    yearly = closes.groupby(closes.index.year).agg(["first", "last"])
    out = {}
    for asset in closes.columns:
        first, last = yearly[(asset, "first")], yearly[(asset, "last")]
        ret = last / first - 1
        listed = closes[asset].first_valid_index()
        if listed is not None and listed > pd.Timestamp(year=listed.year, month=1, day=7):
            ret.loc[listed.year] = np.nan
        out[asset] = ret
    df = pd.DataFrame(out)
    df.index.name = "Year"
    return df


def weekly_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Friday-to-Friday returns. Used when mixing crypto (24/7) with stock markets."""
    return df.resample("W-FRI").last().pct_change(fill_method=None).dropna(how="all")


def forward_return(prices: pd.Series, days: int) -> pd.Series:
    """Return you would have earned by buying on each day and holding `days` days."""
    return prices.shift(-days) / prices - 1


def pct(x: float, digits: int = 1, sign: bool = False) -> str:
    """Format a fraction (0.123) as a percentage string ('12.3%')."""
    if x is None or pd.isna(x):
        return "n/a"
    return f"{x * 100:+.{digits}f}%" if sign else f"{x * 100:.{digits}f}%"


def usd(x: float) -> str:
    """Format a dollar amount compactly: $2.29T, $535.8B, $83,028, $1.39, -$830."""
    if x is None or pd.isna(x):
        return "n/a"
    sign, x = ("-" if x < 0 else ""), abs(x)
    if x >= 1e12:
        return f"{sign}${x / 1e12:.2f}T"
    if x >= 1e9:
        return f"{sign}${x / 1e9:.1f}B"
    if x >= 1e6:
        return f"{sign}${x / 1e6:.1f}M"
    if x >= 100:
        return f"{sign}${x:,.0f}"
    if x >= 1:
        return f"{sign}${x:,.2f}"
    return f"{sign}${x:.4f}"
