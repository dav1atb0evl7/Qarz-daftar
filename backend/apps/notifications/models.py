from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import BaseModel
from apps.shops.models import Shop
from apps.customers.models import Customer
from apps.debts.models import Debt


class NotificationChannel(models.TextChoices):
    TELEGRAM = "TELEGRAM", _("Telegram")
    EMAIL = "EMAIL", _("Email")
    SMS = "SMS", _("SMS")


class NotificationType(models.TextChoices):
    DUE_REMINDER = "DUE_REMINDER", _("Upcoming Due Reminder")
    OVERDUE_ALERT = "OVERDUE_ALERT", _("Overdue Debt Alert")
    PAYMENT_RECEIPT = "PAYMENT_RECEIPT", _("Payment Receipt Confirmation")
    DEBT_CREATED = "DEBT_CREATED", _("New Debt Recorded")


class NotificationStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    SENT = "SENT", _("Sent")
    FAILED = "FAILED", _("Failed")


class NotificationPreference(BaseModel):
    """
    Shop-specific notification preferences and settings.
    """
    shop = models.OneToOneField(
        Shop,
        on_delete=models.CASCADE,
        related_name="notification_preference",
        verbose_name=_("shop")
    )
    enable_telegram = models.BooleanField(_("enable telegram notifications"), default=True)
    enable_email = models.BooleanField(_("enable email notifications"), default=False)
    enable_due_date_reminders = models.BooleanField(_("enable due date reminders"), default=True)
    reminder_days_before = models.PositiveSmallIntegerField(
        _("days before due date to remind"),
        default=1,
        help_text=_("Send reminder N days before the debt due date")
    )
    enable_overdue_alerts = models.BooleanField(_("enable overdue debt alerts"), default=True)
    enable_payment_receipts = models.BooleanField(_("send payment receipt confirmation"), default=True)

    class Meta:
        verbose_name = _("notification preference")
        verbose_name_plural = _("notification preferences")

    def __str__(self):
        return f"Notification Preferences for {self.shop.name}"


class NotificationLog(BaseModel):
    """
    Audit log of all sent notifications with deduplication via idempotency_key.
    """
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("shop")
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="notifications",
        verbose_name=_("customer")
    )
    debt = models.ForeignKey(
        Debt,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="notifications",
        verbose_name=_("debt")
    )
    channel = models.CharField(
        _("channel"),
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.TELEGRAM
    )
    recipient = models.CharField(_("recipient address / chat ID"), max_length=255)
    notification_type = models.CharField(
        _("type"),
        max_length=30,
        choices=NotificationType.choices
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True
    )
    message_body = models.TextField(_("message body"))
    idempotency_key = models.CharField(
        _("idempotency key"),
        max_length=128,
        unique=True,
        db_index=True,
        help_text=_("Prevents sending duplicate notifications")
    )
    sent_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _("notification log")
        verbose_name_plural = _("notification logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["shop", "status"]),
            models.Index(fields=["idempotency_key"]),
        ]

    def __str__(self):
        return f"{self.notification_type} to {self.recipient} [{self.status}]"
