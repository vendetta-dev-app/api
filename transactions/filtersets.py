from django.contrib.contenttypes.models import ContentType
from django_filters import CharFilter, FilterSet
from graphql_relay import from_global_id

from routes.models import Route
from transactions.models import Transaction


class TransactionFilterSet(FilterSet):
    route_id = CharFilter(method='filter_by_route')

    class Meta:
        model = Transaction
        fields = []  # We declare route_id manually

    def filter_by_route(self, queryset, name, value):
        value = from_global_id(value)[1]
        route_content_type = ContentType.objects.get_for_model(Route)
        return queryset.filter(content_type=route_content_type, object_id=value)