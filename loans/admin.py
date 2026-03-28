from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from loans.models import Loan, Payment


class PaymentInline(TabularInline):
    model = Payment
    extra = 0
    fields = ('amount', 'payment_date', 'payment_method', 'notes', 'get_status', 'voided_at', 'void_reason')
    readonly_fields = ('get_status', 'voided_at', 'voided_by', 'void_reason')
    verbose_name = "Payment"
    verbose_name_plural = "Payments"

    def get_status(self, obj):
        if obj.pk and obj.is_voided:
            return format_html('<span style="color:red;font-weight:bold;">Voided</span>')
        return format_html('<span style="color:green;">Valid</span>')
    get_status.short_description = "Status"


STATUS_LABELS = {
    'ACTIVE': ('Active', 'blue'),
    'OVERDUE': ('Overdue', 'red'),
    'PAID': ('Paid', 'green'),
}

PAYMENT_STATUS_LABELS = {
    'AL_DIA': ('Up to date', 'green'),
    'ADELANTADO': ('Ahead', 'teal'),
    'PAGO_PARCIAL': ('Partial payment', 'orange'),
    'ATRASADO': ('Behind', 'red'),
    'PAID': ('Paid', 'gray'),
}


@admin.register(Loan)
class LoanAdmin(ModelAdmin):
    list_display = ('id', 'get_cliente', 'route', 'amount', 'get_total', 'get_pendiente', 'get_status', 'payment_frequency', 'due_date', 'created_at')
    readonly_fields = ('get_total', 'get_total_pagado', 'get_pendiente', 'get_installment_amount', 'get_status', 'get_payment_status', 'get_is_overdue', 'get_days_overdue', 'created_at', 'updated_at')
    list_filter = ('payment_frequency', 'route')
    search_fields = ('client__user__full_name', 'route__name')
    inlines = [PaymentInline]

    fieldsets = (
        ('Loan', {
            'fields': ('route', 'client', 'collector', 'amount', 'interest_rate', 'installments', 'payment_frequency', 'due_date')
        }),
        ('Current Status', {
            'fields': ('get_total', 'get_total_pagado', 'get_pendiente', 'get_installment_amount', 'get_status', 'get_payment_status', 'get_is_overdue', 'get_days_overdue')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_cliente(self, obj):
        return obj.client.user.full_name
    get_cliente.short_description = "Client"

    def get_total(self, obj):
        if not obj.pk or obj.amount is None:
            return "—"
        return obj.total_amount
    get_total.short_description = "Total with interest"

    def get_total_pagado(self, obj):
        if not obj.pk:
            return "—"
        return obj.total_paid
    get_total_pagado.short_description = "Total paid"

    def get_pendiente(self, obj):
        if not obj.pk or obj.amount is None:
            return "—"
        return obj.pending_balance
    get_pendiente.short_description = "Pending balance"

    def get_installment_amount(self, obj):
        if not obj.pk or obj.amount is None or not obj.installments:
            return "—"
        return obj.installment_amount
    get_installment_amount.short_description = "Installment amount"

    def get_status(self, obj):
        if not obj.pk or obj.amount is None:
            return "—"
        label, color = STATUS_LABELS.get(obj.status, (obj.status, 'gray'))
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', color, label)
    get_status.short_description = "Status"

    def get_payment_status(self, obj):
        if not obj.pk or obj.amount is None:
            return "—"
        label, color = PAYMENT_STATUS_LABELS.get(obj.payment_status, (obj.payment_status, 'gray'))
        return format_html('<span style="color:{};">{}</span>', color, label)
    get_payment_status.short_description = "Installment status"

    def get_is_overdue(self, obj):
        if not obj.pk or obj.amount is None:
            return "—"
        if obj.is_overdue:
            return format_html('<span style="color:red;font-weight:bold;">Yes — {} days</span>', obj.days_overdue)
        return "No"
    get_is_overdue.short_description = "Overdue?"

    def get_days_overdue(self, obj):
        if not obj.pk:
            return "—"
        return obj.days_overdue
    get_days_overdue.short_description = "Days overdue"


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ('id', 'get_client', 'loan', 'amount', 'payment_date', 'payment_method', 'get_status')
    readonly_fields = ('voided_at', 'voided_by', 'void_reason', 'created_at', 'updated_at')
    list_filter = ('payment_method',)
    search_fields = ('loan__client__user__full_name', 'loan__route__name')

    def get_client(self, obj):
        return obj.loan.client.user.full_name
    get_client.short_description = "Client"

    def get_status(self, obj):
        if obj.is_voided:
            return format_html('<span style="color:red;font-weight:bold;">Voided</span>')
        return format_html('<span style="color:green;">Valid</span>')
    get_status.short_description = "Status"
