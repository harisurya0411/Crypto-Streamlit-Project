"""
Builds the bundled datasets in data/ from free public APIs (no API keys).

Run from the project root:
    python scripts/build_dataset.py

Outputs
-------
data/crypto_daily.csv     daily OHLCV for the 10 coins (Binance spot, USDT pairs)
data/fear_greed.csv       Crypto Fear & Greed Index (alternative.me)
data/benchmarks.csv       S&P 500, Gold, USD/INR daily closes (Yahoo Finance)
data/market_snapshot.csv  market cap / supply / all-time-high snapshot (CoinGecko)

The app reads these CSVs instead of calling the APIs on every page load,
so it is fast, works offline and every chart is reproducible.
"""

import time
from datetime import datetime, timezone

import pandas as pd
import requests

START = "2018-01-01"
OUT = "data"
UA = {"User-Agent": "Mozilla/5.0 (crypto-insights student project)"}

# Asset name -> list of (Binance symbol, valid from, valid until).
# Polygon renamed MATIC -> POL in Sept 2024 (1:1 token swap), so the two
# Binance pairs are stitched into one continuous series.
BINANCE_PAIRS = {
    "Bitcoin": [("BTCUSDT", None, None)],
    "Ethereum": [("ETHUSDT", None, None)],
    "BNB": [("BNBUSDT", None, None)],
    "XRP": [("XRPUSDT", None, None)],
    "Solana": [("SOLUSDT", None, None)],
    "Cardano": [("ADAUSDT", None, None)],
    "Dogecoin": [("DOGEUSDT", None, None)],
    "Litecoin": [("LTCUSDT", None, None)],
    "Polkadot": [("DOTUSDT", None, None)],
    "Polygon": [("MATICUSDT", None, "2024-09-12"), ("POLUSDT", "2024-09-13", None)],
}

COINGECKO_IDS = {
    "Bitcoin": "bitcoin", "Ethereum": "ethereum", "BNB": "binancecoin",
    "XRP": "ripple", "Solana": "solana", "Cardano": "cardano",
    "Dogecoin": "dogecoin", "Litecoin": "litecoin", "Polkadot": "polkadot",
    "Polygon": "polygon-ecosystem-token",
}

YAHOO_TICKERS = {"SP500": "^GSPC", "Gold": "GC=F", "USDINR": "INR=X"}


def to_ms(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def fetch_binance(symbol: str) -> pd.DataFrame:
    """Page through /api/v3/klines (max 1000 candles per call)."""
    rows, start = [], to_ms(START)
    now_ms = int(time.time() * 1000)
    while True:
        resp = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": symbol, "interval": "1d", "startTime": start, "limit": 1000},
            timeout=20,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        rows += batch
        start = batch[-1][0] + 86_400_000
        if len(batch) < 1000:
            break
        time.sleep(0.3)

    df = pd.DataFrame(rows, columns=[
        "OpenTime", "Open", "High", "Low", "Close", "Volume", "CloseTime",
        "QuoteVolume", "Trades", "TakerBase", "TakerQuote", "Ignore",
    ])
    df = df[df["CloseTime"] < now_ms]  # keep only fully closed days
    df["Date"] = pd.to_datetime(df["OpenTime"], unit="ms").dt.date
    for col in ["Open", "High", "Low", "Close", "Volume", "QuoteVolume"]:
        df[col] = df[col].astype(float)
    return df[["Date", "Open", "High", "Low", "Close", "Volume", "QuoteVolume", "Trades"]]


def build_crypto() -> pd.DataFrame:
    frames = []
    for asset, pairs in BINANCE_PAIRS.items():
        for symbol, valid_from, valid_until in pairs:
            print(f"  Binance {symbol} ...")
            df = fetch_binance(symbol)
            if valid_from:
                df = df[pd.to_datetime(df["Date"]) >= valid_from]
            if valid_until:
                df = df[pd.to_datetime(df["Date"]) <= valid_until]
            df.insert(1, "Asset", asset)
            df.insert(2, "Symbol", symbol)
            frames.append(df)
    out = pd.concat(frames, ignore_index=True).sort_values(["Asset", "Date"])
    out = out.drop_duplicates(["Asset", "Date"], keep="last")
    out.to_csv(f"{OUT}/crypto_daily.csv", index=False)
    return out


def build_fear_greed(until) -> pd.DataFrame:
    print("  Fear & Greed index ...")
    data = requests.get("https://api.alternative.me/fng/?limit=0&format=json", timeout=20).json()["data"]
    df = pd.DataFrame(data)
    df["Date"] = pd.to_datetime(df["timestamp"].astype(int), unit="s").dt.date
    df = df.rename(columns={"value": "FearGreed", "value_classification": "Sentiment"})
    df["FearGreed"] = df["FearGreed"].astype(int)
    df = df[["Date", "FearGreed", "Sentiment"]].sort_values("Date").drop_duplicates("Date")
    df = df[df["Date"] <= until]
    df.to_csv(f"{OUT}/fear_greed.csv", index=False)
    return df


def build_benchmarks(until) -> pd.DataFrame:
    series = {}
    p1, p2 = to_ms(START) // 1000, int(time.time())
    for name, ticker in YAHOO_TICKERS.items():
        print(f"  Yahoo {ticker} ...")
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
            params={"period1": p1, "period2": p2, "interval": "1d"},
            headers=UA, timeout=20,
        )
        resp.raise_for_status()
        result = resp.json()["chart"]["result"][0]
        dates = pd.to_datetime(result["timestamp"], unit="s").date
        closes = result["indicators"]["quote"][0]["close"]
        series[name] = pd.Series(closes, index=dates)
    df = pd.DataFrame(series)
    df.index.name = "Date"
    df = df.groupby(level=0).last().dropna(how="all")
    df = df[df.index <= until]   # drop today's still-trading (intraday) row
    df.to_csv(f"{OUT}/benchmarks.csv")
    return df


def build_snapshot() -> pd.DataFrame:
    print("  CoinGecko market snapshot ...")
    resp = requests.get(
        "https://api.coingecko.com/api/v3/coins/markets",
        params={"vs_currency": "usd", "ids": ",".join(COINGECKO_IDS.values())},
        timeout=20,
    )
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    name_by_id = {v: k for k, v in COINGECKO_IDS.items()}
    df["Asset"] = df["id"].map(name_by_id)
    df["SnapshotDate"] = datetime.now(timezone.utc).date()
    cols = ["Asset", "SnapshotDate", "current_price", "market_cap", "market_cap_rank",
            "total_volume", "circulating_supply", "max_supply", "ath", "ath_date",
            "ath_change_percentage"]
    df = df[cols].sort_values("market_cap", ascending=False)
    df.to_csv(f"{OUT}/market_snapshot.csv", index=False)
    return df


if __name__ == "__main__":
    print("Building datasets ...")
    crypto = build_crypto()
    last_day = crypto["Date"].max()   # align every dataset to the last complete crypto day
    fng = build_fear_greed(last_day)
    bench = build_benchmarks(last_day)
    snap = build_snapshot()
    print(f"crypto_daily.csv    {len(crypto):>6} rows, {crypto['Date'].min()} -> {crypto['Date'].max()}")
    print(f"fear_greed.csv      {len(fng):>6} rows, {fng['Date'].min()} -> {fng['Date'].max()}")
    print(f"benchmarks.csv      {len(bench):>6} rows, {bench.index.min()} -> {bench.index.max()}")
    print(f"market_snapshot.csv {len(snap):>6} rows")
