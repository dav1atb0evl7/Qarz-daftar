from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Payment, PaymentMethod
from apps.debts.models import Debt, DebtStatus, DebtHistory
from apps.common.utils import generate_receipt_number
from apps.common.exceptions import (
    BusinessValidationError,
    InsufficientBalanceError,
    DebtAlreadyPaidError,
    PaymentReversalNotAllowedError
)
from apps.audit.services import AuditService


class PaymentService:
    @staticmethod
    @transaction.atomic
    def process_payment(shop, debt_id, received_by, payment_method, amount, cash_amount=None, card_amount=None, notes="", payment_date=None, request=None):
        """
        Executes an atomic payment with row-level locking on the target debt.
        Prevents race conditions, negative balances, and overpayments.
        """
        amount = Decimal(str(amount))
        if amount <= Decimal("0.00"):
            raise BusinessValidationError("Payment amount must be greater than zero.")

        # Row-level lock on target debt to prevent race conditions
        try:
            debt = Debt.objects.select_for_update().get(id=debt_id, shop=shop)
        except Debt.DoesNotExist:
            raise BusinessValidationError("Debt record not found for this shop.")

        if debt.status == DebtStatus.CANCELLED:
            raise BusinessValidationError("Cannot make a payment towards a cancelled debt.")

        if debt.status == DebtStatus.PAID or debt.remaining_balance <= Decimal("0.00"):
            raise DebtAlreadyPaidError("This debt is already fully paid.")

        if amount > debt.remaining_balance:
            raise InsufficientBalanceError(
                f"Payment amount ({amount}) exceeds remaining balance ({debt.remaining_balance})."
            )

        # Validate cash / card allocation
        if payment_method == PaymentMethod.CASH:
            cash_amount = amount
            card_amount = Decimal("0.00")
        elif payment_method == PaymentMethod.CARD:
            cash_amount = Decimal("0.00")
            card_amount = amount
        elif payment_method == PaymentMethod.MIXED:
            cash_amount = Decimal(str(cash_amount or "0.00"))
            card_amount = Decimal(str(card_amount or "0.00"))
            if cash_amount + card_amount != amount:
                raise BusinessValidationError(
                    f"Cash portion ({cash_amount}) + Card portion ({card_amount}) "
                    f"must equal total payment amount ({amount})."
                )
            if cash_amount < Decimal("0.00") or card_amount < Decimal("0.00"):
                raise BusinessValidationError("Portion amounts cannot be negative.")
        else:
            raise BusinessValidationError(f"Invalid payment method: {payment_method}")

        if not payment_date:
            payment_date = timezone.now()

        # Generate unique receipt number
        receipt_number = generate_receipt_number(prefix="RCP")
        while Payment.objects.filter(receipt_number=receipt_number).exists():
            receipt_number = generate_receipt_number(prefix="RCP")

        payment = Payment.objects.create(
            shop=shop,
            branch=debt.branch,
            debt=debt,
            customer=debt.customer,
            received_by=received_by,
            payment_method=payment_method,
            amount=amount,
            cash_amount=cash_amount,
            card_amount=card_amount,
            receipt_number=receipt_number,
            notes=notes,
            payment_date=payment_date
        )

        prev_remaining = debt.remaining_balance

        # Recalculate debt balance and status
        debt.recalculate_balance_and_status(save=True)

        # Log DebtHistory
        DebtHistory.objects.create(
            debt=debt,
            changed_by=received_by,
            action="PAYMENT_APPLIED",
            previous_remaining=prev_remaining,
            new_remaining=debt.remaining_balance,
            notes=f"Payment {receipt_number} applied: {amount} via {payment_method}."
        )

        # Log system-wide Audit
        AuditService.log_action(
            request=request,
            user=received_by,
            shop=shop,
            action="PAYMENT_CREATE",
            entity_type="Payment",
            entity_id=str(payment.id),
            changes={
                "receipt_number": receipt_number,
                "amount": str(amount),
                "payment_method": payment_method,
                "debt_id": str(debt.id),
                "customer": debt.customer.full_name,
                "remaining_balance": str(debt.remaining_balance)
            }
        )

        # Trigger Celery notification if configured
        try:
            from apps.notifications.tasks import send_payment_receipt_notification
            send_payment_receipt_notification.delay(str(payment.id))
        except Exception:
            pass  # Don't fail the transaction if async queue is not connected in dev

        return payment

    @staticmethod
    @transaction.atomic
    def reverse_payment(payment, reversed_by, reason, request=None):
        """
        Reverses a completed payment atomically, updating the debt's
        balance and maintaining an immutable audit log.
        """
        if payment.is_reversed:
            raise PaymentReversalNotAllowedError("This payment has already been reversed.")

        # Row-level lock on the target debt
        debt = Debt.objects.select_for_update().get(id=payment.debt_id)

        prev_remaining = debt.remaining_balance

        payment.is_reversed = True
        payment.reversal_reason = reason
        payment.reversed_at = timezone.now()
        payment.reversed_by = reversed_by
        payment.save(update_fields=["is_reversed", "reversal_reason", "reversed_at", "reversed_by", "updated_at"])

        # Recalculate debt balance and status
        debt.recalculate_balance_and_status(save=True)

        # Log DebtHistory
        DebtHistory.objects.create(
            debt=debt,
            changed_by=reversed_by,
            action="PAYMENT_REVERSED",
            previous_remaining=prev_remaining,
            new_remaining=debt.remaining_balance,
            notes=f"Reversed payment {payment.receipt_number} of {payment.amount}: {reason}"
        )

        # Log system-wide Audit
        AuditService.log_action(
            request=request,
            user=reversed_by,
            shop=payment.shop,
            action="PAYMENT_REVERSE",
            entity_type="Payment",
            entity_id=str(payment.id),
            changes={
                "receipt_number": payment.receipt_number,
                "amount": str(payment.amount),
                "reason": reason,
                "new_debt_balance": str(debt.remaining_balance)
            }
        )

        return payment
