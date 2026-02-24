from bot.ai_engine import understand_message
from bot.db import (save_sale, get_daily_summary, get_yesterday_summary,
                    get_weekly_summary, get_monthly_summary, get_last_n_days,
                    get_weekend_summary, get_summary_by_range,
                    get_top_products, get_top_customers,
                    archive_records, save_debt, get_all_debts,
                    get_customer_debt, record_payment,
                    add_stock, get_all_stock,
                    get_current_section, set_current_section,
                    get_all_sections_summary, get_section_summary)
from bot.charts import generate_sales_chart, generate_top_products_chart
from twilio.rest import Client
import os
import tempfile
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def get_twilio_client():
    return Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))


def send_whatsapp_message(phone: str, message: str):
    client = get_twilio_client()
    client.messages.create(
        from_=f"whatsapp:{os.getenv('TWILIO_WHATSAPP_NUMBER')}",
        body=message,
        to=f"whatsapp:+{phone}"
    )


def send_whatsapp_image(phone: str, image_buf, caption: str):
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(image_buf.read())
            tmp_path = tmp.name
        send_whatsapp_message(phone, caption)
        os.unlink(tmp_path)
    except Exception as e:
        print(f"Image send error: {e}")
        send_whatsapp_message(phone, caption)


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

    # Get active section for every message
    mentioned_section = parsed.get("section")
    active_section = mentioned_section if mentioned_section else get_current_section(phone)

    # ─── RECORD SALE ─────────────────────────────────────
    if intent == "record_sale":
        items = parsed.get("items", [])
        if not items:
            send_whatsapp_message(phone,
                "I need more details about the sale.\n\n"
                "Try: 'I sell 3 bags rice 45k, I buy am 38k'"
            )
            return

        reply_lines = [f"✅ Sales recorded! [{active_section.upper()}]\n"]
        total_profit = 0
        missing_cost = []
        customer = parsed.get("customer_name")

        for item_data in items:
            item = item_data.get("item", "item")
            qty = item_data.get("quantity", 1) or 1
            amount = item_data.get("amount")
            cost = item_data.get("cost_price")

            if amount and cost:
                profit = (amount - cost) * qty
                total_profit += profit
                save_sale(phone, item, qty, amount, cost, profit, customer, active_section)
                reply_lines.append(
                    f"📦 {item} × {qty}\n"
                    f"   Sell: ₦{amount:,.0f} | Cost: ₦{cost:,.0f} | Profit: ₦{profit:,.0f}"
                )
            elif amount and not cost:
                missing_cost.append(item)
                save_sale(phone, item, qty, amount, 0, 0, customer, active_section)
                reply_lines.append(f"📦 {item} × {qty} — ₦{amount:,.0f} (no cost price)")

        reply_lines.append(f"\n💰 Total Profit: ₦{total_profit:,.0f}")
        if missing_cost:
            reply_lines.append(f"⚠️ No cost price for: {', '.join(missing_cost)}")
        if customer:
            reply_lines.append(f"👤 Customer: {customer}")
        reply_lines.append("Keep it up! 💪")
        send_whatsapp_message(phone, "\n".join(reply_lines))

    # ─── ADD STOCK ───────────────────────────────────────
    elif intent == "add_stock":
        items = parsed.get("items", [])
        if not items:
            send_whatsapp_message(phone,
                "Tell me what stock you're adding.\n\n"
                "Try: 'I buy 10 bags rice 38k each'"
            )
            return

        reply_lines = [f"📦 Stock added! [{active_section.upper()}]\n"]
        for item_data in items:
            item = item_data.get("item", "item")
            qty = item_data.get("quantity", 1) or 1
            cost = item_data.get("cost_price") or item_data.get("amount")
            if not cost:
                cost = 0
            add_stock(phone, item, qty, cost, active_section)
            reply_lines.append(f"✅ {item}: +{qty} units @ ₦{cost:,.0f} each")

        reply_lines.append("\nStock updated successfully! 🏪")
        send_whatsapp_message(phone, "\n".join(reply_lines))

    # ─── VIEW STOCK ──────────────────────────────────────
    elif intent == "view_stock":
        stock = get_all_stock(phone, active_section)
        if not stock:
            send_whatsapp_message(phone,
                f"No stock in {active_section.upper()} section yet.\n\n"
                "Add stock with: 'I buy 10 bags rice 38k each'"
            )
            return
        total_value = sum(s["quantity"] * s["cost_price"] for s in stock)
        lines = [f"🏪 *{active_section.upper()} Stock*\n\nTotal Value: ₦{total_value:,.0f}\n"]
        for s in stock:
            qty = s["quantity"]
            status = "⚠️ LOW" if qty <= 2 else "✅"
            lines.append(f"{status} {s['item']}: {qty} units @ ₦{s['cost_price']:,.0f}")
        send_whatsapp_message(phone, "\n".join(lines))

    # ─── ADD DEBT ────────────────────────────────────────
    elif intent == "add_debt":
        customer = parsed.get("customer_name")
        due_date = parsed.get("due_date")
        amount = parsed.get("amount")
        item = "goods"
        qty = 1

        if parsed.get("items"):
            first_item = parsed["items"][0]
            item = first_item.get("item", "goods")
            qty = first_item.get("quantity", 1) or 1
            if not amount and first_item.get("amount"):
                amount = first_item["amount"] * qty

        if not customer:
            send_whatsapp_message(phone,
                "Who took the goods? Tell me their name.\n\n"
                "Try: 'Seun take 2 bags rice 45k, go pay Friday'"
            )
            return

        if not amount:
            send_whatsapp_message(phone,
                f"How much does {customer} owe?\n\n"
                f"Try: '{customer} take 3 bags rice 45k'"
            )
            return

        save_debt(phone, customer, item, qty, amount, due_date, active_section)
        reply = (
            f"📝 Debt recorded! [{active_section.upper()}]\n\n"
            f"👤 {customer}\n"
            f"📦 {item} × {qty}\n"
            f"💰 Owes: ₦{amount:,.0f}\n"
        )
        if due_date:
            reply += f"📅 Due: {due_date}\n"
        reply += "\nI'll help you track this! 💪"
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
                f"No debt record found for {customer}.\n"
                "Check the name and try again."
            )
        elif remaining == 0:
            send_whatsapp_message(phone,
                f"✅ {customer} don clear everything!\n\n"
                f"💰 Paid: ₦{amount:,.0f}\n"
                f"🎉 Balance: ₦0 — Fully paid!"
            )
        else:
            send_whatsapp_message(phone,
                f"💰 Payment recorded!\n\n"
                f"👤 {customer}\n"
                f"✅ Paid: ₦{amount:,.0f}\n"
                f"⚠️ Still owes: ₦{remaining:,.0f}"
            )

    # ─── VIEW ALL DEBTS ───────────────────────────────────
    elif intent == "view_debts":
        debts = get_all_debts(phone)
        if not debts:
            send_whatsapp_message(phone, "🎉 Nobody owes you money!")
            return
        total_owed = sum(d["balance"] for d in debts)
        lines = [f"📋 *People Who Owe You*\n\nTotal: ₦{total_owed:,.0f}\n"]
        for d in debts:
            lines.append(
                f"👤 {d['customer_name']} — ₦{d['balance']:,.0f}"
                + (f" (due {d['due_date']})" if d.get('due_date') else "")
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
        lines.append(f"\n💰 Total: ₦{total:,.0f}")
        send_whatsapp_message(phone, "\n".join(lines))

    # ─── SWITCH SECTION ──────────────────────────────────
    elif intent == "switch_section":
        section = parsed.get("section")
        if not section:
            summaries = get_all_sections_summary(phone)
            existing = list(summaries.keys())
            send_whatsapp_message(phone,
                "Which section do you want to switch to?\n\n"
                f"Your sections: {', '.join(existing) if existing else 'none yet'}\n\n"
                "Try: 'switch to drinks' or 'switch to food'"
            )
            return
        set_current_section(phone, section)
        send_whatsapp_message(phone,
            f"✅ Switched to *{section.upper()}* section!\n\n"
            f"All sales, stock and summaries will now be recorded under {section}.\n\n"
            f"To switch back say: 'switch to [section name]'"
        )

    # ─── VIEW ONE SECTION SUMMARY ─────────────────────────
    elif intent == "view_section_summary":
        section = parsed.get("section") or get_current_section(phone)
        summary = get_section_summary(phone, section)
        send_whatsapp_message(phone,
            f"📊 *{section.upper()} Summary*\n\n"
            f"💰 Revenue: ₦{summary['revenue']:,.0f}\n"
            f"📈 Profit: ₦{summary['profit']:,.0f}\n"
            f"📦 Sales: {summary['count']}\n\n"
            f"Keep it up! 🚀"
        )

    # ─── VIEW ALL SECTIONS ────────────────────────────────
    elif intent == "view_all_sections":
        summaries = get_all_sections_summary(phone)
        if not summaries:
            send_whatsapp_message(phone, "No sections found yet.")
            return
        total_revenue = sum(s["revenue"] for s in summaries.values())
        total_profit = sum(s["profit"] for s in summaries.values())
        lines = [f"📊 *All Business Sections*\n\nTotal Revenue: ₦{total_revenue:,.0f}\nTotal Profit: ₦{total_profit:,.0f}\n"]
        for section, data in summaries.items():
            lines.append(
                f"🏷️ *{section.upper()}*\n"
                f"   💰 Revenue: ₦{data['revenue']:,.0f}\n"
                f"   📈 Profit: ₦{data['profit']:,.0f}\n"
                f"   📦 Sales: {data['count']}"
            )
        send_whatsapp_message(phone, "\n".join(lines))

    # ─── VIEW SECTION STOCK ───────────────────────────────
    elif intent == "view_section_stock":
        section = parsed.get("section") or get_current_section(phone)
        stock = get_all_stock(phone, section)
        if not stock:
            send_whatsapp_message(phone,
                f"No stock in {section} section yet.\n\n"
                "Add stock with: 'I buy 10 bags rice 38k each'"
            )
            return
        total_value = sum(s["quantity"] * s["cost_price"] for s in stock)
        lines = [f"🏪 *{section.upper()} Stock*\n\nTotal Value: ₦{total_value:,.0f}\n"]
        for s in stock:
            qty = s["quantity"]
            status = "⚠️ LOW" if qty <= 2 else "✅"
            lines.append(f"{status} {s['item']}: {qty} units @ ₦{s['cost_price']:,.0f}")
        send_whatsapp_message(phone, "\n".join(lines))

    # ─── SUMMARIES ───────────────────────────────────────
    elif intent == "view_daily":
        summary = get_daily_summary(phone)
        send_whatsapp_message(phone, format_summary("Today's Summary", summary))

    elif intent == "view_yesterday":
        summary = get_yesterday_summary(phone)
        send_whatsapp_message(phone, format_summary("Yesterday's Summary", summary))

    elif intent in ("view_weekly", "view_summary"):
        summary = get_weekly_summary(phone)
        send_whatsapp_message(phone, format_summary("This Week's Summary", summary))

    elif intent == "view_monthly":
        summary = get_monthly_summary(phone)
        send_whatsapp_message(phone, format_summary("This Month's Summary", summary))

    elif intent == "view_last_n_days":
        n = parsed.get("n_days", 7)
        summary = get_last_n_days(phone, n)
        send_whatsapp_message(phone, format_summary(f"Last {n} Days Summary", summary))

    elif intent == "view_weekend":
        summary = get_weekend_summary(phone)
        send_whatsapp_message(phone, format_summary("Weekend Sales Summary", summary))

    elif intent == "view_date_range":
        start = parsed.get("start_date")
        end = parsed.get("end_date")
        if not start or not end:
            send_whatsapp_message(phone,
                "Tell me the date range.\n\n"
                "Try: 'sales from Feb 10 to Feb 20'"
            )
            return
        summary = get_summary_by_range(phone, start, end)
        send_whatsapp_message(phone, format_summary(f"Sales {start} to {end}", summary))

    # ─── TOP PRODUCTS ─────────────────────────────────────
    elif intent == "view_top_products":
        products = get_top_products(phone)
        if not products:
            send_whatsapp_message(phone, "No sales data yet to analyze.")
            return
        lines = ["🏆 *Top Products*\n"]
        for i, (name, data) in enumerate(products, 1):
            lines.append(
                f"{i}. {name}\n"
                f"   💰 Revenue: ₦{data['revenue']:,.0f}\n"
                f"   📈 Profit: ₦{data['profit']:,.0f}\n"
                f"   📊 ROI: {data['roi']}%\n"
                f"   📦 Units sold: {data['quantity']:.0f}"
            )
        chart = generate_top_products_chart(products, "Top Products Analysis")
        if chart:
            send_whatsapp_image(phone, chart, "\n".join(lines))
        else:
            send_whatsapp_message(phone, "\n".join(lines))

    # ─── TOP CUSTOMERS ────────────────────────────────────
    elif intent == "view_top_customers":
        customers = get_top_customers(phone)
        if not customers:
            send_whatsapp_message(phone,
                "No customer data yet.\n\n"
                "Record sales with customer names to track them.\n"
                "Try: 'I sell 3 bags rice 45k to Emeka, I buy am 38k'"
            )
            return
        lines = ["👑 *Top Customers*\n"]
        for i, c in enumerate(customers, 1):
            lines.append(
                f"{i}. {c['customer_name']}\n"
                f"   💰 Total: ₦{c['total_purchases']:,.0f}\n"
                f"   🛒 Orders: {c['total_orders']}"
            )
        send_whatsapp_message(phone, "\n".join(lines))

    # ─── SALES CHART ─────────────────────────────────────
    elif intent == "view_chart":
        days = parsed.get("chart_days", 7)
        summary = get_last_n_days(phone, days)
        rows = summary.get("rows", [])
        if not rows:
            send_whatsapp_message(phone, f"No sales data for the last {days} days.")
            return
        chart = generate_sales_chart(rows, f"Sales - Last {days} Days")
        if chart:
            caption = (
                f"📊 *Sales Chart - Last {days} Days*\n\n"
                f"💰 Revenue: ₦{summary['revenue']:,.0f}\n"
                f"📈 Profit: ₦{summary['profit']:,.0f}\n"
                f"📦 Sales: {summary['count']}"
            )
            send_whatsapp_image(phone, chart, caption)
        else:
            send_whatsapp_message(phone, "Could not generate chart. Try again.")

    # ─── CLEAR RECORDS ───────────────────────────────────
    elif intent == "clear_records":
        count = archive_records(phone)
        send_whatsapp_message(phone,
            f"✅ Done! {count} old records archived.\n\n"
            f"Your slate is clean — start fresh! 🆕"
        )

    # ─── GREETING ────────────────────────────────────────
    elif intent == "greeting":
        current = get_current_section(phone)
        send_whatsapp_message(phone,
            f"👋 Hello! I'm your business assistant.\n\n"
            f"📍 Current section: *{current.upper()}*\n\n"
            f"Here's what I can do:\n"
            f"📦 Record sales & stock\n"
            f"💰 Daily, weekly, monthly summaries\n"
            f"📅 Any date range or last N days\n"
            f"🏆 Top products + ROI analysis\n"
            f"👑 Top customers\n"
            f"📊 Sales charts\n"
            f"📝 Debt tracking\n"
            f"🏪 Stock management\n"
            f"🏷️ Multiple business sections\n\n"
            f"Say 'switch to food' or 'switch to drinks' to change section! 😊"
        )

    # ─── UNKNOWN ─────────────────────────────────────────
    else:
        send_whatsapp_message(phone,
            "I didn't quite get that 😅\n\n"
            "Try:\n"
            "• 'I sell 3 bags rice 45k, I buy am 38k'\n"
            "• 'Last 5 days summary'\n"
            "• 'Show top products'\n"
            "• 'Show my stock'\n"
            "• 'Sales chart'\n"
            "• 'Who owe me money'\n"
            "• 'Switch to food'"
        )