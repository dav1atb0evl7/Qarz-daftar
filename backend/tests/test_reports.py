import pytest
from decimal import Decimal
from rest_framework import status
from tests.conftest import auth_client
from apps.payments.models import Payment, PaymentMethod


@pytest.mark.django_db
def test_reports_summary_and_exports(owner_user, shop_a, debt_a):
    client = auth_client(owner_user)
    client.credentials(
        HTTP_AUTHORIZATION=client._credentials['HTTP_AUTHORIZATION'],
        HTTP_X_SHOP_ID=str(shop_a.id)
    )

    # Make a payment first
    client.post("/api/v1/payments/", {
        "debt_id": str(debt_a.id),
        "payment_method": PaymentMethod.CASH,
        "amount": "150000.00"
    }, format="json")

    # 1. Summary report
    summary_res = client.get("/api/v1/reports/summary/")
    assert summary_res.status_code == status.HTTP_200_OK
    data = summary_res.data["data"]
    assert Decimal(data["total_debt_created"]) == Decimal("500000.00")
    assert Decimal(data["total_payments_collected"]) == Decimal("150000.00")
    assert Decimal(data["current_outstanding_debt"]) == Decimal("350000.00")

    # 2. Payment trends
    trends_res = client.get("/api/v1/reports/payments/?interval=daily")
    assert trends_res.status_code == status.HTTP_200_OK
    assert len(trends_res.data["data"]) >= 1

    # 3. Debt aging report
    debts_rep_res = client.get("/api/v1/reports/debts/")
    assert debts_rep_res.status_code == status.HTTP_200_OK
    assert "aging_distribution" in debts_rep_res.data["data"]
    assert "top_debtors" in debts_rep_res.data["data"]

    # 4. CSV export
    csv_res = client.get("/api/v1/reports/export/?type=debts&format=csv")
    assert csv_res.status_code == status.HTTP_200_OK
    assert csv_res["Content-Type"].startswith("text/csv")

    # 5. Excel export
    xlsx_res = client.get("/api/v1/reports/export/?type=payments&format=xlsx")
    assert xlsx_res.status_code == status.HTTP_200_OK
    assert "spreadsheetml" in xlsx_res["Content-Type"]
