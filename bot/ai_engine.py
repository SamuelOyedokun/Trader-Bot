from groq import Groq
import os
from dotenv import load_dotenv
import json
import time
from datetime import datetime

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def understand_message(text: str, retries: int = 3) -> dict:
    today = datetime.utcnow().strftime('%Y-%m-%d')
    current_year = datetime.utcnow().year
    current_month = datetime.utcnow().month

    prompt = f"""
You are a helpful assistant for Nigerian market traders.
Today's date is {today}. Current year is {current_year}. Current month is {current_month}.

STRICT DATE RULES:
1. When a date has NO year, ALWAYS use {current_year} as the year.
2. When a SPECIFIC past year is mentioned (e.g. "March 2020", "2019 summary"), use THAT year exactly — do NOT default to current year.
3. "this month" = start of current month to today. Do NOT use last-30-days range.
4. "last month" = full previous calendar month.
5. "today" = {today}
6. For view_monthly with a SPECIFIC month+year: set start_date to first day of that month, end_date to last day of that month.

The user may write in English, Pidgin English, Yoruba, Hausa, Igbo or any mix.

Message: "{text}"

Return ONLY a JSON object. No explanation.

INTENT OPTIONS:
- record_sale: sold something. ALWAYS record_sale if BOTH selling price AND cost price are mentioned, even if a customer name is included.
- add_stock: adding new inventory/stock to the system
- view_stock: check CURRENT stock levels only. Use ONLY when user says "show my stock", "what is my stock", "stock level" — NOT for restock history
- add_debt: gave goods on credit with NO payment yet
- record_payment: customer paying back debt
- view_debts: see all debtors
- view_customer_debt: check one customer's debt
- view_daily: "today", "today's profit", "my profit today"
- view_yesterday: yesterday's summary
- view_weekly: this week
- view_monthly: this month OR a specific named month (e.g. "March 2020 summary", "summary for January 2019")
- view_last_n_days: last N days (extract n)
- view_date_range: specific date range (extract start and end dates)
- view_weekend: weekend sales
- view_yearly: this year, last year, or a specific year (e.g. "2024 summary", "annual summary")
- view_top_products: best selling products + ROI
- view_top_customers: best customers by purchases
- view_chart: show sales chart
- switch_section: user wants to change active business section
- view_section_summary: user wants summary of a specific section
- view_all_sections: user wants to compare all sections
- view_section_stock: user wants stock for a specific section
- clear_records: archive old records
- greeting: hello, hi, good morning etc
- set_unit_conversion: defining how many small units are in one bulk unit e.g. "1 bag rice = 33 mudu"
- view_unit_conversions: see all saved unit breakdowns
- correct_stock: correct/update stock quantity to a specific number
- remove_stock: remove/reduce stock quantity by some amount
- delete_stock: completely delete an item from stock
- view_restock_history: see stock PURCHASE history (what was bought/restocked before). Use when user says "show restock history", "show my purchases", "what have I been buying"
- view_restock_by_date: see what was restocked/bought on a SPECIFIC date. Use when user says "what did I buy on [date]", "what did I restock on [date]", "restock on [date]", "what did I buy today", "what did I buy yesterday"
- subscribe: user wants to subscribe or says they have paid
- unknown: cannot understand

CRITICAL INTENT RULES — READ CAREFULLY:

RESTOCK vs STOCK:
- "show my stock" / "my stock" / "stock level" / "view stock" = view_stock (current inventory)
- "show restock history" / "restock history" / "show my purchases" = view_restock_history
- "what did I buy on [date]" / "what did I restock on [date]" / "what did I buy today" / "what did I buy yesterday" = view_restock_by_date
- "what did I buy" (no date) = view_restock_history
- "what did I restock today" = view_restock_by_date with start_date={today}
- NEVER use view_stock for restock/purchase history questions

MONTHLY WITH SPECIFIC YEAR:
- "summary for March 2020" = view_monthly, start_date=2020-03-01, end_date=2020-03-31
- "January 2019 sales" = view_monthly, start_date=2019-01-01, end_date=2019-01-31
- "this month" = view_monthly (no start/end dates needed, handler uses current month)
- "last month" = view_monthly, set start_date and end_date to last calendar month

YEARLY vs YESTERDAY:
- "this year / yearly / annual / 2026 summary / 2024 summary" = view_yearly — NOT view_yesterday
- IMPORTANT: "year" and "yearly" = view_yearly, never view_yesterday

OTHER PATTERNS:
- "last 3 days / last 5 days" = view_last_n_days, n=3 or 5
- "from [date] to [date]" = view_date_range
- "weekend sales" = view_weekend
- "top products / best sellers" = view_top_products
- "top customers / best customers" = view_top_customers
- "show chart / sales chart" = view_chart
- "add stock / I buy [item] [qty] [price]" = add_stock
- "yesterday sales" = view_yesterday
- "switch to [section] / go to [section]" = switch_section
- "[section] summary / [section] profit" = view_section_summary
- "all sections / compare sections" = view_all_sections
- "food summary", "drinks summary", "clothes summary" = view_section_summary NOT view_daily
- "[name] don pay everything / [name] clear debt" = record_payment, amount=999999999
- "1 [bulk] [item] = [number] [retail]" = set_unit_conversion
- "show my units / show conversions" = view_unit_conversions
- "correct [item] to [number]" = correct_stock
- "remove [number] [item] from stock" = remove_stock
- "delete [item] from stock" = delete_stock
- "subscribe / I have paid / I don pay" = subscribe

JSON STRUCTURE:
{{
  "intent": "<intent>",
  "items": [
    {{
      "item": "<name>",
      "quantity": <number or 1>,
      "amount": <selling price per unit, convert k to thousands>,
      "cost_price": <cost per unit or null>
    }}
  ],
  "customer_name": "<name or null>",
  "amount": <payment amount as number or null>,
  "due_date": "<due date or null>",
  "n_days": <number of days or null>,
  "start_date": "<YYYY-MM-DD or null>",
  "end_date": "<YYYY-MM-DD or null>",
  "chart_days": <number of days for chart, default 7>,
  "section": "<section name or null>",
  "bulk_unit": "<bag, crate, carton, pack, basket or null>",
  "retail_unit": "<mudu, paint, rubber, tin, cup, piece, wrap or null>",
  "units_per_bulk": <number or null>,
  "is_retail": <true if selling small units, false if selling full bulk>
}}

AMOUNT RULES:
- Convert 45k=45000, 1.5k=1500, 200k=200000
- amount in items is ALWAYS per unit price
- "Biodun take 5 tins tomato 1000 each" → amount=1000, quantity=5
- "Amaka take 2 bags rice 45000" → amount=22500, quantity=2 (split evenly)
- "Emeka owe me 10000" → top-level amount=10000

- Extract ANY name as customer_name
- For set_unit_conversion: put the product name in items[0].item
- Only return valid JSON, nothing else
"""

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                timeout=15
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())

        except json.JSONDecodeError:
            print(f"JSON parse error on attempt {attempt + 1}")
            if attempt < retries - 1:
                time.sleep(1)
            continue

        except Exception as e:
            print(f"Groq API error on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                time.sleep(2)
            continue

    # All retries failed
    return {"intent": "error"}