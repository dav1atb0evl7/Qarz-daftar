from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.common.models import BaseModel
from apps.shops.models import Shop, Branch
from apps.customers.models import Customer
from apps.accounts.models import CustomUser


class DebtStatus(models.TextChoices):
    UNPAID = "UNPAID", _("Unpaid")
    PARTIALLY_PAID = "PARTIALLY_PAID", _("Partially Paid")
    PAID = "PAID", _("Paid")
    OVERDUE = "OVERDUE", _("Overdue")
    CANCELLED = "CANCELLED", _("Cancelled")


class Debt(BaseModel):
    """
    Debt record created for a customer within a specific shop.
    Financial calculations are always strictly verified on the server.
    """
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="debts",
        verbose_name=_("shop")
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="debts",
        verbose_name=_("branch")
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="debts",
        verbose_name=_("customer")
    )
    creator = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="created_debts",
        verbose_name=_("created by")
    )
    amount = models.DecimalField(
        _("debt amount"),
        max_digits=14,
        decimal_places=2,
        help_text=_("Total original principal debt amount")
    )
    paid_amount = models.DecimalField(
        _("paid amount"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total amount paid so far from non-reversed payments")
    )
    remaining_balance = models.DecimalField(
        _("remaining balance"),
        max_digits=14,
        decimal_places=2,
        help_text=_("Calculated server-side: amount - paid_amount")
    )
    description = models.TextField(_("description / item details"), blank=True, default="")
    debt_date = models.DateField(_("debt date"), default=timezone.now, db_index=True)
    due_date = models.DateField(_("due date"), blank=True, null=True, db_index=True)
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=DebtStatus.choices,
        default=DebtStatus.UNPAID,
        db_index=True
    )

    # Cancellation audit
    cancel_reason = models.TextField(_("cancel reason"), blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    cancelled_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="cancelled_debts",
        verbose_name=_("cancelled by")
    )

    class Meta:
        verbose_name = _("debt")
        verbose_name_plural = _("debts")
        ordering = ["-debt_date", "-created_at"]
        indexes = [
            models.Index(fields=["shop", "status"]),
            models.Index(fields=["shop", "due_date"]),
            models.Index(fields=["customer", "status"]),
        ]

    def __str__(self):
        return f"{self.customer.full_name}: {self.remaining_balance} / {self.amount} ({self.status})"

    def recalculate_balance_and_status(self, save=True):
        """
        Derives paid_amount from all valid (non-reversed) payments,
        computes remaining_balance, and updates status accurately.
        """
        if self.status == DebtStatus.CANCELLED:
            self.remaining_balance = Decimal("0.00")
            if save:
                self.save(update_fields=["remaining_balance", "status", "updated_at"])
            return

        valid_payments = self.payments.filter(is_reversed=False)
        total_paid = valid_payments.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

        self.paid_amount = total_paid
        self.remaining_balance = max(Decimal("0.00"), self.amount - self.paid_amount)

        today = timezone.localdate()
        if self.remaining_balance <= Decimal("0.00"):
            self.status = DebtStatus.PAID
        elif self.paid_amount > Decimal("0.00"):
            if self.due_date and self.due_date < today:
                self.status = DebtStatus.OVERDUE
            else:
                self.status = DebtStatus.PARTIALLY_PAID
        else:
            if self.due_date and self.due_date < today:
                self.status = DebtStatus.OVERDUE
            else:
                self.status = DebtStatus.UNPAID

        if save:
            self.save(update_fields=["paid_amount", "remaining_balance", "status", "updated_at"])


class DebtHistory(BaseModel):
    """
    Immutable audit history of modifications to a debt.
    """
    debt = models.ForeignKey(
        Debt,
        on_delete=models.CASCADE,
        related_name="history_logs",
        verbose_name=_("debt")
    )
    changed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="debt_changes",
        verbose_name=_("changed by")
    )
    action = models.CharField(max_length=50)  # e.g., CREATED, UPDATED, PAYMENT_APPLIED, PAYMENT_REVERSED, CANCELLED
    previous_remaining = models.DecimalField(max_digits=14, decimal_places=2)
    new_remaining = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = _("debt history")
        verbose_name_plural = _("debt histories")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Debt {self.debt_id} - {self.action} at {self.created_at}"
