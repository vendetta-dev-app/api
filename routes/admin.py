from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from accounts.models import ClientProfile
from routes.models import Route


class ClientInline(TabularInline):
    model = ClientProfile
    extra = 0
    fields = ('get_full_name', 'alias', 'neighborhood', 'is_active', 'visit_order')
    readonly_fields = ('get_full_name',)
    show_change_link = True
    verbose_name = "Client"
    verbose_name_plural = "Clients"

    def get_full_name(self, obj):
        return obj.user.full_name
    get_full_name.short_description = "Full Name"


@admin.register(Route)
class RouteAdmin(ModelAdmin):
    list_display = ('name', 'city', 'get_collector', 'get_manager', 'starting_balance', 'current_balance', 'created_at')
    readonly_fields = ('get_collector', 'starting_balance', 'current_balance', 'created_at', 'updated_at')
    list_filter = ('city',)
    inlines = [ClientInline]

    fieldsets = (
        ('General', {
            'fields': ('name', 'city', 'administrators', 'manager')
        }),
        ('Collector', {
            'fields': ('get_collector',)
        }),
        ('Balance', {
            'fields': ('starting_balance', 'current_balance')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_collector(self, obj):
        try:
            return obj.collector_profile.user.full_name
        except AttributeError:
            return "No collector assigned"
    get_collector.short_description = "Collector"

    def get_manager(self, obj):
        if obj.manager:
            return obj.manager.user.full_name
        return "—"
    get_manager.short_description = "Manager"
