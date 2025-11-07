import os
import json
import stripe
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from starlette.responses import JSONResponse
from tortoise import Tortoise
from tortoise_config import TORTOISE_ORM
from utils.logger import logger
from db.PaymentIntent import save_payment_intent
from db.Charge import save_charge
from db.Customer import save_customer, update_telegram_from_checkout_session, get_customer
from db.Subscription import save_subscription, get_subscription
from dotenv import load_dotenv

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


@app.get('/api/check_subcription/')
async def check_payment_by(telegram_tag: str = None, email: str = None):
    filters = {k: v for k, v in {
        "telegram_tag": telegram_tag,
        "email": email
    }.items() if v is not None}

    if not filters:
        return JSONResponse({"error": "Bad filters passed"}, status_code=400)

    logger.info(f"[CHECK SUBSCRIPTION] Looking for payment by {filters.keys()}...")

    customer_id = await get_customer(**filters)
    if not customer_id:
        logger.info(f"[CHECK SUBSCRIPTION] No customer found {filters.keys()} {filters.values()}")
        return JSONResponse({"message": "No customer found", "paid": False}, status_code=200)

    payment_status = await get_subscription({"customer_id": customer_id})
    logger.info(f"[CHECK SUBSCRIPTION] Found successful payment intent for {customer_id} {payment_status}")
    return {"paid": payment_status, "message": "Found subscription for customer"}


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
