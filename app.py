# TraderBot — AI Telegram Business Assistant
# Built by Samuel Oyedokun
# Stack: Python · python-telegram-bot · Groq AI · Supabase · Render

import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import requests
from supabase import create_client, Client

# ── LOGGING ──
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── CONFIG ──
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
SUPABASE_URL   = os.getenv("SUPABASE_URL")
SUPABASE_KEY   = os.getenv("SUPABASE_KEY")

# Init Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ════════════════════════════════════════════════
# ── DATABASE HELPERS ──
# ════════════════════════════════════════════════

def get_or_create_trader(telegram_id: int, name: str) -> dict:
    """Get existing trader or create new one"""
    result = supabase.table("traders").select("*").eq("telegram_id", str(telegram_id)).execute()
    if result.data:
        return result.data[0]
    new_trader = {
        "telegram_id": str(telegram_id),
        "name": name,
        "balance": 0.0,
        "created_at": datetime.now().isoformat()
    }
    result = supabase.table("traders").insert(new_trader).execute()
    return result.data[0]

def record_sale(trader_id: str, product: str, qty: float, price: float, amount: float) -> dict:
    """Record a sale transaction"""
    sale = {
        "trader_id": trader_id,
        "product": product,
        "quantity": qty,
        "unit_price": price,
        "amount": amount,
        "type": "sale",
        "created_at": datetime.now().isoformat()
    }
    result = supabase.table("transactions").insert(sale).execute()
    # Update trader balance
    supabase.table("traders").update({"balance": trader_id}).eq("id", trader_id).execute()
    return result.data[0] if result.data else sale

def record_expense(trader_id: str, description: str, amount: float) -> dict:
    """Record an expense"""
    expense = {
        "trader_id": trader_id,
        "product": description,
        "quantity": 1,
        "unit_price": amount,
        "amount": amount,
        "type": "expense",
        "created_at": datetime.now().isoformat()
    }
    result = supabase.table("transactions").insert(expense).execute()
    return result.data[0] if result.data else expense

def record_debt(trader_id: str, customer: str, amount: float, description: str) -> dict:
    """Record a debt owed to trader"""
    debt = {
        "trader_id": trader_id,
        "customer_name": customer,
        "amount": amount,
        "description": description,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    result = supabase.table("debts").insert(debt).execute()
    return result.data[0] if result.data else debt

def get_summary(trader_id: str) -> dict:
    """Get trader's business summary"""
    txns = supabase.table("transactions").select("*").eq("trader_id", trader_id).execute()
    debts = supabase.table("debts").select("*").eq("trader_id", trader_id).eq("status", "pending").execute()

    sales    = [t for t in (txns.data or []) if t["type"] == "sale"]
    expenses = [t for t in (txns.data or []) if t["type"] == "expense"]

    total_sales    = sum(t["amount"] for t in sales)
    total_expenses = sum(t["amount"] for t in expenses)
    total_debts    = sum(d["amount"] for d in (debts.data or []))

    # Today's numbers
    today = datetime.now().date().isoformat()
    today_sales = [t for t in sales if t["created_at"][:10] == today]
    today_sales_total = sum(t["amount"] for t in today_sales)

    return {
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "profit": total_sales - total_expenses,
        "pending_debts": total_debts,
        "today_sales": today_sales_total,
        "debt_count": len(debts.data or []),
        "transactions_count": len(txns.data or [])
    }

# ════════════════════════════════════════════════
# ── AI BRAIN ──
# ════════════════════════════════════════════════

SYSTEM_PROMPT = """You are SOT TraderBot — an AI business assistant for Nigerian market traders.
You help traders manage their daily business through simple conversation.

You understand:
- Nigerian Pidgin English (e.g. "I sell rice 5k", "customer owe me 2000")
- Naira amounts written as "2k" = ₦2,000, "50k" = ₦50,000
- Common market products (rice, beans, garri, tomatoes, palm oil, pepper, etc.)

Your capabilities:
1. Record sales — detect when trader mentions selling something
2. Record expenses — detect when trader mentions buying stock or paying costs
3. Record debts — detect when a customer owes money
4. Show business summary — when asked for report, summary, or "how e dey"
5. Track stock levels (basic)
6. Answer business questions

When extracting data from messages, respond in this JSON format for actions:
{
  "action": "sale|expense|debt|summary|greeting|unknown",
  "product": "product name",
  "quantity": number,
  "unit_price": number,
  "amount": number,
  "customer": "customer name if debt",
  "message": "friendly response in trader's language"
}

If you can't determine an action clearly, ask for clarification.
Always respond warmly and in a mix of English and Pidgin that matches the trader's tone.
Use ₦ for Naira amounts. Keep responses concise."""

def ask_groq(user_message: str, context: str = "") -> dict:
    """Send message to Groq AI and parse response"""
    if not GROQ_API_KEY:
        return {"action": "unknown", "message": "AI not configured. Add GROQ_API_KEY."}
    try:
        full_prompt = f"{context}\n\nTrader message: {user_message}" if context else user_message
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 500,
                "temperature": 0.3,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt}
                ]
            },
            timeout=15
        )
        content = response.json()["choices"][0]["message"]["content"].strip()
        # Try to parse as JSON
        import json, re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"action": "unknown", "message": content}
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return {"action": "unknown", "message": "Sorry, I dey process your message. Try again."}

