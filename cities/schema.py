from graphene import ObjectType, Field
from graphene_django.filter import DjangoFilterConnectionField

from cities.nodes import CityNode, RegionNode


class Query(ObjectType):
    city = Field(CityNode)
    cities = DjangoFilterConnectionField(CityNode)

    region = Field(RegionNode)
    regions = DjangoFilterConnectionField(RegionNode)