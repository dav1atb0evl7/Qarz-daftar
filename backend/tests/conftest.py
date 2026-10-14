import pytest
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser, UserRole
from apps.shops.models import Shop, Branch, ShopMember
from apps.customers.models import Customer
from apps.debts.models import Debt, DebtStatus


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def owner_user(db):
    user = CustomUser.objects.create_user(
        email="owner@test.uz",
        password="Password123!",
        first_name="Anvar",
        last_name="Karimov",
        phone_number="+998901234567",
        role=UserRole.SHOP_OWNER,
        is_verified=True
    )
    return user


@pytest.fixture
def cashier_user(db):
    user = CustomUser.objects.create_user(
        email="cashier@test.uz",
        password="Password123!",
        first_name="Dilshod",
        last_name="Alimov",
        phone_number="+998907654321",
        role=UserRole.CASHIER,
        is_verified=True
    )
    return user


@pytest.fixture
def other_owner_user(db):
    user = CustomUser.objects.create_user(
        email="other_owner@test.uz",
        password="Password123!",
        first_name="Bobur",
        last_name="Yusupov",
        phone_number="+998909876543",
        role=UserRole.SHOP_OWNER,
        is_verified=True
    )
    return user


@pytest.fixture
def shop_a(db, owner_user, cashier_user):
    shop = Shop.objects.create(
        name="Do'kon A",
        owner=owner_user,
        phone_number="+998901234567",
        address="Toshkent, Chilonzor 5",
        currency="UZS"
    )
    branch = Branch.objects.create(
        shop=shop,
        name="Asosiy filial",
        is_main=True
    )
    ShopMember.objects.create(
        shop=shop,
        branch=branch,
        user=owner_user,
        role=UserRole.SHOP_OWNER
    )
    ShopMember.objects.create(
        shop=shop,
        branch=branch,
        user=cashier_user,
        role=UserRole.CASHIER
    )
    return shop


@pytest.fixture
def shop_b(db, other_owner_user):
    shop = Shop.objects.create(
        name="Do'kon B",
        owner=other_owner_user,
        phone_number="+998909876543",
        address="Samarqand, Registon",
        currency="USD"
    )
    branch = Branch.objects.create(
        shop=shop,
        name="Samarqand filial",
        is_main=True
    )
    ShopMember.objects.create(
        shop=shop,
        branch=branch,
        user=other_owner_user,
        role=UserRole.SHOP_OWNER
    )
    return shop


@pytest.fixture
def customer_a(db, shop_a):
    return Customer.objects.create(
        shop=shop_a,
        full_name="Jamshid Normatov",
        phone_number="+998911112233",
        credit_limit=Decimal("1000000.00")
    )


@pytest.fixture
def customer_b(db, shop_b):
    return Customer.objects.create(
        shop=shop_b,
        full_name="Rustam Qodirov",
        phone_number="+998922223344",
        credit_limit=Decimal("500.00")
    )


@pytest.fixture
def debt_a(db, shop_a, customer_a, owner_user):
    return Debt.objects.create(
        shop=shop_a,
        customer=customer_a,
        creator=owner_user,
        amount=Decimal("500000.00"),
        paid_amount=Decimal("0.00"),
        remaining_balance=Decimal("500000.00"),
        description="Oziq-ovqat mahsulotlari",
        debt_date=timezone.localdate(),
        status=DebtStatus.UNPAID
    )


def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client
