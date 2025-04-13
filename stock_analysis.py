import pandas as pd

# WORK IN PROGRESS; abandoned in favor of analysis by LLM

# Function to add technical indicators to each stock's DataFrame
def add_indicators(df):
    df['SMA50'] = ta.SMA(df['Close'], timeperiod=50)
    df['SMA200'] = ta.SMA(df['Close'], timeperiod=200)
    df['RSI'] = ta.RSI(df['Close'], timeperiod=14)
    df['MACD'], df['MACD_signal'], _ = ta.MACD(df['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
    return df

# Function to generate buy/sell signals
# If 50Day Noving Average is above 200Day Moving Average; and RSI reflects that stock is oversold; Bullish Indicator = BUY
# If 50Day Noving Average is below 200Day Moving Average; and RSI reflects that stock is overbought; Bearish Indicator = SELL


def generate_signals(df):
    df['Buy_Signal'] = ((df['SMA50'] > df['SMA200']) & (df['RSI'] < 30))
    df['Sell_Signal'] = ((df['SMA50'] < df['SMA200']) & (df['RSI'] > 70))
    return df
