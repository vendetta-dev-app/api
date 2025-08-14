from graphene import ObjectType, Field
from graphql_jwt import ObtainJSONWebToken, Verify, Refresh

from accounts.mutations import CreateAdmin, CreateCollector, CreateClient
from accounts.nodes import UserNode


class Query(ObjectType):
    me = Field(UserNode)

    def resolve_me(self, info):
        return info.context.user


class Mutation(ObjectType):
    token_auth = ObtainJSONWebToken.Field()
    verify_token = Verify.Field()
    refresh_token = Refresh.Field()

    create_admin = CreateAdmin.Field()
    create_collector = CreateCollector.Field()
    create_client = CreateClient.Field()