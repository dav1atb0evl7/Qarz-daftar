from rest_framework import serializers
from .models import AuditLog
from apps.accounts.serializers import UserMinimalSerializer


class AuditLogSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            'id', 'shop', 'user', 'action', 'source', 'entity_type',
            'entity_id', 'changes', 'ip_address', 'user_agent', 'timestamp'
        )
        read_only_fields = fields
