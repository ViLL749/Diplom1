from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0003_service_base_hours'),
    ]

    operations = [
        migrations.DeleteModel(name='ServicePrice'),
        migrations.DeleteModel(name='OrderService'),
        migrations.DeleteModel(name='CustomService'),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('Первичный осмотр', 'Первичный осмотр'),
                    ('Диагностика', 'Диагностика'),
                    ('В работе', 'В работе'),
                    ('Готов', 'Готов'),
                    ('Завершён', 'Завершён'),
                    ('Отменён', 'Отменён'),
                ],
                default='Первичный осмотр',
                max_length=50,
                verbose_name='Статус',
            ),
        ),
    ]
