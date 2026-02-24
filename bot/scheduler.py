from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from bot.db import get_weekly_summary, supabase
from bot.message_handler import send_whatsapp_message
import pytz
import logging
from bot.subscription import get_expiry_warning
from datetime import datetime, timedelta

def send_expiry_reminders():
    """Send reminders to users whose subscription expires in 3 days."""
    logger.info("🔔 Running expiry reminder job...")
    try:
        # Find subscriptions expiring in 3 days
        three_days_from_now = datetime.utcnow() + timedelta(days=3)
        two_days_from_now = datetime.utcnow() + timedelta(days=2)

        result = supabase.table("subscriptions")\
            .select("*")\
            .eq("status", "active")\
            .gte("subscription_end", two_days_from_now.isoformat())\
            .lte("subscription_end", three_days_from_now.isoformat())\
            .execute()

        for sub in result.data:
            phone = sub["phone"]
            sub_end = datetime.fromisoformat(sub["subscription_end"].replace("Z", "+00:00")).replace(tzinfo=None)
            days_left = (sub_end - datetime.utcnow()).days
            try:
                send_whatsapp_message(phone, get_expiry_warning(days_left))
                logger.info(f"✅ Reminder sent to {phone}")
            except Exception as e:
                logger.error(f"❌ Failed reminder for {phone}: {e}")

    except Exception as e:
        logger.error(f"Expiry reminder error: {e}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_all_active_users():
    """Get all unique phone numbers that have sales records."""
    try:
        result = supabase.table("sales")\
            .select("phone")\
            .eq("archived", False)\
            .execute()
        phones = list(set(r["phone"] for r in result.data if r["phone"]))
        return phones
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return []


def send_weekly_summaries():
    """Send weekly summary to all active users."""
    logger.info("🕗 Running weekly summary job...")
    phones = get_all_active_users()
    logger.info(f"Found {len(phones)} active users")

    success = 0
    failed = 0

    for phone in phones:
        try:
            summary = get_weekly_summary(phone)

            # Only send if they have at least 1 sale this week
            if summary["count"] == 0:
                continue

            message = (
                f"📊 *Your Weekly Business Report*\n\n"
                f"Here's how your business performed this week:\n\n"
                f"💰 Total Revenue: ₦{summary['revenue']:,.0f}\n"
                f"📈 Total Profit: ₦{summary['profit']:,.0f}\n"
                f"📦 Total Sales: {summary['count']}\n\n"
                f"{'🔥 Great week! Keep pushing!' if summary['profit'] > 0 else '💪 Keep going, better week ahead!'}\n\n"
                f"Reply *'this week summary'* anytime for updates.\n"
                f"Reply *'show top products'* to see your best sellers."
            )

            send_whatsapp_message(phone, message)
            success += 1
            logger.info(f"✅ Sent to {phone}")

        except Exception as e:
            failed += 1
            logger.error(f"❌ Failed for {phone}: {e}")

    logger.info(f"Weekly summary complete. ✅ {success} sent, ❌ {failed} failed")


def start_scheduler():
    """Start the background scheduler."""
    nigeria_tz = pytz.timezone("Africa/Lagos")

    scheduler = BackgroundScheduler(timezone=nigeria_tz)

    # Every Sunday at 8:00 PM Nigeria time
    scheduler.add_job(
        send_weekly_summaries,
        trigger=CronTrigger(
            day_of_week="sun",
            hour=20,
            minute=0,
            timezone=nigeria_tz
        ),
        id="weekly_summary",
        name="Weekly Summary to All Users",
        replace_existing=True
    )
    
    # Every day at 9AM Nigeria time — check expiring subscriptions
    scheduler.add_job(
        send_expiry_reminders,
        trigger=CronTrigger(
            hour=9,
            minute=0,
            timezone=nigeria_tz
        ),
        id="expiry_reminders",
        name="Subscription Expiry Reminders",
        replace_existing=True
    )

    scheduler.start()
    logger.info("✅ Scheduler started — Weekly summaries every Sunday at 8PM Nigeria time")
    return scheduler