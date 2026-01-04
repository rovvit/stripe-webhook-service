from datetime import datetime, timezone, UTC
from utils.logger import logger
from db.models import Customer
from tortoise.expressions import Q
from tortoise.exceptions import IntegrityError

from utils.make_aware import make_aware


async def save_customer(event):
    customer = event.get("data").get("object")
    customer_id = customer.get("id")
    created_event = event.get("created")
    logger.info(f"[INFO] Starting saving charge {customer_id}")

    try:
        await Customer.create(
            id=customer_id,
            name=customer.get("name"),
            email=customer.get("email"),
            phone=customer.get("phone"),
            description=customer.get("description"),
            created_at=datetime.fromtimestamp(customer.get("created"), tz=UTC),
            updated=created_event,
        )
        logger.info(f"[NEW] Created Customer {customer_id}")

    except IntegrityError:
        existing = await Customer.get(id=customer_id)
        existing_updated = make_aware(existing.updated)

        if created_event > existing_updated:
            await existing.update_from_dict({
                "name": customer.get("name"),
                "email": customer.get("email"),
                "phone": customer.get("phone"),
                "description": customer.get("description"),
                "updated": created_event,
            }).save()
            logger.info(f"[UPDATE] Updated Charge {customer_id} (newer timestamp)")
            return
        else:
            logger.info(f"[SKIP] Ignored outdated event for {customer_id}")
    except Exception as e:
        logger.error(f"[ERROR] [CUSTOMER_SAVE] {e}")


async def update_customer_username_from_checkout_session(event):
    body = event.get("data").get("object")
    customer_id = body.get("customer")
    custom_fields = body.get("custom_fields")
    telegram_tag = None
    logger.info(f"[UPDATE USERNAME] Starting saving telegram username for customer_id={customer_id}")

    for field in custom_fields:
        key = field.get("key")
        if isinstance(key, str) and (key.lower() == "telegramusername" or key.lower() == "telegram"):
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
        logger.info(f"[UPDATE USERNAME] Normalized username is {telegram_tag}")

    if not telegram_tag:
        logger.error(f"[UPDATE USERNAME] Telegram tag not found in request body, skipping update for {customer_id}")
        return

    try:
        created_event = datetime.fromtimestamp(event.get("created"), tz=UTC)

        await Customer.update_or_create(
            defaults={
                "telegram_tag": telegram_tag,
                "updated": created_event,
            },
            **{"id": customer_id}
        )
        logger.info(f"[UPDATE USERNAME] Successfully updated {customer_id} with {telegram_tag}")

    except Exception as e:
        logger.error(f"[ERROR] [UPDATE USERNAME] {e}")


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
