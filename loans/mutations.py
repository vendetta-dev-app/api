from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from graphene import relay, Field, String, Decimal as GrapheneDecimal, Int
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
    """
    Creates a new loan and disburses it immediately. No approval required.
    """
    loan = Field(LoanNode)

    class Input:
        route_id = String(required=True)
        client_id = String(required=True)
        amount = GrapheneDecimal(required=True)
        installments = Int(description="Number of installments (1-90)")
        payment_frequency = String(description="Payment frequency: DAILY, WEEKLY, or MONTHLY")
        due_date = String(description="Due date in YYYY-MM-DD format")

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

        # Validate user has access to route
        if user.is_admin:
            if not route.administrators.filter(id=user.admin_profile.id).exists():
                raise GraphQLError("No tienes acceso a esta ruta")
        elif user.is_collector:
            if route.collector_profile != user.collector_profile:
                raise GraphQLError("No tienes acceso a esta ruta")

        # Get client
        try:
            client = ClientProfile.objects.select_related('route', 'user').get(id=client_id)
        except ClientProfile.DoesNotExist:
            raise GraphQLError("No existe un cliente con este id")

        # Validate client belongs to the route
        if client.route != route:
            raise GraphQLError("El cliente no pertenece a esta ruta")

        amount = Decimal(str(input.get('amount')))
        installments = input.get('installments', 1)
        payment_frequency = input.get('payment_frequency', 'WEEKLY')
        due_date = input.get('due_date')
        interest_rate = "20"

        # Validate amount is positive
        if amount <= Decimal('0.00'):
            raise GraphQLError("El monto debe ser mayor a cero")

        # Validate installments
        if installments < 1 or installments > 90:
            raise GraphQLError("El número de cuotas debe estar entre 1 y 90")

        # Validate payment frequency
        valid_frequencies = ['DAILY', 'WEEKLY', 'MONTHLY']
        if payment_frequency not in valid_frequencies:
            raise GraphQLError("La frecuencia de pago debe ser DAILY, WEEKLY o MONTHLY")

        # Get collector from route
        collector = route.collector_profile
        if not collector:
            raise GraphQLError("La ruta no tiene un cobrador asignado")

        # Validate route has sufficient balance
        if route.current_balance < amount:
            raise GraphQLError("Balance insuficiente en la ruta para otorgar este préstamo")

        with transaction.atomic():
            loan = Loan.objects.create(
                route=route,
                client=client,
                collector=collector,
                amount=amount,
                interest_rate=interest_rate,
                installments=installments,
                payment_frequency=payment_frequency,
                due_date=due_date,
                is_approved=True,
                approved_at=timezone.now(),
                approved_by=user,
            )

            # Disbursement transaction on the route (reduces balance)
            Transaction.objects.create(
                related_object=route,
                transaction_type=transaction_types.LOAN_DISBURSEMENT,
                amount=amount,
                description=f"Desembolso préstamo #{loan.id} - {client.user.full_name}",
                maker=user,
                associated_profile=client.user,
            )

            # Disbursement transaction on the loan (audit trail)
            Transaction.objects.create(
                related_object=loan,
                transaction_type=transaction_types.LOAN_DISBURSEMENT,
                amount=amount,
                description="Préstamo otorgado",
                maker=user,
                associated_profile=client.user,
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
            loan = Loan.objects.select_related(
                'route', 'client__user', 'route__collector_profile'
            ).get(id=loan_id)
        except Loan.DoesNotExist:
            raise GraphQLError("No existe un préstamo con este id")

        # Validate user has access to loan's route
        if user.is_admin:
            if not loan.route.administrators.filter(id=user.admin_profile.id).exists():
                raise GraphQLError("No tienes acceso a este préstamo")
        elif user.is_collector:
            if loan.route.collector_profile != user.collector_profile:
                raise GraphQLError("No tienes acceso a este préstamo")

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


class VoidPayment(relay.ClientIDMutation):
    """
    Voids a payment and creates reversal transaction on the route.
    Only admins can void payments.
    """
    payment = Field(PaymentNode)
    loan = Field(LoanNode)

    class Input:
        payment_id = String(required=True)
        reason = String(required=True, description="Reason for voiding the payment")

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_admin:
            raise GraphQLError('Solo los administradores pueden anular pagos')

        # Parse payment_id
        try:
            payment_id = from_global_id(input.get('payment_id'))[1]
        except Exception:
            raise GraphQLError("El id del pago no es válido")

        reason = input.get('reason', '').strip()
        if not reason:
            raise GraphQLError("Debe proporcionar una razón para anular el pago")

        # Get payment
        try:
            payment = Payment.objects.select_related(
                'loan__route', 'loan__client__user'
            ).get(id=payment_id)
        except Payment.DoesNotExist:
            raise GraphQLError("No existe un pago con este id")

        # Validate admin has access to loan's route
        if not payment.loan.route.administrators.filter(id=user.admin_profile.id).exists():
            raise GraphQLError("No tienes acceso a este pago")

        # Validate payment is not already voided
        if payment.is_voided:
            raise GraphQLError("El pago ya fue anulado")

        with transaction.atomic():
            # Mark payment as voided
            payment.voided_at = timezone.now()
            payment.voided_by = user
            payment.void_reason = reason
            payment.save()

            # Mark associated transaction as voided
            for tx in payment.transactions.all():
                tx.voided = True
                tx.save()

            # Create reversal transaction on Route (deduct from balance)
            Transaction.objects.create(
                related_object=payment.loan.route,
                transaction_type=transaction_types.PAYMENT_VOID,
                amount=payment.amount,
                description=f"Anulación de pago #{payment.id} - Préstamo #{payment.loan.id} - {reason}",
                maker=user,
                associated_profile=payment.loan.client.user
            )

        # Refresh loan to get updated calculated properties
        payment.loan.refresh_from_db()

        return VoidPayment(payment=payment, loan=payment.loan)
