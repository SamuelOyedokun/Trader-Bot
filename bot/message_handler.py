from bot.ai_engine import understand_message
from bot.db import (save_sale, get_daily_summary, get_weekly_summary,
                    get_monthly_summary, archive_records, save_debt,
                    get_all_debts, get_customer_debt, record_payment)
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()


def send_whatsapp_message(phone: str, message: str):
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    client.messages.create(
        from_=f"whatsapp:{os.getenv('TWILIO_WHATSAPP_NUMBER')}",
        body=message,
        to=f"whatsapp:+{phone}"
    )


def format_summary(title, summary):
    return (
        f"📊 *{title}*\n\n"
        f"💰 Revenue: ₦{summary['revenue']:,.0f}\n"
        f"📈 Profit: ₦{summary['profit']:,.0f}\n"
        f"📦 Sales recorded: {summary['count']}\n\n"
        f"Keep it up! 🚀"
    )


def handle_message(phone: str, text: str):
    if not text:
        return

    parsed = understand_message(text)
    intent = parsed.get("intent")

    # ─── RECORD SALE ─────────────────────────────────────
    if intent == "record_sale":
        items = parsed.get("items", [])
        if not items:
            send_whatsapp_message(phone,
                "I understood you made a sale but I need more details.\n\n"
                "Try: 'I sell 3 bags rice 45k, I buy am 38k'"
            )
            return

        reply_lines = ["✅ Sales recorded!\n"]
        total_profit = 0
        missing_cost = []

        for item_data in items:
            item = item_data.get("item", "item")
            qty = item_data.get("quantity", 1) or 1
            amount = item_data.get("amount")
            cost = item_data.get("cost_price")

            if amount and cost:
                profit = (amount - cost) * qty
                total_profit += profit
                save_sale(phone, item, qty, amount, cost, profit)
                reply_lines.append(
                    f"📦 {item} × {qty}\n"
                    f"   Sell: ₦{amount:,.0f} | Cost: ₦{cost:,.0f} | Profit: ₦{profit:,.0f}"
                )
            elif amount and not cost:
                missing_cost.append(item)
                save_sale(phone, item, qty, amount, 0, 0)
                reply_lines.append(f"📦 {item} × {qty} — ₦{amount:,.0f} (no cost price)")

        reply_lines.append(f"\n💰 Total Profit: ₦{total_profit:,.0f}")
        if missing_cost:
            reply_lines.append(f"⚠️ Missing cost price for: {', '.join(missing_cost)}")
        reply_lines.append("Keep it up! 💪")
        send_whatsapp_message(phone, "\n".join(reply_lines))

    # ─── ADD DEBT ─────────────────────────────────────────
    elif intent == "add_debt":
        customer = parsed.get("customer_name")
        due_date = parsed.get("due_date")

        # Get amount from top level OR from items
        amount = parsed.get("amount")
        item = "goods"
        qty = 1

        if parsed.get("items"):
            first_item = parsed["items"][0]
            item = first_item.get("item", "goods")
            qty = first_item.get("quantity", 1) or 1
            # If amount not at top level, calculate from items
            if not amount and first_item.get("amount"):
                amount = first_item["amount"] * qty

        if not customer:
            send_whatsapp_message(phone,
                "Who took the goods on credit? Tell me their name.\n\n"
                "Try: 'Seun take 2 bags rice 45k, go pay Friday'"
            )
            return

        if not amount:
            send_whatsapp_message(phone,
                f"How much does {customer} owe? I need the total amount.\n\n"
                f"Try: '{customer} take 3 bags rice 45k'"
            )
            return

        save_debt(phone, customer, item, qty, amount, due_date)
        reply = (
            f"📝 Debt recorded!\n\n"
            f"👤 Customer: {customer}\n"
            f"📦 Item: {item} × {qty}\n"
            f"💰 Amount owed: ₦{amount:,.0f}\n"
        )
        if due_date:
            reply += f"📅 Due: {due_date}\n"
        reply += "\nI will help you track this! 💪"
        send_whatsapp_message(phone, reply)

    # ─── RECORD PAYMENT ──────────────────────────────────
    elif intent == "record_payment":
        customer = parsed.get("customer_name")
        amount = parsed.get("amount")

        if not customer or not amount:
            send_whatsapp_message(phone,
                "Tell me who paid and how much.\n\n"
                "Try: 'Seun don pay 5000'"
            )
            return

        remaining, status = record_payment(phone, customer, amount)

        if status == "not_found":
            send_whatsapp_message(phone,
                f"I don't have any debt record for {customer}.\n"
                "Check the name and try again."
            )
        elif remaining == 0:
            send_whatsapp_message(phone,
                f"✅ {customer} don clear everything!\n\n"
                f"💰 Payment received: ₦{amount:,.0f}\n"
                f"🎉 Balance: ₦0 — Fully paid!"
            )
        else:
            send_whatsapp_message(phone,
                f"💰 Payment recorded!\n\n"
                f"👤 {customer}\n"
                f"✅ Paid now: ₦{amount:,.0f}\n"
                f"⚠️ Still owes: ₦{remaining:,.0f}"
            )

    # ─── VIEW ALL DEBTS ───────────────────────────────────
    elif intent == "view_debts":
        debts = get_all_debts(phone)
        if not debts:
            send_whatsapp_message(phone,
                "🎉 Nobody owes you money right now!\n"
                "All debts are cleared."
            )
            return

        total_owed = sum(d["balance"] for d in debts)
        lines = [f"📋 *People Who Owe You*\n\nTotal: ₦{total_owed:,.0f}\n"]
        for d in debts:
            lines.append(
                f"👤 {d['customer_name']}\n"
                f"   ₦{d['balance']:,.0f}"
                + (f" — due {d['due_date']}" if d.get('due_date') else "")
            )
        send_whatsapp_message(phone, "\n".join(lines))

    # ─── VIEW ONE CUSTOMER DEBT ───────────────────────────
    elif intent == "view_customer_debt":
        customer = parsed.get("customer_name")
        if not customer:
            send_whatsapp_message(phone, "Which customer? Tell me their name.")
            return

        debts = get_customer_debt(phone, customer)
        if not debts:
            send_whatsapp_message(phone, f"{customer} doesn't owe you anything! ✅")
            return

        total = sum(d["balance"] for d in debts)
        lines = [f"👤 *{customer}'s Debt*\n"]
        for d in debts:
            lines.append(
                f"📦 {d['item']} — ₦{d['balance']:,.0f}"
                + (f" (due {d['due_date']})" if d.get('due_date') else "")
            )
        lines.append(f"\n💰 Total owed: ₦{total:,.0f}")
        send_whatsapp_message(phone, "\n".join(lines))

    # ─── SUMMARIES ───────────────────────────────────────
    elif intent == "view_daily":
        summary = get_daily_summary(phone)
        send_whatsapp_message(phone, format_summary("Today's Summary", summary))

    elif intent in ("view_weekly", "view_summary"):
        summary = get_weekly_summary(phone)
        send_whatsapp_message(phone, format_summary("This Week's Summary", summary))

    elif intent == "view_monthly":
        summary = get_monthly_summary(phone)
        send_whatsapp_message(phone, format_summary("This Month's Summary", summary))

    # ─── CLEAR RECORDS ───────────────────────────────────
    elif intent == "clear_records":
        count = archive_records(phone)
        send_whatsapp_message(phone,
            f"✅ Done! {count} old records archived.\n\n"
            f"Your slate is clean — start recording your new stock! 🆕"
        )

    # ─── GREETING ────────────────────────────────────────
    elif intent == "greeting":
        send_whatsapp_message(phone,
            "👋 Hello! I'm your business assistant.\n\n"
            "Here's what I can do:\n"
            "• Record your sales\n"
            "• Track who owes you money\n"
            "• Record when customers pay back\n"
            "• Daily, weekly and monthly summaries\n"
            "• Clear old records when you start new stock\n\n"
            "Just tell me what you sold today! 😊"
        )

    # ─── UNKNOWN ─────────────────────────────────────────
    else:
        send_whatsapp_message(phone,
            "I didn't quite understand that 😅\n\n"
            "Try:\n"
            "• 'I sell 3 bags rice 45k, I buy am 38k'\n"
            "• 'Seun take 2 bags rice 45k, go pay Friday'\n"
            "• 'Seun don pay 5000'\n"
            "• 'Who owe me money'\n"
            "• 'My profit today'"
        )