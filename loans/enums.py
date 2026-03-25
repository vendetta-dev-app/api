from graphene import Enum

from loans.choices import INTEREST_RATE_CHOICES, PAYMENT_FREQUENCY_CHOICES, PAYMENT_METHOD_CHOICES
from snipets.graphql.enums import choices_to_enum

LoanInterestRate = Enum('LoanInterestRate', choices_to_enum(INTEREST_RATE_CHOICES))
LoanPaymentFrequency = Enum('LoanPaymentFrequency', choices_to_enum(PAYMENT_FREQUENCY_CHOICES))

PaymentMethodType = Enum("PaymentMethodType", choices_to_enum(PAYMENT_METHOD_CHOICES))
