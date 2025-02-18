# Robinhood Technical Analysis & Trading Bot

This repository contains a modular Python codebase designed to integrate with Robinhood via the `robin_stocks` library. The project is built for technical analysis and short-term trading, enabling you to retrieve market data, compute technical indicators, identify bullish signals, and even execute trades directly through Robinhood.

## Features

- **Authentication**  
  Log into your Robinhood account securely using environment variables.

- **Data Retrieval**  
  - Fetch real-time quotes for stocks.
  - Retrieve historical candlestick data for various intervals (e.g., 5-minute, daily).

- **Technical Indicator Calculations**  
  - **Moving Averages (SMA):** Compute short-term (e.g., 10/50-day) and long-term (e.g., 200-day) moving averages.
  - **RSI (Relative Strength Index):** Analyze momentum to determine overbought or oversold conditions.
  - **MACD (Moving Average Convergence Divergence):** Generate MACD, signal line, and histogram for trend analysis.
  - **Bollinger Bands:** Calculate upper, lower, and middle bands to assess volatility.

- **Bullish Signal Detection**  
  Identify various bullish indicators:
  - Bullish MACD crossovers.
  - Bollinger Band bounces.
  - Volume spikes.
  - Candlestick patterns such as bullish engulfing and hammer formations.

- **Golden Cross Analysis**  
  Check if a stock is nearing a golden cross (i.e., when a short-term moving average is about to cross above a long-term moving average) by analyzing trends and narrowing gaps.

- **DataFrame Generation**  
  Convert historical data into pandas DataFrames for further analysis, such as checking for a golden cross.

- **Trade Execution**  
  Execute market orders (buy/sell) through Robinhood’s API.

- **Watchlist Integration**  
  Retrieve stocks from a specific Robinhood watchlist (e.g., "xstonks") and analyze each for bullish setups.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/your-repo-name.git
   cd your-repo-name
