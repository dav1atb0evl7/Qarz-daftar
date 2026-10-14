from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from rest_framework import viewsets, permissions, filters
from drf_spectacular.utils import extend_schema

from .models import AuditLog, AuditAction, AuditSource
from .serializers import AuditLogSerializer
from apps.common.permissions import IsManagerOrAbove, get_requested_shop


class AuditLogFilter(django_filters.FilterSet):
    action = django_filters.ChoiceFilter(choices=AuditAction.choices)
    source = django_filters.ChoiceFilter(choices=AuditSource.choices)
    entity_type = django_filters.CharFilter(lookup_expr='iexact')
    start_date = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    end_date = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')

    class Meta:
        model = AuditLog
        fields = ['action', 'source', 'entity_type', 'start_date', 'end_date']


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only view for reviewing system and financial audit history.
    Accessible only to Shop Owners and Managers.
    """
    permission_classes = [permissions.IsAuthenticated, IsManagerOrAbove]
    serializer_class = AuditLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AuditLogFilter
    search_fields = ['entity_id', 'entity_type', 'user__email', 'ip_address']
    ordering_fields = ['timestamp', 'action']
    ordering = ['-timestamp']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return AuditLog.objects.none()
        shop = get_requested_shop(self.request)
        return AuditLog.objects.filter(shop=shop).select_related('user', 'shop')
