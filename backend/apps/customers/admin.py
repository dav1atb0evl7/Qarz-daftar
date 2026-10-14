from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone_number', 'shop', 'branch', 'credit_limit', 'status', 'created_at')
    list_filter = ('status', 'shop', 'branch', 'created_at')
    search_fields = ('full_name', 'phone_number', 'shop__name')
