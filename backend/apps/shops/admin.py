from django.contrib import admin
from .models import Shop, Branch, ShopMember


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 1


class ShopMemberInline(admin.TabularInline):
    model = ShopMember
    extra = 1


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'phone_number', 'currency', 'is_active', 'created_at')
    list_filter = ('currency', 'is_active', 'created_at')
    search_fields = ('name', 'owner__email', 'phone_number')
    inlines = [BranchInline, ShopMemberInline]


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'shop', 'phone_number', 'is_main', 'is_active')
    list_filter = ('is_main', 'is_active')
    search_fields = ('name', 'shop__name')


@admin.register(ShopMember)
class ShopMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'shop', 'branch', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active')
    search_fields = ('user__email', 'shop__name')
