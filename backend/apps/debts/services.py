from decimal import Decimal
from django.db import transaction, models
from django.utils import timezone
from apps.common.exceptions import BusinessValidationError
from .models import Debt, DebtStatus, DebtHistory


class DebtService:
    @staticmethod
    @transaction.atomic
    def create_debt(shop, customer, creator, amount, description="", debt_date=None, due_date=None, branch=None):
        if amount <= Decimal("0.00"):
            raise BusinessValidationError("Debt amount must be greater than zero.")

        if customer.shop_id != shop.id:
            raise BusinessValidationError("Customer does not belong to this shop.")

        if customer.status == "ARCHIVED":
            raise BusinessValidationError("Cannot add debt to an archived customer. Reactivate customer first.")

        # Check credit limit
        if customer.credit_limit and customer.credit_limit > Decimal("0.00"):
            current_balance = customer.debts.exclude(status=DebtStatus.CANCELLED).aggregate(
                rem=models.Sum("remaining_balance")
            )["rem"] or Decimal("0.00")
            if current_balance + amount > customer.credit_limit:
                raise BusinessValidationError(
                    f"Customer credit limit of {customer.credit_limit} exceeded! "
                    f"Current balance: {current_balance}, attempted addition: {amount}"
                )

        if not debt_date:
            debt_date = timezone.localdate()

        status = DebtStatus.UNPAID
        if due_date and due_date < timezone.localdate():
            status = DebtStatus.OVERDUE

        debt = Debt.objects.create(
            shop=shop,
            branch=branch or customer.branch,
            customer=customer,
            creator=creator,
            amount=amount,
            paid_amount=Decimal("0.00"),
            remaining_balance=amount,
            description=description,
            debt_date=debt_date,
            due_date=due_date,
            status=status
        )

        DebtHistory.objects.create(
            debt=debt,
            changed_by=creator,
            action="CREATED",
            previous_remaining=Decimal("0.00"),
            new_remaining=amount,
            notes=f"Debt created with initial amount {amount}."
        )

        return debt

    @staticmethod
    @transaction.atomic
    def cancel_debt(debt, user, reason):
        # Prevent cancellation if there are active payments
        has_active_payments = debt.payments.filter(is_reversed=False).exists()
        if has_active_payments:
            raise BusinessValidationError(
                "Cannot cancel debt with existing payments. Reverse all payments first."
            )

        prev_remaining = debt.remaining_balance
        debt.status = DebtStatus.CANCELLED
        debt.remaining_balance = Decimal("0.00")
        debt.cancel_reason = reason
        debt.cancelled_at = timezone.now()
        debt.cancelled_by = user
        debt.save()

        DebtHistory.objects.create(
            debt=debt,
            changed_by=user,
            action="CANCELLED",
            previous_remaining=prev_remaining,
            new_remaining=Decimal("0.00"),
            notes=f"Cancelled: {reason}"
        )

        return debt

    @staticmethod
    def detect_and_mark_overdue_debts(shop=None):
        """Scans and transitions unpaid debts past due_date to OVERDUE."""
        today = timezone.localdate()
        qs = Debt.objects.filter(
            due_date__lt=today,
            remaining_balance__gt=Decimal("0.00"),
            status__in=[DebtStatus.UNPAID, DebtStatus.PARTIALLY_PAID]
        )
        if shop:
            qs = qs.filter(shop=shop)

        updated_count = qs.update(status=DebtStatus.OVERDUE, updated_at=timezone.now())
        return updated_count
