from graphene import relay
from graphene_django import DjangoObjectType

from transactions.filtersets import TransactionFilterSet
from transactions.models import Transaction


class TransactionNode(DjangoObjectType):
    """Node for admin queries with filterset"""
    class Meta:
        model = Transaction
        filterset_class = TransactionFilterSet
        interfaces = (relay.Node,)


class CollectorTransactionNode(DjangoObjectType):
    """Node for collector queries without restrictive filterset"""
    class Meta:
        model = Transaction
        filterset_class = None
        interfaces = (relay.Node,)