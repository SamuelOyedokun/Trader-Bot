from groq import Groq
import os
from dotenv import load_dotenv
import json

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def understand_message(text: str) -> dict:
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
- view_daily: today's summary
- view_yesterday: yesterday's summary  
- view_weekly: this week
- view_monthly: this month
- view_last_n_days: last N days (extract n)
- view_date_range: specific date range (extract start and end dates)
- view_weekend: weekend sales
- view_top_products: best selling products + ROI
- view_top_customers: best customers by purchases
- view_chart: show sales chart
- clear_records: archive old records, start fresh
- greeting: hello etc
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
  "chart_days": <number of days for chart, default 7>
}}

IMPORTANT:
- Convert 45k=45000, 1.5k=1500, 200k=200000
- Extract ANY name as customer_name
- Only return JSON
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    try:
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except:
        return {"intent": "unknown"}