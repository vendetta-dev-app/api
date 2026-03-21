from graphene import ObjectType, relay, Field, String
from graphene_django.filter import DjangoFilterConnectionField
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from graphql_relay import from_global_id

from routes.models import Route
from routes.mutations import CreateRoute, EditRoute, AddAdminToRoute
from routes.nodes import RouteNode


class Query(ObjectType):
    # Query to get routes where the logged-in user is an admin
    routes_by_admin = DjangoFilterConnectionField(RouteNode)

    # Query to get routes where the logged-in user is a collector
    routes_by_collector = DjangoFilterConnectionField(RouteNode)

    # Query single route by ID with authorization
    route = Field(RouteNode, id=String(required=True))

    @login_required
    def resolve_routes_by_admin(self, info, **kwargs):
        user = info.context.user

        if not user.is_admin:
            raise GraphQLError('No eres administrador')

        return Route.objects.filter(administrators=user.admin_profile)

    @login_required
    def resolve_routes_by_collector(self, info, **kwargs):
        user = info.context.user

        if not user.is_collector:
            raise GraphQLError('No eres cobrador')

        return Route.objects.filter(collector__user=user)

    @login_required
    def resolve_route(self, info, id, **kwargs):
        user = info.context.user

        try:
            pk = from_global_id(id)[1]
        except Exception:
            raise GraphQLError("El id de la ruta no es válido")

        try:
            route = Route.objects.get(id=pk)
        except Route.DoesNotExist:
            raise GraphQLError("La ruta no existe")

        # Validate user has access to this route
        if user.is_admin:
            if not route.administrators.filter(id=user.admin_profile.id).exists():
                raise GraphQLError("No tienes acceso a esta ruta")
        elif user.is_collector:
            if route.collector_profile != user.collector_profile:
                raise GraphQLError("No tienes acceso a esta ruta")
        else:
            raise GraphQLError("No tienes permisos para consultar rutas")

        return route


class Mutation(ObjectType):
    create_route = CreateRoute.Field()
    edit_route = EditRoute.Field()
    add_admin_to_route = AddAdminToRoute.Field()