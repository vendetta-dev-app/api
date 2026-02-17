from decimal import Decimal

from django.db import transaction
from django.utils import timezone
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
    """
    Creates a new loan request in PENDING status.
    The loan must be approved by an admin before disbursement.
    """
    loan = Field(LoanNode)

    class Input:
        route_id = String(required=True)
        client_id = String(required=True)
        amount = GrapheneDecimal(required=True)
        interest_rate = GrapheneDecimal(required=True)
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
            if route.collector != user.collector_profile:
                raise GraphQLError("No tienes acceso a esta ruta")

        # Get client
        try:
            client = ClientProfile.objects.select_related('collector', 'user').get(id=client_id)
        except ClientProfile.DoesNotExist:
            raise GraphQLError("No existe un cliente con este id")

        # Validate client belongs to the route's collector
        if route.collector and client.collector != route.collector:
            raise GraphQLError("El cliente no pertenece al cobrador asignado a esta ruta")

        amount = Decimal(str(input.get('amount')))
        interest_rate = Decimal(str(input.get('interest_rate')))
        due_date = input.get('due_date')

        # Validate amount is positive
        if amount <= Decimal('0.00'):
            raise GraphQLError("El monto debe ser mayor a cero")

        # Validate interest rate is valid (0, 10, or 20)
        valid_rates = [Decimal('0'), Decimal('10'), Decimal('20')]
        if interest_rate not in valid_rates:
            raise GraphQLError("La tasa de interés debe ser 0%, 10% o 20%")

        # Get collector from client
        collector = client.collector
        if not collector:
            raise GraphQLError("El cliente no tiene un cobrador asignado")

        # Create Loan in PENDING status (no transactions yet)
        loan = Loan.objects.create(
            route=route,
            client=client,
            collector=collector,
            amount=amount,
            interest_rate=interest_rate,
            due_date=due_date,
            is_approved=False  # Requires admin approval
        )

        return CreateLoan(loan=loan)


class ApproveLoan(relay.ClientIDMutation):
    """
    Approves a pending loan and creates disbursement transactions.
    Only admins can approve loans.
    """
    loan = Field(LoanNode)

    class Input:
        loan_id = String(required=True)

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_admin:
            raise GraphQLError('Solo los administradores pueden aprobar préstamos')

        # Parse loan_id
        try:
            loan_id = from_global_id(input.get('loan_id'))[1]
        except Exception:
            raise GraphQLError("El id del préstamo no es válido")

        # Get loan
        try:
            loan = Loan.objects.select_related(
                'route', 'client__user', 'collector'
            ).get(id=loan_id)
        except Loan.DoesNotExist:
            raise GraphQLError("No existe un préstamo con este id")

        # Validate admin has access to loan's route
        if not loan.route.administrators.filter(id=user.admin_profile.id).exists():
            raise GraphQLError("No tienes acceso a este préstamo")

        # Validate loan is not already approved
        if loan.is_approved:
            raise GraphQLError("El préstamo ya está aprobado")

        # Validate loan is not rejected
        if loan.is_rejected:
            raise GraphQLError("El préstamo fue rechazado y no puede ser aprobado")

        # Validate route has sufficient balance
        if loan.route.current_balance < loan.amount:
            raise GraphQLError("Balance insuficiente en la ruta")

        with transaction.atomic():
            # Update loan status
            loan.is_approved = True
            loan.approved_at = timezone.now()
            loan.approved_by = user
            loan.save()

            # Create Transaction for disbursement on Route
            Transaction.objects.create(
                related_object=loan.route,
                transaction_type=transaction_types.LOAN_DISBURSEMENT,
                amount=loan.amount,
                description=f"Desembolso préstamo #{loan.id} - {loan.client.user.full_name}",
                maker=user,
                associated_profile=loan.client.user
            )

            # Create Transaction on Loan
            Transaction.objects.create(
                related_object=loan,
                transaction_type=transaction_types.LOAN_DISBURSEMENT,
                amount=loan.amount,
                description="Préstamo otorgado",
                maker=user,
                associated_profile=loan.client.user
            )

        return ApproveLoan(loan=loan)


class RejectLoan(relay.ClientIDMutation):
    """
    Rejects a pending loan request.
    Only admins can reject loans.
    """
    loan = Field(LoanNode)

    class Input:
        loan_id = String(required=True)
        reason = String(required=True, description="Reason for rejection")

    @classmethod
    @login_required
    def mutate_and_get_payload(cls, root, info, **input):
        user = info.context.user

        if not user.is_admin:
            raise GraphQLError('Solo los administradores pueden rechazar préstamos')

        # Parse loan_id
        try:
            loan_id = from_global_id(input.get('loan_id'))[1]
        except Exception:
            raise GraphQLError("El id del préstamo no es válido")

        reason = input.get('reason', '').strip()
        if not reason:
            raise GraphQLError("Debe proporcionar una razón para el rechazo")

        # Get loan
        try:
            loan = Loan.objects.select_related('route').get(id=loan_id)
        except Loan.DoesNotExist:
            raise GraphQLError("No existe un préstamo con este id")

        # Validate admin has access to loan's route
        if not loan.route.administrators.filter(id=user.admin_profile.id).exists():
            raise GraphQLError("No tienes acceso a este préstamo")

        # Validate loan is not already approved
        if loan.is_approved:
            raise GraphQLError("No se puede rechazar un préstamo ya aprobado")

        # Validate loan is not already rejected
        if loan.is_rejected:
            raise GraphQLError("El préstamo ya fue rechazado")

        # Update loan status
        loan.is_rejected = True
        loan.rejection_reason = reason
        loan.save()

        return RejectLoan(loan=loan)


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
                'route', 'client__user', 'collector'
            ).get(id=loan_id)
        except Loan.DoesNotExist:
            raise GraphQLError("No existe un préstamo con este id")

        # Validate user has access to loan's route
        if user.is_admin:
            if not loan.route.administrators.filter(id=user.admin_profile.id).exists():
                raise GraphQLError("No tienes acceso a este préstamo")
        elif user.is_collector:
            if loan.collector != user.collector_profile:
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
