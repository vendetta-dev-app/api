from django.db.models.deletion import Collector
from graphene_django import DjangoObjectType
from graphene import relay

from accounts.models import User, AdminProfile, CollectorProfile, ClientProfile
from snipets.graphql.connection import CountableConnection


class UserNode(DjangoObjectType):
    class Meta:
        model = User
        filter_fields = []
        interfaces = (relay.Node,)


class AdminNode(DjangoObjectType):
    class Meta:
        model = AdminProfile
        filter_fields = []
        interfaces = (relay.Node,)


class CollectorNode(DjangoObjectType):
    class Meta:
        model = CollectorProfile
        filter_fields = []
        interfaces = (relay.Node,)
        connection_class = CountableConnection


class ClientNode(DjangoObjectType):
    class Meta:
        model = ClientProfile
        filter_fields = []
        interfaces = (relay.Node,)
