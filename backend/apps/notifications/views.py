from rest_framework import views, generics, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import NotificationPreference, NotificationLog
from .serializers import NotificationPreferenceSerializer, NotificationLogSerializer
from .tasks import check_and_send_due_date_reminders, check_and_send_overdue_alerts
from apps.common.permissions import IsShopMember, IsManagerOrAbove, get_requested_shop
from apps.audit.services import AuditService


class NotificationPreferenceView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsManagerOrAbove]

    @extend_schema(
        summary="Get notification settings for active shop",
        responses={200: NotificationPreferenceSerializer}
    )
    def get(self, request):
        shop = get_requested_shop(request)
        pref, _ = NotificationPreference.objects.get_or_create(shop=shop)
        return Response({"success": True, "data": NotificationPreferenceSerializer(pref).data})

    @extend_schema(
        summary="Update notification settings for active shop",
        request=NotificationPreferenceSerializer,
        responses={200: NotificationPreferenceSerializer}
    )
    def patch(self, request):
        shop = get_requested_shop(request)
        pref, _ = NotificationPreference.objects.get_or_create(shop=shop)
        serializer = NotificationPreferenceSerializer(pref, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        AuditService.log_action(
            request=request,
            user=request.user,
            shop=shop,
            action="PREFERENCE_UPDATE",
            entity_type="NotificationPreference",
            entity_id=str(pref.id),
            changes=request.data
        )

        return Response({
            "success": True,
            "message": "Notification preferences updated.",
            "data": serializer.data
        })


class NotificationLogListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsShopMember]
    serializer_class = NotificationLogSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return NotificationLog.objects.none()
        shop = get_requested_shop(self.request)
        return NotificationLog.objects.filter(shop=shop).select_related('customer', 'debt')


class TriggerRemindersView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsManagerOrAbove]

    @extend_schema(
        summary="Manually trigger due date and overdue scans",
        request=None,
        responses={200: OpenApiResponse(description="Reminders and overdue scan completed successfully")}
    )
    def post(self, request):
        shop = get_requested_shop(request)
        due_res = check_and_send_due_date_reminders()
        overdue_res = check_and_send_overdue_alerts()

        return Response({
            "success": True,
            "message": "Reminders and overdue scan completed successfully.",
            "details": {
                "due_reminders": due_res,
                "overdue_alerts": overdue_res
            }
        }, status=status.HTTP_200_OK)
