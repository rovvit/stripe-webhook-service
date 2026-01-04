from datetime import datetime, timezone, UTC

from db.TelegramUser import update_telegram_user_from_event
from utils.logger import logger
from utils.make_aware import make_aware
from db.models import Subscription, Customer


async def save_subscription(event):
    body =event.get('data').get('object')
    customer = await Customer.get_or_none(id=body.get('customer'))
    data = {
      "id": body.get('id'),
      "status": body.get("status"),
      "customer": customer,
      "started": datetime.fromtimestamp(body.get("current_period_start"), tz=UTC),
      "ending": datetime.fromtimestamp(body.get("current_period_end"), tz=UTC),
      "created_at": datetime.fromtimestamp(event.get("created"), tz=UTC),
      "url": body.get("items").get("url"),
      "cancel_at_period_end": body.get("cancel_at_period_end")
    }

    data = {k: v for k, v in data.items() if v not in (None, "", [])}
    logger.info(f"[INFO] Starting saving subscription {data.get('id')} for customer {data.get('customer')} from {data}")

    try:
        existing = await Subscription.get_or_none(id=data.get('id'))

        if not existing:
            updated = data.get('created_at') or datetime.now(UTC)
            await Subscription.create(
                updated=updated,
                **data
            )
            logger.info(f"[NEW] Created subscription {data.get('id')}")
            return

        existing_updated = make_aware(existing.updated)
        if data.get('created_at') and data.get('created_at') > existing_updated:
            await existing.update_from_dict(data).save()
            logger.info(f"[UPDATE] Updated subscription {data.get('id')}")
        else:
            partial_update = {
                k: v for k, v in data.items()
                if getattr(existing, k) in (None, "", [])
            }
            if partial_update:
                await existing.update_from_dict(partial_update).save()
                logger.info(f"[UPDATE] Partially updated subscription {data.get('id')}")
            else:
                logger.info(f"[SKIP] No new data for subscription {data.get('id')}, skipped")

    except Exception as e:
        logger.error(f"[ERROR] [SUBSCRIPTION] {e}")


async def get_subscriptions(filters: dict):
    logger.info(f"[GET SUBSCRIPTION] Looking for subscriptions by {filters}")

    subscriptions = await Subscription.filter(**filters).order_by('-updated')

    if subscriptions is None:
        logger.info("[GET SUBSCRIPTION] No subscription found")
        return []

    return subscriptions

async def delete_subscription(event):
    body = event.get('data').get('object')
    sub_id = body.get('id')
    status = body.get('status')
    ended_at = datetime.fromtimestamp(body.get('ended_at'), tz=UTC)
    subscription = get_subscriptions({"id": sub_id})

    if not subscription:
        logger.info(f"[DELETE SUBSCRIPTION] No subscription {sub_id} found, skipped")

    subscription.status = status
    subscription.ending = ended_at
    try:
        await subscription.save()
        logger.info(f"[DELETE SUBSCRIPTION] Updated subscription {sub_id}")
    except Exception as e:
        logger.error(f"[DELETE SUBSCRIPTION] {e}")

    await update_telegram_user_from_event(event)
