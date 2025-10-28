from django_filters import FilterSet, CharFilter

from accounts.models import CollectorProfile, ManagerProfile


class CollectorProfileFilterset(FilterSet):
    full_name = CharFilter(
        field_name="user__full_name",
        lookup_expr="icontains"
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