# ════════════════════════════════════════════════
# ── TELEGRAM HANDLERS ──
# ════════════════════════════════════════════════

MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("📊 My Summary"), KeyboardButton("💰 Record Sale")],
    [KeyboardButton("🛒 Record Expense"), KeyboardButton("📋 Debts Owed")],
    [KeyboardButton("❓ Help"), KeyboardButton("📈 Today's Sales")]
], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    trader = get_or_create_trader(user.id, user.first_name)

    welcome = f"""🤖 *Welcome to SOT TraderBot!*

I be your AI business assistant for your daily trading.

I go help you:
✅ Record your sales
✅ Track your expenses  
✅ Remember who owe you money
✅ Give you daily business summary

Just talk to me naturally — you fit use Pidgin or English!

*Example messages:*
• "I sell 5 bags rice at 45k each"
• "Customer Emma owe me 15,000"
• "I buy stock for 30k"
• "Show me my summary"

*Press any button below or just type to start!*"""

    await update.message.reply_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """📖 *SOT TraderBot Help*

*How to record a sale:*
Just tell me what you sold:
• "Sold 10kg tomatoes for 5000"
• "I sell rice 3 bags, 45k per bag"
• "Customer buy pepper 2000"

*How to record an expense:*
Tell me what you spent:
• "I buy new stock 50k"
• "Paid for transport 2000"
• "Spent 15k on bags"

*How to record a debt:*
Tell me who owes you:
• "Mama Ngozi owe me 10k for rice"
• "Customer Emeka dey owe 25,000"

*How to see your summary:*
Ask for a report:
• "Show my summary"
• "How e dey?"
• "My daily report"
• Press 📊 My Summary button

*Commands:*
/start - Start the bot
/help - Show this help
/summary - See your business summary
/debts - See pending debts
/clear - Clear today's data"""

    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show business summary"""
    user = update.effective_user
    trader = get_or_create_trader(user.id, user.first_name)
    data = get_summary(trader["id"])

    summary_text = f"""📊 *Your Business Summary*

💰 *Total Sales:* ₦{data['total_sales']:,.2f}
🛒 *Total Expenses:* ₦{data['total_expenses']:,.2f}
📈 *Net Profit:* ₦{data['profit']:,.2f}
📅 *Today's Sales:* ₦{data['today_sales']:,.2f}

⚠️ *Pending Debts:* ₦{data['pending_debts']:,.2f} ({data['debt_count']} customers)
📋 *Total Transactions:* {data['transactions_count']}

