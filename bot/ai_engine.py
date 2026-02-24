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

Your job is to understand the MEANING and return ONLY a JSON object.

INTENT RULES:
- record_sale: user sold something and got paid immediately
- add_debt: user gave goods/services but customer has NOT paid yet (will pay later)
- record_payment: a customer is paying back money they previously owed
- view_debts: user wants to see everyone who owes them
- view_customer_debt: user wants to see what one specific person owes
- view_daily: user asking about today's business
- view_weekly: user asking about this week
- view_monthly: user asking about this month
- view_summary: general business summary
- clear_records: user wants to start fresh / new stock
- greeting: hello, hi, how are you etc
- unknown: cannot understand

KEY PATTERNS TO RECOGNIZE (regardless of name or item):
- "[name] take/collect/carry [item/amount], go pay [time]" = add_debt
- "[name] owe me [amount]" = add_debt
- "[name] don pay / [name] pay me [amount]" = record_payment
- "I sell [item] [price], I buy am [cost]" = record_sale
- "who owe me / my debtors / people wey owe me" = view_debts
- "how much [name] owe" = view_customer_debt
- "my profit today / wetin I make today" = view_daily
- "this week / weekly" = view_weekly
- "this month / monthly" = view_monthly
- "clear / start fresh / don finish goods / new stock" = clear_records

Return ONLY this JSON structure:
{{
  "intent": "<intent>",
  "items": [
    {{
      "item": "<item name or 'goods' if unknown>",
      "quantity": <number or 1>,
      "amount": <total amount or price per unit as number, convert k to thousands e.g. 45k=45000>,
      "cost_price": <cost price as number or null>
    }}
  ],
  "customer_name": "<full name mentioned or null>",
  "amount": <payment amount as number or null>,
  "due_date": "<when they will pay or null>",
  "notes": null
}}

IMPORTANT:
- Convert 45k to 45000, 1.5k to 1500, 200k to 200000
- If no cost price mentioned, set cost_price to null
- Extract ANY name mentioned as customer_name
- Only return JSON, no explanation
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