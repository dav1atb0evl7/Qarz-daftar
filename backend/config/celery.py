import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module for 'celery'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('qarz_daftar')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Periodic Tasks
app.conf.beat_schedule = {
    'send-due-date-reminders-daily': {
        'task': 'apps.notifications.tasks.check_and_send_due_date_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 09:00 AM
    },
    'mark-and-alert-overdue-debts-daily': {
        'task': 'apps.notifications.tasks.check_and_send_overdue_alerts',
        'schedule': crontab(hour=10, minute=0),  # Daily at 10:00 AM
    },
}
