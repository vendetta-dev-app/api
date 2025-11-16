from django.contrib.contenttypes.models import ContentType
from graphene import ObjectType, String
from graphene_django.filter import DjangoFilterConnectionField
from graphql_jwt.decorators import login_required
from graphql_relay import from_global_id

from routes.models import Route
from transactions.filtersets import TransactionFilterSet
from transactions.models import Transaction
from transactions.nodes import TransactionNode


class Query(ObjectType):
    transactions_by_admin = DjangoFilterConnectionField(TransactionNode)

    transactions_by_route = DjangoFilterConnectionField(
        TransactionNode,
    )

    @login_required
    def resolve_transactions_by_admin(self, info, **kwargs):
        user = info.context.user
        admin_profile = getattr(user, "adminprofile", None)

        if not admin_profile:
            raise Exception("No tienes permiso para consultar esta informacion")

        routes = admin_profile.routes_as_admin.all()
        route_ids = routes.values_list("id", flat=True)

        route_ct = ContentType.objects.get_for_model(Route)
        qs = Transaction.objects.filter(
            content_type=route_ct,
            object_id__in=route_ids
        )

        filterset = TransactionFilterSet(
            data=kwargs,
            queryset=qs,
            request=info.context
        )

        if not filterset.is_valid():
            raise Exception(f"Invalid filters: {filterset.errors}")

        return filterset.qs

    @login_required
    def resolve_transactions_by_route(self, info, route, **kwargs):
        user = info.context.user

        admin_profile = getattr(user, "adminprofile", None)

        if not admin_profile:
            raise Exception("No tienes permiso para consultar esta informacion")

        try:
            route_pk = from_global_id(route)[1]
            route = Route.objects.get(pk=route_pk)
        except Exception:
            raise Exception(f"Error al obtener la ruta {route_pk}")
        except Route.DoesNotExist:
            raise Exception(f"Ruta {route_pk} no existe")

        if not admin_profile.routes_as_admin.filter(pk=route.id).exists():
            raise Exception("No tienes permiso para ver las transacciones de esta ruta")

        qs = route.transactions.all()

        filterset = TransactionFilterSet(
            data=kwargs,
            queryset=qs,
            request=info.context
        )

        if not filterset.is_valid():
            raise Exception(f"Filtros inválidos: {filterset.errors}")

        return filterset.qs
