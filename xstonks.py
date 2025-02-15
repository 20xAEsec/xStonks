#!/usr/bin/env python3
"""
modular_trading_bot.py

This script:
- Logs into Robinhood using the robin_stocks API.
- Retrieves stocks from a watchlist named 'xstonks'.
- For each stock, collects data and computes several technical indicators:
    * Moving averages, RSI, MACD, Bollinger Bands,
      plus additional bullish signals (MACD crossover, Bollinger bounce,
      volume spike, bullish engulfing, bullish hammer).
- Aggregates the results into a pandas DataFrame.
"""

import robin_stocks.robinhood as r
import pandas as pd
import numpy as np
import datetime
import time
import os
import pyotp
import json
from dotenv import load_dotenv
load_dotenv()
# -------------------- Authentication --------------------
def login_to_robinhood(username, password, mfa=False):
    """
    Log into Robinhood.
    """
    print(username)
    print(password)
    try:
        if mfa:
            #mfa_code = input("Enter MFA Code: ") # MFA INFO
            totp = pyotp.TOTP(os.getenv("2FA_APP_CODE")).now()
            print("Current OTP:", totp)
            login = r.login(username, password, store_session=False, mfa_code=totp)
        else:
            login = r.login(username, password)

        print("Successfully logged in.")
        return login
    except Exception as e:
        print(f"Login failed: {e}")
        print(str(login))
        return None

# -------------------- Data Retrieval Functions --------------------
def get_quote(symbol):
    """
    Retrieve real-time quote data for a given symbol.
    """
    try:
        quote = r.stocks.get_stock_quote_by_symbol(symbol)
        return quote
    except Exception as e:
        print(f"Error getting quote for {symbol}: {e}")
        return None

def get_historicals(symbol, interval="5minute", span="day", bounds="regular"):
    """
    Retrieve historical price data (candlesticks) for a given symbol.
    Returns a pandas DataFrame.
    """
    try:
        historicals = r.stocks.get_stock_historicals(symbol, interval=interval, span=span, bounds=bounds)
        df = pd.DataFrame(historicals)
        if df.empty:
            print(f"No historical data for {symbol}.")
            return None
        # Convert time and price columns
        df['begins_at'] = pd.to_datetime(df['begins_at'])
        df['close_price'] = df['close_price'].astype(float)
        if 'open_price' in df.columns:
            df['open_price'] = df['open_price'].astype(float)
        if 'high_price' in df.columns:
            df['high_price'] = df['high_price'].astype(float)
        if 'low_price' in df.columns:
            df['low_price'] = df['low_price'].astype(float)
        if 'volume' in df.columns:
            df['volume'] = df['volume'].astype(float)
        return df
    except Exception as e:
        print(f"Error getting historical data for {symbol}: {e}")
        return None

# -------------------- Technical Indicator Functions --------------------
def compute_moving_average(prices, period):
    """
    Calculate the simple moving average (SMA) for a series of prices.
    """
    return prices.rolling(window=period).mean()

