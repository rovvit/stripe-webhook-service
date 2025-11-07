from tortoise import fields, models
from datetime import datetime, timezone

class TelegramUser(models.Model):
    tg_chat_id = fields.BigIntField(primary_key=True)
    tg_user = fields.CharField(max_length=256, unique=True, null=False)
    is_admin = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "telegram_user"

class PaymentIntent(models.Model):
    id = fields.CharField(max_length=128, pk=True)
    amount = fields.IntField()
    currency = fields.CharField(max_length=10)
    status = fields.CharField(max_length=50)
    description = fields.CharField(max_length=128, null=True)
    statement = fields.CharField(max_length=128, null=True)
    tg_chat_id = fields.CharField(max_length=128, null=True)
    email = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField()
    updated = fields.DatetimeField(auto_now=False, default=datetime(1970, 1, 1, tzinfo=timezone.utc))

    class Meta:
        table = "payment"

class Charge(models.Model):
    id = fields.CharField(max_length=128, pk=True)
    amount = fields.IntField()
    currency = fields.CharField(max_length=10)
    status = fields.CharField(max_length=50)
    payment_intent = fields.ForeignKeyField(
    "models.PaymentIntent",
    related_name="charges",
    null=True,
    on_delete=fields.SET_NULL
)
    created_at = fields.DatetimeField()
    updated = fields.DatetimeField(auto_now=False, default=datetime(1970, 1, 1, tzinfo=timezone.utc))
    receipt_url = fields.CharField(max_length=256)
    email = fields.CharField(max_length=128, null=True)
    phone = fields.CharField(max_length=16, null=True)

    class Meta:
        table = "charge"

class Customer(models.Model):
    id = fields.CharField(max_length=128, pk=True)
    name = fields.CharField(max_length=128, default=None, null=True)
    email = fields.CharField(max_length=128, default=None, null=True)
    phone = fields.CharField(max_length=128, default=None, null=True)
    telegram_tag = fields.CharField(max_length=128, default=None, null=True)
    telegram_chat_id = fields.IntField(default=None, null=True)
    description = fields.CharField(max_length=128, default=None, null=True)

    created_at = fields.DatetimeField()
    updated = fields.DatetimeField(auto_now=False, default=datetime(1970, 1, 1, tzinfo=timezone.utc))

    class Meta:
        table = "customer"

class Subscription(models.Model):
    id = fields.CharField(pk=True, max_length=128)
    status = fields.CharField(max_length=64, default='inactive')
    customer = fields.ForeignKeyField(
        "models.Customer",
        related_name="subscription",
        null=True,
        on_delete=fields.SET_NULL
    )
    started = fields.DatetimeField(default=None)
    ending = fields.DatetimeField(default=None)
    url = fields.CharField(max_length=256, default=None)
    created = fields.DatetimeField(auto_now=False, default=datetime(1970, 1, 1, tzinfo=timezone.utc))
    updated = fields.DatetimeField(auto_now=False, default=datetime(1970, 1, 1, tzinfo=timezone.utc))
    class Meta:
        table = "subscription"
