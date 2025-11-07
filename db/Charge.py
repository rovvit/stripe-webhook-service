from datetime import datetime
from tortoise.transactions import in_transaction
from utils.logger import logger
from db.models import Charge
from db.PaymentIntent import fulfill_payment_intent, save_empty_payment_intent_from_charge


async def save_charge(event):
    charge = event.get("data").get("object")
    charge_id = charge.get("id")
    created_event = event.get("created")
    logger.info(f"[INFO] Starting saving charge {charge_id}")

    try:
        async with in_transaction():
            await save_empty_payment_intent_from_charge(charge)
            existing = await Charge.get_or_none(id=charge_id)

            if not existing:
                await Charge.create(
                    id=charge_id,
                    payment_intent_id=charge.get("payment_intent"),
                    amount=charge.get("amount"),
                    currency=charge.get("currency"),
                    status=charge.get("status"),
                    receipt_url=charge.get("receipt_url"),
                    email=charge.get("billing_details").get("email"),
                    created_at=datetime.now()
                )
                logger.info(f"[NEW] Created Charge {charge_id}")
                return

            if created_event and created_event > datetime.timestamp(existing.updated):
                await existing.update_from_dict({
                    "status": charge.get("status"),
                    "updated": datetime.now()
                }).save()
                logger.info(f"[UPDATE] Updated Charge {charge_id} (newer timestamp)")
            else:
                logger.info(f"[SKIP] Ignored outdated event for {charge_id}")

            await fulfill_payment_intent(charge.get("payment_intent"))
    except Exception as e:
        logger.error(f"[ERROR] {e}")