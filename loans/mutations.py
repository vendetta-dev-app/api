from graphene import relay, Field, String, Float
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from graphql_relay import from_global_id

from loans.enums import LoanInterestRate
from loans.models import Loan


class CreateLoan(relay.ClientIDMutation):
    loan = Field(Loan)

    class Input:
        route_id = String(required=True)
        client_id = String(required=True)
        collector_id = String(required=True)
        amount = Float(required=True)
        interest_rate = LoanInterestRate(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_collector:
            raise GraphQLError("Solo los cobbradores pueden crear prestamos")

        try:
            route_id = from_global_id(input["route_id"])[1]
        except GraphQLError as e:
            raise GraphQLError('')
