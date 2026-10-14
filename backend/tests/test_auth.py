import pytest
from rest_framework import status
from django.urls import reverse
from tests.conftest import auth_client
from apps.accounts.models import CustomUser


@pytest.mark.django_db
def test_user_registration(api_client):
    url = "/api/v1/auth/register/"
    data = {
        "email": "newuser@test.uz",
        "password": "SecurePassword123!",
        "password_confirm": "SecurePassword123!",
        "full_name": "Sardor Rahimov",
        "phone_number": "+998935556677"
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["success"] is True
    assert CustomUser.objects.filter(email="newuser@test.uz").exists()


@pytest.mark.django_db
def test_user_registration_password_mismatch(api_client):
    url = "/api/v1/auth/register/"
    data = {
        "email": "mismatch@test.uz",
        "password": "SecurePassword123!",
        "password_confirm": "DifferentPassword123!",
        "full_name": "Test User"
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["success"] is False


@pytest.mark.django_db
def test_user_login_success(api_client, owner_user):
    url = "/api/v1/auth/login/"
    data = {
        "email": "owner@test.uz",
        "password": "Password123!"
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert "access" in response.data["data"]
    assert "refresh" in response.data["data"]


@pytest.mark.django_db
def test_user_login_invalid_credentials(api_client, owner_user):
    url = "/api/v1/auth/login/"
    data = {
        "email": "owner@test.uz",
        "password": "WrongPassword!"
    }
    response = api_client.post(url, data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["success"] is False


@pytest.mark.django_db
def test_get_current_user_profile(owner_user):
    client = auth_client(owner_user)
    response = client.get("/api/v1/auth/me/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert response.data["data"]["email"] == "owner@test.uz"


@pytest.mark.django_db
def test_email_verification(api_client):
    user = CustomUser.objects.create_user(
        email="verify_me@test.uz",
        password="Password123!",
        verification_token="test-verification-token-xyz"
    )
    assert user.is_verified is False

    response = api_client.post("/api/v1/auth/verify-email/", {"token": "test-verification-token-xyz"})
    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.is_verified is True


@pytest.mark.django_db
def test_change_password_flow(api_client, owner_user):
    api_client.force_authenticate(user=owner_user)

    # Wrong old password should fail
    resp = api_client.post("/api/v1/auth/change-password/", {
        "old_password": "WrongPassword123!",
        "new_password": "NewSecretPassword123!",
        "new_password_confirm": "NewSecretPassword123!"
    })
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # Valid change
    resp = api_client.post("/api/v1/auth/change-password/", {
        "old_password": "Password123!",
        "new_password": "NewSecretPassword123!",
        "new_password_confirm": "NewSecretPassword123!"
    })
    assert resp.status_code == status.HTTP_200_OK
    owner_user.refresh_from_db()
    assert owner_user.check_password("NewSecretPassword123!") is True
