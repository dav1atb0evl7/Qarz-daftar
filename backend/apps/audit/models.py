import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.shops.models import Shop
from apps.accounts.models import CustomUser


class AuditAction(models.TextChoices):
    LOGIN = "LOGIN", _("User Login")
    LOGOUT = "LOGOUT", _("User Logout")
    USER_REGISTER = "USER_REGISTER", _("User Registration")
    EMAIL_VERIFIED = "EMAIL_VERIFIED", _("Email Verified")
    PASSWORD_RESET = "PASSWORD_RESET", _("Password Reset")
    PROFILE_UPDATE = "PROFILE_UPDATE", _("Profile Update")
    TELEGRAM_LINKED = "TELEGRAM_LINKED", _("Telegram Linked")
    SHOP_CREATE = "SHOP_CREATE", _("Shop Created")
    SHOP_UPDATE = "SHOP_UPDATE", _("Shop Updated")
    BRANCH_CREATE = "BRANCH_CREATE", _("Branch Created")
    MEMBER_ADDED = "MEMBER_ADDED", _("Member Added")
    MEMBER_UPDATED = "MEMBER_UPDATED", _("Member Updated")
    MEMBER_REMOVED = "MEMBER_REMOVED", _("Member Removed")
    CUSTOMER_CREATE = "CUSTOMER_CREATE", _("Customer Created")
    CUSTOMER_UPDATE = "CUSTOMER_UPDATE", _("Customer Updated")
    CUSTOMER_ARCHIVE = "CUSTOMER_ARCHIVE", _("Customer Archived")
    DEBT_CREATE = "DEBT_CREATE", _("Debt Created")
    DEBT_UPDATE = "DEBT_UPDATE", _("Debt Updated")
    DEBT_CANCEL = "DEBT_CANCEL", _("Debt Cancelled")
    PAYMENT_CREATE = "PAYMENT_CREATE", _("Payment Processed")
    PAYMENT_REVERSE = "PAYMENT_REVERSE", _("Payment Reversed")
    PREFERENCE_UPDATE = "PREFERENCE_UPDATE", _("Preferences Updated")
    EXPORT_REPORT = "EXPORT_REPORT", _("Report Exported")


class AuditSource(models.TextChoices):
    WEB = "WEB", _("Web App / API")
    TELEGRAM_BOT = "TELEGRAM_BOT", _("Telegram Bot")
    SYSTEM = "SYSTEM", _("System / Background Task")


class AuditLog(models.Model):
    """
    Immutable security audit trail for all business and financial operations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
        verbose_name=_("shop")
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name="audit_actions",
        null=True,
        blank=True,
        verbose_name=_("user")
    )
    action = models.CharField(
        _("action"),
        max_length=50,
        choices=AuditAction.choices,
        db_index=True
    )
    source = models.CharField(
        _("source"),
        max_length=30,
        choices=AuditSource.choices,
        default=AuditSource.WEB,
        db_index=True
    )
    entity_type = models.CharField(_("entity type"), max_length=100, db_index=True)
    entity_id = models.CharField(_("entity ID"), max_length=100, db_index=True)
    changes = models.JSONField(_("state changes or payload"), default=dict, blank=True)
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.TextField(_("user agent"), null=True, blank=True)
    timestamp = models.DateTimeField(_("timestamp"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("audit log")
        verbose_name_plural = _("audit logs")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["shop", "action"]),
            models.Index(fields=["shop", "timestamp"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self):
        user_str = self.user.email if self.user else "System"
        return f"[{self.timestamp}] {self.action} by {user_str} ({self.entity_type} {self.entity_id})"
