from datetime import datetime, timezone
from utils.logger import logger
from db.models import Customer
from tortoise.expressions import Q

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
                normalized = tag.strip()

                if normalized.startswith("@"):
                    normalized = normalized[1:]

                prefixes = [
                    "https://t.me/",
                    "http://t.me/",
                    "t.me/",
                    "https://telegram.me/",
                    "http://telegram.me/",
                    "telegram.me/",
                ]

                for p in prefixes:
                    if normalized.startswith(p):
                        normalized = normalized[len(p):]
                        break

                normalized = normalized.strip("/")

                telegram_tag = normalized or None

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

async def get_customers(*, email=None, name=None, phone=None, username=None):
    fields = {k: v for k, v in locals().items() if v is not None}
    queries = [Q(**{k: v}) for k, v in fields.items()]
    if not queries:
        logger.error("[GET CUSTOMER] No filters was given")
        return None

    query = queries.pop()
    for q in queries:
        query |= q

    customers = await Customer.filter(query)
    customers_info = [
        {'id': c.id, 'email': c.email, 'username': c.username, 'phone': c.phone}
        for c in customers
    ]

    if customers:
        logger.info(f"[GET CUSTOMER] Found customers {customers_info} by {fields}")
    else:
        logger.info(f"[GET CUSTOMER] No customer found by {fields}")
    return customers