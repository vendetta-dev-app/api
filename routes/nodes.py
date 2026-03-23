from graphene import relay, Decimal, List, Int
from graphene_django import DjangoObjectType

from routes.models import Route
from transactions.nodes import TransactionNode


class RouteNode(DjangoObjectType):
    starting_balance = Decimal()
    current_balance = Decimal()
    transactions = List(TransactionNode)
    loans_count = Int()
    overdue_loans_count = Int()

    class Meta:
        model = Route
        filter_fields = []
        interfaces = (relay.Node,)

    def resolve_transactions(self, info):
        return self.transactions.select_related('maker', 'associated_profile').all()

    def resolve_loans_count(self, info):
        return self.loans.count()

    def resolve_overdue_loans_count(self, info):
        from django.utils import timezone
        return self.loans.filter(due_date__lt=timezone.now().date()).count()

    @classmethod
    def get_queryset(cls, queryset, info):
        """Optimize queries with select_related and prefetch_related"""
        return queryset.select_related(
            'collector_profile__user',
            'manager__user',
            'city'
        ).prefetch_related('administrators__user')