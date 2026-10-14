from decimal import Decimal
from django.db.models import Sum, Q, Count
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Customer, CustomerStatus
from apps.shops.serializers import BranchSerializer


class CustomerSerializer(serializers.ModelSerializer):
    total_debt = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    remaining_balance = serializers.SerializerMethodField()
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = Customer
        fields = (
            'id', 'shop', 'branch', 'branch_name', 'full_name',
            'phone_number', 'address', 'notes', 'credit_limit',
            'status', 'total_debt', 'total_paid', 'remaining_balance',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'shop', 'created_at', 'updated_at')

    @extend_schema_field(serializers.DecimalField(max_digits=14, decimal_places=2))
    def get_total_debt(self, obj):
        val = obj.debts.exclude(status='CANCELLED').aggregate(total=Sum('amount'))['total']
        return val or Decimal('0.00')

    @extend_schema_field(serializers.DecimalField(max_digits=14, decimal_places=2))
    def get_total_paid(self, obj):
        val = obj.debts.exclude(status='CANCELLED').aggregate(total=Sum('paid_amount'))['total']
        return val or Decimal('0.00')

    @extend_schema_field(serializers.DecimalField(max_digits=14, decimal_places=2))
    def get_remaining_balance(self, obj):
        val = obj.debts.exclude(status='CANCELLED').aggregate(total=Sum('remaining_balance'))['total']
        return val or Decimal('0.00')


class CustomerSummarySerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    full_name = serializers.CharField()
    phone_number = serializers.CharField()
    total_debt = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=14, decimal_places=2)
    remaining_balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    active_debts_count = serializers.IntegerField()
    overdue_debts_count = serializers.IntegerField()
    status = serializers.CharField()


class CustomerDetailSerializer(CustomerSerializer):
    active_debts_count = serializers.SerializerMethodField()
    overdue_debts_count = serializers.SerializerMethodField()

    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields + ('active_debts_count', 'overdue_debts_count')

    @extend_schema_field(serializers.IntegerField())
    def get_active_debts_count(self, obj):
        return obj.debts.filter(status__in=['UNPAID', 'PARTIALLY_PAID', 'OVERDUE']).count()

    @extend_schema_field(serializers.IntegerField())
    def get_overdue_debts_count(self, obj):
        return obj.debts.filter(status='OVERDUE').count()
