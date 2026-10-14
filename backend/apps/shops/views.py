from django.db.models import Q
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .models import Shop, Branch, ShopMember
from .serializers import (
    ShopSerializer,
    ShopCreateSerializer,
    BranchSerializer,
    ShopMemberSerializer,
    ShopMemberCreateSerializer,
)
from apps.accounts.models import CustomUser, UserRole
from apps.common.permissions import IsShopOwner, IsManagerOrAbove, get_user_role_in_shop
from apps.common.exceptions import ShopAccessDeniedError, BusinessValidationError
from apps.audit.services import AuditService


class ShopViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Shop.objects.none()
        user = self.request.user
        if not user or not user.is_authenticated:
            return Shop.objects.none()
        if user.is_superuser or getattr(user, 'role', '') == 'SUPER_ADMIN':
            return Shop.objects.all().prefetch_related('branches', 'members')
        return Shop.objects.filter(
            Q(owner=user) | Q(members__user=user, members__is_active=True),
            is_active=True
        ).distinct().prefetch_related('branches', 'members')

    def get_serializer_class(self):
        if self.action == 'create':
            return ShopCreateSerializer
        return ShopSerializer

    def perform_create(self, serializer):
        shop = serializer.save()
        AuditService.log_action(
            request=self.request,
            user=self.request.user,
            shop=shop,
            action="SHOP_CREATE",
            entity_type="Shop",
            entity_id=str(shop.id),
            changes={"name": shop.name, "currency": shop.currency}
        )

    def perform_update(self, serializer):
        shop = self.get_object()
        role = get_user_role_in_shop(self.request.user, shop)
        if role not in ('SUPER_ADMIN', 'SHOP_OWNER', 'MANAGER'):
            raise ShopAccessDeniedError("Only shop owners or managers can edit shop details.")
        old_name = shop.name
        updated_shop = serializer.save()
        AuditService.log_action(
            request=self.request,
            user=self.request.user,
            shop=updated_shop,
            action="SHOP_UPDATE",
            entity_type="Shop",
            entity_id=str(updated_shop.id),
            changes={"old_name": old_name, "new_name": updated_shop.name}
        )

    # ================= Branches Sub-Endpoints =================
    @action(detail=True, methods=['get', 'post'], url_path='branches')
    def branches(self, request, pk=None):
        shop = self.get_object()
        role = get_user_role_in_shop(request.user, shop)
        if not role:
            raise ShopAccessDeniedError()

        if request.method == 'GET':
            branches = shop.branches.all()
            serializer = BranchSerializer(branches, many=True)
            return Response({"success": True, "data": serializer.data})

        # POST - create branch (Owner or Manager)
        if role not in ('SUPER_ADMIN', 'SHOP_OWNER', 'MANAGER'):
            raise ShopAccessDeniedError("Only shop owners or managers can add branches.")

        data = request.data.copy()
        data['shop'] = shop.id
        serializer = BranchSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        branch = serializer.save()

        AuditService.log_action(
            request=request,
            user=request.user,
            shop=shop,
            action="BRANCH_CREATE",
            entity_type="Branch",
            entity_id=str(branch.id),
            changes={"name": branch.name}
        )

        return Response({"success": True, "data": serializer.data}, status=status.HTTP_201_CREATED)

    # ================= Members Sub-Endpoints =================
    @action(detail=True, methods=['get', 'post'], url_path='members')
    def members(self, request, pk=None):
        shop = self.get_object()
        role = get_user_role_in_shop(request.user, shop)
        if not role:
            raise ShopAccessDeniedError()

        if request.method == 'GET':
            members = shop.members.filter(is_active=True).select_related('user', 'branch')
            serializer = ShopMemberSerializer(members, many=True)
            return Response({"success": True, "data": serializer.data})

        # POST - add employee (Owner or Manager)
        if role not in ('SUPER_ADMIN', 'SHOP_OWNER', 'MANAGER'):
            raise ShopAccessDeniedError("Only shop owners or managers can add members.")

        create_serializer = ShopMemberCreateSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)

        user_to_add = CustomUser.objects.get(email=create_serializer.validated_data['email'])
        desired_role = create_serializer.validated_data['role']
        branch_id = create_serializer.validated_data.get('branch_id')

        # Only Owner can appoint another Owner or Manager
        if desired_role in (UserRole.SHOP_OWNER, UserRole.MANAGER) and role not in ('SUPER_ADMIN', 'SHOP_OWNER'):
            raise ShopAccessDeniedError("Only the shop owner can assign Manager or Owner roles.")

        branch = None
        if branch_id:
            branch = shop.branches.filter(id=branch_id).first()

        member, created = ShopMember.objects.update_or_create(
            shop=shop,
            user=user_to_add,
            defaults={
                'role': desired_role,
                'branch': branch,
                'is_active': True
            }
        )

        AuditService.log_action(
            request=request,
            user=request.user,
            shop=shop,
            action="MEMBER_ADDED" if created else "MEMBER_UPDATED",
            entity_type="ShopMember",
            entity_id=str(member.id),
            changes={"user_email": user_to_add.email, "role": desired_role}
        )

        return Response({
            "success": True,
            "message": "Member added successfully.",
            "data": ShopMemberSerializer(member).data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['delete', 'patch'], url_path=r'members/(?P<member_id>[^/.]+)')
    def member_detail(self, request, pk=None, member_id=None):
        shop = self.get_object()
        current_user_role = get_user_role_in_shop(request.user, shop)

        if current_user_role not in ('SUPER_ADMIN', 'SHOP_OWNER', 'MANAGER'):
            raise ShopAccessDeniedError("Permission denied.")

        member = shop.members.filter(id=member_id).first()
        if not member:
            return Response(
                {"success": False, "error": {"code": "not_found", "message": "Member not found."}},
                status=status.HTTP_404_NOT_FOUND
            )

        if member.user_id == shop.owner_id:
            raise BusinessValidationError("Cannot modify or remove the primary shop owner.")

        if request.method == 'DELETE':
            member.is_active = False
            member.save(update_fields=['is_active'])

            AuditService.log_action(
                request=request,
                user=request.user,
                shop=shop,
                action="MEMBER_REMOVED",
                entity_type="ShopMember",
                entity_id=str(member.id)
            )

            return Response({"success": True, "message": "Member successfully deactivated."})

        # PATCH - update role or branch
        new_role = request.data.get('role')
        if new_role:
            if new_role in (UserRole.SHOP_OWNER, UserRole.MANAGER) and current_user_role not in ('SUPER_ADMIN', 'SHOP_OWNER'):
                raise ShopAccessDeniedError("Only shop owner can promote to Manager.")
            member.role = new_role

        if 'branch_id' in request.data:
            b_id = request.data.get('branch_id')
            member.branch = shop.branches.filter(id=b_id).first() if b_id else None

        member.save()

        AuditService.log_action(
            request=request,
            user=request.user,
            shop=shop,
            action="MEMBER_UPDATED",
            entity_type="ShopMember",
            entity_id=str(member.id),
            changes=request.data
        )

        return Response({"success": True, "data": ShopMemberSerializer(member).data})
