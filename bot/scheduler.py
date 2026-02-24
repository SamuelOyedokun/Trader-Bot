from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from bot.db import get_weekly_summary, supabase
from bot.message_handler import send_whatsapp_message
import pytz
import logging

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

    scheduler.start()
    logger.info("✅ Scheduler started — Weekly summaries every Sunday at 8PM Nigeria time")
    return scheduler