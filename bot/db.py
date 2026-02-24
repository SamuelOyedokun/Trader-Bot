from supabase import create_client
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# ─── SALES ───────────────────────────────────────────────

def save_sale(phone, item, quantity, selling_price, cost_price, profit):
    supabase.table("sales").insert({
        "phone": phone,
        "item": item,
        "quantity": quantity,
        "selling_price": selling_price,
        "cost_price": cost_price,
        "profit": profit,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

def get_daily_summary(phone):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0).isoformat()
    result = supabase.table("sales")\
        .select("*").eq("phone", phone)\
        .eq("archived", False)\
        .gte("created_at", today).execute()
    rows = result.data
    revenue = sum(r["selling_price"] * r["quantity"] for r in rows)
    profit = sum(r["profit"] for r in rows)
    return {"revenue": revenue, "profit": profit, "count": len(rows)}

def get_weekly_summary(phone):
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    result = supabase.table("sales")\
        .select("*").eq("phone", phone)\
        .eq("archived", False)\
        .gte("created_at", week_ago).execute()
    rows = result.data
    revenue = sum(r["selling_price"] * r["quantity"] for r in rows)
    profit = sum(r["profit"] for r in rows)
    return {"revenue": revenue, "profit": profit, "count": len(rows)}

def get_monthly_summary(phone):
    month_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
    result = supabase.table("sales")\
        .select("*").eq("phone", phone)\
        .eq("archived", False)\
        .gte("created_at", month_ago).execute()
    rows = result.data
    revenue = sum(r["selling_price"] * r["quantity"] for r in rows)
    profit = sum(r["profit"] for r in rows)
    return {"revenue": revenue, "profit": profit, "count": len(rows)}

def archive_records(phone):
    result = supabase.table("sales")\
        .select("*").eq("phone", phone)\
        .eq("archived", False).execute()
    rows = result.data
    if not rows:
        return 0
    supabase.table("sales")\
        .update({"archived": True, "archived_at": datetime.utcnow().isoformat()})\
        .eq("phone", phone).eq("archived", False).execute()
    return len(rows)

# ─── DEBTS ───────────────────────────────────────────────

def save_debt(phone, customer_name, item, quantity, amount, due_date=None):
    supabase.table("debts").insert({
        "phone": phone,
        "customer_name": customer_name,
        "item": item,
        "quantity": quantity,
        "amount": amount,
        "amount_paid": 0,
        "balance": amount,
        "due_date": due_date,
        "status": "unpaid",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }).execute()

def get_all_debts(phone):
    result = supabase.table("debts")\
        .select("*").eq("phone", phone)\
        .eq("status", "unpaid")\
        .order("created_at", desc=False).execute()
    return result.data

def get_customer_debt(phone, customer_name):
    result = supabase.table("debts")\
        .select("*").eq("phone", phone)\
        .ilike("customer_name", f"%{customer_name}%")\
        .eq("status", "unpaid").execute()
    return result.data

def record_payment(phone, customer_name, amount_paid):
    debts = get_customer_debt(phone, customer_name)
    if not debts:
        return None, "not_found"
    
    remaining_payment = amount_paid
    updated = []
    
    for debt in debts:
        if remaining_payment <= 0:
            break
        balance = debt["balance"]
        if remaining_payment >= balance:
            supabase.table("debts")\
                .update({
                    "amount_paid": debt["amount_paid"] + balance,
                    "balance": 0,
                    "status": "paid",
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", debt["id"]).execute()
            remaining_payment -= balance
            updated.append({**debt, "balance": 0, "status": "paid"})
        else:
            new_balance = balance - remaining_payment
            supabase.table("debts")\
                .update({
                    "amount_paid": debt["amount_paid"] + remaining_payment,
                    "balance": new_balance,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", debt["id"]).execute()
            updated.append({**debt, "balance": new_balance})
            remaining_payment = 0
    
    remaining_debts = get_customer_debt(phone, customer_name)
    total_remaining = sum(d["balance"] for d in remaining_debts)
    return total_remaining, "ok"