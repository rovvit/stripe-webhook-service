from pydantic import BaseModel
from typing import Optional

from datetime import datetime, timedelta, UTC

from db.models import Subscription
from db.models import TelegramUser
from utils.logger import logger
from fastapi import HTTPException, APIRouter
from starlette.responses import JSONResponse
from db.Subscription import get_subscriptions
from db.TelegramUser import get_telegram_user, create_telegram_user
from db.Customer import get_customers
from .router import router

@router.get("/expiring")
async def get_expiring_subscriptions(days: int = 5):
    now = datetime.now(UTC)
    start = now + timedelta(days=days)
    end = start + timedelta(days=1)

    users = await TelegramUser.filter(
        date_end__gte=start,
        date_end__lt=end,
        subscription_status=True
    ).all()

    logger.info(f"[GET EXPIRING SUBS] Found subscriptions: {users} and tg users:")
    user_ids = [user["user_id"] for user in users]

    return user_ids





