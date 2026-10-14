import uuid
from rest_framework import permissions
from .exceptions import ShopAccessDeniedError


def get_user_role_in_shop(user, shop):
    """
    Returns the role of the user in the specified shop:
    'SUPER_ADMIN', 'SHOP_OWNER', 'MANAGER', 'CASHIER', or None.
    """
    if not user or not user.is_authenticated:
        return None

    if user.is_superuser or getattr(user, 'role', '') == 'SUPER_ADMIN':
        return 'SUPER_ADMIN'

    if shop.owner_id == user.id:
        return 'SHOP_OWNER'

    # Check ShopMember
    from apps.shops.models import ShopMember
    member = ShopMember.objects.filter(shop=shop, user=user, is_active=True).first()
    if member:
        return member.role

    return None


def get_requested_shop(request, shop_id=None):
    """
    Resolves and verifies active shop for current request.
    Looks in:
    1. explicit shop_id argument
    2. 'X-Shop-ID' request header
    3. 'shop_id' query param or request.data
    4. Default: User's owned shop or first active shop membership
    Raises ShopAccessDeniedError if unauthorized or shop not found.
    """
    from apps.shops.models import Shop, ShopMember

    user = request.user
    if not user or not user.is_authenticated:
        raise ShopAccessDeniedError("Authentication required.")

    target_shop_id = (
        shop_id
        or request.headers.get("X-Shop-ID")
        or request.query_params.get("shop_id")
        or (request.data.get("shop_id") if isinstance(request.data, dict) else None)
    )

    if target_shop_id:
        try:
            shop_uuid = uuid.UUID(str(target_shop_id))
        except (ValueError, AttributeError):
            raise ShopAccessDeniedError("Invalid shop ID format.")

        try:
            shop = Shop.objects.get(id=shop_uuid, is_active=True)
        except Shop.DoesNotExist:
            raise ShopAccessDeniedError("Shop not found or inactive.")

        # Check membership
        role = get_user_role_in_shop(user, shop)
        if not role:
            raise ShopAccessDeniedError("You are not authorized for this shop.")

        return shop

    # Fallback to user's first owned or joined shop
    owned_shop = Shop.objects.filter(owner=user, is_active=True).first()
    if owned_shop:
        return owned_shop

    member = ShopMember.objects.filter(user=user, is_active=True).select_related('shop').first()
    if member and member.shop.is_active:
        return member.shop

    if user.is_superuser or getattr(user, 'role', '') == 'SUPER_ADMIN':
        first_shop = Shop.objects.filter(is_active=True).first()
        if first_shop:
            return first_shop

    raise ShopAccessDeniedError("No active shop found for this user. Please create or join a shop.")


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            (request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPER_ADMIN')
        )


class IsShopOwner(permissions.BasePermission):
    """Allows access only to shop owners or superadmins."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPER_ADMIN':
            return True
        try:
            shop = get_requested_shop(request)
            role = get_user_role_in_shop(request.user, shop)
            return role in ('SUPER_ADMIN', 'SHOP_OWNER')
        except ShopAccessDeniedError:
            return False

    def has_object_permission(self, request, view, obj):
        shop = getattr(obj, 'shop', obj)
        role = get_user_role_in_shop(request.user, shop)
        return role in ('SUPER_ADMIN', 'SHOP_OWNER')


class IsManagerOrAbove(permissions.BasePermission):
    """Allows access to shop owner, manager, or superadmin."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPER_ADMIN':
            return True
        try:
            shop = get_requested_shop(request)
            role = get_user_role_in_shop(request.user, shop)
            return role in ('SUPER_ADMIN', 'SHOP_OWNER', 'MANAGER')
        except ShopAccessDeniedError:
            return False

    def has_object_permission(self, request, view, obj):
        shop = getattr(obj, 'shop', obj)
        role = get_user_role_in_shop(request.user, shop)
        return role in ('SUPER_ADMIN', 'SHOP_OWNER', 'MANAGER')


class IsShopMember(permissions.BasePermission):
    """Allows access to any authorized member of the active shop (owner, manager, cashier)."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPER_ADMIN':
            return True
        try:
            shop = get_requested_shop(request)
            role = get_user_role_in_shop(request.user, shop)
            return role is not None
        except ShopAccessDeniedError:
            return False

    def has_object_permission(self, request, view, obj):
        shop = getattr(obj, 'shop', obj)
        role = get_user_role_in_shop(request.user, shop)
        return role is not None
