from graphene import Enum
from loans.choices import INTEREST_RATE_CHOICES
from snipets.graphql.enums import choices_to_enum

LoanInterestRate = Enum('LoanInterestRate', choices_to_enum(INTEREST_RATE_CHOICES))