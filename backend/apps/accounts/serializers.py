import secrets
from datetime import timedelta
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser, UserRole, TelegramLinkCode, PasswordResetToken
from apps.common.utils import generate_verification_code


from drf_spectacular.utils import extend_schema_field


class UserMinimalSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'full_name', 'phone_number', 'role', 'is_active', 'is_verified')
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else obj.email


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'full_name', 'phone_number', 'role', 'is_verified',
            'telegram_id', 'telegram_username', 'created_at'
        )
        read_only_fields = ('id', 'email', 'role', 'is_verified', 'telegram_id', 'telegram_username', 'created_at')

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else obj.email


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'phone_number', 'full_name', 'password', 'password_confirm', 'role')
        read_only_fields = ('id',)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        if 'email' in attrs:
            attrs['email'] = attrs['email'].strip().lower()
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        full_name = validated_data.pop('full_name', '')
        password = validated_data.pop('password')
        email = validated_data['email'].strip().lower()

        first_name = ""
        last_name = ""
        if full_name:
            parts = full_name.strip().split(" ", 1)
            first_name = parts[0]
            if len(parts) > 1:
                last_name = parts[1]

        verification_token = secrets.token_urlsafe(32)
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=validated_data.get('phone_number'),
            role=validated_data.get('role', UserRole.SHOP_OWNER),
            verification_token=verification_token,
            is_verified=False
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get('email').lower()
        password = attrs.get('password')

        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated. Please contact support.")

        refresh = RefreshToken.for_user(user)

        return {
            'user': UserProfileSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)

    def validate_token(self, value):
        user = CustomUser.objects.filter(verification_token=value).first()
        if not user:
            raise serializers.ValidationError("Invalid or expired verification token.")
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})

        reset_token = PasswordResetToken.objects.filter(token=attrs['token']).first()
        if not reset_token or not reset_token.is_valid():
            raise serializers.ValidationError({"token": "Password reset link is invalid or expired."})

        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "Yangi parollar bir-biriga mos kelmadi."})
        return attrs


class TelegramVerifyLinkSerializer(serializers.Serializer):
    code = serializers.CharField(required=True, max_length=6)
    telegram_id = serializers.CharField(required=True, max_length=64)
    telegram_username = serializers.CharField(required=False, allow_blank=True, max_length=128)

    def validate(self, attrs):
        code = attrs['code'].strip()
        link_record = TelegramLinkCode.objects.filter(code=code).first()

        if not link_record or not link_record.is_valid():
            raise serializers.ValidationError({"code": "Verification code is invalid or has expired."})

        attrs['link_record'] = link_record
        return attrs


class TelegramAuthSerializer(serializers.Serializer):
    telegram_id = serializers.CharField(required=True, max_length=64)
