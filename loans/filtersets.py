from decimal import Decimal

from django.db.models import Sum, Subquery, OuterRef, DecimalField, F, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django_filters import FilterSet, CharFilter
from graphql_relay import from_global_id

from loans.models import Loan, Payment


class LoanFilterSet(FilterSet):
    route_id = CharFilter(method="filter_by_route")
    collector_id = CharFilter(method="filter_by_collector")
    client_id = CharFilter(method="filter_by_client")
    status = CharFilter(method="filter_by_status")

    class Meta:
        model = Loan
        fields = {
            "is_approved": ["exact"],
        }

    def filter_by_route(self, queryset, name, value):
        route_pk = from_global_id(value)[1]
        return queryset.filter(route_id=route_pk)

    def filter_by_collector(self, queryset, name, value):
        collector_pk = from_global_id(value)[1]
        return queryset.filter(collector_id=collector_pk)

    def filter_by_client(self, queryset, name, value):
        client_pk = from_global_id(value)[1]
        return queryset.filter(client_id=client_pk)

    def filter_by_status(self, queryset, name, value):
        """
        Filter by calculated status: PENDING, REJECTED, ACTIVE, OVERDUE, PAID
        Optimized to use database-level calculations
        """
        if value == "PENDING":
            return queryset.filter(is_approved=False, is_rejected=False)

        if value == "REJECTED":
            return queryset.filter(is_rejected=True)

        # For ACTIVE, OVERDUE, and PAID, we need approved loans with balance calculations
        queryset = queryset.filter(is_approved=True, is_rejected=False)

        # Subquery to calculate total_paid for each loan (excluding voided payments)
        total_paid_subquery = Payment.objects.filter(
            loan=OuterRef('pk'),
            voided_at__isnull=True
        ).values('loan').annotate(
            total=Sum('amount')
        ).values('total')

        # Annotate with calculated fields
        queryset = queryset.annotate(
            calculated_total_paid=Coalesce(
                Subquery(total_paid_subquery, output_field=DecimalField()),
                Value(Decimal('0.00'))
            ),
            calculated_total_amount=F('amount') + (F('interest_rate') / 100 * F('amount')),
        ).annotate(
            calculated_pending_balance=F('calculated_total_amount') - F('calculated_total_paid')
        )

        today = timezone.now().date()

        if value == "PAID":
            return queryset.filter(calculated_pending_balance__lte=Decimal('0.00'))
        elif value == "OVERDUE":
            return queryset.filter(
                calculated_pending_balance__gt=Decimal('0.00'),
                due_date__lt=today
            )
        elif value == "ACTIVE":
            # Active: has pending balance AND (no due_date OR not yet overdue)
            from django.db.models import Q
            return queryset.filter(
                calculated_pending_balance__gt=Decimal('0.00')
            ).filter(
                Q(due_date__isnull=True) | Q(due_date__gte=today)
            )

        return queryset


class PaymentFilterSet(FilterSet):
    loan_id = CharFilter(method="filter_by_loan")

    class Meta:
        model = Payment
        fields = {
            "payment_method": ["exact"],
        }

    def filter_by_loan(self, queryset, name, value):
        loan_pk = from_global_id(value)[1]
        return queryset.filter(loan_id=loan_pk)
