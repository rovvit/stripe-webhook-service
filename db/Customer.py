from datetime import datetime, timezone
from utils.logger import logger
from db.models import Customer

async def save_customer(event):
    customer = event.get("data").get("object")
    customer_id = customer.get("id")
    created_event = event.get("created")
    logger.info(f"[INFO] Starting saving charge {customer_id}")

    try:
        existing = await Customer.get_or_none(id=customer_id)

        if (not existing) or (created_event > datetime.timestamp(existing.updated)):
            await Customer.update_or_create(
                id=customer_id,
                name=customer.get("name"),
                email=customer.get("email"),
                phone=customer.get("phone"),
                description=customer.get("description"),
                created_at=datetime.fromtimestamp(customer.get("created")),
                updated=datetime.fromtimestamp(created_event),
            )
            if not existing:
                logger.info(f"[NEW] Created Customer {customer_id}")
            else:
                logger.info(f"[UPDATE] Updated Charge {customer_id} (newer timestamp)")
            return

        else:
            logger.info(f"[SKIP] Ignored outdated event for {customer_id}")
    except Exception as e:
        logger.error(f"[ERROR] [CUSTOMER_SAVE] {e}")

async def update_telegram_from_checkout_session(event):
    body = event.get("data").get("object")
    customer_id = body.get("customer")
    custom_fields = body.get("custom_fields")
    telegram_tag = None
    logger.info(f"[INFO] Starting saving telegram tag for customer_id={customer_id}")

    for field in custom_fields:
        key = field.get("key")
        if isinstance(key, str) and "telegram" in key.lower():
            text = field.get("text", {})
            tag = text.get("value")

            if isinstance(tag, str):
                telegram_tag = tag.strip().lstrip("@")
            else:
                telegram_tag = None

    try:
        existing = await Customer.get_or_none(id=customer_id)
        if telegram_tag:
            if not existing:
                await Customer.update_or_create(
                    defaults={
                        "telegram_tag": telegram_tag,
                        "updated": datetime.fromtimestamp(event.get("created")),
                    },
                    id=customer_id,
                )
            else:
                await existing.update_or_create(
                    defaults={
                        "telegram_tag": telegram_tag,
                        "created_at": datetime(1970, 1, 1, tzinfo=timezone.utc),
                        "updated": datetime.fromtimestamp(event.get("created")),
                    },
                    id=customer_id,
                )
        else:
            logger.error(f"Telegram tag not found in request body, updating customer {customer_id} skipped")
    except Exception as e:
        logger.error(f"[ERROR] [CUSTOMER_UPDATE_TG] {e}")

async def get_customer(*, email=None, name=None, phone=None, telegram_tag=None):
    filters = {k: v for k, v in locals().items() if v is not None}
    if not filters:
        logger.error("[GET CUSTOMER] No filters was given")
        return None
    query = await Customer.get_or_none(**filters)
    if query:
        logger.info(f"[GET CUSTOMER] Found customer {query.id} by {filters.keys()}")
        return query.id
    else:
        logger.info(f"[GET CUSTOMER] No customer found by {filters.keys()}")
        return None


# """
# {
#   "created": 1762336003,
#   "data": {
#     "object": {
#       "created": 1762335982,
#       "custom_fields": [
#         {
#           "key": "telegram",
#           "label": {
#             "custom": "Telegram",
#             "type": "custom"
#           },
#           "text": {
#             "default_value": null,
#             "maximum_length": null,
#             "minimum_length": null,
#             "value": "telelelel"
#           },
#         }
#       ],
#       "customer": "cus_TMmsfyGpy24Od0",
#       "customer_details": {
#         "email": "email@example.com",
#         "name": "imya vvvvv",
#         "phone": null,
#       },
#       "expires_at": 1762422382,
#       "mode": "subscription",
#       "object": "checkout.session",
#       "payment_status": "paid",
#       "status": "complete",
#       "subscription": "sub_1SQ3IbC6yWgQqHtJmtoslpgE",
#     }
#   },
#   "id": "evt_1SQ3IdC6yWgQqHtJHsNR42qL",
#   "object": "event",
#   "type": "checkout.session.completed"
# }
# """