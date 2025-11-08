from graphene import relay
from graphene_django import DjangoObjectType

from transactions.filtersets import TransactionFilterSet
from transactions.models import Transaction


class TransactionNode(DjangoObjectType):
    class Meta:
        model = Transaction
        filterset_class = TransactionFilterSet
        interfaces = (relay.Node,)