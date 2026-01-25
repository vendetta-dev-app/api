from decimal import Decimal

from django.db import transaction
from graphene import relay, Field, String, Decimal as GrapheneDecimal
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from graphql_relay import from_global_id

from accounts.models import ClientProfile
from loans.models import Loan, Payment
from loans.nodes import LoanNode, PaymentNode
from routes.models import Route
from transactions.constants import transaction_types
from transactions.models import Transaction


class CreateLoan(relay.ClientIDMutation):
    loan = Field(LoanNode)

    class Input:
        route_id = String(required=True)
        client_id = String(required=True)
        amount = GrapheneDecimal(required=True)
        interest_rate = GrapheneDecimal(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_admin and not user.is_collector:
            raise GraphQLError('No tienes permisos para realizar esta acción')

        # Parse route_id
        try:
            route_id = from_global_id(input.get('route_id'))[1]
        except Exception:
            raise GraphQLError("El id de la ruta no es válido")

        # Parse client_id
        try:
            client_id = from_global_id(input.get('client_id'))[1]
        except Exception:
            raise GraphQLError("El id del cliente no es válido")

        # Get route
        try:
            route = Route.objects.get(id=route_id)
        except Route.DoesNotExist:
            raise GraphQLError("No existe una ruta con este id")

        # Get client
        try:
            client = ClientProfile.objects.select_related('collector', 'user').get(id=client_id)
        except ClientProfile.DoesNotExist:
            raise GraphQLError("No existe un cliente con este id")

        amount = Decimal(str(input.get('amount')))
        interest_rate = Decimal(str(input.get('interest_rate')))

        # Validate amount is positive
        if amount <= Decimal('0.00'):
            raise GraphQLError("El monto debe ser mayor a cero")

        # Validate interest rate is valid (0, 10, or 20)
        valid_rates = [Decimal('0'), Decimal('10'), Decimal('20')]
        if interest_rate not in valid_rates:
            raise GraphQLError("La tasa de interés debe ser 0%, 10% o 20%")

        # Validate route has sufficient balance
        if route.current_balance < amount:
            raise GraphQLError("Balance insuficiente en la ruta")

        # Get collector from client
        collector = client.collector
        if not collector:
            raise GraphQLError("El cliente no tiene un cobrador asignado")

        with transaction.atomic():
            # Create Loan
            loan = Loan.objects.create(
                route=route,
                client=client,
                collector=collector,
                amount=amount,
                interest_rate=interest_rate,
                is_approved=True
            )

            # Create Transaction for disbursement on Route
            Transaction.objects.create(
                related_object=route,
                transaction_type=transaction_types.LOAN_DISBURSEMENT,
                amount=amount,
                description=f"Desembolso préstamo #{loan.id} - {client.user.full_name}",
                maker=user,
                associated_profile=client.user
            )

            # Create Transaction on Loan
            Transaction.objects.create(
                related_object=loan,
                transaction_type=transaction_types.LOAN_DISBURSEMENT,
                amount=amount,
                description="Préstamo otorgado",
                maker=user,
                associated_profile=client.user
            )

        return CreateLoan(loan=loan)


class CreatePayment(relay.ClientIDMutation):
    payment = Field(PaymentNode)
    loan = Field(LoanNode)

    class Input:
        loan_id = String(required=True)
        amount = GrapheneDecimal(required=True)
        payment_date = String(required=True)
        payment_method = String(required=True)
        notes = String()

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_admin and not user.is_collector:
            raise GraphQLError('No tienes permisos para realizar esta acción')

        # Parse loan_id
        try:
            loan_id = from_global_id(input.get('loan_id'))[1]
        except Exception:
            raise GraphQLError("El id del préstamo no es válido")

        # Get loan
        try:
            loan = Loan.objects.select_related('route', 'client__user').get(id=loan_id)
        except Loan.DoesNotExist:
            raise GraphQLError("No existe un préstamo con este id")

        # Validate loan is approved
        if not loan.is_approved:
            raise GraphQLError("El préstamo no está aprobado")

        amount = Decimal(str(input.get('amount')))
        payment_date = input.get('payment_date')
        payment_method = input.get('payment_method')
        notes = input.get('notes', '')

        # Validate amount is positive
        if amount <= Decimal('0.00'):
            raise GraphQLError("El monto debe ser mayor a cero")

        # Validate payment method
        valid_methods = ['CASH', 'TRANSFER', 'OTHER']
        if payment_method not in valid_methods:
            raise GraphQLError("Método de pago no válido. Use: CASH, TRANSFER u OTHER")

        # Calculate pending balance
        pending = loan.pending_balance

        # Validate amount doesn't exceed pending balance
        if amount > pending:
            raise GraphQLError(f"El monto ({amount}) excede el saldo pendiente ({pending})")

        with transaction.atomic():
            # Create Payment
            payment = Payment.objects.create(
                loan=loan,
                amount=amount,
                payment_date=payment_date,
                payment_method=payment_method,
                notes=notes
            )

            # Create Transaction associated with Payment (payment audit)
            Transaction.objects.create(
                related_object=payment,
                transaction_type=transaction_types.LOAN_PAYMENT,
                amount=amount,
                description=f"Pago de préstamo #{loan.id}",
                maker=user,
                associated_profile=loan.client.user
            )

            # Create Transaction on Route (updates cash balance)
            Transaction.objects.create(
                related_object=loan.route,
                transaction_type=transaction_types.LOAN_PAYMENT,
                amount=amount,
                description=f"Pago recibido - Préstamo #{loan.id} - {loan.client.user.full_name}",
                maker=user,
                associated_profile=loan.client.user
            )

        # Refresh loan to get updated calculated properties
        loan.refresh_from_db()

        return CreatePayment(payment=payment, loan=loan)
