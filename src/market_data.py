import yfinance as yf
import pandas as pd
import os
import sys
import contextlib

@contextlib.contextmanager
def suppress_output():
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

COMMON_TICKER_MAP = {
    "reliance": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "infosys": "INFY.NS",
    "hdfc": "HDFCBANK.NS",
    "sbi": "SBIN.NS",
    "icici": "ICICIBANK.NS",
    "tesla": "TSLA",
    "apple": "AAPL",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "microsoft": "MSFT",
}


def search_ticker(query: str) -> str:
    q_lower = query.lower()
    for name, ticker in COMMON_TICKER_MAP.items():
        if name in q_lower:
            return ticker

    words = query.split()
    exclude_indices = {"BSE", "NSE", "NIFTY", "SENSEX", "BANKNIFTY", "RBI", "SEBI"}
    for w in words:
        w_clean = w.strip("?,.!;:'\"")
        if w_clean.isupper() and 2 <= len(w_clean) <= 5 and w_clean not in exclude_indices:
            with suppress_output():
                try:
                    if not yf.Ticker(w_clean).history(period="1d").empty:
                        return w_clean
                    if not yf.Ticker(f"{w_clean}.NS").history(period="1d").empty:
                        return f"{w_clean}.NS"
                except Exception:
                    pass

    return ""

def get_ticker_data(symbol: str, period: str = "1mo") -> pd.DataFrame:
    """Fetch OHLCV data from yfinance for a given period."""
    if not symbol: return pd.DataFrame()
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        return df
    except Exception as e:
        print(f"yfinance data error for {symbol}: {e}")
        return pd.DataFrame()

def get_ticker_info(symbol: str) -> dict:
    """Fetch company info from yfinance."""
    if not symbol: return {}
    try:
        ticker = yf.Ticker(symbol)
        return ticker.info
    except Exception as e:
        print(f"yfinance info error for {symbol}: {e}")
        return {}

def get_monthly_summary(symbol: str) -> dict:
    """Fetch 1Y of data, resample to monthly and return basic stats."""
    df = get_ticker_data(symbol, period="1y")
    if df.empty:
        return {}
    monthly = df['Close'].resample('ME').last()
    return {
        "latest_close": float(monthly.iloc[-1]),
        "1m_return": float(monthly.pct_change().iloc[-1] * 100) if len(monthly) > 1 else 0.0
    }

def get_yearly_summary(symbol: str) -> dict:
    """Fetch 5Y of data and summarize annual performance."""
    df = get_ticker_data(symbol, period="5y")
    if df.empty:
        return {}

    yearly = df['Close'].resample('YE').last()
    return {
        "latest_close": float(yearly.iloc[-1]),
        "1y_return": float(yearly.pct_change().iloc[-1] * 100) if len(yearly) > 1 else 0.0
    }

def get_daily_summary(symbol: str) -> dict:
    """Fetch 60d of data and return basic daily stats."""
    df = get_ticker_data(symbol, period="60d")
    if df.empty:
        return {}

    return {
        "latest_close": float(df['Close'].iloc[-1]),
        "60d_high": float(df['High'].max()),
        "60d_low": float(df['Low'].min()),
        "60d_return": float(df['Close'].pct_change(periods=len(df)-1).iloc[-1] * 100) if len(df) > 1 else 0.0
    }
