from django.db import transaction
from graphene import ClientIDMutation
from graphene import relay, Field, String, Decimal
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from graphql_relay import from_global_id

from accounts.constants import roles
from accounts.models import CollectorProfile, ManagerProfile, User, AdminProfile
from routes.models import Route
from routes.nodes import RouteNode


class CreateRoute(relay.ClientIDMutation):
    route = Field(RouteNode)

    class Input:
        name = String(required=True)
        city_id = String(required=True)
        collector_id = String(required=True)
        manager_id = String(required=True)
        initial_value = Decimal(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user
        initial_value = input.pop('initial_value')

        if not user.is_admin:
            raise GraphQLError('No tienes permisos para realizar esta acción')

        try:
            city_id = from_global_id(input.pop('city_id'))[1]
        except Exception:
            raise GraphQLError("El id de la ciudad no es válido")

        try:
            collector_id = from_global_id(input.pop('collector_id'))[1]
        except Exception:
            raise GraphQLError("El id del cobrador no es válido")

        try:
            manager_id = from_global_id(input.pop('manager_id'))[1]
        except Exception:
            raise GraphQLError("el id del manager no es valido")

        admin_profile = user.admin_profile

        with transaction.atomic():
            try:
                collector = CollectorProfile.objects.select_for_update().get(id=collector_id)
            except CollectorProfile.DoesNotExist:
                raise GraphQLError("No existe un cobrador con este id")

            if collector.route is not None:
                raise GraphQLError("El cobrador ya tiene una ruta asignada")

            route = Route.objects.create(
                name=input.get('name'),
                city_id=city_id,
                manager_id=manager_id,
            )
            route.administrators.set([admin_profile])

            collector.route = route
            collector.save()

            if initial_value:
                route.set_starting_balance(
                    initial_value,
                    description=f"Initial value for route '{route.name}'"
                )

        return CreateRoute(route=route)


class EditRoute(ClientIDMutation):
    route = Field(RouteNode)

    class Input:
        route_id = String(required=True)
        collector_id = String(required=True)
        manager_id = String(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_admin:
            raise GraphQLError('No tienes permisos para realizar esta acción')

        try:
            route_id = from_global_id(input.pop('route_id'))[1]
        except Exception:
            raise GraphQLError("El id de la routa no es valido")

        try:
            collector_id = from_global_id(input.pop('collector_id'))[1]
        except Exception:
            raise GraphQLError("El id del cobrador no es valido")

        try:
            manager_id = from_global_id(input.pop('manager_id'))[1]
        except Exception:
            raise GraphQLError("el id del manager no es valido")

        try:
            route = Route.objects.get(id=route_id)
        except Route.DoesNotExist:
            raise GraphQLError("No existe una ruta con este id")

        try:
            manager = ManagerProfile.objects.get(id=manager_id)
        except ManagerProfile.DoesNotExist:
            raise GraphQLError("No existe un manager con este id")

        with transaction.atomic():
            try:
                collector = CollectorProfile.objects.select_for_update().get(id=collector_id)
            except CollectorProfile.DoesNotExist:
                raise GraphQLError("No existe un cobrador con este id")

            if collector.route is not None and collector.route.id != route.id:
                raise GraphQLError("El cobrador ya tiene otra ruta asignada")

            route.manager = manager
            route.save()

            current_collector = CollectorProfile.objects.filter(route=route).select_for_update().first()
            if current_collector and current_collector != collector:
                current_collector.route = None
                current_collector.save()

            collector.route = route
            collector.save()

        return EditRoute(route=route)


class AddAdminToRoute(relay.ClientIDMutation):
    route = Field(RouteNode)

    class Input:
        route_id = String(required=True)
        admin_email = String(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_admin:
            raise GraphQLError("No tienes permisos para realizar esta acción")

        try:
            route_id = from_global_id(input.get("route_id"))[1]
            route = Route.objects.get(id=route_id)
        except Exception:
            raise GraphQLError("Ruta no válida")

        try:
            admin_user = User.objects.get(
                email=input.get("admin_email"),
                role=roles.ADMIN
            )
        except User.DoesNotExist:
            raise GraphQLError("El usuario no es un administrador válido")

        try:
            admin_profile = admin_user.admin_profile
        except AdminProfile.DoesNotExist:
            raise GraphQLError("El administrador no tiene perfil asignado")

        if route.administrators.filter(id=admin_profile.id).exists():
            raise GraphQLError("Este administrador ya está asignado a la ruta")

        route.administrators.add(admin_profile)

        return AddAdminToRoute(route=route)
