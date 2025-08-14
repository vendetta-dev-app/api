from graphene import relay
from graphene_django import DjangoObjectType

from routes.models import Route


class RouteNode(DjangoObjectType):
    class Meta:
        model = Route
        filter_fields = []
        interfaces = (relay.Node,)