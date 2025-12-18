from datetime import datetime, timedelta, UTC

from db.models import TelegramUser
from utils.logger import logger
from .router import router

@router.get("/expiring")
async def get_expiring_subscriptions(days: int = 5):
    now = datetime.now(UTC)
    start = now + timedelta(days=days)
    end = start + timedelta(days=1)

    users = await TelegramUser.filter(
        date_end__gte=start,
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

@router.get('/expired')
async def get_expired_subscriptions():
    end = datetime.now(UTC)
    start = end - timedelta(days=1)

    users = await TelegramUser.filter(
        date_end__gte=start,
        date_end__lt=end,
        subscription_status=True,
        is_admin=False
    ).all()

    logger.info(f"[GET EXPIRED SUBS] Found subscriptions than expired today: {users}")
    user_ids = [
        {
            "user_id": user.user_id,
            "date_end": user.date_end
        }
        for user in users]

    return user_ids

