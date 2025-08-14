from graphene import ObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from routes.models import Route
from routes.mutations import CreateRoute
from routes.nodes import RouteNode


class Query(ObjectType):
    # Query to get routes where the logged-in user is an admin
    routes_by_admin = DjangoFilterConnectionField(RouteNode)

    # Query to get routes where the logged-in user is a collector
    routes_by_collector = DjangoFilterConnectionField(RouteNode)

    @login_required
    def resolve_routes_by_admin(self, info, **kwargs):
        user = info.context.user

        if not user.is_admin:
            raise GraphQLError('You are not an admin.')

        return Route.objects.filter(administrators=user.adminprofile)

    @login_required
    def resolve_routes_by_collector(self, info, **kwargs):
        user = info.context.user

        if not user.is_collector:
            raise GraphQLError('You are not a collector.')

        return Route.objects.filter(collector__user=user)


class Mutation(ObjectType):
    create_route = CreateRoute.Field()