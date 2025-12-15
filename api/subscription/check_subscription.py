from pydantic import BaseModel
from typing import Optional

from utils.logger import logger
from fastapi import HTTPException, APIRouter
from starlette.responses import JSONResponse
from db.Subscription import get_subscriptions
from db.TelegramUser import get_telegram_user, create_telegram_user
from db.Customer import get_customers
from .router import router

class SubscriptionCheckRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    user_id: Optional[int] = None

@router.post("/check")
async def check_subscription(payload: SubscriptionCheckRequest):
    try:
        data = {k: v for k, v in {
            "email": payload.email,
            "username": payload.username,
            "user_id": payload.user_id
        }.items() if v is not None}
        logger.info(f"filters: {data}, types: {[type(v) for v in data.values()]}")

        if not data:
            return JSONResponse({"error": "Bad filters passed"}, status_code=400)

        logger.info(f"[CHECK SUBSCRIPTION] New request with data {data.items()}...")

        telegram_user = await get_telegram_user(**data)
        if telegram_user:
            logger.info(f"[CHECK SUBSCRIPTION] Found Telegram User! {telegram_user.user_id}")
        else:
            telegram_user = await create_telegram_user(**data)

        logger.info(f"[CHECK SUBSCRIPTION] Telegram User not found, searching for customer...")
        customers = await get_customers(email=data.get('email'), username=data.get('username'))

        if not customers:
            logger.info(f"[CHECK SUBSCRIPTION] No customer found {data.keys()} {data.values()}")
            return JSONResponse({"message": "No customer found", "subscription_status": False}, status_code=200)

        for cus in customers:
            cus.user_id = telegram_user
            await cus.save()

            cid = cus.id
            subscriptions = await get_subscriptions({"customer_id": cid})
            active_sub = None
            for sub in subscriptions:
                if sub.status == "active":
                    telegram_user.subscription_status = True
                    telegram_user.date_end = sub.ending
                    await telegram_user.save()
                    active_sub = sub
                    break

            if active_sub:
                logger.info(f"[CHECK SUBSCRIPTION] Found subscription for {cid} {subscriptions}")
                return telegram_user

        logger.info(f"[CHECK SUBSCRIPTION] Subscription not found for {customers}")
        return {"subscription_status": False, "message": "Not found subscription for customer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[CHECK SUBSCRIPTION] Unexpected error")
        return {"error": "Internal Server Error", "detail": str(e)}