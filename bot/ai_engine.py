from groq import Groq
import os
from dotenv import load_dotenv
import json
import time

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def understand_message(text: str, retries: int = 3) -> dict:
    prompt = f"""
You are a helpful assistant for Nigerian market traders.
The user may write in English, Pidgin English, Yoruba, Hausa, Igbo or any mix.

Message: "{text}"

Return ONLY a JSON object. No explanation.

INTENT OPTIONS:
- record_sale: sold something. ALWAYS record_sale if BOTH selling price AND cost price are mentioned, even if a customer name is included. "I sell X to [name], I buy am Y" = record_sale NOT add_debt
- add_stock: adding new or old stock/inventory
- view_stock: check current stock levels
- add_debt: gave goods on credit with NO payment yet. Only use this if there is NO cost price mentioned and customer will pay LATER
- record_payment: customer paying back debt
- view_debts: see all debtors
- view_customer_debt: check one customer's debt
- view_daily: ONLY use this for "today", "today's profit", "my profit today" — NOT for section names like food/drinks/clothes
- view_yesterday: yesterday's summary
- view_weekly: this week
- view_monthly: this month
- view_last_n_days: last N days (extract n)
- view_date_range: specific date range (extract start and end dates)
- view_weekend: weekend sales
- view_top_products: best selling products + ROI
- view_top_customers: best customers by purchases
- view_chart: show sales chart
- switch_section: user wants to change active business section
- view_section_summary: user wants summary of a specific section
- view_all_sections: user wants to compare all sections
- view_section_stock: user wants stock for a specific section
- clear_records: archive old records, start fresh
- greeting: hello etc
- set_unit_conversion: trader is defining how many small units are in one bulk unit e.g. "1 bag rice = 33 mudu". Extract the product name into items array.
- view_unit_conversions: trader wants to see all their saved unit breakdowns e.g. "show my units", "show my conversions"
- correct_stock: trader wants to correct/update stock quantity to a specific number e.g. "correct rice to 8 bags", "rice stock is wrong, change to 15", "update rice stock to 10"
- remove_stock: trader wants to remove/reduce stock quantity e.g. "remove 5 bags rice from stock", "reduce rice by 3"
- delete_stock: trader wants to completely delete an item from stock e.g. "delete rice from stock", "remove rice completely"
- unknown: cannot understand

KEY PATTERNS:
- "last 3 days / last 5 days" = view_last_n_days, n=3 or 5
- "from [date] to [date]" = view_date_range
- "weekend sales" = view_weekend
- "top products / best sellers" = view_top_products
- "top customers / best customers" = view_top_customers
- "show chart / sales chart" = view_chart
- "add stock / I buy [item] [qty] [price]" = add_stock
- "show stock / my stock" = view_stock
- "yesterday sales" = view_yesterday
- "switch to [section] / go to [section]" = switch_section
- "[section] summary / [section] profit" = view_section_summary
- "all sections / compare sections" = view_all_sections
- "[name] don pay everything / [name] clear debt" = record_payment, amount should be set to 999999999 (will be capped at actual balance)
- "[section name] summary / [section name] profit / [section name] sales" = view_section_summary, extract section name
- "1 [bulk] [item] = [number] [retail]" = set_unit_conversion
- "1 [bulk] [item] get/contain/has [number] [retail]" = set_unit_conversion
- "show my units / show conversions" = view_unit_conversions
- "correct [item] to [number]" = correct_stock
- "update [item] stock to [number]" = correct_stock
- "remove [number] [item] from stock" = remove_stock
- "reduce [item] by [number]" = remove_stock
- "delete [item] from stock" = delete_stock
- "remove [item] completely" = delete_stock
- IMPORTANT: "food summary", "drinks summary", "clothes summary" = view_section_summary NOT view_daily

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

- For set_unit_conversion: put the product name in items[0].item field

DEBT AMOUNT RULES:
- amount in items is ALWAYS per unit price
- "Biodun take 5 tins tomato 1000 each" → amount=1000, quantity=5 (total=5000)
- "Amaka take 2 bags rice 45000" → amount=22500, quantity=2 (total=45000) — split evenly
- "Emeka owe me 10000" → put 10000 in top-level amount field, not items

IMPORTANT:
- Convert 45k=45000, 1.5k=1500, 200k=200000
- Extract ANY name as customer_name
- Only return JSON
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