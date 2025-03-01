import os
from openai import OpenAI
from dotenv import load_dotenv
import re
import json
from telegram import Update
import asyncio
import threading
from typing import AsyncGenerator
from telegram.ext import ConversationHandler
from xstonks import generate_historical_dataframes, bullish_stock_check_data

# Load environment variables
load_dotenv()

SELECTING_ACTION, WAITING_FOR_COMPANY = range(2)


# Initialize OpenAI client
openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special_chars = r'\_*[]()~`>#+-=|{}.!'
    pattern = f"([{re.escape(special_chars)}])"
    return re.sub(pattern, r"\\\1", text)

def stream_chatgpt_response_sync(prompt_list, system_prompt):
    """Synchronous generator for OpenAI streaming response."""
    messages = []
    if system_prompt:
        messages.append({"role": "user", "content": f"This should be treated as the system prompt - : {system_prompt}"})
    for prompt in prompt_list:
        messages.append({"role": "user", "content": prompt})

    response = openai_client.chat.completions.create(
        model="o3-mini",
        messages=messages,
        stream=True,
    )

    for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content

async def stream_chatgpt_response(prompt_list: list, system_prompt: str) -> AsyncGenerator[str, None]:
    """Async generator to stream ChatGPT responses."""
    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def worker():
        """Worker thread to run the synchronous generator and feed the queue."""
        for chunk in stream_chatgpt_response_sync(prompt_list, system_prompt):
            loop.call_soon_threadsafe(queue.put_nowait, chunk)
        loop.call_soon_threadsafe(queue.put_nowait, None)  # Signal end of stream

    thread = threading.Thread(target=worker)
    thread.start()

    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        yield chunk

async def bullish_check_gpt(update: Update) -> AsyncGenerator[str, None]:
    """Perform bullish check using ChatGPT, yielding escaped chunks."""
    message = update.message.text
    stock_ticker = await get_stock_ticker(update)
    
    if stock_ticker:
        await update.message.reply_text(f"Stock Ticker found: {stock_ticker}\nChecking for bullish indicators...")
        bullish_check_result = await bullish_stock_check_data(stock_ticker)
        
        if bullish_check_result:
            system_prompt = """
            I will provide you with a JSON containing the results of a stock analysis, that looks for bullish indicators, marking them as True if found and False if not found.
            The JSON will contain the following fields:
                - symbol,
                - last_trade_price,
                - ma_short,
                - ma_long,
                - rsi,
                - basic_ma_rsi_criteria: True if last_trade_price > ma_short > ma_long and rsi < 70.
                - bullish_macd: True if a bullish MACD crossover is detected.
                - bollinger_bounce: True if a bounce off the lower Bollinger Band is detected.
                - volume_spike: True if a volume spike is detected.
                - bullish_engulfing: True if a bullish engulfing pattern is detected.
                - bullish_hammer: True if a bullish hammer pattern is detected.
                 
            Analyze the JSON in the next prompt for this information, and use it to provide me with a concise, well-formatted analysis 
            that determines a confidence score for how likely the stock is to experience positive price action in the short term.
            Provide the results of your analysis in a clean and logical formatting.
            """
            user_prompt = f"""
            Here is the JSON containing the analysis results. With it, provide your analysis in accordance with the provided instructions.
            {json.dumps(bullish_check_result)}
            """
            async for chunk in stream_chatgpt_response([user_prompt], system_prompt):
                yield chunk
        else:
            await update.message.reply_text(f"Could not analyze bullish indicators for {stock_ticker}")


async def get_stock_ticker(update: Update) -> str:
    """Extract stock ticker from user input using ChatGPT."""
    message = update.message.text.strip()
    system_prompt = """
    Your task is to extract a valid stock ticker from the following message:
    - Analyze the message and identify the company name or ticker symbol.
    - Format your response as "Ticker: <ticker>".
    - Reply with "No Ticker Found" if no valid ticker is detected.
    """
    user_prompt = message

    chunks = []
    async for chunk in stream_chatgpt_response([user_prompt], system_prompt):
        chunks.append(chunk)

    full_response = ''.join(chunks)

    if "No Ticker Found" in full_response:
        await update.message.reply_text("No stock ticker found. Please try again.")
        return None

    try:
        stock_ticker = full_response.split("Ticker: ")[1].strip()
        await update.message.reply_text(f"Extracted ticker: `{stock_ticker}`")
        return stock_ticker
    except IndexError:
        await update.message.reply_text("Unable to parse the stock ticker.")
        return None

async def gpt_stock_analysis(update: Update) -> AsyncGenerator[str, None]:
    """Perform stock analysis using ChatGPT, yielding chunks."""
    message = update.message.text.strip()
    
    # Extract ticker
    system_prompt_ticker = """
    Your task is to extract a valid stock ticker from the following message:
    - Analyze the message and identify the company name or ticker symbol.
    - Format your response as "Ticker: <ticker>".
    - Reply with "No Ticker Found" if no valid ticker is detected.
    """
    user_prompt = message

    chunks = []
    async for chunk in stream_chatgpt_response([user_prompt], system_prompt_ticker):
        chunks.append(chunk)
    
    full_response = ''.join(chunks)
    if "No Ticker Found" in full_response:
        await update.message.reply_text("No stock ticker found. Please try again.")
        return
    try:
        stock_ticker = full_response.split("Ticker: ")[1].strip()
        await update.message.reply_text(f"Extracted ticker: `\*{stock_ticker}\*`", parse_mode='MarkdownV2')
    except IndexError:
        await update.message.reply_text("Unable to parse the stock ticker.")
        return

    # Fetch historical data
    stock_df = await generate_historical_dataframes(stock_ticker)
    if stock_df is None:
        await update.message.reply_text("No historical data found.")
        return
    csv_data = stock_df.to_csv(index=False)

    # Stream analysis
    system_prompt_analysis = """
    You are an expert financial analyst. Using the 1 year of stock price data provided, perform a technical analysis, determining candlestick patterns and using indicators such as the RSI, moving averages (50 day, 200 day, etc)
    to determine wether positive price action is expected in the short to medium term.
    Your response should be cleanly formatted, and easy on the eyes to read, with as little special characters and unnecessary information as possible.
    Be sure to only include the most important information, written in a manner that provides the topic and the result of your analysis on the topic.
    """
    user_prompt_analysis = f"Analyze the 1-year stock performance for {stock_ticker}:\n{csv_data}"
    async for chunk in stream_chatgpt_response([user_prompt_analysis], system_prompt_analysis):
        yield chunk

async def company_input(update: Update, context) -> str:
    """Handle company input for stock analysis."""
    try:
        stock_ticker = await get_stock_ticker(update)
        if not stock_ticker:
            return ConversationHandler.END

        message = await update.message.reply_text("Analyzing 1 Year Stock Data")

        # Placeholder for actual stock data analysis
        # For now, we'll simulate it with ChatGPT
        system_prompt = "You are a financial analyst. Provide a 1-year stock analysis for the given ticker."
        user_prompt = f"Analyze the 1-year stock performance for {stock_ticker}."

        chunks = []
        async for chunk in stream_chatgpt_response([user_prompt], system_prompt):
            chunks.append(chunk)
            await message.edit_text(f"\_Analysis\_\:\n{''.join(chunks)}")

        return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text("An error occurred. Please try again later.")
        print(f"Error in company_input: {e}")
        return ConversationHandler.END