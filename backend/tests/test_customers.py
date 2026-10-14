import pytest
from decimal import Decimal
from rest_framework import status
from tests.conftest import auth_client
from apps.customers.models import Customer, CustomerStatus


@pytest.mark.django_db
def test_customer_crud_and_search(owner_user, shop_a):
    client = auth_client(owner_user)
    client.credentials(
        HTTP_AUTHORIZATION=client._credentials['HTTP_AUTHORIZATION'],
        HTTP_X_SHOP_ID=str(shop_a.id)
    )

    # 1. Create Customer
    data = {
        "full_name": "Aziz Qodirov",
        "phone_number": "+998901119988",
        "address": "Yunusobod 4-mavze",
        "notes": "Doimiy xaridor",
        "credit_limit": "2000000.00"
    }
    response = client.post("/api/v1/customers/", data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    customer_id = response.data["id"]

    # 2. Search Customer
    search_res = client.get("/api/v1/customers/?search=Aziz")
    assert search_res.status_code == status.HTTP_200_OK
    assert search_res.data["count"] >= 1
    assert any(c["id"] == customer_id for c in search_res.data["results"])

    # 3. Update Customer
    patch_res = client.patch(f"/api/v1/customers/{customer_id}/", {"notes": "VIP xaridor"}, format="json")
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.data["notes"] == "VIP xaridor"

    # 4. Soft Archive Customer (DELETE should archive, not drop record from DB)
    delete_res = client.delete(f"/api/v1/customers/{customer_id}/")
    assert delete_res.status_code == status.HTTP_200_OK
    archived_customer = Customer.objects.get(id=customer_id)
    assert archived_customer.status == CustomerStatus.ARCHIVED
