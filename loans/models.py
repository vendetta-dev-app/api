from decimal import Decimal

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Sum

from loans.choices import INTEREST_RATE_CHOICES, PAYMENT_METHOD_CHOICES
from transactions.models import Transaction


class Loan(models.Model):
    route = models.ForeignKey("routes.Route", on_delete=models.PROTECT, related_name="loans")
    client = models.ForeignKey("accounts.ClientProfile", on_delete=models.PROTECT, related_name="loans")
    collector = models.ForeignKey("accounts.CollectorProfile", on_delete=models.PROTECT, related_name="loans")

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
        return f'{self.amount}-{self.route.name}-{self.collector.user.full_name}'

    @property
    def total_amount(self):
        return self.amount + ((self.interest_rate / 100) * self.amount)

    @property
    def total_paid(self) -> Decimal:
        """Suma de todos los pagos no anulados"""
        result = self.payments.filter(
            transactions__voided=False
        ).aggregate(total=Sum('amount'))['total']
        return result or Decimal('0.00')

    @property
    def pending_balance(self) -> Decimal:
        """Saldo pendiente = total_amount - total_paid"""
        return self.total_amount - self.total_paid

    @property
    def status(self) -> str:
        """Estado del préstamo: PENDING, ACTIVE, PAID"""
        if not self.is_approved:
            return "PENDING"
        if self.pending_balance <= Decimal('0.00'):
            return "PAID"
        return "ACTIVE"

    @property
    def is_fully_paid(self) -> bool:
        return self.pending_balance <= Decimal('0.00')


class Payment(models.Model):
    loan = models.ForeignKey(
        "loans.Loan",
        on_delete=models.PROTECT,
        related_name="payments"
    )

    transactions = GenericRelation(
        Transaction,
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='payment'
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f"Payment {self.id} - {self.amount} for Loan {self.loan_id}"
