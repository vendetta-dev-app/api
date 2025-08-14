from graphene import ClientIDMutation, Field, String
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from graphql_relay import from_global_id

from routes.models import Route
from routes.nodes import RouteNode


class CreateRoute(ClientIDMutation):
    route = Field(RouteNode)

    class Input:
        name = String(required=True)
        city_id = String(required=True)
        collector_id = String(required=False)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_admin:
            raise GraphQLError('No tienes persmisos para realizar esta acción')

        try:
            city_id = from_global_id(input.pop('city_id'))[1]
        except Exception:
            raise GraphQLError("El id de la ciudad no es valido")

        try:
            colletor_id = from_global_id(input.pop('collector_id'))[1]
        except Exception:
            raise GraphQLError("El id del cobrador no es valido")


        admin_profile = user.admin_profile

        route = Route.objects.create(
            name = input.get('name'),
            city_id = city_id,
            collector_id = colletor_id,
            administrators = admin_profile,
        )

        return CreateRoute(route=route)
