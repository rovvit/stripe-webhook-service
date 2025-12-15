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
    limit_date = now + timedelta(days=days)

    users = await TelegramUser.filter(
        date_end__gte=now,
        date_end__lte=limit_date,
        subscription_status=True  # если нужно учитывать только активные
    ).all()

    logger.info(f"[GET EXPIRING SUBS] Found subscriptions: {users} and tg users:")

    return 0





