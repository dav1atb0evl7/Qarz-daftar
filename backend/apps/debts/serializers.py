from decimal import Decimal
from rest_framework import serializers
from .models import Debt, DebtStatus, DebtHistory
from apps.customers.models import Customer
from apps.shops.models import Branch
from apps.accounts.serializers import UserMinimalSerializer


class DebtHistorySerializer(serializers.ModelSerializer):
    changed_by = UserMinimalSerializer(read_only=True)

    class Meta:
        model = DebtHistory
        fields = ('id', 'changed_by', 'action', 'previous_remaining', 'new_remaining', 'notes', 'created_at')


class DebtSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    creator = UserMinimalSerializer(read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = Debt
        fields = (
            'id', 'shop', 'branch', 'branch_name', 'customer', 'customer_name',
            'customer_phone', 'creator', 'amount', 'paid_amount', 'remaining_balance',
            'description', 'debt_date', 'due_date', 'status', 'cancel_reason',
            'cancelled_at', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'shop', 'creator', 'paid_amount', 'remaining_balance',
            'status', 'cancel_reason', 'cancelled_at', 'created_at', 'updated_at'
        )


class DebtCreateSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    description = serializers.CharField(required=False, allow_blank=True, default="")
    debt_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    branch_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_customer_id(self, value):
        shop = self.context['shop']
        customer = Customer.objects.filter(id=value, shop=shop).first()
        if not customer:
            raise serializers.ValidationError("Customer not found in this shop.")
        if customer.status == 'ARCHIVED':
            raise serializers.ValidationError("Cannot create debt for archived customer.")
        return value


class DebtUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Debt
        fields = ('description', 'due_date')


class DebtCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, min_length=3)
