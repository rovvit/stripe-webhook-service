from contextlib import asynccontextmanager
from fastapi import FastAPI
from tortoise import Tortoise
from tortoise_config import TORTOISE_ORM
from utils.logger import logger
from api.subscription.check_subscription import router as sub_router
from api.webhook.stripe_webhook import router as webhook_router

logger.info('Started webhook service')

@asynccontextmanager
async def lifespan(app: FastAPI):
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
    logger.info("Tortoise ORM initialized")
    try:
        yield
    finally:
        await Tortoise.close_connections()
        logger.info("Tortoise ORM connections closed")


app = FastAPI(lifespan=lifespan)
app.include_router(sub_router, prefix="/api")
app.include_router(webhook_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}