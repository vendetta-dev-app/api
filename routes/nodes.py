from graphene import relay, Decimal, List
from graphene_django import DjangoObjectType

from routes.models import Route
from transactions.nodes import TransactionNode


class RouteNode(DjangoObjectType):
    starting_balance = Decimal()
    current_balance = Decimal()
    transactions = List(TransactionNode)

    class Meta:
        model = Route
        filter_fields = []
        interfaces = (relay.Node,)