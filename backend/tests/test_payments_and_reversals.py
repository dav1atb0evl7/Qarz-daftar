import pytest
from decimal import Decimal
from rest_framework import status
from tests.conftest import auth_client
from apps.payments.models import Payment, PaymentMethod
from apps.debts.models import Debt, DebtStatus


@pytest.mark.django_db
def test_partial_and_mixed_payment(owner_user, shop_a, debt_a):
    """
    Original debt: 500,000 UZS
    Mixed payment: 250,000 UZS (100,000 Cash + 150,000 Card)
    Expected remaining: 250,000 UZS, status: PARTIALLY_PAID
    """
    client = auth_client(owner_user)
    client.credentials(
        HTTP_AUTHORIZATION=client._credentials['HTTP_AUTHORIZATION'],
        HTTP_X_SHOP_ID=str(shop_a.id)
    )

    pay_data = {
        "debt_id": str(debt_a.id),
        "payment_method": PaymentMethod.MIXED,
        "amount": "250000.00",
        "cash_amount": "100000.00",
        "card_amount": "150000.00",
        "notes": "Qisman to'lov"
    }

    response = client.post("/api/v1/payments/", pay_data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    payment_data = response.data["data"]

    assert payment_data["receipt_number"].startswith("RCP-")
    assert Decimal(payment_data["amount"]) == Decimal("250000.00")

    debt_a.refresh_from_db()
    assert debt_a.paid_amount == Decimal("250000.00")
    assert debt_a.remaining_balance == Decimal("250000.00")
    assert debt_a.status == DebtStatus.PARTIALLY_PAID


@pytest.mark.django_db
def test_full_payment_transitions_to_paid(owner_user, shop_a, debt_a):
    client = auth_client(owner_user)
    client.credentials(
        HTTP_AUTHORIZATION=client._credentials['HTTP_AUTHORIZATION'],
        HTTP_X_SHOP_ID=str(shop_a.id)
    )

    pay_data = {
        "debt_id": str(debt_a.id),
        "payment_method": PaymentMethod.CASH,
        "amount": "500000.00"
    }
    response = client.post("/api/v1/payments/", pay_data, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    debt_a.refresh_from_db()
    assert debt_a.paid_amount == Decimal("500000.00")
    assert debt_a.remaining_balance == Decimal("0.00")
    assert debt_a.status == DebtStatus.PAID


@pytest.mark.django_db
def test_prevent_overpayment_beyond_balance(owner_user, shop_a, debt_a):
    """
    Debt remaining balance is 500,000 UZS.
    Attempting to pay 600,000 UZS must be rejected by server.
    """
    client = auth_client(owner_user)
    client.credentials(
        HTTP_AUTHORIZATION=client._credentials['HTTP_AUTHORIZATION'],
        HTTP_X_SHOP_ID=str(shop_a.id)
    )

    pay_data = {
        "debt_id": str(debt_a.id),
        "payment_method": PaymentMethod.CASH,
        "amount": "600000.00"
    }
    response = client.post("/api/v1/payments/", pay_data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["success"] is False

    debt_a.refresh_from_db()
    assert debt_a.remaining_balance == Decimal("500000.00")


@pytest.mark.django_db
def test_payment_reversal_restores_balance(owner_user, shop_a, debt_a):
    client = auth_client(owner_user)
    client.credentials(
        HTTP_AUTHORIZATION=client._credentials['HTTP_AUTHORIZATION'],
        HTTP_X_SHOP_ID=str(shop_a.id)
    )

    # 1. Pay 200,000 UZS
    pay_res = client.post("/api/v1/payments/", {
        "debt_id": str(debt_a.id),
        "payment_method": PaymentMethod.CASH,
        "amount": "200000.00"
    }, format="json")
    payment_id = pay_res.data["data"]["id"]

    debt_a.refresh_from_db()
    assert debt_a.remaining_balance == Decimal("300000.00")

    # 2. Reverse payment
    rev_res = client.post(f"/api/v1/payments/{payment_id}/reverse/", {
        "reason": "Mijoz adashib to'lagan ekan"
    }, format="json")
    assert rev_res.status_code == status.HTTP_200_OK

    # 3. Verify debt restored
    debt_a.refresh_from_db()
    assert debt_a.paid_amount == Decimal("0.00")
    assert debt_a.remaining_balance == Decimal("500000.00")
    assert debt_a.status == DebtStatus.UNPAID

    payment = Payment.objects.get(id=payment_id)
    assert payment.is_reversed is True
    assert payment.reversal_reason == "Mijoz adashib to'lagan ekan"


@pytest.mark.django_db
def test_cashier_cannot_reverse_payment(cashier_user, owner_user, shop_a, debt_a):
    owner_client = auth_client(owner_user)
    owner_client.credentials(
        HTTP_AUTHORIZATION=owner_client._credentials['HTTP_AUTHORIZATION'],
        HTTP_X_SHOP_ID=str(shop_a.id)
    )
    pay_res = owner_client.post("/api/v1/payments/", {
        "debt_id": str(debt_a.id),
        "payment_method": PaymentMethod.CASH,
        "amount": "100000.00"
    }, format="json")
    payment_id = pay_res.data["data"]["id"]

    # Cashier attempts reversal
    cashier_client = auth_client(cashier_user)
    cashier_client.credentials(
        HTTP_AUTHORIZATION=cashier_client._credentials['HTTP_AUTHORIZATION'],
        HTTP_X_SHOP_ID=str(shop_a.id)
    )
    rev_res = cashier_client.post(f"/api/v1/payments/{payment_id}/reverse/", {
        "reason": "Hacking attempt"
    }, format="json")
    assert rev_res.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)
