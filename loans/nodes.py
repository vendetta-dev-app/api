from graphene import relay, Decimal, String, Boolean, List
from graphene_django import DjangoObjectType

from loans.models import Loan, Payment
from transactions.nodes import TransactionNode


class PaymentNode(DjangoObjectType):
    transactions = List(TransactionNode)

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
    status = String()
    is_fully_paid = Boolean()
    payments = List(PaymentNode)
    transactions = List(TransactionNode)

    class Meta:
        model = Loan
        filter_fields = []
        interfaces = (relay.Node,)

    def resolve_payments(self, info):
        return self.payments.all()

    def resolve_transactions(self, info):
        return self.transactions.all()
