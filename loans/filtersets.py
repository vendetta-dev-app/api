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
        """Filter by calculated status: PENDING, ACTIVE, PAID"""
        loans_ids = [
            loan.id for loan in queryset
            if loan.status == value
        ]
        return queryset.filter(id__in=loans_ids)


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
