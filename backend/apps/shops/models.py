from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import BaseModel
from apps.accounts.models import CustomUser, UserRole


class Shop(BaseModel):
    """
    Shop tenant model. Every customer, debt, and payment belongs
    strictly to an isolated Shop.
    """
    name = models.CharField(_("shop name"), max_length=255, db_index=True)
    slug = models.SlugField(_("slug / unique identifier"), max_length=255, unique=True, blank=True)
    owner = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="owned_shops",
        verbose_name=_("shop owner")
    )
    phone_number = models.CharField(_("phone number"), max_length=30)
    address = models.TextField(_("address"), blank=True, null=True)
    currency = models.CharField(
        _("currency"),
        max_length=10,
        default="UZS",
        help_text=_("Primary currency for accounting (e.g. UZS, USD, RUB)")
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("shop")
        verbose_name_plural = _("shops")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.currency})"

    def save(self, *args, **kwargs):
        if not self.slug:
            import re
            import uuid
            base_slug = re.sub(r'[^a-zA-Z0-9]+', '-', self.name.lower()).strip('-')
            self.slug = f"{base_slug[:40]}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)


class Branch(BaseModel):
    """
    Physical or logical branch of a shop.
    """
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="branches",
        verbose_name=_("shop")
    )
    name = models.CharField(_("branch name"), max_length=255)
    address = models.TextField(_("branch address"), blank=True, null=True)
    phone_number = models.CharField(_("branch phone number"), max_length=30, blank=True, null=True)
    is_main = models.BooleanField(_("main branch"), default=False)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("branch")
        verbose_name_plural = _("branches")
        unique_together = ("shop", "name")
        ordering = ["-is_main", "name"]

    def __str__(self):
        return f"{self.shop.name} - {self.name}"

    def save(self, *args, **kwargs):
        if self.is_main:
            # Ensure other branches for this shop are not main
            Branch.objects.filter(shop=self.shop, is_main=True).exclude(pk=self.pk).update(is_main=False)
        super().save(*args, **kwargs)


class ShopMember(BaseModel):
    """
    Membership association linking a user to a shop with an assigned role.
    """
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name=_("shop")
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="members",
        verbose_name=_("branch")
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="shop_memberships",
        verbose_name=_("user")
    )
    role = models.CharField(
        _("shop role"),
        max_length=20,
        choices=[
            (UserRole.SHOP_OWNER, _("Shop Owner")),
            (UserRole.MANAGER, _("Manager")),
            (UserRole.CASHIER, _("Cashier")),
        ],
        default=UserRole.CASHIER
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("shop member")
        verbose_name_plural = _("shop members")
        unique_together = ("shop", "user")
        ordering = ["role", "-created_at"]

    def __str__(self):
        return f"{self.user.email} in {self.shop.name} ({self.get_role_display()})"
