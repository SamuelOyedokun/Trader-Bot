from supabase import create_client
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


# ─── SALES ───────────────────────────────────────────────

def save_sale(phone, item, quantity, selling_price, cost_price, profit, customer_name=None):
    supabase.table("sales").insert({
        "phone": phone,
        "item": item,
        "quantity": quantity,
        "selling_price": selling_price,
        "cost_price": cost_price,
        "profit": profit,
        "customer_name": customer_name,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    # Auto-deduct stock
    if item and quantity:
        deduct_stock(phone, item, quantity)

    # Update customer record
    if customer_name:
        update_customer(phone, customer_name, selling_price * quantity)


def get_summary_by_range(phone, start_date, end_date):
    result = supabase.table("sales")\
        .select("*").eq("phone", phone)\
        .eq("archived", False)\
        .gte("created_at", start_date)\
        .lte("created_at", end_date).execute()
    rows = result.data
    revenue = sum(r["selling_price"] * r["quantity"] for r in rows)
    profit = sum(r["profit"] for r in rows)
    return {"revenue": revenue, "profit": profit, "count": len(rows), "rows": rows}


def get_daily_summary(phone):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = today + timedelta(days=1)
    return get_summary_by_range(phone, today.isoformat(), end.isoformat())


def get_yesterday_summary(phone):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    return get_summary_by_range(phone, yesterday.isoformat(), today.isoformat())


def get_weekly_summary(phone):
    end = datetime.utcnow()
    start = end - timedelta(days=7)
    return get_summary_by_range(phone, start.isoformat(), end.isoformat())


def get_monthly_summary(phone):
    end = datetime.utcnow()
    start = end - timedelta(days=30)
    return get_summary_by_range(phone, start.isoformat(), end.isoformat())


def get_last_n_days(phone, n):
    end = datetime.utcnow()
    start = end - timedelta(days=n)
    return get_summary_by_range(phone, start.isoformat(), end.isoformat())


def get_weekend_summary(phone):
    today = datetime.utcnow()
    # Find last Saturday
    days_since_saturday = (today.weekday() - 5) % 7
    saturday = today - timedelta(days=days_since_saturday)
    saturday = saturday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = saturday + timedelta(days=2)
    return get_summary_by_range(phone, saturday.isoformat(), sunday.isoformat())


def get_top_products(phone, limit=5):
    result = supabase.table("sales")\
        .select("*").eq("phone", phone)\
        .eq("archived", False).execute()
    rows = result.data
    products = {}
    for r in rows:
        item = r["item"]
        if item not in products:
            products[item] = {"revenue": 0, "profit": 0, "quantity": 0, "count": 0}
        products[item]["revenue"] += r["selling_price"] * r["quantity"]
        products[item]["profit"] += r["profit"]
        products[item]["quantity"] += r["quantity"]
        products[item]["count"] += 1

    # Calculate ROI
    for item in products:
        total_cost = sum(
            r["cost_price"] * r["quantity"]
            for r in rows if r["item"] == item and r["cost_price"]
        )
        if total_cost > 0:
            products[item]["roi"] = round((products[item]["profit"] / total_cost) * 100, 1)
        else:
            products[item]["roi"] = 0

    sorted_products = sorted(products.items(), key=lambda x: x[1]["revenue"], reverse=True)
    return sorted_products[:limit]


def get_top_customers(phone, limit=5):
    result = supabase.table("customers")\
        .select("*").eq("phone", phone)\
        .order("total_purchases", desc=True)\
        .limit(limit).execute()
    return result.data


def update_customer(phone, customer_name, amount):
    existing = supabase.table("customers")\
        .select("*").eq("phone", phone)\
        .ilike("customer_name", customer_name).execute()
    if existing.data:
        row = existing.data[0]
        supabase.table("customers").update({
            "total_purchases": row["total_purchases"] + amount,
            "total_orders": row["total_orders"] + 1,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", row["id"]).execute()
    else:
        supabase.table("customers").insert({
            "phone": phone,
            "customer_name": customer_name,
            "total_purchases": amount,
            "total_orders": 1,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).execute()


# ─── STOCK ───────────────────────────────────────────────

def add_stock(phone, item, quantity, cost_price):
    existing = supabase.table("stock")\
        .select("*").eq("phone", phone)\
        .ilike("item", item).execute()
    if existing.data:
        row = existing.data[0]
        new_qty = row["quantity"] + quantity
        avg_cost = ((row["cost_price"] * row["quantity"]) + (cost_price * quantity)) / new_qty
        supabase.table("stock").update({
            "quantity": new_qty,
            "cost_price": round(avg_cost, 2),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", row["id"]).execute()
    else:
        supabase.table("stock").insert({
            "phone": phone,
            "item": item,
            "quantity": quantity,
            "cost_price": cost_price,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).execute()


def deduct_stock(phone, item, quantity):
    existing = supabase.table("stock")\
        .select("*").eq("phone", phone)\
        .ilike("item", item).execute()
    if existing.data:
        row = existing.data[0]
        new_qty = max(0, row["quantity"] - quantity)
        supabase.table("stock").update({
            "quantity": new_qty,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", row["id"]).execute()


def get_all_stock(phone):
    result = supabase.table("stock")\
        .select("*").eq("phone", phone)\
        .order("item").execute()
    return result.data


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
        .order("created_at").execute()
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
    for debt in debts:
        if remaining_payment <= 0:
            break
        balance = debt["balance"]
        if remaining_payment >= balance:
            supabase.table("debts").update({
                "amount_paid": debt["amount_paid"] + balance,
                "balance": 0,
                "status": "paid",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", debt["id"]).execute()
            remaining_payment -= balance
        else:
            supabase.table("debts").update({
                "amount_paid": debt["amount_paid"] + remaining_payment,
                "balance": balance - remaining_payment,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", debt["id"]).execute()
            remaining_payment = 0
    remaining_debts = get_customer_debt(phone, customer_name)
    total_remaining = sum(d["balance"] for d in remaining_debts)
    return total_remaining, "ok"


def archive_records(phone):
    result = supabase.table("sales")\
        .select("*").eq("phone", phone)\
        .eq("archived", False).execute()
    rows = result.data
    if not rows:
        return 0
    supabase.table("sales").update({
        "archived": True,
        "archived_at": datetime.utcnow().isoformat()
    }).eq("phone", phone).eq("archived", False).execute()
    return len(rows)