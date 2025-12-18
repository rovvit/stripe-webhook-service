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
    start = datetime(start_date.year, start_date.month, start_date.day).replace(hour=00, minute=00, second=00)

    users = await TelegramUser.filter(
        date_end__gte=start,
        date_end__lte=end,
        subscription_status=True,
        is_admin=False
    ).all()

    logger.info(f"[GET EXPIRING SUBS] Found subscriptions: {users}.")
    user_ids = [
        {
            "user_id": user.user_id,
            "date_end": user.date_end
        }
        for user in users]

    return user_ids