from django_filters import FilterSet, CharFilter

from accounts.models import CollectorProfile


class CollectorProfileFilterset(FilterSet):
    full_name = CharFilter(
        field_name="user__full_name",
        lookup_expr="icontains"
    )

    class Meta:
        model = CollectorProfile
        fields = []