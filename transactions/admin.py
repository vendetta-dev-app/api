from django.contrib import admin
from unfold.admin import ModelAdmin

from transactions.models import Transaction


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ('transaction_type', 'amount', 'related_object', 'voided', 'created_at')
    readonly_fields = ('transaction_type', 'amount', 'description', 'related_object', 'content_type', 'object_id', 'voided', 'maker', 'associated_profile', 'created_at', 'updated_at')
    list_filter = ('transaction_type', 'voided')
    search_fields = ('description',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
