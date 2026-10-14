from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'user', 'shop', 'source', 'entity_type', 'entity_id', 'ip_address')
    list_filter = ('action', 'source', 'entity_type', 'shop', 'timestamp')
    search_fields = ('entity_id', 'user__email', 'ip_address')
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
