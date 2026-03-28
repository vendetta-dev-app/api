from django_filters import FilterSet, CharFilter, BooleanFilter

from accounts.models import CollectorProfile, ManagerProfile


class CollectorProfileFilterset(FilterSet):
    full_name = CharFilter(
        field_name="user__full_name",
        lookup_expr="icontains"
    )
    route_isnull = BooleanFilter(
        field_name="route",
        lookup_expr="isnull"
    )

    class Meta:
        model = CollectorProfile
        fields = {
            "is_active": ["exact"],
        }


class ManagerProfileFilterset(FilterSet):
    full_name = CharFilter(
        field_name="user__full_name",
        lookup_expr="icontains"
    )

    class Meta:
        model = ManagerProfile
        fields = {
            "is_active": ["exact"],
        }
