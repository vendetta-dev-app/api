from graphene import relay, Decimal
from graphene_django import DjangoObjectType

from routes.models import Route


class RouteNode(DjangoObjectType):
    starting_balance = Decimal()
    current_balance = Decimal()

    class Meta:
        model = Route
        filter_fields = []
        interfaces = (relay.Node,)