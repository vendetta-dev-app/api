from graphene import ObjectType, Field
from graphene_django.filter import DjangoFilterConnectionField
from graphql import GraphQLError
from graphql_jwt import ObtainJSONWebToken, Verify, Refresh
from graphql_jwt.decorators import login_required

from accounts.mutations import CreateAdmin, CreateCollector, CreateClient
from accounts.nodes import UserNode, CollectorNode


class Query(ObjectType):
    me = Field(UserNode)

    collectors_by_admin = DjangoFilterConnectionField(CollectorNode)

    def resolve_me(self, info):
        return info.context.user

    @login_required
    def resolve_collectors_by_admin(self, info):
        user = info.context.user
        print(user)
        if not user.is_admin:
            raise GraphQLError("You are not an admin.")

        return user.admin_profile.collectors.all()


class Mutation(ObjectType):
    token_auth = ObtainJSONWebToken.Field()
    verify_token = Verify.Field()
    refresh_token = Refresh.Field()

    create_admin = CreateAdmin.Field()
    create_collector = CreateCollector.Field()
    create_client = CreateClient.Field()