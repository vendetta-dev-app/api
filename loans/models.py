from datetime import timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from loans.choices import INTEREST_RATE_CHOICES, PAYMENT_METHOD_CHOICES, PAYMENT_FREQUENCY_CHOICES
from loans.constants import payment_frequency
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

    # Approval workflow fields
    is_approved = models.BooleanField(default=True)
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

    def clean(self):
        if self.installments < 1 or self.installments > 90:
            raise ValidationError({'installments': 'La cantidad de cuotas debe estar entre 1 y 90.'})

    def __str__(self):
        collector_name = self.route.collector_profile.user.full_name if self.route.collector_profile else 'Sin Collector'
        return f'{self.amount}-{self.route.name}-{collector_name}'

    @property
    def total_amount(self):
        # Convert interest_rate to Decimal if it's stored as string (due to choices)
        rate = Decimal(self.interest_rate) if isinstance(self.interest_rate, str) else self.interest_rate
        return self.amount + ((rate / 100) * self.amount)

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
        """Estado del préstamo: ACTIVE, OVERDUE, PAID"""
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
        if not self.due_date:
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

    # --- Visit schedule & payment status ---

    def _frequency_delta(self, periods: int):
        if self.payment_frequency == payment_frequency.DAILY:
            return timedelta(days=periods)
        if self.payment_frequency == payment_frequency.WEEKLY:
            return timedelta(weeks=periods)
        return relativedelta(months=periods)

    @property
    def installment_amount(self) -> Decimal:
        return self.total_amount / self.installments

    @property
    def installments_completed(self) -> int:
        """Cuotas completamente cubiertas por los pagos válidos realizados."""
        return min(int(self.total_paid / self.installment_amount), self.installments)

    @property
    def installments_due(self) -> int:
        """Cuotas que debieron haberse pagado hasta hoy según la periodicidad del préstamo."""
        today = timezone.now().date()
        created = self.created_at.date()

        if self.payment_frequency == payment_frequency.DAILY:
            elapsed = (today - created).days
        elif self.payment_frequency == payment_frequency.WEEKLY:
            elapsed = (today - created).days // 7
        else:
            elapsed = (today.year - created.year) * 12 + (today.month - created.month)

        return min(elapsed, self.installments)

    @property
    def payment_status(self) -> str:
        """
        AL_DIA       → pagos al corriente
        ADELANTADO   → pagó más cuotas de las que van hasta hoy
        PAGO_PARCIAL → pagó parcialmente la cuota vigente (exactamente 1 cuota atrás con abono)
        ATRASADO     → debe una o más cuotas sin abono suficiente
        """
        if self.is_fully_paid:
            return "PAID"

        completed = self.installments_completed
        due = self.installments_due

        if completed > due:
            return "ADELANTADO"
        if completed == due:
            return "AL_DIA"

        partial_paid = self.total_paid - (completed * self.installment_amount)
        if completed == due - 1 and partial_paid > 0:
            return "PAGO_PARCIAL"

        return "ATRASADO"

    @property
    def should_visit_today(self) -> bool:
        """True si la agenda fija del préstamo indica visita hoy o hay cuotas pendientes de días anteriores."""
        if self.is_fully_paid:
            return False
        first_visit = self.created_at.date() + self._frequency_delta(1)
        return first_visit <= timezone.now().date()

    @property
    def next_visit_date(self):
        """Fecha de la próxima visita programada según la agenda fija (siguiente período desde hoy)."""
        if self.is_fully_paid:
            return None
        today = timezone.now().date()
        created = self.created_at.date()

        if self.payment_frequency == payment_frequency.DAILY:
            elapsed_periods = (today - created).days
        elif self.payment_frequency == payment_frequency.WEEKLY:
            elapsed_periods = (today - created).days // 7
        else:
            elapsed_periods = (today.year - created.year) * 12 + (today.month - created.month)

        return created + self._frequency_delta(elapsed_periods + 1)


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
    payment_date = models.DateTimeField(default=timezone.now)
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

    @property
    def installment_amount(self):
        """Calcula el valor de cada cuota basado en el número de cuotas"""
        return self.total_amount / self.installments
