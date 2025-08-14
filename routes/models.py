from cities_light.models import City
from django.db import models

class Route(models.Model):
    name = models.CharField(max_length=100)
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='routes')

    # One collector per route
    collector = models.ForeignKey(
        'accounts.CollectorProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='routes_as_collector'
    )

    # Multiple administrators per route, and each administrator can have multiple routes
    administrators = models.ManyToManyField(
        'accounts.AdminProfile',
        related_name='routes_as_admin'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.city}"