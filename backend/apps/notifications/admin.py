from django.contrib import admin
from .models import NotificationPreference, NotificationLog


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('shop', 'enable_telegram', 'enable_email', 'enable_due_date_reminders', 'reminder_days_before', 'enable_overdue_alerts')


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('notification_type', 'channel', 'recipient', 'shop', 'status', 'sent_at', 'created_at')
    list_filter = ('channel', 'status', 'notification_type', 'shop', 'created_at')
    search_fields = ('recipient', 'message_body', 'idempotency_key')
    readonly_fields = ('idempotency_key', 'created_at')
