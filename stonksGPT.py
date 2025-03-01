import os
import time
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes
)
from telegram.error import BadRequest
from dotenv import load_dotenv
from gpt_actions_kimi import (
    escape_markdown_v2,
    get_stock_ticker,
    gpt_stock_analysis,
    bullish_check_gpt
)
from xstonks import (
    generate_historical_dataframes,
    golden_cross_detector,
    analyze_top_movers,
    bullish_stock_check_data,
    login_to_robinhood
)

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define conversation states
SELECTING_ACTION, WAITING_FOR_COMPANY = range(2)

# Callback data constants
CALLBACK_START_MENU = 'start_menu'
CALLBACK_ONE_YEAR_ANALYSIS = 'one_year_analysis'
CALLBACK_BULLISH_CHECK = 'bullish_check'
CALLBACK_TOP_MOVERS = 'analyze_top_movers'

# Feature display names
FEATURE_DISPLAY_NAMES = {
    CALLBACK_START_MENU: "Start",
    CALLBACK_ONE_YEAR_ANALYSIS: "1 Year Stock Analysis",
    CALLBACK_BULLISH_CHECK: "Bullish Check",
    CALLBACK_TOP_MOVERS: "Analyze Top Movers",
}

# Main menu keyboard
main_menu_keyboard = [
    [InlineKeyboardButton(FEATURE_DISPLAY_NAMES[CALLBACK_ONE_YEAR_ANALYSIS], callback_data=CALLBACK_ONE_YEAR_ANALYSIS)],
    [InlineKeyboardButton(FEATURE_DISPLAY_NAMES[CALLBACK_BULLISH_CHECK], callback_data=CALLBACK_BULLISH_CHECK)],
    [InlineKeyboardButton(FEATURE_DISPLAY_NAMES[CALLBACK_TOP_MOVERS], callback_data=CALLBACK_TOP_MOVERS)],
]
main_menu_markup = InlineKeyboardMarkup(main_menu_keyboard)

