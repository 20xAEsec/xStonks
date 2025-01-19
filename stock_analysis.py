import yfinance as yf
import pandas as pd
import talib as ta
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
import shap

# Define stock symbols and download historical data
symbols = ['AAPL', 'MSFT', 'GOOG']  # Replace with your desired stocks
data = {}

for symbol in symbols:
    stock_data = yf.download(symbol, start="2023-01-01", end="2024-01-01", interval="1d")
    data[symbol] = stock_data

# Function to add technical indicators to each stock's DataFrame
def add_indicators(df):
    df['SMA50'] = ta.SMA(df['Close'], timeperiod=50)
    df['SMA200'] = ta.SMA(df['Close'], timeperiod=200)
    df['RSI'] = ta.RSI(df['Close'], timeperiod=14)
    df['MACD'], df['MACD_signal'], _ = ta.MACD(df['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
    return df

# Apply indicators to each stock
stock_dfs = {symbol: add_indicators(pd.DataFrame(data[symbol])) for symbol in symbols}

# Function to generate buy/sell signals
def generate_signals(df):
    df['Buy_Signal'] = ((df['SMA50'] > df['SMA200']) & (df['RSI'] < 30))
    df['Sell_Signal'] = ((df['SMA50'] < df['SMA200']) & (df['RSI'] > 70))
    return df

# Apply signal generation to each stock
for symbol in symbols:
    stock_dfs[symbol] = generate_signals(stock_dfs[symbol])

# Prepare data for model training (example with AAPL)
symbol = 'AAPL'
df = stock_dfs[symbol].dropna()  # Drop rows with NaN values from indicators

# Define features and target
X = df[['SMA50', 'SMA200', 'RSI', 'MACD', 'MACD_signal']]
y = df['Buy_Signal'].astype(int)  # Using Buy_Signal as the target

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train an XGBoost classifier
model = XGBClassifier()
model.fit(X_train, y_train)

# Explain the model predictions using SHAP
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# Plot SHAP summary for feature importance
shap.summary_plot(shap_values, X_test, plot_type="bar")

# Function to get daily buy/sell signals and explainability for each stock
def get_daily_signals(model, df):
    X = df[['SMA50', 'SMA200', 'RSI', 'MACD', 'MACD_signal']].tail(1)
    prediction = model.predict(X)
    shap_values = explainer.shap_values(X)

    if prediction == 1:
        print("Buy Signal")
    else:
        print("Sell Signal")
    
    # Display SHAP values for interpretability
    shap.force_plot(explainer.expected_value, shap_values[0], X)

# Example usage for AAPL
get_daily_signals(model, stock_dfs['AAPL'])