_{datetime.now().strftime('%d %B %Y, %H:%M')}_"""

    await update.message.reply_text(summary_text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)

async def debts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending debts"""
    user = update.effective_user
    trader = get_or_create_trader(user.id, user.first_name)
    debts = supabase.table("debts").select("*").eq("trader_id", trader["id"]).eq("status", "pending").execute()

    if not debts.data:
        await update.message.reply_text(
            "✅ Nobody owe you money right now! E good!",
            reply_markup=MAIN_KEYBOARD
        )
        return

    debt_lines = "\n".join([
        f"• *{d['customer_name']}* — ₦{d['amount']:,.2f} ({d.get('description', 'debt')})"
        for d in debts.data
    ])
    total = sum(d["amount"] for d in debts.data)

    await update.message.reply_text(
        f"📋 *Pending Debts*\n\n{debt_lines}\n\n*Total Owed: ₦{total:,.2f}*",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all regular messages through AI"""
    user = update.effective_user
    text = update.message.text

    # Handle keyboard buttons
    if text == "📊 My Summary":
        await summary_command(update, context)
        return
    elif text == "📋 Debts Owed":
        await debts_command(update, context)
        return
    elif text == "❓ Help":
        await help_command(update, context)
        return
    elif text == "📈 Today's Sales":
        trader = get_or_create_trader(user.id, user.first_name)
        data = get_summary(trader["id"])
        await update.message.reply_text(
            f"📈 *Today's Sales*\n\n₦{data['today_sales']:,.2f}\n\n_{datetime.now().strftime('%d %B %Y')}_",
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD
        )
        return
    elif text == "💰 Record Sale":
        await update.message.reply_text(
            "💰 Tell me what you sold!\n\nExample:\n• 'I sell 5 bags rice at 45k each'\n• 'Sold tomatoes 3000'",
            reply_markup=MAIN_KEYBOARD
        )
        return
    elif text == "🛒 Record Expense":
        await update.message.reply_text(
            "🛒 Tell me what you spent!\n\nExample:\n• 'I buy stock 50k'\n• 'Paid transport 2000'",
            reply_markup=MAIN_KEYBOARD
        )
        return

    # Get trader record
    trader = get_or_create_trader(user.id, user.first_name)

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Process through AI
    result = ask_groq(text)
    action  = result.get("action", "unknown")
    message = result.get("message", "I no understand. Try again.")

    # Execute the detected action
    try:
        if action == "sale":
            amount = result.get("amount", 0) or (
                (result.get("quantity", 1) or 1) * (result.get("unit_price", 0) or 0)
            )
            if amount > 0:
                record_sale(
                    trader["id"],
                    result.get("product", "unknown"),
                    result.get("quantity", 1),
                    result.get("unit_price", amount),
                    amount
                )
                message = f"✅ *Sale recorded!*\n\n{message}\n\n_Press 📊 My Summary to see your total_"

        elif action == "expense":
            amount = result.get("amount", 0)
            if amount > 0:
                record_expense(
                    trader["id"],
                    result.get("product", "expense"),
                    amount
                )
                message = f"🛒 *Expense recorded!*\n\n{message}"

        elif action == "debt":
            amount = result.get("amount", 0)
            customer = result.get("customer", "Unknown Customer")
            if amount > 0:
                record_debt(
                    trader["id"],
                    customer,
                    amount,
                    result.get("product", "debt")
                )
                message = f"📋 *Debt recorded!*\n\n{message}\n\n_Press 📋 Debts Owed to see all debts_"

        elif action == "summary":
            await summary_command(update, context)
            return

    except Exception as e:
        logger.error(f"DB error: {e}")
        message = f"{message}\n\n_(Note: Could not save to database — check Supabase config)_"

    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)

# ════════════════════════════════════════════════
# ── MAIN ──
# ════════════════════════════════════════════════

def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN environment variable not set!")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("help",    help_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("debts",   debts_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 SOT TraderBot starting on Telegram...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
