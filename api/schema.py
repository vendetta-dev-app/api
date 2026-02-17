from graphene import ObjectType, Schema

import accounts.schema
import routes.schema
import cities.schema
import transactions.schema
import loans.schema


class Query(
    accounts.schema.Query,
    cities.schema.Query,
    routes.schema.Query,
    transactions.schema.Query,
    loans.schema.Query,
    ObjectType):
    pass


class Mutation(
    accounts.schema.Mutation,
    routes.schema.Mutation,
    loans.schema.Mutation,
    ObjectType):
    pass


schema = Schema(query=Query, mutation=Mutation)