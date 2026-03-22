from graphene import ObjectType, String, Decimal, Boolean, DateTime, List
from graphene_django.filter import DjangoFilterConnectionField
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from transactions.models import Transaction
from transactions.nodes import TransactionNode


class CollectorTransactionType(ObjectType):
    """Simple transaction type for collectors (not a Node, no relay connection)"""
    id = String()
    transaction_type = String()
    amount = Decimal()
    description = String()
    created_at = DateTime()
    voided = Boolean()

    def resolve_id(self, info):
        return self.id

    def resolve_transaction_type(self, info):
        return self.transaction_type

    def resolve_amount(self, info):
        return self.amount

    def resolve_description(self, info):
        return self.description

    def resolve_created_at(self, info):
        return self.created_at

    def resolve_voided(self, info):
        return self.voided


class Query(ObjectType):
    transactions = DjangoFilterConnectionField(TransactionNode)
    transactions_by_collector = List(CollectorTransactionType)

    @login_required
    def resolve_transactions_by_collector(self, info, **kwargs):
        """Get transactions for the logged-in collector (filtered by their route)."""
        from django.contrib.contenttypes.models import ContentType
        from routes.models import Route

        user = info.context.user

        if not user.is_collector:
            raise GraphQLError("Solo los cobradores pueden consultar sus transacciones")

        # Get the collector's route
        collector_route = user.collector_profile.route
        if not collector_route:
            return []

        # Get transactions for the collector's route
        route_ct = ContentType.objects.get_for_model(Route)

        return Transaction.objects.filter(
            content_type=route_ct,
            object_id=collector_route.id,
            voided=False
        ).select_related('maker', 'associated_profile').order_by('-created_at')
