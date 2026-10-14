import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

logger = logging.getLogger(__name__)


class BusinessValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Business logic validation failed."
    default_code = "business_validation_error"


class InsufficientBalanceError(BusinessValidationError):
    default_detail = "Payment amount exceeds remaining debt balance."
    default_code = "insufficient_balance"


class DebtAlreadyPaidError(BusinessValidationError):
    default_detail = "Debt is already fully paid or cancelled."
    default_code = "debt_already_paid"


class PaymentReversalNotAllowedError(BusinessValidationError):
    default_detail = "Payment cannot be reversed."
    default_code = "payment_reversal_not_allowed"


class ShopAccessDeniedError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to access data for this shop."
    default_code = "shop_access_denied"


def custom_exception_handler(exc, context):
    """
    Standardizes error responses across all endpoints to:
    {
        "success": false,
        "error": {
            "code": "error_code",
            "message": "Human readable message",
            "details": {...}
        }
    }
    """
    # Call REST framework's default exception handler first to get the standard response
    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, 'default_code', 'error')
        if hasattr(exc, 'get_codes'):
            codes = exc.get_codes()
            if isinstance(codes, str):
                error_code = codes
            elif isinstance(codes, dict) and codes:
                error_code = next(iter(codes.values()))
                if isinstance(error_code, list) and error_code:
                    error_code = str(error_code[0])

        details = response.data
        message = "An error occurred."

        if isinstance(details, dict):
            if 'detail' in details:
                message = str(details['detail'])
            elif 'non_field_errors' in details:
                message = str(details['non_field_errors'][0])
            elif details:
                # First field error
                first_key = next(iter(details.keys()))
                first_val = details[first_key]
                if isinstance(first_val, list) and first_val:
                    message = f"{first_key}: {first_val[0]}"
                else:
                    message = f"{first_key}: {first_val}"
        elif isinstance(details, list) and details:
            message = str(details[0])

        response.data = {
            "success": False,
            "error": {
                "code": str(error_code),
                "message": message,
                "details": details,
            }
        }
    else:
        # Unhandled 500 error
        logger.exception("Unhandled server exception: %s", exc)
        response = Response(
            {
                "success": False,
                "error": {
                    "code": "server_error",
                    "message": "Internal server error occurred.",
                    "details": str(exc) if getattr(context.get('request'), 'user', None) and getattr(context.get('request').user, 'is_staff', False) else None
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response
