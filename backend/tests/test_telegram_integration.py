import pytest
from rest_framework import status
from django.conf import settings
from tests.conftest import auth_client
from apps.accounts.models import CustomUser, TelegramLinkCode


@pytest.mark.django_db
def test_telegram_linking_and_bot_auth_flow(owner_user, shop_a):
    user_client = auth_client(owner_user)

    # 1. User generates 6-digit code on web dashboard
    gen_res = user_client.post("/api/v1/telegram/link-code/")
    assert gen_res.status_code == status.HTTP_200_OK
    code = gen_res.data["code"]
    assert len(code) == 6

    # 2. Telegram bot submits code with Bot Secret Header
    from rest_framework.test import APIClient
    bot_client = APIClient()

    # Unauthorized request (wrong secret)
    bad_res = bot_client.post(
        "/api/v1/telegram/verify-link/",
        {"code": code, "telegram_id": "987654321", "telegram_username": "anvar_dev"},
        HTTP_X_TELEGRAM_BOT_SECRET="wrong-secret"
    )
    assert bad_res.status_code == status.HTTP_401_UNAUTHORIZED

    # Authorized request (correct secret)
    link_res = bot_client.post(
        "/api/v1/telegram/verify-link/",
        {"code": code, "telegram_id": "987654321", "telegram_username": "anvar_dev"},
        HTTP_X_TELEGRAM_BOT_SECRET=settings.TELEGRAM_BOT_API_SECRET
    )
    assert link_res.status_code == status.HTTP_200_OK
    assert link_res.data["success"] is True

    owner_user.refresh_from_db()
    assert owner_user.telegram_id == "987654321"
    assert owner_user.telegram_username == "anvar_dev"

    # 3. Bot retrieves user profile and shops by Telegram ID
    auth_res = bot_client.post(
        "/api/v1/telegram/auth/",
        {"telegram_id": "987654321"},
        HTTP_X_TELEGRAM_BOT_SECRET=settings.TELEGRAM_BOT_API_SECRET
    )
    assert auth_res.status_code == status.HTTP_200_OK
    assert "token" in auth_res.data
    assert len(auth_res.data["owned_shops"]) >= 1
    assert auth_res.data["owned_shops"][0]["name"] == shop_a.name
