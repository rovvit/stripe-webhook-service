from datetime import datetime, timedelta
from asyncpg import UniqueViolationError
from tortoise.transactions import in_transaction
from utils.logger import logger
from db.models import PaymentIntent

async def save_payment_intent(event):
    intent = event["data"]["object"]
    intent_id = intent.get("id")
    created_event = event.get("created")

    async with in_transaction():
        existing = await PaymentIntent.get_or_none(id=intent_id)

        if not existing:
            try:
                await PaymentIntent.create(
                    id=intent_id,
                    created_at=datetime.fromtimestamp(intent.get("created")),
                    updated=datetime.fromtimestamp(intent.get("created")),
                    amount=intent.get("amount"),
                    currency=intent.get("currency"),
                    email=intent.get("receipt_email"),
                    status=intent.get("status"),
                    statement=intent.get("statement_descriptor"),
                    description=intent.get("description"),
                )
                logger.info(f"[NEW] Created PaymentIntent {intent_id}")
                return
            except UniqueViolationError:
                logger.warning(f"[RACE] PaymentIntent {intent_id} already exists (created concurrently)")
                existing = await PaymentIntent.get(id=intent_id)


        if created_event and created_event > datetime.timestamp(existing.updated):
            await existing.update_from_dict({
                "amount": intent.get("amount"),
                "currency": intent.get("currency"),
                "email": intent.get("receipt_email"),
                "status": intent.get("status"),
                "statement": intent.get("statement_descriptor"),
                "description": intent.get("description"),
                "updated": created_event
            }).save()
            logger.info(f"[UPDATE] Updated PaymentIntent {intent_id} (newer timestamp)")
        else:
            logger.info(f"[SKIP] Ignored outdated event for {intent_id}")

async def fulfill_payment_intent(intent_id):
    updated = await PaymentIntent.filter(id=intent_id).update(
        status="succeeded",
        updated=datetime.now()
    )
    if updated == 0:
        logger.info(f"[SKIP] No PaymentIntent found for {intent_id}, skipped")
    else:
        logger.info(f"[UPDATED] PaymentIntent {intent_id} fulfilled successfully")

async def save_empty_payment_intent_from_charge(charge):
    payment_intent_id = charge.get("payment_intent")
    if payment_intent_id:
        payment_intent = await PaymentIntent.get_or_none(id=payment_intent_id)
        if not payment_intent:
            logger.info(f"[PLACEHOLDER] Creating placeholder PaymentIntent {payment_intent_id}")
            await PaymentIntent.create(
                id=payment_intent_id,
                amount=0,
                currency=charge.get("currency", "eur"),
                status="placeholder",
                created_at=datetime.now() - timedelta(days=365),
                updated=datetime.now() - timedelta(days=365)
            )
