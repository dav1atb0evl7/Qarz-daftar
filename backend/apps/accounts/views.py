import secrets
import threading
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status, views, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import CustomUser, TelegramLinkCode, PasswordResetToken
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserProfileSerializer,
    VerifyEmailSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    ChangePasswordSerializer,
    TelegramVerifyLinkSerializer,
    TelegramAuthSerializer
)
from apps.common.utils import generate_verification_code
from apps.audit.services import AuditService


class RegisterView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Register new user account",
        request=RegisterSerializer,
        responses={201: UserProfileSerializer}
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate email verification URL/token asynchronously to avoid blocking HTTP response
        if user.verification_token:
            verification_url = f"{settings.DEFAULT_FROM_EMAIL}/verify-email?token={user.verification_token}"
            def _send_email_async():
                try:
                    send_mail(
                        subject="Qarz Daftar Pro - Hisobni faollashtirish",
                        message=f"Assalomu alaykum, {user.first_name}!\n\nHisobingizni tasdiqlash uchun havola:\n{verification_url}\n\nToken: {user.verification_token}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True
                    )
                except Exception:
                    pass
            threading.Thread(target=_send_email_async, daemon=True).start()

        AuditService.log_action(
            request=request,
            user=user,
            action="USER_REGISTER",
            entity_type="User",
            entity_id=str(user.id),
            changes={"email": user.email, "role": user.role}
        )

        refresh = RefreshToken.for_user(user)
        response_data = UserProfileSerializer(user).data
        response_data["access"] = str(refresh.access_token)
        response_data["refresh"] = str(refresh)

        return Response({
            "success": True,
            "message": "Registration successful.",
            "data": response_data,
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            },
            "verification_token": user.verification_token if settings.DEBUG else None
        }, status=status.HTTP_201_CREATED)


class VerifyEmailView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Verify email with token",
        request=VerifyEmailSerializer,
        responses={200: OpenApiResponse(description="Email verified successfully")}
    )
    def post(self, request):
        token = request.data.get("token") or request.query_params.get("token")
        serializer = VerifyEmailSerializer(data={"token": token})
        serializer.is_valid(raise_exception=True)

        user = CustomUser.objects.get(verification_token=serializer.validated_data["token"])
        user.is_verified = True
        user.verification_token = ""
        user.save(update_fields=["is_verified", "verification_token"])

        AuditService.log_action(
            request=request,
            user=user,
            action="EMAIL_VERIFIED",
            entity_type="User",
            entity_id=str(user.id)
        )

        return Response({
            "success": True,
            "message": "Email successfully verified. You can now log in."
        }, status=status.HTTP_200_OK)


class LoginView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="User login with email and password",
        request=LoginSerializer,
        responses={200: OpenApiResponse(description="Returns user profile and JWT tokens")}
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        login_data = serializer.validated_data

        user_id = login_data["user"]["id"]
        user = CustomUser.objects.get(id=user_id)

        AuditService.log_action(
            request=request,
            user=user,
            action="LOGIN",
            entity_type="User",
            entity_id=str(user.id)
        )

        return Response({
            "success": True,
            "message": "Login successful.",
            "data": login_data
        }, status=status.HTTP_200_OK)


from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import serializers as drf_serializers


class LogoutView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Logout user and blacklist refresh token",
        request=inline_serializer(
            name='LogoutRequest',
            fields={'refresh': drf_serializers.CharField()}
        ),
        responses={200: OpenApiResponse(description="Successfully logged out.")}
    )
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass

        AuditService.log_action(
            request=request,
            user=request.user,
            action="LOGOUT",
            entity_type="User",
            entity_id=str(request.user.id)
        )

        return Response({
            "success": True,
            "message": "Successfully logged out."
        }, status=status.HTTP_200_OK)


