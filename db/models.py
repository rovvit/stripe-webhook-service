from tortoise import fields, models
from datetime import datetime, timezone

class TelegramUser(models.Model):
    id = fields.IntField(pk=True)
    user_id = fields.BigIntField(unique=True)
    username = fields.CharField(max_length=256, unique=True, null=False)
    email = fields.CharField(max_length=255, null=True, unique=True)
    subscription_status = fields.BooleanField(default=False, null=False)
    date_end = fields.DatetimeField(auto_now=False, tzinfo=timezone.utc, null=True, default=None)
    is_admin = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    class Meta:
        table = "telegram_user"

class StripeTable(models.Model):
    id = fields.CharField(max_length=128, pk=True)
    created_at = fields.DatetimeField(auto_now=False, default=datetime(1970, 1, 1, tzinfo=timezone.utc))
    updated = fields.DatetimeField(auto_now=False, default=datetime(1970, 1, 1, tzinfo=timezone.utc))
    class Meta:
        abstract = True

class PaymentIntent(StripeTable):
    amount = fields.IntField()
    currency = fields.CharField(max_length=10)
    status = fields.CharField(max_length=50)
    description = fields.CharField(max_length=128, null=True)
    statement = fields.CharField(max_length=128, null=True)
    email = fields.CharField(max_length=255, null=True)
    class Meta:
        table = "payment"

class Charge(StripeTable):
    amount = fields.IntField()
    currency = fields.CharField(max_length=10)
    status = fields.CharField(max_length=50)
    payment_intent = fields.ForeignKeyField(
    "models.PaymentIntent",
    related_name="charges",
    null=True,
    on_delete=fields.SET_NULL
    )
    receipt_url = fields.CharField(max_length=256)
    email = fields.CharField(max_length=128, null=True)
    phone = fields.CharField(max_length=16, null=True)
    class Meta:
        table = "charge"

class Customer(StripeTable):
    name = fields.CharField(max_length=128, default=None, null=True)
    email = fields.CharField(max_length=128, default=None, null=True)
    phone = fields.CharField(max_length=128, default=None, null=True)
    username = fields.CharField(max_length=128, default=None, null=True)
    description = fields.CharField(max_length=128, default=None, null=True)
    user_id = fields.ForeignKeyField(
        "models.TelegramUser",
        related_name="customer",
        on_delete=fields.SET_NULL,
        null=True
    )
    class Meta:
        table = "customer"

class Subscription(StripeTable):
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
    class Meta:
        table = "subscription"
