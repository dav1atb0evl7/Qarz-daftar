from decimal import Decimal
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .models import Payment, PaymentMethod
from .serializers import (
    PaymentSerializer,
    PaymentCreateSerializer,
    PaymentReverseSerializer
)
from .services import PaymentService
from apps.common.permissions import IsShopMember, IsManagerOrAbove, get_requested_shop
from apps.common.utils import format_currency


class PaymentFilter(django_filters.FilterSet):
    customer = django_filters.UUIDFilter(field_name='customer_id')
    debt = django_filters.UUIDFilter(field_name='debt_id')
    payment_method = django_filters.ChoiceFilter(choices=PaymentMethod.choices)
    is_reversed = django_filters.BooleanFilter(field_name='is_reversed')
    branch = django_filters.UUIDFilter(field_name='branch_id')
    start_date = django_filters.DateTimeFilter(field_name='payment_date', lookup_expr='gte')
    end_date = django_filters.DateTimeFilter(field_name='payment_date', lookup_expr='lte')
    min_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')

    class Meta:
        model = Payment
        fields = ['customer', 'debt', 'payment_method', 'is_reversed', 'branch', 'start_date', 'end_date']


class PaymentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsShopMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PaymentFilter
    search_fields = ['receipt_number', 'customer__full_name', 'customer__phone_number', 'notes']
    ordering_fields = ['payment_date', 'amount', 'created_at']
    ordering = ['-payment_date']
    http_method_names = ['get', 'post', 'head', 'options']  # No direct PUT/DELETE on payments

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Payment.objects.none()
        shop = get_requested_shop(self.request)
        return Payment.objects.filter(shop=shop).select_related(
            'customer', 'debt', 'received_by', 'reversed_by', 'branch', 'shop'
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer

    def create(self, request, *args, **kwargs):
        shop = get_requested_shop(request)
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = PaymentService.process_payment(
            shop=shop,
            debt_id=serializer.validated_data['debt_id'],
            received_by=request.user,
            payment_method=serializer.validated_data['payment_method'],
            amount=serializer.validated_data['amount'],
            cash_amount=serializer.validated_data.get('cash_amount'),
            card_amount=serializer.validated_data.get('card_amount'),
            notes=serializer.validated_data.get('notes', ''),
            payment_date=serializer.validated_data.get('payment_date'),
            request=request
        )

        return Response({
            "success": True,
            "message": "Payment processed successfully.",
            "data": PaymentSerializer(payment).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='reverse', permission_classes=[permissions.IsAuthenticated, IsManagerOrAbove])
    def reverse(self, request, pk=None):
        """Reverses an existing payment transaction with reason."""
        payment = self.get_object()
        serializer = PaymentReverseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data['reason']
        reversed_payment = PaymentService.reverse_payment(
            payment=payment,
            reversed_by=request.user,
            reason=reason,
            request=request
        )

        return Response({
            "success": True,
            "message": "Payment has been successfully reversed.",
            "data": PaymentSerializer(reversed_payment).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='receipt')
    def receipt(self, request, pk=None):
        """Generates receipt summary data for printing or customer sharing."""
        payment = self.get_object()
        shop = payment.shop
        currency = shop.currency

        receipt_data = {
            "shop_name": shop.name,
            "shop_phone": shop.phone_number,
            "shop_address": shop.address,
            "branch_name": payment.branch.name if payment.branch else "Asosiy",
            "receipt_number": payment.receipt_number,
            "payment_date": payment.payment_date.strftime("%Y-%m-%d %H:%M:%S"),
            "customer_name": payment.customer.full_name,
            "customer_phone": payment.customer.phone_number,
            "payment_method": payment.get_payment_method_display(),
            "amount_paid": format_currency(payment.amount, currency),
            "cash_portion": format_currency(payment.cash_amount, currency) if payment.cash_amount > 0 else None,
            "card_portion": format_currency(payment.card_amount, currency) if payment.card_amount > 0 else None,
            "remaining_debt": format_currency(payment.debt.remaining_balance, currency),
            "original_debt_amount": format_currency(payment.debt.amount, currency),
            "cashier": f"{payment.received_by.first_name} {payment.received_by.last_name}".strip() or payment.received_by.email,
            "is_reversed": payment.is_reversed,
            "reversal_reason": payment.reversal_reason if payment.is_reversed else None
        }

        return Response({"success": True, "receipt": receipt_data})
