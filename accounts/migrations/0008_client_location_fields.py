# Generated migration for client location fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_remove_clientprofile_collector_clientprofile_route_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='clientprofile',
            name='city',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Ciudad'),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='address_reference',
            field=models.TextField(
                blank=True,
                help_text="Puntos de referencia para llegar (ej: 'cerca de la plaza', 'edificio color azul')",
                null=True,
                verbose_name='Referencia'
            ),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True, verbose_name='Latitud'),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True, verbose_name='Longitud'),
        ),
        migrations.AlterField(
            model_name='clientprofile',
            name='neighborhood',
            field=models.CharField(max_length=100, verbose_name='Comuna/Barrio'),
        ),
    ]
