from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal

from transactions.choices import TRANSACTION_TYPES_CHOICES


class Transaction(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    related_object = GenericForeignKey('content_type', 'object_id')

    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.amount == Decimal("0.00"):
            raise ValueError("Transaction amount cannot be zero.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type}: {self.amount} ({self.related_object})"