# Start screen keyboard
start_screen_keyboard = [[InlineKeyboardButton('🚀 Start', callback_data=CALLBACK_START_MENU)]]
start_screen_markup = InlineKeyboardMarkup(start_screen_keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send the start message with a photo and start button."""
    chat_id = update.effective_chat.id
    logger.info(f"Starting bot for chat_id: {chat_id}")
    await context.bot.send_photo(
        chat_id,
        photo="https://imgur.com/a/EixnwPs",
        caption=(
            "Welcome to StonksGPT! This bot provides financial analysis using GPT-4 and financial data.\n\n"
            "[GitHub Page](https://github.com/your_username/stonksGPT)"
        ),
        reply_markup=start_screen_markup
    )
    return SELECTING_ACTION

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the main menu by editing the photo's caption and updating the reply markup."""
    query = update.callback_query
    await query.answer()
    logger.info("Showing main menu")
    await query.edit_message_media(
        media=InputMediaPhoto(media="https://imgur.com/a/EixnwPs", caption="Select an action:"),
        reply_markup=main_menu_markup
    )
    return SELECTING_ACTION

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the main menu photo with options."""
    chat_id = update.effective_chat.id
    await context.bot.send_photo(
        chat_id,
        photo="https://imgur.com/a/EixnwPs",
        caption="Select an action:",
        reply_markup=main_menu_markup
    )

async def handle_feature_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, feature: str) -> int:
    """Handle feature selection by prompting for company input."""
    query = update.callback_query
    await query.answer()
    display_name = FEATURE_DISPLAY_NAMES.get(feature, "Unknown Feature")
    logger.info(f"Handling feature selection: {feature} ({display_name})")
    await query.edit_message_caption(
        caption=f"Please enter a company name or ticker symbol for {display_name}:",
        reply_markup=None
    )
    context.user_data['selected_feature'] = feature
    return WAITING_FOR_COMPANY

async def one_year_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the '1 Year Stock Analysis' button click."""
    logger.info("1 Year Stock Analysis button clicked")
    return await handle_feature_selection(update, context, CALLBACK_ONE_YEAR_ANALYSIS)

async def bullish_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the 'Bullish Check' button click."""
    logger.info("Bullish Check button clicked")
    return await handle_feature_selection(update, context, CALLBACK_BULLISH_CHECK)

async def analyze_top_movers_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the 'Analyze Top Movers' button click."""
    query = update.callback_query
    await query.answer()
    logger.info("Analyzing top movers")
    try:
        await query.edit_message_caption(caption="Analyzing top movers...")
        analysis_results = await analyze_top_movers()
        formatted_results = format_top_movers(analysis_results)
        await query.edit_message_caption(
            caption=f"Top Movers Analysis Results:\n{formatted_results}"
        )
    except Exception as e:
        logger.error(f"Failed to analyze top movers: {e}")
        await query.message.reply_text("Something went wrong while analyzing top movers.")
    finally:
        await send_main_menu(update, context)
        return SELECTING_ACTION

def format_top_movers(df):
    """Format the top movers DataFrame into a readable MarkdownV2 string."""
    if df.empty:
        return "No top movers data available."
    result = "**Top Movers Analysis:**\n\n"
    for index, row in df.iterrows():
        result += f"**Stock: {row['symbol']}**\n"
        result += f"- Last Trade Price: ${row['last_trade_price']:.2f}\n"
        result += f"- Short MA: ${row['ma_short']:.2f}\n"
        result += f"- Long MA: ${row['ma_long']:.2f}\n"
        result += f"- RSI: {row['rsi']:.2f}\n"
        result += f"- Basic MA RSI Criteria: {'Yes' if row['basic_ma_rsi_criteria'] else 'No'}\n"
        result += f"- Bullish MACD: {'Yes' if row['bullish_macd'] else 'No'}\n"
        result += f"- Bollinger Bounce: {'Yes' if row['bollinger_bounce'] else 'No'}\n"
        result += f"- Volume Spike: {'Yes' if row['volume_spike'] else 'No'}\n"
        result += f"- Bullish Engulfing: {'Yes' if row['bullish_engulfing'] else 'No'}\n"
        result += f"- Bullish Hammer: {'Yes' if row['bullish_hammer'] else 'No'}\n\n"
    return result

async def company_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle company input with real-time streaming and message splitting."""
    company = update.message.text.strip()
    selected_feature = context.user_data.get('selected_feature')
    logger.info(f"Received company input: {company} for feature: {selected_feature}")
    message = await update.message.reply_text("Processing")
    accumulated_content = ""
    current_message = message
    last_edit_time = 0
    TELEGRAM_MAX_LENGTH = 4096

    try:
        # Select the appropriate analysis stream
        if selected_feature == CALLBACK_ONE_YEAR_ANALYSIS:
            analysis_stream = gpt_stock_analysis(update)
        elif selected_feature == CALLBACK_BULLISH_CHECK:
            analysis_stream = bullish_check_gpt(update)
        else:
            analysis_stream = None

        if analysis_stream:
            async for chunk in analysis_stream:
                if chunk:
                    # Add chunk to accumulated content
                    temp_content = accumulated_content + chunk                    

                    accumulated_content = temp_content

                    # Update message periodically (every 1 second)
                    current_time = time.time()
                    if current_time - last_edit_time >= 1:
                        try:
                            await current_message.edit_text(accumulated_content)
                            last_edit_time = current_time
                        except BadRequest as e:
                            if "Message is not modified" in str(e):
                                pass  # Ignore if content hasn't changed
                            else:
                                raise

            # Send remaining content if any
            if accumulated_content:
                if len(accumulated_content) < TELEGRAM_MAX_LENGTH:
                    await current_message.edit_text(accumulated_content)
                else:
                    # Split remaining content into multiple messages
                    while accumulated_content:
                        await current_message.edit_text(accumulated_content[:TELEGRAM_MAX_LENGTH])
                        accumulated_content = accumulated_content[TELEGRAM_MAX_LENGTH:]
                        if accumulated_content:
                            current_message = await context.bot.send_message(
                                chat_id=update.effective_chat.id,
                                text="Continuing analysis"
                            )
    except Exception as e:
        logger.error(f"Error in company_input: {e}")
        await message.edit_text(f"An error occurred: {str(e)}. Please try again later.")
    finally:
        await send_main_menu(update, context)
        return SELECTING_ACTION

def main() -> None:
    """Run the bot."""
    login_to_robinhood(os.getenv("ROBINHOOD_USER"), os.getenv("ROBINHOOD_PASS"), mfa=True)
    token = os.getenv("STONK_BOT_ID")
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(show_main_menu, pattern=f'^{CALLBACK_START_MENU}$'),
                CallbackQueryHandler(one_year_analysis, pattern=f'^{CALLBACK_ONE_YEAR_ANALYSIS}$'),
                CallbackQueryHandler(bullish_check, pattern=f'^{CALLBACK_BULLISH_CHECK}$'),
                CallbackQueryHandler(analyze_top_movers_handler, pattern=f'^{CALLBACK_TOP_MOVERS}$'),
            ],
            WAITING_FOR_COMPANY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, company_input)
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()