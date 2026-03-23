from graphene import ObjectType, relay, String
from graphene_django.filter import DjangoFilterConnectionField
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from graphql_relay import from_global_id

from loans.filtersets import LoanFilterSet, PaymentFilterSet
from loans.models import Loan, Payment
from loans.mutations import CreateLoan, CreatePayment, VoidPayment
from loans.nodes import LoanNode, PaymentNode


class Query(ObjectType):
    # Query single loan by ID
    loan = relay.Node.Field(LoanNode)

    # Query single payment by ID
    payment = relay.Node.Field(PaymentNode)

    # Query loans by collector (for logged-in collector)
    loans_by_collector = DjangoFilterConnectionField(
        LoanNode,
        collector_id=String(description="Optional collector ID to filter by")
    )

    # Query loans by route
    loans_by_route = DjangoFilterConnectionField(
        LoanNode,
        route_id=String(required=True, description="Route ID to filter by")
    )

    # Query loans by client
    loans_by_client = DjangoFilterConnectionField(
        LoanNode,
        client_id=String(required=True, description="Client ID to filter by")
    )

    # Query overdue loans
    overdue_loans = DjangoFilterConnectionField(
        LoanNode,
        description="Loans past their due date"
    )

    # Query payments by loan
    payments_by_loan = DjangoFilterConnectionField(
        PaymentNode,
        loan_id=String(required=True, description="Loan ID to filter by")
    )

    @login_required
    def resolve_loans_by_collector(self, info, collector_id=None, **kwargs):
        user = info.context.user

        if user.is_collector:
            # Collector sees their own loans
            return Loan.objects.filter(collector__user=user).select_related(
                'route', 'client__user', 'collector__user'
            )
        elif user.is_admin:
            # Admin can see loans by specific collector or all loans in their routes
            if collector_id:
                try:
                    pk = from_global_id(collector_id)[1]
                    return Loan.objects.filter(collector_id=pk).select_related(
                        'route', 'client__user', 'collector__user'
                    )
                except Exception:
                    raise GraphQLError("El id del cobrador no es válido")
            else:
                # Return loans from routes managed by this admin
                routes = user.admin_profile.routes_as_admin.all()
                return Loan.objects.filter(route__in=routes).select_related(
                    'route', 'client__user', 'collector__user'
                )
        else:
            raise GraphQLError("No tienes permisos para consultar préstamos")

    @login_required
    def resolve_loans_by_route(self, info, route_id, **kwargs):
        user = info.context.user

        try:
            pk = from_global_id(route_id)[1]
        except Exception:
            raise GraphQLError("El id de la ruta no es válido")

        if user.is_admin:
            # Verify admin has access to this route
            if not user.admin_profile.routes_as_admin.filter(id=pk).exists():
                raise GraphQLError("No tienes acceso a esta ruta")
        elif user.is_collector:
            # Verify collector is assigned to this route
            from routes.models import Route
            try:
                route = Route.objects.get(id=pk)
                if route.collector_profile != user.collector_profile:
                    raise GraphQLError("No tienes acceso a esta ruta")
            except Route.DoesNotExist:
                raise GraphQLError("La ruta no existe")
        else:
            raise GraphQLError("No tienes permisos para consultar préstamos")

        return Loan.objects.filter(route_id=pk).select_related(
            'route', 'client__user', 'route__collector_profile__user'
        )

    @login_required
    def resolve_loans_by_client(self, info, client_id, **kwargs):
        user = info.context.user

        try:
            pk = from_global_id(client_id)[1]
        except Exception:
            raise GraphQLError("El id del cliente no es válido")

        if not user.is_admin and not user.is_collector:
            raise GraphQLError("No tienes permisos para consultar préstamos")

        return Loan.objects.filter(client_id=pk).select_related(
            'route', 'client__user', 'collector__user'
        )

    @login_required
    def resolve_payments_by_loan(self, info, loan_id, **kwargs):
        user = info.context.user

        try:
            pk = from_global_id(loan_id)[1]
        except Exception:
            raise GraphQLError("El id del préstamo no es válido")

        if not user.is_admin and not user.is_collector:
            raise GraphQLError("No tienes permisos para consultar pagos")

        return Payment.objects.filter(loan_id=pk).select_related('loan')

    @login_required
    def resolve_overdue_loans(self, info, **kwargs):
        user = info.context.user
        from django.utils import timezone

        if user.is_admin:
            routes = user.admin_profile.routes_as_admin.all()
            queryset = Loan.objects.filter(route__in=routes)
        elif user.is_collector:
            queryset = Loan.objects.filter(collector__user=user)
        else:
            raise GraphQLError("No tienes permisos para consultar préstamos")

        # Filter overdue loans: not fully paid, past due date
        return queryset.filter(
            due_date__lt=timezone.now().date()
        ).select_related('route', 'client__user', 'collector__user')


class Mutation(ObjectType):
    create_loan = CreateLoan.Field()
    create_payment = CreatePayment.Field()
    void_payment = VoidPayment.Field()
