import pandas as pd
import numpy as np
from robin_stocks import robinhood as r

async def get_historicals(symbol, interval="5minute", span="day", bounds="regular"):
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
    


async def generate_historical_dataframes(symbol, interval="day", span="year", bounds="regular"):
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
    
    try:
        historicals = await r.stocks.get_stock_historicals(symbol, interval=interval, span=span, bounds=bounds)
        # Convert the list of dictionaries to a DataFrame
        df = pd.DataFrame(historicals)
        if df.empty:
            print(f"No historical data found for {symbol}.")

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

    except Exception as e:
        print(f"Error retrieving data for {symbol}: {e}")
    
    return df