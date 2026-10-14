from django.urls import path
from .views import (
    TelegramLinkCodeView,
    TelegramVerifyLinkView,
    TelegramAuthView,
)

urlpatterns = [
    path('link-code/', TelegramLinkCodeView.as_view(), name='telegram-link-code'),
    path('verify-link/', TelegramVerifyLinkView.as_view(), name='telegram-verify-link'),
    path('auth/', TelegramAuthView.as_view(), name='telegram-auth'),
]
