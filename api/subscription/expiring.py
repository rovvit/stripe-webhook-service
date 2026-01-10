from datetime import date, datetime, timedelta, UTC

from fastapi import Query
from db.models import TelegramUser
from utils.logger import logger
from .router import router

@router.get("/expiring")
async def get_expiring_subscriptions(days: int = 5, start_date: date = Query(None, description="Format: YYYY-MM-DD") ):
    if not start_date:
        start_date = datetime.now(UTC).date()
    if days <= 0:
        days = 1

    end_date = start_date - timedelta(days=days-1)
    start = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
    end = datetime.combine(end_date, datetime.max.time(), tzinfo=UTC)

    logger.info(f"[GET EXPIRING SUBS] Looking for subs from {start} to {end}")
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