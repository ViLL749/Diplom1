from django.db import migrations
from decimal import Decimal


def sale_price_to_total(apps, schema_editor):
    """Multiply each WorkOrderPart.sale_price by its quantity (per-unit → total)."""
    WorkOrderPart = apps.get_model('warehouse', 'WorkOrderPart')
    for wop in WorkOrderPart.objects.exclude(sale_price=None):
        wop.sale_price = (wop.sale_price * wop.quantity).quantize(Decimal('0.01'))
        wop.save(update_fields=['sale_price'])


def sale_price_to_per_unit(apps, schema_editor):
    """Reverse: divide sale_price by quantity (total → per-unit)."""
    WorkOrderPart = apps.get_model('warehouse', 'WorkOrderPart')
    for wop in WorkOrderPart.objects.exclude(sale_price=None):
        if wop.quantity and wop.quantity > 0:
            wop.sale_price = (wop.sale_price / wop.quantity).quantize(Decimal('0.01'))
            wop.save(update_fields=['sale_price'])


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0016_add_part_default_markup'),
    ]

    operations = [
        migrations.RunPython(sale_price_to_total, sale_price_to_per_unit),
    ]
