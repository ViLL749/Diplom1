from django.db import migrations


def backfill_snapshots(apps, schema_editor):
    WOSE = apps.get_model('warehouse', 'WorkOrderServiceEmployee')
    to_update = []
    for asgn in WOSE.objects.filter(salary_coefficient_snapshot__isnull=True).select_related('employee'):
        asgn.salary_coefficient_snapshot = asgn.employee.salary_coefficient
        to_update.append(asgn)
    if to_update:
        WOSE.objects.bulk_update(to_update, ['salary_coefficient_snapshot'])


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0014_add_salary_coeff_snapshot'),
    ]

    operations = [
        migrations.RunPython(backfill_snapshots, migrations.RunPython.noop),
    ]
