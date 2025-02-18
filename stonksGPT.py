

import logging
from html import escape
from uuid import uuid4
import os

from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, InlineQueryHandler


from gpt_actions import gpt_stock_analysis, get_stock_ticker
from stock_info import get_historicals, generate_historical_dataframes

from dotenv import load_dotenv
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text("Hi!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


# create a stock_command function that activates when the command /stock is issued
async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /stock is issued."""

    # get the stock message from the command
    stock_message = update.message.text
    if not stock_message:
        await update.message.reply_text("Provide a message on the stock ticker you'd like to analyze")
        return
    
    # if stock ticker found, run the gpt_stock_analysis function
    gpt_stock_analysis_response = await gpt_stock_analysis(stock_message)
    if gpt_stock_analysis_response:
        # send the response to the user
        await update.message.reply_text(f"Analyzing...\n\n{gpt_stock_analysis_response}")
    else:
        # if the message does not contain a stock ticker, send a message to the user
        await update.message.reply_text("No Ticker Found; Analysis can not be performed")
        


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the inline query. This is run when you type: @botusername <query>"""
    query = update.inline_query.query

    if not query:  # empty query should not be handled
        return

    results = [
        InlineQueryResultArticle(
            id=str(uuid4()),
            title="Caps",
            input_message_content=InputTextMessageContent(query.upper()),
        ),
        InlineQueryResultArticle(
            id=str(uuid4()),
            title="Bold",
            input_message_content=InputTextMessageContent(
                f"<b>{escape(query)}</b>", parse_mode=ParseMode.HTML
            ),
        ),
        InlineQueryResultArticle(
            id=str(uuid4()),
            title="Italic",
            input_message_content=InputTextMessageContent(
                f"<i>{escape(query)}</i>", parse_mode=ParseMode.HTML
            ),
        ),
    ]

    await update.inline_query.answer(results)


def main() -> None:
    """Run the bot."""

    STONK_BOT_TOKEN = os.getenv("STONK_BOT_ID")
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(STONK_BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stock", stock_command))


    # on inline queries - show corresponding inline results
    application.add_handler(InlineQueryHandler(inline_query))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()