from decimal import Decimal

from cities_light.models import City
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Sum

from transactions.models import Transaction
from transactions.constants import transaction_types


class Route(models.Model):
    name = models.CharField(max_length=100)
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='routes')

    transactions = GenericRelation(
        Transaction,
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='route'
    )

    # Multiple administrators per route, and each administrator can have multiple routes
    administrators = models.ManyToManyField(
        'accounts.AdminProfile',
        related_name='routes_as_admin'
    )

    manager = models.ForeignKey(
        'accounts.ManagerProfile',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='routes_as_manager'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.city}"

    def set_starting_balance(self, amount, description="Initial route balance"):
        """
        Create or update the route_initial transaction for this route.
        Enforces the 'only one starting balance per route' rule.
        """
        tx = Transaction.objects.create(
            related_object=self,
            transaction_type=transaction_types.ROUTE_INITIAL,
            amount=amount,
            description=description
        )
        return tx

    @property
    def starting_balance(self):
        """
        Returns the unique 'route_initial' transaction amount for this route.
        """
        tx_amount = (
            Transaction.objects.filter(
                content_type=ContentType.objects.get_for_model(Route),
                object_id=self.id,
                transaction_type=transaction_types.ROUTE_INITIAL,
            )
            .values_list("amount", flat=True)
            .first()
        )
        return tx_amount or Decimal("0.00")

    @property
    def current_balance(self):
        """
        Calcula el saldo actual de la ruta:
        starting_balance - préstamos + pagos de préstamos - pagos anulados
        """
        qs = Transaction.objects.filter(
            content_type=ContentType.objects.get_for_model(Route),
            object_id=self.id
        )

        loans_total = qs.filter(
            transaction_type=transaction_types.LOAN_DISBURSEMENT
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        loan_payments_total = qs.filter(
            transaction_type=transaction_types.LOAN_PAYMENT
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Subtract voided payments (they reduce the balance)
        voided_payments_total = qs.filter(
            transaction_type=transaction_types.PAYMENT_VOID
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        return self.starting_balance - loans_total + loan_payments_total - voided_payments_total