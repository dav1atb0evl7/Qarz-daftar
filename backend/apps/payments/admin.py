from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'receipt_number', 'customer', 'amount', 'payment_method',
        'cash_amount', 'card_amount', 'payment_date', 'received_by',
        'is_reversed'
    )
    list_filter = ('payment_method', 'is_reversed', 'shop', 'branch', 'payment_date')
    search_fields = ('receipt_number', 'customer__full_name', 'notes')
    readonly_fields = (
        'receipt_number', 'shop', 'debt', 'customer', 'amount',
        'cash_amount', 'card_amount', 'payment_date', 'received_by',
        'is_reversed', 'reversal_reason', 'reversed_at', 'reversed_by',
        'created_at', 'updated_at'
    )
