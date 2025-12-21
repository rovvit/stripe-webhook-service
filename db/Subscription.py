from datetime import datetime, timezone, UTC

from utils.logger import logger
from db.models import Subscription, Customer

async def save_subscription(event):
    body =event.get('data').get('object')
    customer = await Customer.get_or_none(id=body.get('customer'))
    data = {
      "id": body.get('id'),
      "status": body.get("status"),
      "customer": customer,
      "started": datetime.fromtimestamp(body.get("current_period_start"), tz=timezone.utc),
      "ending": datetime.fromtimestamp(body.get("current_period_end"), tz=timezone.utc),
      "created_at": datetime.fromtimestamp(event.get("created"), tz=timezone.utc),
      "url": body.get("items").get("url"),
      "cancel_at_period_end": body.get("cancel_at_period_end")
    }

    data = {k: v for k, v in data.items() if v not in (None, "", [])}
    logger.info(f"[INFO] Starting saving subscription {data.get('id')} for customer {data.get('customer')} from {data}")

    try:
        existing = await Subscription.get_or_none(id=data.get('id'))

        if not existing:
            await Subscription.create(
                updated=data.get('created'),
                **data
            )
            logger.info(f"[NEW] Created subscription {data.get('id')}")
            return

        # if data.get('created_at') > existing.updated:
        #     await existing.update_from_dict(data).save()
        #     logger.info(f"[UPDATE] Updated subscription {data.get('id')}")
        # else:
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