import os
import json
import stripe
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from starlette.responses import JSONResponse
from tortoise import Tortoise
from db.TelegramUser import get_telegram_user, create_telegram_user
from tortoise_config import TORTOISE_ORM
from utils.logger import logger
from db.PaymentIntent import save_payment_intent
from db.Charge import save_charge
from db.Customer import save_customer, update_telegram_from_checkout_session, get_customers
from db.Subscription import save_subscription, get_subscriptions
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional

load_dotenv()

logger.info('Started webhook service')

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
    logger.info("Tortoise ORM initialized")
    try:
        yield
    finally:
        await Tortoise.close_connections()
        logger.info("Tortoise ORM connections closed")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


class SubscriptionCheckRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    user_id: Optional[int] = None


@app.post("/api/check_subscription/")
async def check_payment_by(payload: SubscriptionCheckRequest):
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
            return telegram_user

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
        raise  # пробрасываем HTTP ошибки как есть
    except Exception as e:
        logger.exception("[CHECK SUBSCRIPTION] Unexpected error")
        return {"error": "Internal Server Error", "detail": str(e)}


@app.post("/stripe_webhook")
async def webhook_handler(request: Request):
    event = None
    is_processed = False
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", None)
    if sig_header is None:
        logger.error("Missing Stripe‑Signature header")
        return JSONResponse({"error": "Missing Stripe‑Signature header"}, status_code=400)

    try:
        event = stripe.Event.construct_from(
            json.loads(payload),
            sig_header,
            STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError as e:
        logger.error(e)
        return JSONResponse({"error": "Invalid signature"}, status_code=400)
    except Exception as e:
        logger.error(e)
        return JSONResponse({"error": str(e)}, status_code=400)

    if "payment_intent" in event.type:
        is_processed = True
        logger.info(f"[RECEIVE] Received payment_intent with status={event.get('type')} event_id={event.get('id')}")
        await save_payment_intent(event)

    elif "charge" in event.type:
        is_processed = True
        logger.info(f"[RECEIVE] Received charge with status={event.get('type')} event_id={event.get('id')}")
        await save_charge(event)

    elif "customer" in event.type:
        logger.info(f"[RECEIVE] Received customer event {event.type}: event_id={event.get('id')}")
        is_processed = True
        if event.type in ["customer.created", "customer.updated"]:
            await save_customer(event)

        elif event.type in ["customer.subscription.created"]:
            await save_subscription(event)

    elif event.type == "checkout.session.completed":
        logger.info(f"[RECEIVE] Received checkout session event {event.type}: event_id={event.get('id')}")
        is_processed = True
        await update_telegram_from_checkout_session(event)

    if not is_processed:
        logger.info(f"[INFO] Unsupported event type {event.type}, ignored.")

    return JSONResponse({"status": "ok"}, status_code=status.HTTP_200_OK)
