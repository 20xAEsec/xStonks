import robin_stocks as r # robinhood API
import pyotp # library to handle MFA
from datetime import datetime 

import credentials


# If your account is configured with MFA
# set mfa=True on function invocation
def authenticate(mfa=False):
    user = credentials.USERNAME
    passw = credentials.PASSWORD

    if mfa == True:
        mfa_code = input("Enter your MFA code:")
        totp = pyotp.TOTP(mfa_code).now()
        result = r.login(user,passw , mfa_code=totp) # Login
    else:
        result = r.login(user,passw) # Login


def generate_holdings_csv():

    with open("./my_stocks.csv", "w") as my_stocks_csv: # Open CSV file
        my_stocks_csv.write("Ticker Name,Price,Quantity,Average_Buy_Price,Equity,Equity_Change,Average_Buy_Price\n") # For OpenOffice

    my_stocks = r.build_holdings() # Get Stock Data
    stock_info_line = ""

    my_stock_tickers = [] # Buffer Variables
    total_equity_change = 0 

    # Go through every stock element
    # and construct the line to be written to csv
    for key,val in my_stocks.items():
        my_stock_tickers.append(key)
        stock_name_val = val["name"]
        stock_name_val = stock_name_val.replace(" ","_" )

        total_equity_change += float(val["equity_change"]) # calculates running total for the day
        
        # For OpenOffice
        stock_info_line = key + " " + stock_name_val + " " + val["price"] + " " + val["quantity"] + " " + val["average_buy_price"] + " " + val["equity"] + " " + val["equity_change"] + " " + val["average_buy_price"] + "\n"    # For Microsoft Excel
        #stock_info_line = key + "," + val["name"] + "," + val["price"] + "," + val["quantity"] + val["average_buy_price"] + "," + val["equity"] + "," + val["equity_change"] + "," + val["average_buy_price"] + "\n"
        
        with open("./my_stocks.csv", "a") as my_stocks_csv:
            my_stocks_csv.write(stock_info_line)
            print(stock_info_line)

    #print(robin_bot.stocks.find_instrument_data("STPK"))
    #print(my_stock_tickers)


def calculate_holdings():

    profileData = r.load_portfolio_profile()
    allTransactions = r.get_bank_transfers()
    cardTransactions= r.get_card_transactions()
    #Calculate total holdings
    deposits = sum(float(x['amount']) for x in allTransactions if (x['direction'] == 'deposit') and (x['state'] == 'completed'))
    withdrawals = sum(float(x['amount']) for x in allTransactions if (x['direction'] == 'withdraw') and (x['state'] == 'completed'))
    debits = sum(float(x['amount']['amount']) for x in cardTransactions if (x['direction'] == 'debit' and (x['transaction_type'] == 'settled')))
    reversal_fees = sum(float(x['fees']) for x in allTransactions if (x['direction'] == 'deposit') and (x['state'] == 'reversed'))

    money_invested = deposits + reversal_fees - (withdrawals - debits)
    dividends = r.get_total_dividends()
    percentDividend = dividends/money_invested*100

    equity = float(profileData['extended_hours_equity'])
    print("Profile Data #####\n######")

    for key,val in profileData.items():
        print("- "+ key, " -> " + val)

    totalGainMinusDividends = equity - dividends - money_invested
    percentGain = totalGainMinusDividends/money_invested*100

    print("The total money invested is {:.2f}".format(money_invested))
    print("The total equity is {:.2f}".format(equity))
    print("The net worth has increased {:0.2}% due to dividends that amount to {:0.2f}".format(percentDividend, dividends))
    print("The net worth has increased {:0.3}% due to other gains that amount to {:0.2f}".format(percentGain, totalGainMinusDividends))
