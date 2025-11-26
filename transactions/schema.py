from graphene import ObjectType
from graphene_django.filter import DjangoFilterConnectionField

from transactions.nodes import TransactionNode


class Query(ObjectType):
    transactions = DjangoFilterConnectionField(TransactionNode)
