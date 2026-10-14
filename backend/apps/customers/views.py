from decimal import Decimal
from django.db.models import Sum, Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import Customer, CustomerStatus
from .serializers import (
    CustomerSerializer,
    CustomerDetailSerializer,
    CustomerSummarySerializer
)
from apps.common.permissions import IsShopMember, get_requested_shop
from apps.common.exceptions import BusinessValidationError
from apps.audit.services import AuditService


class CustomerViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsShopMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'branch']
    search_fields = ['full_name', 'phone_number', 'notes', 'address']
    ordering_fields = ['full_name', 'created_at']
    ordering = ['full_name']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Customer.objects.none()
        shop = get_requested_shop(self.request)
        return Customer.objects.filter(shop=shop).select_related('shop', 'branch')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CustomerDetailSerializer
        return CustomerSerializer

    def perform_create(self, serializer):
        shop = get_requested_shop(self.request)
        customer = serializer.save(shop=shop)

        AuditService.log_action(
            request=self.request,
            user=self.request.user,
            shop=shop,
            action="CUSTOMER_CREATE",
            entity_type="Customer",
            entity_id=str(customer.id),
            changes={"full_name": customer.full_name, "phone_number": customer.phone_number}
        )

    def perform_update(self, serializer):
        shop = get_requested_shop(self.request)
        old_instance = self.get_object()
        old_name = old_instance.full_name
        customer = serializer.save()

        AuditService.log_action(
            request=self.request,
            user=self.request.user,
            shop=shop,
            action="CUSTOMER_UPDATE",
            entity_type="Customer",
            entity_id=str(customer.id),
            changes={"old_name": old_name, "new_name": customer.full_name}
        )

    def destroy(self, request, *args, **kwargs):
        """
        Soft archive: financial records are never permanently deleted!
        """
        customer = self.get_object()
        shop = get_requested_shop(request)

        # Check if customer has outstanding debt
        outstanding = customer.debts.exclude(status='CANCELLED').aggregate(
            remaining=Sum('remaining_balance')
        )['remaining'] or Decimal('0.00')

        customer.status = CustomerStatus.ARCHIVED
        customer.save(update_fields=['status'])

        AuditService.log_action(
            request=request,
            user=request.user,
            shop=shop,
            action="CUSTOMER_ARCHIVE",
            entity_type="Customer",
            entity_id=str(customer.id),
            changes={"archived": True, "outstanding_debt_at_archive": str(outstanding)}
        )

        return Response({
            "success": True,
            "message": "Customer successfully archived. Financial history is preserved.",
            "outstanding_balance": outstanding
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='summary')
    def summary(self, request, pk=None):
        """Returns financial summary for this specific customer."""
        customer = self.get_object()
        valid_debts = customer.debts.exclude(status='CANCELLED')

        agg = valid_debts.aggregate(
            total_debt=Sum('amount'),
            total_paid=Sum('paid_amount'),
            remaining=Sum('remaining_balance'),
        )

        active_count = valid_debts.filter(status__in=['UNPAID', 'PARTIALLY_PAID', 'OVERDUE']).count()
        overdue_count = valid_debts.filter(status='OVERDUE').count()

        data = {
            "customer_id": customer.id,
            "full_name": customer.full_name,
            "phone_number": customer.phone_number,
            "total_debt": agg['total_debt'] or Decimal('0.00'),
            "total_paid": agg['total_paid'] or Decimal('0.00'),
            "remaining_balance": agg['remaining'] or Decimal('0.00'),
            "active_debts_count": active_count,
            "overdue_debts_count": overdue_count,
            "status": customer.status
        }
        return Response({"success": True, "data": CustomerSummarySerializer(data).data})

    @action(detail=True, methods=['get'], url_path='debts')
    def debts(self, request, pk=None):
        """List all debts belonging to this customer."""
        customer = self.get_object()
        debts_qs = customer.debts.all().order_by('-debt_date', '-created_at')

        from apps.debts.serializers import DebtSerializer
        page = self.paginate_queryset(debts_qs)
        if page is not None:
            serializer = DebtSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = DebtSerializer(debts_qs, many=True)
        return Response({"success": True, "results": serializer.data})

    @action(detail=True, methods=['get'], url_path='payments')
    def payments(self, request, pk=None):
        """List all payments made by this customer."""
        customer = self.get_object()
        payments_qs = customer.payments.all().order_by('-payment_date')

        from apps.payments.serializers import PaymentSerializer
        page = self.paginate_queryset(payments_qs)
        if page is not None:
            serializer = PaymentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PaymentSerializer(payments_qs, many=True)
        return Response({"success": True, "results": serializer.data})
