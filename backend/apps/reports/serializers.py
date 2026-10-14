from rest_framework import serializers


class StatusCountsSerializer(serializers.Serializer):
    unpaid = serializers.IntegerField()
    partially_paid = serializers.IntegerField()
    paid = serializers.IntegerField()
    overdue = serializers.IntegerField()
    cancelled = serializers.IntegerField()


class ReportSummarySerializer(serializers.Serializer):
    currency = serializers.CharField()
    total_debt_created = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_payments_collected = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_cash_collected = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_card_collected = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_reversed_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    count_reversed_payments = serializers.IntegerField()
    current_outstanding_debt = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_overdue_debt = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_customers_count = serializers.IntegerField()
    active_debtors_count = serializers.IntegerField()
    debt_counts_by_status = StatusCountsSerializer()


class PaymentTrendItemSerializer(serializers.Serializer):
    period = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    cash_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    card_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    transaction_count = serializers.IntegerField()


class BranchPerformanceItemSerializer(serializers.Serializer):
    branch_id = serializers.CharField()
    branch_name = serializers.CharField()
    is_main = serializers.BooleanField()
    total_debt_issued = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_payments_collected = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding_balance = serializers.DecimalField(max_digits=14, decimal_places=2)
