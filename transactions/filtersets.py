from django.contrib.contenttypes.models import ContentType
from django_filters import CharFilter, FilterSet
from graphql_relay import from_global_id

from accounts.models import AdminProfile
from routes.models import Route
from transactions.models import Transaction


class TransactionFilterSet(FilterSet):
    route_id = CharFilter(method="filter_by_route")

    class Meta:
        model = Transaction
        exclude = ['content_type', 'object_id']  # Exclude generic foreign key fields

    def filter_queryset(self, queryset):
        request = self.request
        user = getattr(request, "user", None)
        admin_profile = getattr(user, "admin_profile", None)

        if not admin_profile:
            raise Exception("No tienes permiso para consultar esta informacion")

        # base filtering: all routes of logged admin
        routes = admin_profile.routes_as_admin.all()
        route_ids = routes.values_list("id", flat=True)
        route_ct = ContentType.objects.get_for_model(Route)

        queryset = queryset.filter(
            content_type=route_ct,
            object_id__in=route_ids
        )

        return super().filter_queryset(queryset)

    def filter_by_route(self, queryset, name, value):
        """Extra filter: narrow to a specific route"""
        route_pk = from_global_id(value)[1]
        return queryset.filter(object_id=route_pk)
