from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from loans.choices import INTEREST_RATE_CHOICES
from transactions.models import Transaction


class Loan(models.Model):
    route = models.ForeignKey("routes.Route", on_delete=models.PROTECT, related_name="loans")
    client = models.ForeignKey("accounts.ClientProfile", on_delete=models.PROTECT, related_name="clients")
    collector = models.ForeignKey("accounts.CollectorProfile", on_delete=models.PROTECT, related_name="collectors")

    transactions = GenericRelation(
        Transaction,
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='loan'
    )

    amount = models.DecimalField(decimal_places=2, max_digits=20)
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        choices=INTEREST_RATE_CHOICES,
        help_text="Tasa de interés permitida: 0%, 10% o 20%"
    )

    is_approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Loan"
        verbose_name_plural = "Loans"
        ordering = ['created_at']

    def __str__(self):
        return F'{self.amount}-{self.route.name}-{self.collector.user.full_name}'

    @property
    def total_amount(self):
        return self.amount + ((self.interest_rate/100) * self.amount)
