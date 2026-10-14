from decimal import Decimal
from rest_framework import serializers
from .models import Payment, PaymentMethod
from apps.accounts.serializers import UserMinimalSerializer


class PaymentSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    received_by = UserMinimalSerializer(read_only=True)
    reversed_by = UserMinimalSerializer(read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = Payment
        fields = (
            'id', 'shop', 'branch', 'branch_name', 'debt', 'customer',
            'customer_name', 'customer_phone', 'received_by', 'payment_method',
            'amount', 'cash_amount', 'card_amount', 'receipt_number', 'notes',
            'payment_date', 'is_reversed', 'reversal_reason', 'reversed_at',
            'reversed_by', 'created_at', 'updated_at'
        )
        read_only_fields = fields


class PaymentCreateSerializer(serializers.Serializer):
    debt_id = serializers.UUIDField(required=True)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    cash_amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, min_value=Decimal("0.00"))
    card_amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, min_value=Decimal("0.00"))
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    payment_date = serializers.DateTimeField(required=False, allow_null=True)


class PaymentReverseSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, min_length=3, help_text="Reason for reversing this financial payment")
