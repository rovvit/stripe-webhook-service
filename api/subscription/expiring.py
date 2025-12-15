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

    subscriptions = await Subscription.filter(
        ending__gte=now,
        ending__lte=limit_date,
        status="active",
    ).select_related("customer", "customer__user_id")

    telegram_users = await TelegramUser.filter(
        customer__subscription__ending__gte=now,
        customer__subscription__ending__lte=limit_date,
        customer__subscription__status="active",
    ).distinct()

    logger.info(f"[GET EXPIRING SUBS] Found subscriptions: {subscriptions} and tg users: {telegram_users}")





