from tortoise.exceptions import DoesNotExist

from utils.logger import logger
from db.models import TelegramUser
from typing import Optional

async def get_telegram_user(
        email: Optional[str],
        username: Optional[str],
        user_id: Optional[int]):
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
        user_id: int,
        username: Optional[str],
        email: Optional[str],
        subscription_status: Optional[bool] = False
):
    telegram_user = await TelegramUser.create(*locals().items())
    return telegram_user

async def update_telegram_user():
    pass