def compute_rsi(prices, period=14):
    """
    Compute the Relative Strength Index (RSI) for a series of prices.
    """
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(prices, fast=12, slow=26, signal=9):
    """
    Compute MACD and its signal line using exponential moving averages.
    Returns: macd_line, signal_line, and MACD histogram.
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - signal_line
    return macd_line, signal_line, macd_hist

def compute_bollinger_bands(prices, period=20, num_std=2):
    """
    Calculate Bollinger Bands for a series of prices.
    Returns: middle_band (SMA), upper_band, and lower_band.
    """
    sma = prices.rolling(window=period).mean()
    rolling_std = prices.rolling(window=period).std()
    upper_band = sma + num_std * rolling_std
    lower_band = sma - num_std * rolling_std
    return sma, upper_band, lower_band

# -------------------- Additional Bullish Signal Functions --------------------
def check_bullish_macd(prices):
    """
    Check for a bullish MACD crossover.
    Returns True if the MACD line crosses above its signal line.
    """
    macd_line, signal_line, _ = compute_macd(prices)
    if len(macd_line) < 2:
        return False
    if macd_line.iloc[-2] < signal_line.iloc[-2] and macd_line.iloc[-1] > signal_line.iloc[-1]:
        return True
    return False

def check_bollinger_bounce(df, period=20, num_std=2):
    """
    Check if the price is bouncing off the lower Bollinger Band.
    Returns True if the latest price is near the lower band and above the SMA.
    """
    sma, upper_band, lower_band = compute_bollinger_bands(df['close_price'], period, num_std)
    latest_price = df['close_price'].iloc[-1]
    # Consider it a bounce if price is within ~1% of the lower band and above the SMA.
    if latest_price <= lower_band.iloc[-1] * 1.01 and latest_price > sma.iloc[-1]:
        return True
    return False

def check_volume_spike(df, multiplier=1.5):
    """
    Check if the latest volume is significantly higher than the average.
    Returns True if current volume is at least 'multiplier' times the average of the last 20 periods.
    """
    if 'volume' not in df.columns:
        return False
    avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
    latest_volume = df['volume'].iloc[-1]
    if avg_volume > 0 and latest_volume >= multiplier * avg_volume:
        return True
    return False

def detect_bullish_engulfing(df):
    """
    Detect a bullish engulfing pattern using the last two candlesticks.
    Requires 'open_price' and 'close_price' columns.
    Returns True if a bullish engulfing pattern is detected.
    """
    if len(df) < 2 or 'open_price' not in df.columns or 'close_price' not in df.columns:
        return False
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    # Previous candle bearish and current candle bullish, with current body engulfing previous.
    if prev['close_price'] < prev['open_price'] and curr['close_price'] > curr['open_price']:
        if curr['open_price'] < prev['close_price'] and curr['close_price'] > prev['open_price']:
            return True
    return False

def detect_bullish_hammer(df):
    """
    Detect a bullish hammer pattern in the latest candlestick.
    Requires 'open_price', 'close_price', 'high_price', and 'low_price' columns.
    Returns True if a bullish hammer is detected.
    """
    if len(df) < 1 or not all(col in df.columns for col in ['open_price', 'close_price', 'high_price', 'low_price']):
        return False
    latest = df.iloc[-1]
    open_price = latest['open_price']
    close_price = latest['close_price']
    high_price = latest['high_price']
    low_price = latest['low_price']
    body = abs(close_price - open_price)
    candle_range = high_price - low_price
    lower_shadow = min(open_price, close_price) - low_price
    if candle_range == 0 or body == 0:
        return False
    # A hammer typically has a small body (less than 30% of the candle range) and a lower shadow at least 2x the body.
    if (body / candle_range < 0.3) and (lower_shadow / body > 2):
        return True
    return False

"""
uses get_stock_historocals from robin_stocks to get the historical data for a stock ticker. Args below
    inputSymbols (str or list) – May be a single stock ticker or a list of stock tickers.
    interval (Optional[str]) – Interval to retrieve data for. Values are ‘5minute’, ‘10minute’, ‘hour’, ‘day’, ‘week’. Default is ‘hour’.
    span (Optional[str]) – Sets the range of the data to be either ‘day’, ‘week’, ‘month’, ‘3month’, ‘year’, or ‘5year’. Default is ‘week’.
    bounds (Optional[str]) – Represents if graph will include extended trading hours or just regular trading hours. Values are ‘extended’, ‘trading’, or ‘regular’. Default is ‘regular’
    info (Optional[str]) – Will filter the results to have a list of the values that correspond to key that matches info.
