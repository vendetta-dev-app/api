from decimal import Decimal

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

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

    amount = models.DecimalField(
        decimal_places=2,
        max_digits=20,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        choices=INTEREST_RATE_CHOICES,
        help_text="Tasa de interés permitida: 0%, 10% o 20%"
    )

    # Approval workflow fields
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='approved_loans'
    )
    rejection_reason = models.TextField(blank=True)
    is_rejected = models.BooleanField(default=False)

    # Due date for loan repayment
    due_date = models.DateField(null=True, blank=True)

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
            voided_at__isnull=True
        ).aggregate(total=Sum('amount'))['total']
        return result or Decimal('0.00')

    @property
    def pending_balance(self) -> Decimal:
        """Saldo pendiente = total_amount - total_paid"""
        return self.total_amount - self.total_paid

    @property
    def status(self) -> str:
        """Estado del préstamo: PENDING, REJECTED, ACTIVE, OVERDUE, PAID"""
        if self.is_rejected:
            return "REJECTED"
        if not self.is_approved:
            return "PENDING"
        if self.pending_balance <= Decimal('0.00'):
            return "PAID"
        if self.is_overdue:
            return "OVERDUE"
        return "ACTIVE"

    @property
    def is_fully_paid(self) -> bool:
        return self.pending_balance <= Decimal('0.00')

    @property
    def is_overdue(self) -> bool:
        """Returns True if loan is past due date and not fully paid"""
        if not self.due_date or not self.is_approved:
            return False
        if self.is_fully_paid:
            return False
        return timezone.now().date() > self.due_date

    @property
    def days_overdue(self) -> int:
        """Returns number of days past due date, or 0 if not overdue"""
        if not self.is_overdue:
            return 0
        return (timezone.now().date() - self.due_date).days


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

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    notes = models.TextField(blank=True)

    # Voiding fields
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='voided_payments'
    )
    void_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f"Payment {self.id} - {self.amount} for Loan {self.loan_id}"

    @property
    def is_voided(self) -> bool:
        """Check if payment has been voided"""
        return self.voided_at is not None
