from pydantic import BaseModel
from fastapi import Response, status
from db.models import TelegramUser
from utils.logger import logger
from .router import router

class BanUserRequest(BaseModel):
    user_id: int

@router.post("/ban")
async def update_telegram_user_set_status_false(request: BanUserRequest):
    try:
        uid = request.user_id
    except Exception:
        logger.error(f"[BAN] No user_id passed!")
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    if not uid:
        logger.info(f"[BAN] No user id passed, skipped.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    tgu = await TelegramUser.get_or_none(user_id=uid)
    if not tgu:
        logger.info(f"[BAN] User {uid} not found, skipped.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    try:
        tgu.subscription_status = False
        await tgu.save()
        logger.info(f"[BAN] User {uid} subscription status switch to False.")
        return {'success': True}
    except Exception as e:
        logger.error(f"[BAN] Error occurred: {e}")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)