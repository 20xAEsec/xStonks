import os
from openai import OpenAI
import json
import stock_info

from dotenv import load_dotenv
load_dotenv()

from typing import Optional

gpt_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),  # This is the default and can be omitted
)
# # Input list of prompts to provide to ChatGPT
# # Return - responses to prompts, from ChatGPT
# #async def call_chatgpt(prompt_list: str, contains_instructions: bool) -> str:
#     """
#     Asynchronously calls ChatGPT using the new OpenAI API interface.
#     Returns ChatGPT's response text.

#     """
#     prompt_messages = []
#     # if contains_messages is true
#     # add the system prompt as first prompt in list
#     if contains_instructions and len(prompt_list) > 1:
#         prompt_messages.append({
#             "role": "system",
#             "content": prompt_list[0],
#         })
#         for prompt in prompt_list[1:]:
#             prompt_messages.append({
#                 "role": "user",
#                 "content": prompt,
#             })
#     else:
#         # If no system prompt is provided, add all prompts as user messages
#         for prompt in prompt_list:
#             prompt_messages.append({
#                 "role": "user",
#                 "content": prompt,
#             })

#     chat_completion =  gpt_client.chat.completions.create(messages=prompt_messages, model="gpt-3.5-turbo",)
    
#     # Return the assistant's reply
#     return chat_completion.choices[0].message.content


# Input list of prompts to provide to ChatGPT
# Return - responses to prompts, from ChatGPT
async def call_chatgpt(prompt_list: str, system_prompt:Optional[str] = None):
    """
    Asynchronously calls ChatGPT using the new OpenAI API interface.
    Returns ChatGPT's response text.

    """
    prompt_messages = []
    # if contains_messages is true
    # add the system prompt as first prompt in list
    if system_prompt == None:
        # If no system prompt is provided, add all prompts as user messages
        for prompt in prompt_list:
            prompt_messages.append({
                "role": "user",
                "content": prompt,
            })
    else:
        # attach system prompt
        prompt_messages.append({
            "role": "system",
            "content": system_prompt,
        })
        # attach user prompts
        for prompt in prompt_list:
            prompt_messages.append({
                "role": "user",
                "content": prompt,
            })

    chat_completion =  gpt_client.chat.completions.create(messages=prompt_messages, model="gpt-3.5-turbo",)
    
    # Return the assistant's reply
    return chat_completion.choices[0].message.content


# Queries ChatGPT to determine if a publicly-traded company is mentioned in the message
# If so, returns 
async def get_stock_ticker(message: str) -> str:
    prompt_list = []
    stock_ticker_retrieval_prompt = (
            """
            Do not respond to this first message. Use the instructions I provide here to analyze the message I will provide in the next prompt.
            Analyze the message and determine there is a publicly-traded company mentioned. If so, provide me with the stock ticker for the companyin the following format:
            
            Ticker: <insert_ticker_here>

            Replace <insert_ticker_here> with your determination for the stock ticker.
            Your response should strictly follow the provided format.
            If there is no publicly-traded company mentioned in the message, respond only with "No Ticker Found" and do not provide any other information.
            The message to analyze for this information will be provided in the next prompt.
            
            """
    )
    
    prompt_list.append(message)

    # Call ChatGPT with the prompt
    ticker_response = await call_chatgpt(prompt_list, system_prompt=stock_ticker_retrieval_prompt)

    # Check if the response contains "No Ticker Found"
    if "No Ticker Found" in ticker_response:
        return False
    # extract the token name and platform from the response
    stock_ticker = ticker_response.split("Ticker: ")[1]

    print(f"Extracted ticker - {stock_ticker}")
    return stock_ticker
# provide a dataframe as input to this function


async def gpt_stock_analysis(message: str) -> str:
    stock_ticker = await get_stock_ticker(message) # looks for ticker in message
    if stock_ticker != False:
        print(f"Performing analysis of stock ticker {stock_ticker}")
        stock_df = await stock_info.generate_historical_dataframes(stock_ticker)

        stock_info_csv = stock_df.to_csv(index=False)
        
    
        prompt_list = []
        system_prompt = """"
        You are a financial market data analyst with deep expertise in technical analysis and candlestick chart patterns. When provided with a dataframe containing historical price data for a stock ticker, perform an in-depth analysis by doing the following:

        1. **Technical Indicator Analysis**: 
        - Identify key bullish and bearish technical indicators (e.g., Moving Averages, RSI, MACD, Bollinger Bands).
        - Explain the significance of each indicator and how it relates to potential future price movements.

        2. **Candlestick Analysis**: 
        - Analyze the candlestick patterns present in the data, including patterns such as doji, hammer, engulfing, and others.
        - Discuss what these patterns indicate about market sentiment and price trends.

        3. **Future Price Predictions**:
        - Use the identified indicators and patterns to predict possible future price movements.
        - Provide a reasoned explanation for your predictions, noting any assumptions or relevant trends in the data.

        4. **Data-Driven Insights**:
        - Ensure your analysis is thorough, data-driven, and clearly explained.
        - Include any relevant calculations or statistical observations that support your conclusions.
            """

        full_prompt = f"""
        The following is a dataframe containing historical price data for the stock ticker {stock_ticker}:
        {stock_info_csv}
        """
        prompt_list.append(full_prompt)

        stock_analysis_response = await call_chatgpt(prompt_list, system_prompt=system_prompt)

        return stock_analysis_response
    else:
        print(f"Unable to find stock ticker in message: {message}")
        return False
