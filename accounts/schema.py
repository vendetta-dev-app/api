from graphene import ObjectType, Field
from graphene_django.filter import DjangoFilterConnectionField
from graphql import GraphQLError
from graphql_jwt import ObtainJSONWebToken, Verify, Refresh
from graphql_jwt.decorators import login_required

from accounts.filtersets import CollectorProfileFilterset, ManagerProfileFilterset
from accounts.models import CollectorProfile, ManagerProfile, ClientProfile
from accounts.mutations import CreateAdmin, CreateCollector, CreateClient, EditCollector, CreateManager
from accounts.nodes import UserNode, CollectorNode, ManagerNode, ClientNode


class Query(ObjectType):
    me = Field(UserNode)

    collectors_by_admin = DjangoFilterConnectionField(CollectorNode)

    managers_by_admin = DjangoFilterConnectionField(ManagerNode)

    clients_by_admin = DjangoFilterConnectionField(ClientNode)

    def resolve_me(self, info):
        return info.context.user

    @login_required
    def resolve_collectors_by_admin(self, info, **kwargs):
        user = info.context.user

        if not user.is_admin:
            raise GraphQLError("You are not an admin.")

        # start with only this admin’s collectors
        qs = CollectorProfile.objects.filter(admin=user.admin_profile)

        # let django-filters apply the kwargs
        filterset = CollectorProfileFilterset(data=kwargs, queryset=qs, request=info.context)
        return filterset.qs

    @login_required
    def resolve_managers_by_admin(self, info, **kwargs):
        user = info.context.user

        if not user.is_admin:
            raise GraphQLError("You are not an admin.")

        qs = ManagerProfile.objects.filter(admin=user.admin_profile)

        filterset = ManagerProfileFilterset(data=kwargs, queryset=qs, request=info.context)

        return filterset.qs

    @login_required
    def resolve_clients_by_admin(self, info, **kwargs):
        user = info.context.user

        if not user.is_admin:
            raise GraphQLError("You are not an admin.")

        return ClientProfile.objects.filter(admin=user.admin_profile)

class Mutation(ObjectType):
    token_auth = ObtainJSONWebToken.Field()
    verify_token = Verify.Field()
    refresh_token = Refresh.Field()

    create_admin = CreateAdmin.Field()
    create_manager = CreateManager.Field()
    create_collector = CreateCollector.Field()
    edit_collector = EditCollector.Field()
    create_client = CreateClient.Field()
