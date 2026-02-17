from loans.constants import interest_rates, payment_methods, payment_frequency

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

PAYMENT_FREQUENCY_CHOICES = (
    (payment_frequency.DAILY, 'Diaria'),
    (payment_frequency.WEEKLY, 'Semanal'),
    (payment_frequency.MONTHLY, 'Mensual'),
)
