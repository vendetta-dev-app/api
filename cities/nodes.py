from cities_light.models import City, Region
from graphene import relay
from graphene_django import DjangoObjectType


from cities.filtersets import CityFilterSet


class CityNode(DjangoObjectType):
    class Meta:
        model = City
        filterset_class = CityFilterSet
        interfaces = (relay.Node,)


class RegionNode(DjangoObjectType):
    class Meta:
        model = Region
        filter_fields = []
        interfaces = (relay.Node,)