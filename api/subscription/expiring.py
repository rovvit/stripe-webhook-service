from datetime import datetime, timedelta, UTC

from db.models import TelegramUser
from utils.logger import logger
from .router import router

@router.get("/expiring")
async def get_expiring_subscriptions(days: int = 5, end_date: datetime = datetime.now().date()):
    if days <= 0:
        days = 1

    end = datetime(end_date.year, end_date.month, end_date.day).replace(hour=23, minute=59, second=59)
    start_date = end_date - timedelta(days=days)

    users = await TelegramUser.filter(
        date_end__gte=start_date,
        date_end__lt=end,
        subscription_status=True,
        is_admin=False
    ).all()

    logger.info(f"[GET EXPIRING SUBS] Found subscriptions: {users} and tg users:")
    user_ids = [
        {
            "user_id": user.user_id,
            "date_end": user.date_end
        }
        for user in users]

    return user_ids