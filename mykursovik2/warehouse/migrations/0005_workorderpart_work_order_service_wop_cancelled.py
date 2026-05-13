from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('warehouse', '0004_brand_alter_part_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='workorderpart',
            name='work_order_service',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='parts',
                to='warehouse.workorderservice',
                verbose_name='Услуга в заказ-наряде',
            ),
        ),
        migrations.AlterField(
            model_name='workorderpart',
            name='status',
            field=models.CharField(
                choices=[
                    ('reserved', 'Зарезервировано'),
                    ('issued', 'Выдано'),
                    ('installed', 'Установлено'),
                    ('cancelled', 'Отменено'),
                ],
                default='reserved',
                max_length=20,
                verbose_name='Статус',
            ),
        ),
    ]
