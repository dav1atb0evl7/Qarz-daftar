import logging
from decimal import Decimal
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from apps.shops.models import Shop
from apps.debts.models import Debt, DebtStatus
from apps.payments.models import Payment
from apps.common.utils import format_currency
from .models import (
    NotificationPreference,
    NotificationChannel,
    NotificationType,
)
from .services import NotificationDispatcher

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_and_send_due_date_reminders(self):
    """
    Periodic task running daily:
    Scans for debts due in N days and notifies shop owner/managers.
    """
    today = timezone.localdate()
    logger.info("Executing scheduled due date reminder task for %s", today)

    prefs = NotificationPreference.objects.filter(enable_due_date_reminders=True).select_related('shop', 'shop__owner')
    total_reminders_sent = 0

    for pref in prefs:
        shop = pref.shop
        target_date = today + timedelta(days=pref.reminder_days_before)
        debts = Debt.objects.filter(
            shop=shop,
            due_date=target_date,
            remaining_balance__gt=Decimal('0.00')
        ).exclude(status=DebtStatus.CANCELLED).select_related('customer')

        for debt in debts:
            idempotency_key = f"due-reminder-{debt.id}-{target_date}"
            currency = shop.currency
            message = (
                f"<b>⏰ To'lov muddati eslatmasi ({shop.name})</b>\n\n"
                f"Mijoz: <b>{debt.customer.full_name}</b>\n"
                f"Telefon: {debt.customer.phone_number}\n"
                f"Qoldiq qarz: <b>{format_currency(debt.remaining_balance, currency)}</b>\n"
                f"To'lov muddati: <b>{debt.due_date}</b>\n"
                f"Tavsif: {debt.description or 'Mavjud emas'}"
            )

            # Send to shop owner if Telegram ID is linked
            if pref.enable_telegram and shop.owner.telegram_id:
                NotificationDispatcher.send(
                    shop=shop,
                    channel=NotificationChannel.TELEGRAM,
                    recipient=shop.owner.telegram_id,
                    notification_type=NotificationType.DUE_REMINDER,
                    message_body=message,
                    idempotency_key=idempotency_key,
                    customer=debt.customer,
                    debt=debt
                )
                total_reminders_sent += 1

            if pref.enable_email and shop.owner.email:
                NotificationDispatcher.send(
                    shop=shop,
                    channel=NotificationChannel.EMAIL,
                    recipient=shop.owner.email,
                    notification_type=NotificationType.DUE_REMINDER,
                    message_body=message,
                    idempotency_key=f"{idempotency_key}-email",
                    customer=debt.customer,
                    debt=debt
                )

    return f"Total due reminders triggered: {total_reminders_sent}"


@shared_task(bind=True, max_retries=3)
def check_and_send_overdue_alerts(self):
    """
    Periodic task running daily:
    Updates status of debts past due_date to OVERDUE and sends alerts.
    """
    today = timezone.localdate()
    logger.info("Executing overdue debt scan for %s", today)

    # 1. Update statuses
    overdue_debts = Debt.objects.filter(
        due_date__lt=today,
        remaining_balance__gt=Decimal('0.00'),
        status__in=[DebtStatus.UNPAID, DebtStatus.PARTIALLY_PAID]
    ).select_related('shop', 'shop__owner', 'customer')

    total_alerts_sent = 0

    for debt in overdue_debts:
        debt.status = DebtStatus.OVERDUE
        debt.save(update_fields=['status', 'updated_at'])

        shop = debt.shop
        pref = getattr(shop, 'notification_preference', None)

        if pref and pref.enable_overdue_alerts:
            idempotency_key = f"overdue-alert-{debt.id}-{today}"
            currency = shop.currency
            message = (
                f"<b>⚠️ Muddati o'tgan qarz ogohlantirishi ({shop.name})</b>\n\n"
                f"Mijoz: <b>{debt.customer.full_name}</b>\n"
                f"Telefon: {debt.customer.phone_number}\n"
                f"Qoldiq qarz: <b>{format_currency(debt.remaining_balance, currency)}</b>\n"
                f"Belgilangan muddat: <b>{debt.due_date}</b>\n"
                f"Iltimos, mijoz bilan bog'laning."
            )

            if pref.enable_telegram and shop.owner.telegram_id:
                NotificationDispatcher.send(
                    shop=shop,
                    channel=NotificationChannel.TELEGRAM,
                    recipient=shop.owner.telegram_id,
                    notification_type=NotificationType.OVERDUE_ALERT,
                    message_body=message,
                    idempotency_key=idempotency_key,
                    customer=debt.customer,
                    debt=debt
                )
                total_alerts_sent += 1

    return f"Total overdue debts updated: {overdue_debts.count()}, alerts sent: {total_alerts_sent}"


@shared_task(bind=True, max_retries=2)
def send_payment_receipt_notification(self, payment_id):
    """
    Triggered when a payment is processed to send instant receipt confirmation.
    """
    try:
        payment = Payment.objects.select_related('shop', 'shop__owner', 'customer', 'debt').get(id=payment_id)
    except Payment.DoesNotExist:
        return "Payment not found."

    shop = payment.shop
    pref = getattr(shop, 'notification_preference', None)
    if not pref or not pref.enable_payment_receipts:
        return "Payment receipts disabled."

    currency = shop.currency
    message = (
        f"<b>🧾 To'lov qabul qilindi ({shop.name})</b>\n\n"
        f"Kvitansiya: <code>{payment.receipt_number}</code>\n"
        f"Mijoz: <b>{payment.customer.full_name}</b>\n"
        f"To'langan summa: <b>{format_currency(payment.amount, currency)}</b>\n"
        f"To'lov usuli: {payment.get_payment_method_display()}\n"
        f"Qoldiq qarz: <b>{format_currency(payment.debt.remaining_balance, currency)}</b>\n"
        f"Sana: {payment.payment_date.strftime('%Y-%m-%d %H:%M')}"
    )

    idempotency_key = f"receipt-{payment.id}"

    if pref.enable_telegram and shop.owner.telegram_id:
        NotificationDispatcher.send(
            shop=shop,
            channel=NotificationChannel.TELEGRAM,
            recipient=shop.owner.telegram_id,
            notification_type=NotificationType.PAYMENT_RECEIPT,
            message_body=message,
            idempotency_key=idempotency_key,
            customer=payment.customer,
            debt=payment.debt
        )

    return f"Receipt notification sent for {payment.receipt_number}"
