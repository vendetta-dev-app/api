from transactions.constants import transaction_types

TRANSACTION_TYPES_CHOICES = (
    (transaction_types.ROUTE_INITIAL, "Route initial"),
    (transaction_types.ROUTE_REFUND, "Route refund"),
    (transaction_types.LOAN_DISBURSEMENT, "Loan disbursement"),
    (transaction_types.LOAN_PAYMENT, "Loan payment"),
    (transaction_types.PAYMENT_VOID, "Payment void"),
    (transaction_types.ADJUSTMENT, "Adjustment"),
    (transaction_types.EXPENSE, "Expense"),
    (transaction_types.CASH_OUT, "Cash out"),
)
