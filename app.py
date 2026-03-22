# TraderBot — Telegram Edition
# Messaging layer swapped from Twilio WhatsApp → Telegram
# All business logic in bot/ folder remains unchanged
# Built by Samuel Oyedokun

import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ── Your existing bot modules (unchanged) ──
from bot.message_handler import handle_message as process_message
from bot.db import get_or_create_user

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Quick-action keyboard
KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("📊 Today Summary"), KeyboardButton("📦 My Stock")],
    [KeyboardButton("📋 Who Owe Me"),    KeyboardButton("🏆 Top Products")],
    [KeyboardButton("📈 Sales Chart"),   KeyboardButton("❓ Help")],
], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Use phone-like ID for Supabase compatibility with existing schema
    phone = f"tg_{user.id}"
    get_or_create_user(phone)

    welcome = (
        f"👋 Welcome to SOT TraderBot, {user.first_name}!\n\n"
        "I be your AI business assistant. I go help you:\n"
        "✅ Record sales & stock\n"
        "✅ Track who owe you money\n"
        "✅ Daily/weekly summaries\n"
        "✅ Top products & customers\n"
        "✅ Sales charts\n\n"
        "Just talk to me naturally — Pidgin or English!\n\n"
        "*Example:*\n"
        "• I sell 5 bags rice 45k each\n"
        "• Biodun take 2 bags rice, go pay Friday\n"
        "• My profit today\n"
        "• Show my stock"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=KEYBOARD)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    phone = f"tg_{user.id}"
    text = update.message.text

    # Map keyboard buttons to natural language
    button_map = {
        "📊 Today Summary":  "my profit today",
        "📦 My Stock":        "show my stock",
        "📋 Who Owe Me":      "who owe me money",
        "🏆 Top Products":    "show top products",
        "📈 Sales Chart":     "sales chart",
        "❓ Help":             "help",
    }
    message = button_map.get(text, text)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        # Pass to your existing message handler — unchanged
        reply = process_message(phone, message)

        if isinstance(reply, dict) and reply.get("type") == "image":
            # Handle chart images from charts.py
            await update.message.reply_photo(
                photo=reply["data"],
                caption=reply.get("caption", ""),
                reply_markup=KEYBOARD
            )
        else:
            reply_text = str(reply) if reply else "I no understand. Try again or type *help*."
            await update.message.reply_text(
                reply_text,
                parse_mode="Markdown",
                reply_markup=KEYBOARD
            )
    except Exception as e:
        logger.error(f"Handler error: {e}")
        await update.message.reply_text(
            "Something go wrong. Try again.",
            reply_markup=KEYBOARD
        )

def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN not set in environment variables!")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("🤖 SOT TraderBot (Telegram) is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
