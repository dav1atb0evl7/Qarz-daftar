import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from tests.conftest import auth_client
from apps.debts.models import Debt, DebtStatus
from apps.debts.services import DebtService


@pytest.mark.django_db
def test_create_debt_and_balance_derivation(owner_user, shop_a, customer_a):
    client = auth_client(owner_user)
    client.credentials(
        HTTP_AUTHORIZATION=client._credentials['HTTP_AUTHORIZATION'],
        HTTP_X_SHOP_ID=str(shop_a.id)
    )

    data = {
        "customer_id": str(customer_a.id),
        "amount": "250000.00",
        "description": "Un va shakar xaridi",
        "due_date": str(timezone.localdate() + timedelta(days=7))
    }
    response = client.post("/api/v1/debts/", data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    debt_data = response.data["data"]

    # Server must calculate remaining balance and status correctly
    assert Decimal(debt_data["amount"]) == Decimal("250000.00")
    assert Decimal(debt_data["paid_amount"]) == Decimal("0.00")
    assert Decimal(debt_data["remaining_balance"]) == Decimal("250000.00")
    assert debt_data["status"] == DebtStatus.UNPAID


@pytest.mark.django_db
def test_reject_zero_or_negative_debt_amount(owner_user, shop_a, customer_a):
    client = auth_client(owner_user)
    client.credentials(
        HTTP_AUTHORIZATION=client._credentials['HTTP_AUTHORIZATION'],
        HTTP_X_SHOP_ID=str(shop_a.id)
    )

    response = client.post("/api/v1/debts/", {
        "customer_id": str(customer_a.id),
        "amount": "0.00"
    }, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    response_neg = client.post("/api/v1/debts/", {
        "customer_id": str(customer_a.id),
        "amount": "-50000.00"
    }, format="json")
    assert response_neg.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_credit_limit_enforcement(owner_user, shop_a, customer_a):
    client = auth_client(owner_user)
    client.credentials(
        HTTP_AUTHORIZATION=client._credentials['HTTP_AUTHORIZATION'],
        HTTP_X_SHOP_ID=str(shop_a.id)
    )

    # customer_a credit limit is 1,000,000 UZS. Try to add 1,500,000 UZS
    response = client.post("/api/v1/debts/", {
        "customer_id": str(customer_a.id),
        "amount": "1500000.00"
    }, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "credit limit" in response.data["error"]["message"].lower()


@pytest.mark.django_db
def test_detect_and_mark_overdue_debts(shop_a, customer_a, owner_user):
    yesterday = timezone.localdate() - timedelta(days=1)
    debt = Debt.objects.create(
        shop=shop_a,
        customer=customer_a,
        creator=owner_user,
        amount=Decimal("100000.00"),
        paid_amount=Decimal("0.00"),
        remaining_balance=Decimal("100000.00"),
        due_date=yesterday,
        status=DebtStatus.UNPAID
    )

    updated_count = DebtService.detect_and_mark_overdue_debts(shop=shop_a)
    assert updated_count >= 1
    debt.refresh_from_db()
    assert debt.status == DebtStatus.OVERDUE