class PasswordResetRequestView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Request password reset email",
        request=PasswordResetRequestSerializer,
        responses={200: OpenApiResponse(description="Password reset email sent if account exists")}
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()

        user = CustomUser.objects.filter(email=email).first()
        if user:
            token_str = secrets.token_urlsafe(32)
            PasswordResetToken.objects.create(
                user=user,
                token=token_str,
                expires_at=timezone.now() + timedelta(hours=2)
            )
            send_mail(
                subject="Qarz Daftar Pro - Parolni qayta tiklash",
                message=f"Parolingizni qayta tiklash kodi: {token_str}\nUshbu kod 2 soat davomida amal qiladi.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )

        return Response({
            "success": True,
            "message": "If an account exists with this email, a password reset link has been sent."
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Confirm password reset with token and new password",
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(description="Password successfully reset")}
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_record = PasswordResetToken.objects.get(token=serializer.validated_data["token"])
        user = token_record.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        token_record.is_used = True
        token_record.save()

        AuditService.log_action(
            request=request,
            user=user,
            action="PASSWORD_RESET",
            entity_type="User",
            entity_id=str(user.id)
        )

        return Response({
            "success": True,
            "message": "Password successfully reset. You may now log in with your new password."
        }, status=status.HTTP_200_OK)


class ChangePasswordView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Change current authenticated user password",
        request=ChangePasswordSerializer,
        responses={200: OpenApiResponse(description="Password successfully changed")}
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({
                "success": False,
                "error": {"message": "Amaldagi parol noto'g'ri kiritildi."}
            }, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data["new_password"])
        user.save()

        AuditService.log_action(
            request=request,
            user=user,
            action="PASSWORD_CHANGE",
            entity_type="User",
            entity_id=str(user.id)
        )

        return Response({
            "success": True,
            "message": "Parolingiz muvaffaqiyatli almashtirildi!"
        }, status=status.HTTP_200_OK)


class UserProfileView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Get current user profile", responses={200: UserProfileSerializer})
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response({
            "success": True,
            "data": serializer.data
        })

    @extend_schema(summary="Update current user profile", request=UserProfileSerializer, responses={200: UserProfileSerializer})
    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        AuditService.log_action(
            request=request,
            user=request.user,
            action="PROFILE_UPDATE",
            entity_type="User",
            entity_id=str(request.user.id),
            changes=request.data
        )

        return Response({
            "success": True,
            "message": "Profile updated successfully.",
            "data": serializer.data
        })


# ==========================================
# Telegram Integration Views
# ==========================================

class TelegramLinkCodeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Generate 6-digit Telegram linking code for current user",
        request=None,
        responses={200: OpenApiResponse(description="Returns 6-digit verification code")}
    )
    def post(self, request):
        # Invalidate old unused codes
        TelegramLinkCode.objects.filter(user=request.user, is_used=False).update(is_used=True)

        code = generate_verification_code(6)
        expires_at = timezone.now() + timedelta(minutes=10)

        record = TelegramLinkCode.objects.create(
            user=request.user,
            code=code,
            expires_at=expires_at
        )

        return Response({
            "success": True,
            "code": record.code,
            "expires_in_minutes": 10,
            "bot_username": settings.TELEGRAM_BOT_USERNAME,
            "message": f"Send /link {record.code} to @{settings.TELEGRAM_BOT_USERNAME} in Telegram."
        })


class TelegramVerifyLinkView(views.APIView):
    """
    Called by Telegram bot webhook/server with secret header to verify code and link account.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Verify 6-digit code and link Telegram ID to user",
        request=TelegramVerifyLinkSerializer,
        responses={200: OpenApiResponse(description="User successfully linked to Telegram")}
    )
    def post(self, request):
        secret = request.headers.get("X-Telegram-Bot-Secret")
        if secret != settings.TELEGRAM_BOT_API_SECRET:
            return Response(
                {"success": False, "error": {"code": "unauthorized", "message": "Invalid bot secret."}},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = TelegramVerifyLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        link_record = serializer.validated_data["link_record"]
        user = link_record.user
        telegram_id = serializer.validated_data["telegram_id"]
        telegram_username = serializer.validated_data.get("telegram_username", "")

        user.telegram_id = telegram_id
        if telegram_username:
            user.telegram_username = telegram_username
        user.save(update_fields=["telegram_id", "telegram_username"])

        link_record.is_used = True
        link_record.save(update_fields=["is_used"])

        AuditService.log_action(
            request=request,
            user=user,
            action="TELEGRAM_LINKED",
            source="TELEGRAM_BOT",
            entity_type="User",
            entity_id=str(user.id),
            changes={"telegram_id": telegram_id, "telegram_username": telegram_username}
        )

        return Response({
            "success": True,
            "message": "Telegram successfully linked.",
            "data": {
                "user_id": str(user.id),
                "email": user.email,
                "full_name": f"{user.first_name} {user.last_name}".strip() or user.email,
                "role": user.role
            }
        })


class TelegramAuthView(views.APIView):
    """
    Called by Telegram bot with bot secret to verify if a telegram_id is registered
    and obtain user profile and active shop context.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Authenticate Telegram bot request and return user shops and JWT token",
        request=TelegramAuthSerializer,
        responses={200: OpenApiResponse(description="User details and owned/member shops")}
    )
    def post(self, request):
        secret = request.headers.get("X-Telegram-Bot-Secret")
        if secret != settings.TELEGRAM_BOT_API_SECRET:
            return Response(
                {"success": False, "error": {"code": "unauthorized", "message": "Invalid bot secret."}},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = TelegramAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        telegram_id = serializer.validated_data["telegram_id"]

        user = CustomUser.objects.filter(telegram_id=telegram_id, is_active=True).first()
        if not user:
            return Response({
                "success": False,
                "error": {
                    "code": "telegram_not_linked",
                    "message": "This Telegram account is not linked to any active user."
                }
            }, status=status.HTTP_404_NOT_FOUND)

        # Get shops associated with user
        from apps.shops.models import Shop, ShopMember
        owned_shops = list(Shop.objects.filter(owner=user, is_active=True).values("id", "name", "currency"))
        member_shops = list(
            ShopMember.objects.filter(user=user, is_active=True, shop__is_active=True)
            .select_related("shop")
            .values("shop_id", "shop__name", "shop__currency", "role")
        )

        refresh = RefreshToken.for_user(user)

        return Response({
            "success": True,
            "user": UserProfileSerializer(user).data,
            "token": str(refresh.access_token),
            "owned_shops": owned_shops,
            "member_shops": member_shops
        })
