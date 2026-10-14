from django.contrib import admin
from .models import Debt, DebtHistory


class DebtHistoryInline(admin.TabularInline):
    model = DebtHistory
    extra = 0
    readonly_fields = ('changed_by', 'action', 'previous_remaining', 'new_remaining', 'notes', 'created_at')


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ('customer', 'shop', 'branch', 'amount', 'paid_amount', 'remaining_balance', 'debt_date', 'due_date', 'status')
    list_filter = ('status', 'shop', 'branch', 'debt_date', 'due_date')
    search_fields = ('customer__full_name', 'customer__phone_number', 'description')
    readonly_fields = ('paid_amount', 'remaining_balance', 'created_at', 'updated_at')
    inlines = [DebtHistoryInline]


@admin.register(DebtHistory)
class DebtHistoryAdmin(admin.ModelAdmin):
    list_display = ('debt', 'changed_by', 'action', 'previous_remaining', 'new_remaining', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('debt__customer__full_name', 'notes')
