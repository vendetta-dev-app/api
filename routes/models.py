from decimal import Decimal

from cities_light.models import City
from django.contrib.contenttypes.models import ContentType
from django.db import models

from transactions.models import Transaction
from transactions.constants import transaction_types


class Route(models.Model):
    name = models.CharField(max_length=100)
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='routes')

    # One collector per route
    collector = models.ForeignKey(
        'accounts.CollectorProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='routes_as_collector'
    )

    # Multiple administrators per route, and each administrator can have multiple routes
    administrators = models.ManyToManyField(
        'accounts.AdminProfile',
        related_name='routes_as_admin'
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
        tx, created = Transaction.objects.update_or_create(
            related_object=self,
            transaction_type=transaction_types.ROUTE_INITIAL,
            defaults={"amount": amount, "description": description},
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