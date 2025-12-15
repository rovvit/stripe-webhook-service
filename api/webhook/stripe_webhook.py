import os
import json
import stripe
from dotenv import load_dotenv
from fastapi import APIRouter, Request, status

from db.PaymentIntent import save_payment_intent
from db.Charge import save_charge
from db.Customer import save_customer, update_customer_username_from_checkout_session
from db.Subscription import save_subscription
from db.TelegramUser import update_telegram_user_from_event
from starlette.responses import JSONResponse
from utils.logger import logger

router = APIRouter(
    tags=["Webhook"],
)

load_dotenv()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/stripe_webhook")
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

        elif event.type in ["customer.subscription.created", "customer.subscription.updated"]:
            await save_subscription(event)
            if event.type == "customer.subscription.updated":
                await update_telegram_user_from_event(event)

    elif "invoice" in event.type:
        if event.type == "invoice.paid":
            await update_telegram_user_from_event(event)

    elif event.type == "checkout.session.completed":
        logger.info(f"[RECEIVE] Received checkout session event {event.type}: event_id={event.get('id')}")
        is_processed = True
        await update_customer_username_from_checkout_session(event)

    if not is_processed:
        logger.info(f"[INFO] Unsupported event type {event.type}, ignored.")

    return JSONResponse({"status": "ok"}, status_code=status.HTTP_200_OK)