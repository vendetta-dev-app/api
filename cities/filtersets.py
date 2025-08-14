from django_filters import FilterSet
from cities_light.models import City


class CityFilterSet(FilterSet):
    class Meta:
        model = City
        fields = {
            "search_names": ["exact", "icontains"],
        }