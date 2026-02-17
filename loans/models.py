from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db import models

from loans.choices import INTEREST_RATE_CHOICES, PAYMENT_FREQUENCY_CHOICES
from loans.constants import payment_frequency
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
    installments = models.PositiveIntegerField(
        help_text="Cantidad de cuotas (mínimo 1, máximo 90)",
        default=1
    )

    payment_frequency = models.CharField(
        max_length=10,
        choices=PAYMENT_FREQUENCY_CHOICES,
        default=payment_frequency.WEEKLY,
        help_text="Frecuencia de pagos: Diaria, Semanal o Mensual"
    )

    is_approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Loan"
        verbose_name_plural = "Loans"
        ordering = ['created_at']

    def clean(self):
        if self.installments < 1 or self.installments > 90:
            raise ValidationError({'installments': 'La cantidad de cuotas debe estar entre 1 y 90.'})

    def __str__(self):
        return F'{self.amount}-{self.route.name}-{self.collector.user.full_name}'

    @property
    def total_amount(self):
        """Calcula el valor total del préstamo con interés fijo"""
        return self.amount + ((self.interest_rate/100) * self.amount)

    @property
    def installment_amount(self):
        """Calcula el valor de cada cuota basado en el número de cuotas"""
        return self.total_amount / self.installments
