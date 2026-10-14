from rest_framework import serializers
from .models import Shop, Branch, ShopMember
from apps.accounts.models import CustomUser, UserRole
from apps.accounts.serializers import UserMinimalSerializer


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ('id', 'shop', 'name', 'address', 'phone_number', 'is_main', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


class ShopMemberSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = ShopMember
        fields = ('id', 'shop', 'user', 'branch', 'branch_name', 'role', 'is_active', 'created_at')
        read_only_fields = ('id', 'shop', 'created_at')


class ShopMemberCreateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(choices=[
        (UserRole.SHOP_OWNER, "Shop Owner"),
        (UserRole.MANAGER, "Manager"),
        (UserRole.CASHIER, "Cashier"),
    ], default=UserRole.CASHIER)
    branch_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_email(self, value):
        user = CustomUser.objects.filter(email=value.lower()).first()
        if not user:
            raise serializers.ValidationError("User with this email is not registered yet.")
        return value.lower()


class ShopSerializer(serializers.ModelSerializer):
    owner = UserMinimalSerializer(read_only=True)
    branches = BranchSerializer(many=True, read_only=True)
    members_count = serializers.IntegerField(source='members.count', read_only=True)

    class Meta:
        model = Shop
        fields = (
            'id', 'name', 'slug', 'owner', 'phone_number', 'address',
            'currency', 'is_active', 'branches', 'members_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'slug', 'owner', 'created_at', 'updated_at')


class ShopCreateSerializer(serializers.ModelSerializer):
    main_branch_name = serializers.CharField(required=False, default="Asosiy filial", write_only=True)

    class Meta:
        model = Shop
        fields = ('id', 'name', 'phone_number', 'address', 'currency', 'main_branch_name')
        read_only_fields = ('id',)

    def create(self, validated_data):
        main_branch_name = validated_data.pop('main_branch_name', "Asosiy filial")
        user = self.context['request'].user
        shop = Shop.objects.create(owner=user, **validated_data)

        # Create default main branch
        branch = Branch.objects.create(
            shop=shop,
            name=main_branch_name,
            address=shop.address,
            phone_number=shop.phone_number,
            is_main=True
        )

        # Create shop membership for owner
        ShopMember.objects.create(
            shop=shop,
            branch=branch,
            user=user,
            role=UserRole.SHOP_OWNER,
            is_active=True
        )

        # Initialize default notification preferences
        from apps.notifications.models import NotificationPreference
        NotificationPreference.objects.create(shop=shop)

        return shop