"""

def generate_historical_dataframes(symbols, interval="day", span="year", bounds="regular"):
    """
    For each symbol in the provided list, retrieves historical data using the Robinhood API,
    converts the data to a pandas DataFrame, and returns a dictionary mapping symbol to its DataFrame.
    
    Parameters:
      symbols (list): List of stock ticker symbols (e.g., ["AAPL", "TSLA"]).
      interval (str): The interval between data points (default: "day").
      span (str): The span of historical data to retrieve (default: "year").
      bounds (str): The bounds parameter for the historical data (default: "regular").
    
    Returns:
      dict: A dictionary where the keys are symbols and the values are DataFrames containing
            historical data with at least a 'close_price' column.
    """
    dataframes = {}
    
    for symbol in symbols:
        try:
            historicals = r.stocks.get_stock_historicals(symbol, interval=interval, span=span, bounds=bounds)
            # Convert the list of dictionaries to a DataFrame
            df = pd.DataFrame(historicals)
            if df.empty:
                print(f"No historical data found for {symbol}.")
                continue

            # Convert time and price columns
            df['begins_at'] = pd.to_datetime(df['begins_at'])
            df['close_price'] = df['close_price'].astype(float)
            
            # (Optional) Convert additional columns if needed
            if 'open_price' in df.columns:
                df['open_price'] = df['open_price'].astype(float)
            if 'high_price' in df.columns:
                df['high_price'] = df['high_price'].astype(float)
            if 'low_price' in df.columns:
                df['low_price'] = df['low_price'].astype(float)
            if 'volume' in df.columns:
                df['volume'] = df['volume'].astype(float)
            
            # Sort the data by date in case it isn't already sorted.
            df.sort_values("begins_at", inplace=True)
            df.reset_index(drop=True, inplace=True)
            
            dataframes[symbol] = df
        except Exception as e:
            print(f"Error retrieving data for {symbol}: {e}")
    
    return dataframes

# # Example usage:
# if __name__ == "__main__":
#     symbols_list = ["AAPL", "TSLA", "AMZN", "MSFT"]
#     historical_data = generate_historical_dataframes(symbols_list)
    
#     # Display basic info for each symbol's DataFrame.
#     for symbol, df in historical_data.items():
#         print(f"\n{symbol} historical data:")
#         print(df.head())
        
#     # Example: using one of these DataFrames with the is_golden_cross_imminent function
#     # (Assuming is_golden_cross_imminent is defined and expects a DataFrame with a 'close_price' column.)
#     # from your_golden_cross_module import is_golden_cross_imminent  # Import your function as needed.
#     # result = is_golden_cross_imminent(historical_data["AAPL"])
#     # print(f"\nIs AAPL showing signs of an imminent golden cross? {result}")


def is_golden_cross_imminent(df, short_period=50, long_period=200, lookback=5, gap_threshold=0.02):
    """
    Determines if a stock is showing indications of an imminent golden cross.
    
    A golden cross is typically defined as the short-term moving average (e.g. 50-day MA)
    crossing above the long-term moving average (e.g. 200-day MA). This function checks:
    
      - The golden cross has not yet occurred (i.e., the short MA is still below the long MA).
      - The short-term moving average is trending upward over a recent lookback period.
      - The gap between the long-term and short-term moving averages is narrowing,
        with the current gap (relative to the long-term MA) within a specified threshold.
    
    Parameters:
      df (pd.DataFrame): DataFrame containing historical price data with a 'close_price' column.
      short_period (int): Number of periods for the short-term moving average (default: 50).
      long_period (int): Number of periods for the long-term moving average (default: 200).
      lookback (int): Number of recent data points (days) to evaluate trends (default: 5).
      gap_threshold (float): The maximum allowed ratio (e.g. 0.02 means 2%) of the gap between the MAs
                             relative to the long-term MA for an imminent crossover.
                             
    Returns:
      bool: True if the stock shows signs that a golden cross is imminent, False otherwise.
    """
    # Ensure there are enough data points to compute both MAs
    if len(df) < long_period:
        print(f"Insufficient data: need at least {long_period} data points.")
        return False

    # Create a copy of the DataFrame to avoid modifying the original data
    df = df.copy()
    
    # Calculate moving averages for closing prices
    df['ma_short'] = df['close_price'].rolling(window=short_period).mean()
    df['ma_long'] = df['close_price'].rolling(window=long_period).mean()
    
    # Get the latest (most recent) moving average values
    latest = df.iloc[-1]
    current_ma_short = latest['ma_short']
    current_ma_long = latest['ma_long']
    
    # If the golden cross has already occurred, return False
    if current_ma_short >= current_ma_long:
        return False

    # Drop rows with NaN values (which occur until enough data points are available)
    df_clean = df.dropna(subset=['ma_short', 'ma_long'])
    
    # Ensure we have enough data points for the lookback period
    if len(df_clean) < lookback:
        print("Insufficient clean data in the lookback period.")
        return False

    # Extract the most recent 'lookback' period for analysis
    recent_data = df_clean.tail(lookback)
    
    # Compute the slope (rate of change) of the short-term moving average over the lookback period.
    recent_ma_short = recent_data['ma_short']
    slope_short = (recent_ma_short.iloc[-1] - recent_ma_short.iloc[0]) / lookback

    # Compute the gap between long-term and short-term MAs over the lookback period.
    recent_gap = recent_data['ma_long'] - recent_data['ma_short']
    # A negative slope in the gap indicates that the gap is narrowing.
    gap_slope = (recent_gap.iloc[-1] - recent_gap.iloc[0]) / lookback
    
    # Calculate the current gap ratio relative to the long-term MA.
    current_gap_ratio = (current_ma_long - current_ma_short) / current_ma_long
    
    # Print debug information (optional)
    print(f"Current MA Short: {current_ma_short:.2f}, Current MA Long: {current_ma_long:.2f}")
    print(f"Slope of MA Short over last {lookback} periods: {slope_short:.4f}")
    print(f"Gap slope over last {lookback} periods: {gap_slope:.4f}")
    print(f"Current gap ratio: {current_gap_ratio:.4f}")

    # Conditions for an imminent golden cross:
    # 1. Short-term MA is trending upward.
    # 2. The gap between long-term and short-term MA is narrowing (negative gap slope).
    # 3. The current gap is small (within the threshold).
    if slope_short > 0 and gap_slope < 0 and current_gap_ratio <= gap_threshold:
        return True
    else:
        return False






# -------------------- Extended Stock Analysis --------------------
def analyze_stock_full(symbol):
    """
    Analyze a stock and return a dictionary with the following fields:
      - symbol
      - last_trade_price, ma_short, ma_long, rsi
      - basic_ma_rsi_criteria: True if last_trade_price > ma_short > ma_long and rsi < 70.
      - bullish_macd: True if a bullish MACD crossover is detected.
      - bollinger_bounce: True if a bounce off the lower Bollinger Band is detected.
      - volume_spike: True if a volume spike is detected.
      - bullish_engulfing: True if a bullish engulfing pattern is detected.
      - bullish_hammer: True if a bullish hammer pattern is detected.
    """
    data = {"symbol": symbol}
    
    quote = get_quote(symbol)
    if quote is None:
        print(f"Skipping {symbol} due to missing quote data.")
        return None
    try:
        last_trade_price = float(quote.get('last_trade_price', 0))
    except Exception as e:
        print(f"Error parsing last trade price for {symbol}: {e}")
        return None
    data["last_trade_price"] = last_trade_price

    df = get_historicals(symbol, interval="5minute", span="day", bounds="regular")
    if df is None or df.empty:
        print(f"Skipping {symbol} due to missing historical data.")
        return None

    # Compute moving averages and RSI on closing prices.
    df['ma_short'] = compute_moving_average(df['close_price'], period=10)
    df['ma_long'] = compute_moving_average(df['close_price'], period=50)
    df['rsi'] = compute_rsi(df['close_price'], period=14)
    latest = df.iloc[-1]
    ma_short = latest['ma_short']
    ma_long = latest['ma_long']
    rsi = latest['rsi']
    data["ma_short"] = ma_short
    data["ma_long"] = ma_long
    data["rsi"] = rsi

    # Basic criteria: Price above MA10, MA10 above MA50, RSI under 70.
    data["basic_ma_rsi_criteria"] = (last_trade_price > ma_short and ma_short > ma_long and rsi < 70)
    data["bullish_macd"] = check_bullish_macd(df['close_price'])
    data["bollinger_bounce"] = check_bollinger_bounce(df)
    data["volume_spike"] = check_volume_spike(df)
    data["bullish_engulfing"] = detect_bullish_engulfing(df)
    data["bullish_hammer"] = detect_bullish_hammer(df)

    return data

# -------------------- Watchlist Retrieval --------------------
def get_watchlist_stocks(watchlist_name):
    """
    Retrieve a list of stock symbols from a watchlist in your Robinhood account.
    This example assumes that the robin_stocks library provides a function to get all watchlists.
    Adjust according to your version of the API.
    """
    try:
        watchlists = r.account.get_all_watchlists()
        #print(json.dumps(watchlists, indent=3))
        for wl in watchlists["results"]:
            # Adjust key names as needed; here we assume a 'display_name' field.
            print(json.dumps(wl,indent=3))
            if wl.get('display_name', '').lower() == watchlist_name.lower():
                # Assume the watchlist has a 'symbols' key with a list of stock symbols.
                symbols = wl.get('symbols', [])
                print(f"Found watchlist '{watchlist_name}' with {len(symbols)} symbols.")
                return symbols
        print(f"Watchlist '{watchlist_name}' not found.")
        return []
    except Exception as e:
        print(f"Error retrieving watchlist '{watchlist_name}': {e}")
        return []

def get_top_movers(info=None):
    """
    Fetch and return the top movers data from Robinhood's markets API.
    
    :param info: Optional parameter to specify the type of information. Defaults to None.
    :return: A List of symbols of the top 20 movers in the market today.
    """
    try:
        top_movers_data = r.markets.get_top_movers(info=info)
        top_movers_symbols = []
        for symbol in top_movers_data:
            ticker = symbol["symbol"]
            print(f"Ticker - {ticker}")
            top_movers_symbols.append(ticker)
            return top_movers_symbols
    except Exception as e:
        print(f"Error fetching top movers: {e}")
        return None


# -------------------- Main Function --------------------
def analyze_top_movers():
   
    # Retrieve the watchlist 'xstonks'
    #watchlist_name = "xstonks"
    #symbols = get_watchlist_stocks(watchlist_name)
    print(json.dumps(get_top_movers(), indent=3))
    top_movers_symbols = []
    top_movers = get_top_movers()
    for symbol in top_movers:
        ticker = symbol["symbol"]
        top_movers_symbols.append(ticker)
    symbols = top_movers_symbols

    # If no symbols are found, exit.
    if not symbols:
        print("No symbols. Exiting.")
        return

    # List to store results for each stock.
    results = []
    for symbol in symbols:
        print(f"\nProcessing {symbol}...")
        stock_data = analyze_stock_full(symbol)
        if stock_data:
            results.append(stock_data)
        # Optional: add a short sleep to avoid rate limiting.
        time.sleep(0.5)

    # Create a DataFrame from the results.
    if results:
        df_results = pd.DataFrame(results)
        # Optionally, re-order the columns.
        cols_order = [
            "symbol", "last_trade_price", "ma_short", "ma_long", "rsi",
            "basic_ma_rsi_criteria", "bullish_macd", "bollinger_bounce",
            "volume_spike", "bullish_engulfing", "bullish_hammer"
        ]
        df_results = df_results[cols_order]
        print("\nAnalysis Results:")
        print(df_results)
    else:
        print("No valid stock data was gathered.")


def main():
     # Credentials: Use environment variables or a secure method in production.
    USERNAME = str(os.getenv("ROBINHOOD_USER"))
    PASSWORD = str(os.getenv("ROBINHOOD_PASS"))
    
    # Log into Robinhood.
    login_to_robinhood(USERNAME, PASSWORD, mfa=True)
    
    top_mover_symbols = get_top_movers()
    print(f"Analyzing {top_mover_symbols}...")
    historical_dfs = generate_historical_dataframes(top_mover_symbols)

    for key, val in historical_dfs.items():
        print(f"\n{key} historical data:")
        print(val.head())
        print(f"Checking for imminent golden cross for {key}...")
        
        if is_golden_cross_imminent(val):
            print("{key} is showing signs that a golden cross is imminent.")
        else:
            print("No imminent golden cross signal detected.")
        
    result = is_golden_cross_imminent
if __name__ == "__main__":
    main()
