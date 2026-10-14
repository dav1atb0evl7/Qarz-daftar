from decimal import Decimal
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .models import Debt, DebtStatus, DebtHistory
from .serializers import (
    DebtSerializer,
    DebtCreateSerializer,
    DebtUpdateSerializer,
    DebtCancelSerializer,
    DebtHistorySerializer,
)
from .services import DebtService
from apps.customers.models import Customer
from apps.shops.models import Branch
from apps.common.permissions import IsShopMember, IsManagerOrAbove, get_requested_shop
from apps.common.exceptions import BusinessValidationError
from apps.audit.services import AuditService


class DebtFilter(django_filters.FilterSet):
    customer = django_filters.UUIDFilter(field_name='customer_id')
    status = django_filters.ChoiceFilter(choices=DebtStatus.choices)
    start_date = django_filters.DateFilter(field_name='debt_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='debt_date', lookup_expr='lte')
    due_start = django_filters.DateFilter(field_name='due_date', lookup_expr='gte')
    due_end = django_filters.DateFilter(field_name='due_date', lookup_expr='lte')
    branch = django_filters.UUIDFilter(field_name='branch_id')
    min_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')

    class Meta:
        model = Debt
        fields = ['customer', 'status', 'branch', 'start_date', 'end_date']


class DebtViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsShopMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DebtFilter
    search_fields = ['customer__full_name', 'customer__phone_number', 'description']
    ordering_fields = ['debt_date', 'amount', 'remaining_balance', 'created_at']
    ordering = ['-debt_date', '-created_at']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Debt.objects.none()
        shop = get_requested_shop(self.request)
        return Debt.objects.filter(shop=shop).select_related('customer', 'creator', 'branch', 'shop')

    def get_serializer_class(self):
        if self.action == 'create':
            return DebtCreateSerializer
        if self.action in ('update', 'partial_update'):
            return DebtUpdateSerializer
        return DebtSerializer

    def create(self, request, *args, **kwargs):
        shop = get_requested_shop(request)
        serializer = DebtCreateSerializer(data=request.data, context={'shop': shop, 'request': request})
        serializer.is_valid(raise_exception=True)

        customer = Customer.objects.get(id=serializer.validated_data['customer_id'], shop=shop)
        branch = None
        if serializer.validated_data.get('branch_id'):
            branch = Branch.objects.filter(id=serializer.validated_data['branch_id'], shop=shop).first()

        debt = DebtService.create_debt(
            shop=shop,
            customer=customer,
            creator=request.user,
            amount=serializer.validated_data['amount'],
            description=serializer.validated_data.get('description', ''),
            debt_date=serializer.validated_data.get('debt_date'),
            due_date=serializer.validated_data.get('due_date'),
            branch=branch
        )

        AuditService.log_action(
            request=request,
            user=request.user,
            shop=shop,
            action="DEBT_CREATE",
            entity_type="Debt",
            entity_id=str(debt.id),
            changes={
                "customer": customer.full_name,
                "amount": str(debt.amount),
                "due_date": str(debt.due_date) if debt.due_date else None
            }
        )

        return Response({
            "success": True,
            "message": "Debt recorded successfully.",
            "data": DebtSerializer(debt).data
        }, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        shop = get_requested_shop(self.request)
        debt = self.get_object()
        updated_debt = serializer.save()

        DebtHistory.objects.create(
            debt=updated_debt,
            changed_by=self.request.user,
            action="UPDATED",
            previous_remaining=updated_debt.remaining_balance,
            new_remaining=updated_debt.remaining_balance,
            notes=f"Updated details: {serializer.validated_data}"
        )

        AuditService.log_action(
            request=self.request,
            user=self.request.user,
            shop=shop,
            action="DEBT_UPDATE",
            entity_type="Debt",
            entity_id=str(updated_debt.id),
            changes=serializer.validated_data
        )

    @action(detail=True, methods=['post'], url_path='cancel', permission_classes=[permissions.IsAuthenticated, IsManagerOrAbove])
    def cancel(self, request, pk=None):
        """Cancels a debt if it has no active payments."""
        debt = self.get_object()
        shop = get_requested_shop(request)

        serializer = DebtCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data['reason']

        cancelled_debt = DebtService.cancel_debt(debt=debt, user=request.user, reason=reason)

        AuditService.log_action(
            request=request,
            user=request.user,
            shop=shop,
            action="DEBT_CANCEL",
            entity_type="Debt",
            entity_id=str(cancelled_debt.id),
            changes={"reason": reason}
        )

        return Response({
            "success": True,
            "message": "Debt successfully cancelled.",
            "data": DebtSerializer(cancelled_debt).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='payments')
    def payments(self, request, pk=None):
        """List all payments applied to this debt."""
        debt = self.get_object()
        payments_qs = debt.payments.all().order_by('-payment_date')

        from apps.payments.serializers import PaymentSerializer
        page = self.paginate_queryset(payments_qs)
        if page is not None:
            serializer = PaymentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PaymentSerializer(payments_qs, many=True)
        return Response({"success": True, "results": serializer.data})

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        """List audit history logs for this debt."""
        debt = self.get_object()
        history_qs = debt.history_logs.all().order_by('-created_at')
        serializer = DebtHistorySerializer(history_qs, many=True)
        return Response({"success": True, "results": serializer.data})
