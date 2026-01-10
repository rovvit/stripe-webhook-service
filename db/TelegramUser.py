from tortoise.exceptions import DoesNotExist
from datetime import datetime, timezone

from utils.logger import logger
from db.models import TelegramUser, Customer
from typing import Optional

async def get_telegram_user(
        email: Optional[str] = None,
        username: Optional[str] = None,
        user_id: Optional[int] = None):
    """
    Search for TelegramUser.
    Priority:
      1) user_id
      2) username
      3) email

    Returns object TelegramUser or None.
    """
    logger.info(f"[GET TG USER] Trying to find Telegram User with {locals().items()}...")
    if user_id is not None:
        try:
            tgu = await TelegramUser.get(user_id=user_id)
            logger.debug(f"[GET TG USER] Found Telegram User by id {user_id}")
            return tgu
        except DoesNotExist:
            logger.debug(f"[GET TG USER] No Telegram User found by id {user_id}")

    if username is not None:
        try:
            tgu = await TelegramUser.get(username=username)
            logger.debug(f"[GET TG USER] Found Telegram User by username {username}")
            return tgu
        except DoesNotExist:
            logger.debug(f"[GET TG USER] No Telegram User found by username {username}")

    if email is not None:
        try:
            tgu = await TelegramUser.get(email=email)
            logger.debug(f"[GET TG USER] Found Telegram User by email {email}")
            return tgu
        except DoesNotExist:
            logger.debug(f"[GET TG USER] No Telegram User found by email {email}")

    logger.info(f"[GET TG USER] No Telegram User found")
    return None

async def create_telegram_user(
        user_id: int = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        subscription_status: Optional[bool] = False,
        full_name: Optional[str] = None
):
    data = {k: v for k, v in locals().items() if v is not None}
    telegram_user = await TelegramUser.create(**data)
    return telegram_user

async def update_telegram_user_from_event(event):
    """
    Universal update of TelegramUser based on Stripe events.

    event: Stripe webhook event object (event.data.object)
    """

    logger.info(f"[UPDATE TG USER] Updating Telegram User from event {event.type} {event.id}")

    data = event.data.object
    customer_id = data.customer

    # Fetch the Customer and prefetch the related TelegramUser
    customer = await Customer.filter(id=customer_id).prefetch_related("user_id").first()
    if not customer or not customer.user_id:
        logger.info(f"[UPDATE TG USER] No customer found!")
        return

    user = customer.user_id

    # Always update cancel_at_period_end if the field exists
    if hasattr(data, "cancel_at_period_end"):
        logger.info(f"[UPDATE TG USER] Successfully updated cancel_at_period_end for {user.id}!")
        user.cancel_at_period_end = data.cancel_at_period_end

    if event.type == "customer.subscription.updated":
        if hasattr(data, "current_period_end"):
            period_end = datetime.fromtimestamp(data.current_period_end, tz=timezone.utc)
            logger.info(f"[UPDATE TG USER] Successfully updated period end date {period_end} for {user.id}")
            user.date_end = period_end

    # If the event is invoice.paid, also update the subscription end date
    if event.type == "invoice.paid":
        if hasattr(data, "lines") and len(data.lines.data) > 0:
            period_end = data.lines.data[0].period.end
            logger.info(f"[UPDATE TG USER] Successfully updated prolongation and date {period_end} for {user.id}!")
            user.date_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

    # If the event is subscription.deleted updating end date
    elif event.type == "customer.subscription.deleted":
        user.date_end = datetime.fromtimestamp(data.ended_at, tz=timezone.utc)
        logger.info(f"[UPDATE TG USER] Successfully updated ended_at for deletion")

    await user.save()

