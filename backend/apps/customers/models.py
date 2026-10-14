from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import BaseModel
from apps.shops.models import Shop, Branch


class CustomerStatus(models.TextChoices):
    ACTIVE = "ACTIVE", _("Active")
    ARCHIVED = "ARCHIVED", _("Archived")


class Customer(BaseModel):
    """
    Customer entity strictly linked to a specific shop.
    """
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="customers",
        verbose_name=_("shop")
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="customers",
        verbose_name=_("branch")
    )
    full_name = models.CharField(_("full name"), max_length=255, db_index=True)
    phone_number = models.CharField(_("phone number"), max_length=30, db_index=True)
    address = models.TextField(_("address"), blank=True, null=True)
    notes = models.TextField(_("notes / comments"), blank=True, null=True)
    credit_limit = models.DecimalField(
        _("credit limit"),
        max_digits=14,
        decimal_places=2,
        default=0.00,
        help_text=_("0 means unlimited credit limit")
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=CustomerStatus.choices,
        default=CustomerStatus.ACTIVE,
        db_index=True
    )

    class Meta:
        verbose_name = _("customer")
        verbose_name_plural = _("customers")
        ordering = ["full_name"]
        indexes = [
            models.Index(fields=["shop", "phone_number"]),
            models.Index(fields=["shop", "status"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"
