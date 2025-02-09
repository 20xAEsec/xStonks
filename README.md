# CryptoAI Telegram

This project demonstrates how to combine technical analysis with machine learning to generate buy and sell signals for stocks. It downloads historical stock data, calculates technical indicators, generates trading signals, trains a machine learning model, and uses SHAP to explain model predictions. Although the repository is named **CryptoAI Telegram**, the code currently focuses on stock signal generation and model interpretability.

## Features

- **Historical Data Acquisition**:  
  Uses [yfinance](https://pypi.org/project/yfinance/) to download daily historical data for a list of stock symbols (e.g., AAPL, MSFT, GOOG) for a specified date range.

- **Technical Indicator Computation**:  
  Calculates several key technical indicators using [TA-Lib](https://mrjbq7.github.io/ta-lib/):
  - **SMA50 & SMA200**: 50-day and 200-day Simple Moving Averages.
  - **RSI**: 14-day Relative Strength Index.
  - **MACD**: Moving Average Convergence Divergence and its signal line.

- **Signal Generation**:  
  Generates buy and sell signals based on technical criteria:
  - **Buy Signal**: When the 50-day SMA is above the 200-day SMA and RSI is below 30.
  - **Sell Signal**: When the 50-day SMA is below the 200-day SMA and RSI is above 70.

- **Machine Learning Integration**:  
  Trains an [XGBoost](https://xgboost.readthedocs.io/) classifier using selected technical indicators as features to predict buy signals (binary classification). The model is trained on data (e.g., from AAPL) split into training and testing sets.

- **Model Explainability**:  
  Uses [SHAP](https://shap.readthedocs.io/) to:
  - Generate a SHAP summary plot that visualizes feature importance.
  - Provide a daily signal explanation with a SHAP force plot, helping you understand the model’s decision-making process.

- **Extensible Design**:  
  The code structure allows for easy extension. You can add more stocks, adjust technical indicator parameters, or integrate additional models and data sources (for example, to send trading signals via Telegram).

## Prerequisites

Ensure you have Python 3 installed. You will also need to install the following libraries:

```bash
pip install yfinance pandas ta-lib xgboost scikit-learn shap
