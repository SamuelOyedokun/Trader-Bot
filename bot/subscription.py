from bot.db import supabase
from datetime import datetime, timedelta
import os

# Set your price here when ready
MONTHLY_PRICE = int(os.getenv("MONTHLY_PRICE", "2000"))  # in Naira

# Your Paystack and Flutterwave payment links
# Replace these with your actual payment page links
PAYSTACK_LINK = os.getenv("PAYSTACK_LINK", "https://paystack.com/pay/traderbot")
FLUTTERWAVE_LINK = os.getenv("FLUTTERWAVE_LINK", "https://flutterwave.com/pay/traderbot")

TRIAL_DAYS = 7
SUBSCRIPTION_DAYS = 30


def get_subscription(phone):
    result = supabase.table("subscriptions")\
        .select("*").eq("phone", phone).execute()
    return result.data[0] if result.data else None


def create_trial(phone):
    trial_start = datetime.utcnow()
    trial_end = trial_start + timedelta(days=TRIAL_DAYS)
    supabase.table("subscriptions").insert({
        "phone": phone,
        "status": "trial",
        "trial_start": trial_start.isoformat(),
        "trial_end": trial_end.isoformat(),
        "created_at": trial_start.isoformat(),
        "updated_at": trial_start.isoformat()
    }).execute()
    return trial_end


def activate_subscription(phone, amount, reference, provider):
    now = datetime.utcnow()
    sub_end = now + timedelta(days=SUBSCRIPTION_DAYS)
    existing = get_subscription(phone)
    if existing:
        supabase.table("subscriptions").update({
            "status": "active",
            "subscription_start": now.isoformat(),
            "subscription_end": sub_end.isoformat(),
            "amount_paid": amount,
            "payment_reference": reference,
            "payment_provider": provider,
            "updated_at": now.isoformat()
        }).eq("phone", phone).execute()
    else:
        supabase.table("subscriptions").insert({
            "phone": phone,
            "status": "active",
            "subscription_start": now.isoformat(),
            "subscription_end": sub_end.isoformat(),
            "amount_paid": amount,
            "payment_reference": reference,
            "payment_provider": provider,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }).execute()
    return sub_end


def check_access(phone):
    """
    Returns: (has_access, status, days_remaining)
    status: 'trial', 'active', 'expired', 'new'
    """
    sub = get_subscription(phone)

    # Brand new user
    if not sub:
        trial_end = create_trial(phone)
        days_left = (trial_end - datetime.utcnow()).days
        return True, "new", days_left

    now = datetime.utcnow()

    # Active paid subscription
    if sub["status"] == "active":
        sub_end = datetime.fromisoformat(sub["subscription_end"].replace("Z", "+00:00")).replace(tzinfo=None)
        if now < sub_end:
            days_left = (sub_end - now).days
            return True, "active", days_left
        else:
            # Subscription expired
            supabase.table("subscriptions").update({
                "status": "expired",
                "updated_at": now.isoformat()
            }).eq("phone", phone).execute()
            return False, "expired", 0

    # Trial user
    if sub["status"] == "trial":
        trial_end = datetime.fromisoformat(sub["trial_end"].replace("Z", "+00:00")).replace(tzinfo=None)
        if now < trial_end:
            days_left = (trial_end - now).days
            return True, "trial", days_left
        else:
            # Trial expired
            supabase.table("subscriptions").update({
                "status": "expired",
                "updated_at": now.isoformat()
            }).eq("phone", phone).execute()
            return False, "expired", 0

    # Expired
    return False, "expired", 0


def get_payment_message(phone):
    return (
        f"⏰ Your free trial has ended!\n\n"
        f"To continue using TraderBot, subscribe for just "
        f"₦{MONTHLY_PRICE:,}/month.\n\n"
        f"Choose your payment method:\n\n"
        f"💳 *Paystack:*\n{PAYSTACK_LINK}?phone={phone}\n\n"
        f"💳 *Flutterwave:*\n{FLUTTERWAVE_LINK}?phone={phone}\n\n"
        f"After payment, send: *'I have paid'*\n"
        f"and I will activate your account! ✅"
    )


def get_expiry_warning(days_left):
    return (
        f"⚠️ *Subscription Reminder*\n\n"
        f"Your TraderBot subscription expires in *{days_left} day{'s' if days_left != 1 else ''}*.\n\n"
        f"Renew now to avoid interruption:\n\n"
        f"💳 *Paystack:*\n{PAYSTACK_LINK}\n\n"
        f"💳 *Flutterwave:*\n{FLUTTERWAVE_LINK}\n\n"
        f"Send *'I have paid'* after payment! ✅"
    )