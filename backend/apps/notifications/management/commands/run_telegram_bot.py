"""
Django Management Command: run_telegram_bot
Runs the Qarz Daftar Pro Telegram Bot via Long Polling.
Connects with the real Telegram Bot API and Django Database.
"""

import time
import logging
import requests
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from apps.accounts.models import CustomUser, TelegramLinkCode
from apps.shops.models import Shop, ShopMember
from apps.customers.models import Customer
from apps.debts.models import Debt, DebtStatus
from apps.payments.models import Payment
from apps.reports.services import ReportService
from apps.audit.services import AuditService

logger = logging.getLogger(__name__)


def format_money(val):
    try:
        n = float(val)
        return f"{n:,.0f}".replace(",", " ")
    except Exception:
        return str(val)


class TelegramBotRunner:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0

    def send_request(self, method, payload=None):
        url = f"{self.base_url}/{method}"
        try:
            r = requests.post(url, json=payload or {}, timeout=35)
            return r.json()
        except Exception as e:
            logger.error("Telegram API connection error: %s", e)
            return {"ok": False, "error": str(e)}

    def send_message(self, chat_id, text, reply_markup=None, parse_mode="HTML"):
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.send_request("sendMessage", payload)

    def get_main_keyboard(self):
        return {
            "keyboard": [
                [{"text": "📊 Balans va hisobot"}, {"text": "👥 Qarzdorlar"}],
                [{"text": "📋 So'nggi qarzlar"}, {"text": "💳 To'lovlar"}],
                [{"text": "🔗 Hisobni yangilash"}, {"text": "ℹ️ Yordam"}]
            ],
            "resize_keyboard": True,
            "persistent": True
        }

    def get_user_and_shop(self, telegram_id):
        user = CustomUser.objects.filter(telegram_id=str(telegram_id), is_active=True).first()
        if not user:
            return None, None
        shop = Shop.objects.filter(owner=user, is_active=True).first()
        if not shop:
            member = ShopMember.objects.filter(user=user, is_active=True, shop__is_active=True).select_related("shop").first()
            if member:
                shop = member.shop
        return user, shop

    def handle_update(self, update):
        message = update.get("message")
        if not message:
            return

        chat = message.get("chat", {})
        chat_id = chat.get("id")
        text = (message.get("text") or "").strip()
        from_user = message.get("from", {})
        username = from_user.get("username", "")

        if not chat_id:
            return

        user, shop = self.get_user_and_shop(chat_id)

        # 1. Handle Commands
        if text.startswith("/start"):
            if user and shop:
                name = f"{user.first_name} {user.last_name}".strip() or user.email
                welcome = (
                    f"👋 <b>Assalomu alaykum, {name}!</b>\n\n"
                    f"🏪 Do'kon: <b>{shop.name}</b>\n"
                    f"💼 Rolingiz: <b>{user.get_role_display()}</b>\n\n"
                    f"Siz tizimga muvaffaqiyatli ulangansiz. Kerakli bo'limni tanlang:"
                )
                self.send_message(chat_id, welcome, reply_markup=self.get_main_keyboard())
            else:
                prompt_msg = (
                    "👋 <b>Assalomu alaykum!</b>\n\n"
                    "<b>Qarz Daftar Pro</b> rasmiy botiga xush kelibsiz.\n\n"
                    "Hisobingizni ulash uchun web boshqaruv panelidagi "
                    "<b>'Telegram Bot'</b> bo'limidan 6 xonali tasdiqlash kodini oling va shu yerga yuboring.\n\n"
                    "<i>Masalan: 596681</i>"
                )
                self.send_message(chat_id, prompt_msg)
            return

        # 2. Handle 6-Digit Link Code
        if text.isdigit() and len(text) == 6:
            code_record = TelegramLinkCode.objects.filter(
                code=text,
                is_used=False,
                expires_at__gt=timezone.now()
            ).select_related("user").first()

            if not code_record:
                err_text = (
                    "❌ <b>Tasdiqlash kodi noto'g'ri yoki muddati tugagan!</b>\n\n"
                    "Iltimos, web boshqaruv paneliga kiring va 'Yangi kod olish' tugmasini bosing."
                )
                self.send_message(chat_id, err_text)
                return

            target_user = code_record.user
            target_user.telegram_id = str(chat_id)
            if username:
                target_user.telegram_username = username
            target_user.save(update_fields=["telegram_id", "telegram_username"])

            code_record.is_used = True
            code_record.save(update_fields=["is_used"])

            AuditService.log_action(
                user=target_user,
                action="TELEGRAM_LINKED",
                source="TELEGRAM_BOT",
                entity_type="User",
                entity_id=str(target_user.id),
                changes={"telegram_id": str(chat_id), "telegram_username": username}
            )

            # Retrieve active shop
            _, new_shop = self.get_user_and_shop(chat_id)
            shop_name = new_shop.name if new_shop else "Do'kon"
            name = f"{target_user.first_name} {target_user.last_name}".strip() or target_user.email

            success_text = (
                f"✅ <b>Tabriklaymiz! Hisobingiz muvaffaqiyatli ulandi!</b>\n\n"
                f"👤 Foydalanuvchi: <b>{name}</b>\n"
                f"🏪 Do'kon: <b>{shop_name}</b>\n\n"
                f"Endi bot orqali qarzdorlar ro'yxatini, to'lovlar tarixini va umumiy moliyaviy hisobotlarni tezkor kuzatishingiz mumkin."
            )
            self.send_message(chat_id, success_text, reply_markup=self.get_main_keyboard())
            return

        # Check authentication for remaining actions
        if not user or not shop:
            unlinked_text = (
                "⚠️ <b>Hisobingiz hali tizimga ulanmagan!</b>\n\n"
                "Iltimos, web boshqaruv panelidagi 'Telegram Bot' sahifasidan 6 xonali kodni oling va bu yerga yuboring."
            )
            self.send_message(chat_id, unlinked_text)
            return

        # 3. Handle Menu Buttons
        if text in ("📊 Balans va hisobot", "/balance", "/report"):
            summary = ReportService.get_summary(shop=shop)
            msg = (
                f"📊 <b>{shop.name} — Moliyaviy Holati</b>\n"
                f"📅 <i>{timezone.now().strftime('%Y-%m-%d %H:%M')}</i>\n"
                f"──────────────────────\n"
                f"💰 <b>Jami berilgan qarz:</b> {format_money(summary['total_debt_created'])} UZS\n"
                f"💳 <b>Qabul qilingan to'lovlar:</b> {format_money(summary['total_payments_collected'])} UZS\n"
                f"   • Naqd: {format_money(summary['total_cash_collected'])} UZS\n"
                f"   • Karta: {format_money(summary['total_card_collected'])} UZS\n"
                f"──────────────────────\n"
                f"🔴 <b>Joriy qoldiq qarz:</b> <b>{format_money(summary['current_outstanding_debt'])} UZS</b>\n"
                f"⚠️ <b>Muddati o'tgan qarz:</b> <b>{format_money(summary['total_overdue_debt'])} UZS</b>\n"
                f"──────────────────────\n"
                f"👥 <b>Faol mijozlar:</b> {summary['total_customers_count']} nafar\n"
                f"⚠️ <b>Qarzdor mijozlar:</b> {summary['active_debtors_count']} nafar\n"
            )
            self.send_message(chat_id, msg)
            return

        elif text in ("👥 Qarzdorlar", "/debtors"):
            customers = (
                Customer.objects.filter(shop=shop, status="ACTIVE")
                .prefetch_related("debts")
            )
            debtor_list = []
            for c in customers:
                bal = sum(d.remaining_balance for d in c.debts.all() if d.status not in (DebtStatus.CANCELLED, DebtStatus.PAID))
                if bal > 0:
                    debtor_list.append((c, bal))

            debtor_list.sort(key=lambda x: x[1], reverse=True)

            if not debtor_list:
                self.send_message(chat_id, "🎉 <b>Hozirda do'konda qarzdor mijozlar mavjud emas!</b>")
                return

            lines = [f"👥 <b>Qarzdor mijozlar ro'yxati ({len(debtor_list)} nafar):</b>\n"]
            for idx, (c, bal) in enumerate(debtor_list[:15], 1):
                lines.append(f"{idx}. <b>{c.full_name}</b>\n   📞 <code>{c.phone_number}</code>\n   🔴 Qarz: <b>{format_money(bal)} UZS</b>\n")

            if len(debtor_list) > 15:
                lines.append(f"<i>...va yana {len(debtor_list) - 15} ta mijoz. To'liq ro'yxat web panelda.</i>")

            self.send_message(chat_id, "\n".join(lines))
            return

        elif text in ("📋 So'nggi qarzlar", "/debts"):
            recent_debts = Debt.objects.filter(shop=shop).select_related("customer").order_by("-created_at")[:7]
            if not recent_debts:
                self.send_message(chat_id, "ℹ️ Qarz yozuvlari topilmadi.")
                return

            lines = ["📋 <b>So'nggi qarz shartnomalari:</b>\n"]
            for d in recent_debts:
                status_icon = "🟢" if d.status == DebtStatus.PAID else ("🔴" if d.status == DebtStatus.OVERDUE else "🟡")
                lines.append(
                    f"{status_icon} <b>{d.customer.full_name}</b>\n"
                    f"   Summa: {format_money(d.amount)} UZS | Qoldiq: {format_money(d.remaining_balance)} UZS\n"
                    f"   Holat: {d.get_status_display()} | Muddat: {d.due_date or 'Belgilanmagan'}\n"
                )
            self.send_message(chat_id, "\n".join(lines))
            return

        elif text in ("💳 To'lovlar", "/payments"):
            recent_payments = Payment.objects.filter(shop=shop).select_related("customer").order_by("-payment_date")[:7]
            if not recent_payments:
                self.send_message(chat_id, "ℹ️ To'lovlar tarixi mavjud emas.")
                return

            lines = ["💳 <b>So'nggi qabul qilingan to'lovlar:</b>\n"]
            for p in recent_payments:
                rev = " <i>(Bekor qilingan)</i>" if p.is_reversed else ""
                lines.append(
                    f"🧾 <code>{p.receipt_number}</code> | {p.payment_date.strftime('%d.%m %H:%M')}\n"
                    f"   Mijoz: <b>{p.customer.full_name}</b>\n"
                    f"   Summa: <b>+{format_money(p.amount)} UZS</b> ({p.get_payment_method_display()}){rev}\n"
                )
            self.send_message(chat_id, "\n".join(lines))
            return

        elif text in ("🔗 Hisobni yangilash", "/link"):
            unlink_text = (
                "🔄 <b>Hisobni qayta ulash:</b>\n\n"
                "Agar boshqa foydalanuvchi yoki yangi do'konni ulamoqchi bo'lsangiz, "
                "web boshqaruv panelidagi yangi 6 xonali kodni yuboring."
            )
            self.send_message(chat_id, unlink_text)
            return

        elif text in ("ℹ️ Yordam", "/help"):
            help_text = (
                "ℹ️ <b>Qarz Daftar Pro Bot Yordam:</b>\n\n"
                "• 📊 <b>Balans va hisobot</b> — Jami qarz, to'lovlar va qarzdorlik ko'rsatkichlari\n"
                "• 👥 <b>Qarzdorlar</b> — Faol qarzi bor mijozlar ro'yxati\n"
                "• 📋 <b>So'nggi qarzlar</b> — Oxirgi rasmiylashtirilgan qarzlar\n"
                "• 💳 <b>To'lovlar</b> — Oxirgi qabul qilingan to'lovlar\n"
                "• 🌐 Web panel: <code>http://127.0.0.1:3000</code>\n"
            )
            self.send_message(chat_id, help_text)
            return

        else:
            self.send_message(
                chat_id,
                "Kerakli buyruqni tanlash uchun pastdagi menyudan foydalaning.",
                reply_markup=self.get_main_keyboard()
            )

    def run(self):
        logger.info("Starting Telegram Bot long-polling for token %s...", self.token[:10])
        print(f"[BOT] Telegram Bot ishga tushdi: @{settings.TELEGRAM_BOT_USERNAME}")
        while True:
            try:
                updates_res = self.send_request("getUpdates", {"offset": self.offset, "timeout": 25})
                if updates_res.get("ok"):
                    for item in updates_res.get("result", []):
                        self.offset = item["update_id"] + 1
                        self.handle_update(item)
                else:
                    time.sleep(2)
            except Exception as e:
                logger.error("Polling loop exception: %s", e)
                time.sleep(3)


class Command(BaseCommand):
    help = "Run the real-time Qarz Daftar Pro Telegram Bot daemon"

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token or token == "local-dummy-token":
            self.stderr.write(self.style.ERROR("TELEGRAM_BOT_TOKEN sozlanmagan."))
            return

        bot = TelegramBotRunner(token=token)
        bot.run()
