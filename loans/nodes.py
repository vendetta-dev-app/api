from graphene import relay, Date, Decimal, String, Boolean, List, Int
from graphene_django import DjangoObjectType

from accounts.nodes import UserNode
from loans.models import Loan, Payment
from transactions.nodes import TransactionNode


class PaymentNode(DjangoObjectType):
    transactions = List(TransactionNode)
    is_voided = Boolean()

    class Meta:
        model = Payment
        filter_fields = []
        interfaces = (relay.Node,)

    def resolve_transactions(self, info):
        return self.transactions.all()


class LoanNode(DjangoObjectType):
    total_amount = Decimal()
    total_paid = Decimal()
    pending_balance = Decimal()
    installment_amount = Decimal()
    installments_completed = Int()
    installments_due = Int()
    payment_status = String()
    should_visit_today = Boolean()
    next_visit_date = Date()
    status = String()
    is_fully_paid = Boolean()
    is_overdue = Boolean()
    days_overdue = Int()
    payments = List(PaymentNode)
    transactions = List(TransactionNode)
    approved_by = relay.Node.Field(UserNode)

    class Meta:
        model = Loan
        filter_fields = []
        interfaces = (relay.Node,)
        exclude_fields = ('interest_rate',)  # Exclude to avoid enum issues for now

    def resolve_payments(self, info):
        # Only return non-voided payments by default
        return self.payments.filter(voided_at__isnull=True).order_by('-payment_date')

    def resolve_transactions(self, info):
        return self.transactions.select_related('maker', 'associated_profile').all()

    @classmethod
    def get_queryset(cls, queryset, info):
        """Optimize queries with select_related and prefetch_related"""
        return queryset.select_related(
            'route',
            'client__user',
            'collector__user',
            'approved_by'
        ).prefetch_related('payments', 'transactions')
