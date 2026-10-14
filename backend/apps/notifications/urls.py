from django.urls import path
from .views import (
    NotificationPreferenceView,
    NotificationLogListView,
    TriggerRemindersView
)

urlpatterns = [
    path('preferences/', NotificationPreferenceView.as_view(), name='notification-preferences'),
    path('logs/', NotificationLogListView.as_view(), name='notification-logs'),
    path('trigger-reminders/', TriggerRemindersView.as_view(), name='notification-trigger-reminders'),
]
