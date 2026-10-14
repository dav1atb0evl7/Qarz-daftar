from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.common.models import BaseModel
from apps.shops.models import Shop, Branch
from apps.customers.models import Customer
from apps.debts.models import Debt
from apps.accounts.models import CustomUser


class PaymentMethod(models.TextChoices):
    CASH = "CASH", _("Naqd pul (Cash)")
    CARD = "CARD", _("Karta / O'tkazma (Card)")
    MIXED = "MIXED", _("Aralash (Mixed Cash + Card)")


class Payment(BaseModel):
    """
    Payment transaction record. Money fields use DecimalField exclusively.
    Transactions are immutable; corrections must be performed via reversal.
    """
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("shop")
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="payments",
        verbose_name=_("branch")
    )
    debt = models.ForeignKey(
        Debt,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name=_("debt")
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name=_("customer")
    )
    received_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="received_payments",
        verbose_name=_("received by")
    )
    payment_method = models.CharField(
        _("payment method"),
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        db_index=True
    )
    amount = models.DecimalField(
        _("total payment amount"),
        max_digits=14,
        decimal_places=2,
        help_text=_("Total paid in this transaction")
    )
    cash_amount = models.DecimalField(
        _("cash portion"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00")
    )
    card_amount = models.DecimalField(
        _("card portion"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00")
    )
    receipt_number = models.CharField(
        _("receipt number"),
        max_length=64,
        unique=True,
        db_index=True
    )
    notes = models.TextField(_("notes"), blank=True, default="")
    payment_date = models.DateTimeField(_("payment timestamp"), default=timezone.now, db_index=True)

    # Reversal Audit Trail
    is_reversed = models.BooleanField(_("reversed"), default=False, db_index=True)
    reversal_reason = models.TextField(_("reversal reason"), blank=True, null=True)
    reversed_at = models.DateTimeField(_("reversed timestamp"), blank=True, null=True)
    reversed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reversed_payments",
        verbose_name=_("reversed by")
    )

    class Meta:
        verbose_name = _("payment")
        verbose_name_plural = _("payments")
        ordering = ["-payment_date", "-created_at"]
        indexes = [
            models.Index(fields=["shop", "payment_date"]),
            models.Index(fields=["shop", "is_reversed"]),
            models.Index(fields=["customer", "is_reversed"]),
            models.Index(fields=["debt", "is_reversed"]),
        ]

    def __str__(self):
        status_str = " [REVERSED]" if self.is_reversed else ""
        return f"{self.receipt_number}: {self.amount} ({self.payment_method}){status_str}"
