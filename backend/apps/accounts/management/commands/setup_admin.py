import sys
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import CustomUser, UserRole
from apps.shops.models import Shop, Branch, ShopMember


class Command(BaseCommand):
    help = "Yangi tizim ma'muri yoki do'kon egasini yaratish (Production-ready setup)"

    def add_arguments(self, parser):
        parser.add_argument("--email", type=str, help="Foydalanuvchi elektron pochtasi")
        parser.add_argument("--password", type=str, help="Foydalanuvchi paroli")
        parser.add_argument("--first-name", type=str, default="Administrator", help="Ismi")
        parser.add_argument("--last-name", type=str, default="", help="Familiyasi")
        parser.add_argument("--phone", type=str, default="+998901234567", help="Telefon raqami")
        parser.add_argument("--shop-name", type=str, default="", help="Yaratiladigan do'kon nomi (ixtiyoriy)")
        parser.add_argument("--superadmin", action="store_true", help="Superuser / SuperAdmin sifatida yaratish")

    def handle(self, *args, **options):
        email = options.get("email")
        password = options.get("password")

        if not email:
            email = input("Elektron pochta (Email): ").strip()
        if not password:
            import getpass
            password = getpass.getpass("Parol: ").strip()

        if not email or not password:
            self.stderr.write(self.style.ERROR("Email va parol kiritilishi shart!"))
            sys.exit(1)

        first_name = options.get("first_name") or "Administrator"
        last_name = options.get("last_name") or ""
        phone = options.get("phone") or ""
        shop_name = options.get("shop_name") or ""
        is_super = options.get("superadmin") or False

        with transaction.atomic():
            user, created = CustomUser.objects.get_or_create(
                email=email.lower(),
                defaults={
                    "username": email.lower(),
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone_number": phone,
                    "role": UserRole.SUPER_ADMIN if is_super else UserRole.SHOP_OWNER,
                    "is_staff": is_super,
                    "is_superuser": is_super,
                    "is_verified": True,
                    "is_active": True,
                }
            )

            if not created:
                user.set_password(password)
                user.is_verified = True
                user.is_active = True
                if is_super:
                    user.is_staff = True
                    user.is_superuser = True
                    user.role = UserRole.SUPER_ADMIN
                user.save()
                self.stdout.write(self.style.WARNING(f"Mavjud foydalanuvchi ({email}) yangilandi va paroli yangilandi."))
            else:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Yangi foydalanuvchi ({email}) muvaffaqiyatli yaratildi."))

            if shop_name:
                shop, s_created = Shop.objects.get_or_create(
                    owner=user,
                    name=shop_name,
                    defaults={
                        "phone_number": phone,
                        "currency": "UZS",
                        "is_active": True
                    }
                )
                branch, _ = Branch.objects.get_or_create(
                    shop=shop,
                    is_main=True,
                    defaults={
                        "name": "Asosiy filial #01",
                        "phone_number": phone
                    }
                )
                ShopMember.objects.get_or_create(
                    shop=shop,
                    user=user,
                    defaults={
                        "branch": branch,
                        "role": UserRole.SHOP_OWNER,
                        "is_active": True
                    }
                )
                self.stdout.write(self.style.SUCCESS(f"Do'kon '{shop.name}' va uning filiali muvaffaqiyatli biriktirildi."))

        self.stdout.write(self.style.SUCCESS("\nTayyor! Ushbu ma'lumotlar bilan tizimga kirishingiz mumkin."))
