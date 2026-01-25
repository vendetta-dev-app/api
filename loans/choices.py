from loans.constants import interest_rates, payment_methods

INTEREST_RATE_CHOICES = (
    (interest_rates.A0, '0%'),
    (interest_rates.A10, '10%'),
    (interest_rates.A20, '20%')
)

PAYMENT_METHOD_CHOICES = (
    (payment_methods.CASH, 'Efectivo'),
    (payment_methods.TRANSFER, 'Transferencia'),
    (payment_methods.OTHER, 'Otro'),
)
