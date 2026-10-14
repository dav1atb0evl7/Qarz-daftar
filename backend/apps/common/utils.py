import random
import string
from django.utils import timezone


def generate_receipt_number(prefix="RCP"):
    """
    Generates a human-friendly unique receipt reference number,
    e.g. RCP-20261014-948271
    """
    timestamp = timezone.now().strftime("%Y%m%d")
    random_suffix = ''.join(random.choices(string.digits, k=6))
    return f"{prefix}-{timestamp}-{random_suffix}"


def generate_verification_code(length=6):
    """
    Generates a secure numeric verification or telegram link code.
    """
    return ''.join(random.choices(string.digits, k=length))


def format_currency(amount, currency="UZS"):
    """
    Formats a decimal amount with thousands separator and currency label.
    e.g., 500000 -> '500,000 UZS'
    """
    try:
        formatted = f"{float(amount):,.2f}".rstrip('0').rstrip('.')
        return f"{formatted} {currency}"
    except (ValueError, TypeError):
        return f"{amount} {currency}"
