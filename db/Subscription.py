from datetime import datetime

from utils.logger import logger
from db.models import Subscription

async def save_subscription(event):
    body =event.get('data').get('object')
    data = {
      "id": body.get('id'),
      "status": body.get("status"),
      "customer_id": body.get('customer'),
      "started": datetime.fromtimestamp(body.get("current_period_start")),
      "ending": datetime.fromtimestamp(body.get("current_period_end")),
      "created": datetime.fromtimestamp(event.get("created")),
      "url": body.get("items").get("url")
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

        if data.get('created') > existing.updated:
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

async def get_subscription(filters: dict):
    subscription = await Subscription.filter(**filters).order_by('-updated').first()
    logger.info(f"[GET SUBSCRIPTION] Looking for subscription {filters}")
    return subscription.status