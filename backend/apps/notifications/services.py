import logging
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from .models import NotificationLog, NotificationStatus, NotificationChannel

logger = logging.getLogger(__name__)


class TelegramService:
    @staticmethod
    def send_message(chat_id, text):
        """Sends message via Telegram Bot API."""
        token = settings.TELEGRAM_BOT_TOKEN
        if not token or token == 'local-dummy-token':
            logger.info("Telegram notification simulated for chat_id %s: %s", chat_id, text[:50])
            return True, None

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                return True, None
            return False, f"Telegram API error {resp.status_code}: {resp.text}"
        except Exception as e:
            return False, str(e)


class EmailService:
    @staticmethod
    def send_email(recipient_email, subject, body):
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False
            )
            return True, None
        except Exception as e:
            return False, str(e)


class NotificationDispatcher:
    @staticmethod
    def send(shop, channel, recipient, notification_type, message_body, idempotency_key, customer=None, debt=None):
        """
        Sends an idempotent notification and records the result in NotificationLog.
        """
        if not recipient:
            return None

        # Check if already sent (Deduplication)
        existing = NotificationLog.objects.filter(idempotency_key=idempotency_key).first()
        if existing and existing.status == NotificationStatus.SENT:
            logger.info("Notification with key %s already sent. Skipping.", idempotency_key)
            return existing

        log_record, _ = NotificationLog.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={
                "shop": shop,
                "customer": customer,
                "debt": debt,
                "channel": channel,
                "recipient": recipient,
                "notification_type": notification_type,
                "message_body": message_body,
                "status": NotificationStatus.PENDING,
            }
        )

        success = False
        error_msg = None

        if channel == NotificationChannel.TELEGRAM:
            success, error_msg = TelegramService.send_message(recipient, message_body)
        elif channel == NotificationChannel.EMAIL:
            success, error_msg = EmailService.send_email(
                recipient_email=recipient,
                subject=f"Qarz Daftar Pro - {notification_type}",
                body=message_body
            )

        if success:
            log_record.status = NotificationStatus.SENT
            log_record.sent_at = timezone.now()
            log_record.error_message = None
        else:
            log_record.status = NotificationStatus.FAILED
            log_record.error_message = error_msg

        log_record.save(update_fields=["status", "sent_at", "error_message"])
        return log_record
