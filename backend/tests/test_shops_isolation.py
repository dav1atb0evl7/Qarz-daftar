import pytest
from rest_framework import status
from tests.conftest import auth_client
from apps.shops.models import Shop, Branch, ShopMember
from apps.accounts.models import CustomUser, UserRole


@pytest.mark.django_db
def test_create_shop(owner_user):
    client = auth_client(owner_user)
    data = {
        "name": "Yangi Savdo Markazi",
        "phone_number": "+998901112233",
        "address": "Navoiy ko'chasi 14",
        "currency": "UZS"
    }
    response = client.post("/api/v1/shops/", data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert Shop.objects.filter(name="Yangi Savdo Markazi").exists()


@pytest.mark.django_db
def test_shop_data_isolation(owner_user, other_owner_user, shop_a, shop_b, customer_b):
    """
    Critical requirement: A user from Shop A must NEVER access
    Shop B's customers, debts, payments, or files.
    """
    client_a = auth_client(owner_user)

    # User A attempts to view Shop B's customers by passing X-Shop-ID of Shop B
    client_a.credentials(
        HTTP_AUTHORIZATION=client_a._credentials['HTTP_AUTHORIZATION'],
        HTTP_X_SHOP_ID=str(shop_b.id)
    )

    response = client_a.get("/api/v1/customers/")
    # Must be forbidden / denied access
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["success"] is False

    # Attempt to retrieve customer B directly
    response = client_a.get(f"/api/v1/customers/{customer_b.id}/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_cashier_cannot_update_shop_settings(cashier_user, shop_a):
    client = auth_client(cashier_user)
    client.credentials(
        HTTP_AUTHORIZATION=client._credentials['HTTP_AUTHORIZATION'],
        HTTP_X_SHOP_ID=str(shop_a.id)
    )

    response = client.patch(f"/api/v1/shops/{shop_a.id}/", {"name": "Hacked Name"}, format="json")
    assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)
