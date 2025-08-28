from graphene import Int
from graphene.relay import Connection


class CountableConnection(Connection):
    total_count = Int()

    class Meta:
        abstract = True

    def resolve_total_count(self, info):
        return self.iterable.count()
