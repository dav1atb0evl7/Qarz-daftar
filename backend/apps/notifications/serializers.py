from rest_framework import serializers
from .models import NotificationPreference, NotificationLog


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = (
            'id', 'shop', 'enable_telegram', 'enable_email',
            'enable_due_date_reminders', 'reminder_days_before',
            'enable_overdue_alerts', 'enable_payment_receipts',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'shop', 'created_at', 'updated_at')


class NotificationLogSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)

    class Meta:
        model = NotificationLog
        fields = (
            'id', 'shop', 'customer', 'customer_name', 'debt',
            'channel', 'recipient', 'notification_type', 'status',
            'message_body', 'sent_at', 'error_message', 'created_at'
        )
        read_only_fields = fields
