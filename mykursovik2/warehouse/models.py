from django.db import models
from django.utils import timezone


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Производитель"
        verbose_name_plural = "Производители"
        ordering = ['name']


class Supplier(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название", unique=True)
    phone = models.CharField(max_length=30, verbose_name="Телефон", blank=True)
    contact = models.CharField(max_length=255, verbose_name="Контактное лицо", blank=True)
    notes = models.TextField(verbose_name="Примечания", blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Поставщик"
        verbose_name_plural = "Поставщики"
        ordering = ['name']


class Part(models.Model):
    CATEGORY_CHOICES = [
        ('Расходники', 'Расходники'),
        ('Подвеска', 'Подвеска'),
        ('Двигатель', 'Двигатель'),
        ('Тормозная система', 'Тормозная система'),
        ('Кузов', 'Кузов'),
        ('Электрика', 'Электрика'),
        ('Трансмиссия', 'Трансмиссия'),
        ('Прочее', 'Прочее'),
    ]

    article = models.CharField(max_length=100, verbose_name="Артикул", unique=True)
    name = models.CharField(max_length=255, verbose_name="Название", unique=True)
    brand = models.CharField(max_length=100, verbose_name="Производитель", blank=True)
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES,
        verbose_name="Категория", default='Прочее'
    )
    notes = models.TextField(verbose_name="Примечания", blank=True)
    package_qty = models.PositiveIntegerField(
        default=1, verbose_name="Штук в упаковке"
    )

    def __str__(self):
        return f"{self.article} — {self.name}"

    class Meta:
        verbose_name = "Деталь"
        verbose_name_plural = "Детали"
        ordering = ['article']


class StorageLocation(models.Model):
    rack = models.CharField(max_length=10, verbose_name="Стеллаж")
    shelf = models.CharField(max_length=10, verbose_name="Полка")
    cell = models.CharField(max_length=10, verbose_name="Ячейка")
    label = models.CharField(max_length=30, verbose_name="Адрес", blank=True)

    def save(self, *args, **kwargs):
        self.label = f"{self.rack}-{self.shelf}-{self.cell}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.label

    class Meta:
        verbose_name = "Место хранения"
        verbose_name_plural = "Места хранения"
        unique_together = ('rack', 'shelf', 'cell')
        ordering = ['rack', 'shelf', 'cell']


class StockEntry(models.Model):
    part = models.ForeignKey(
        Part, on_delete=models.CASCADE,
        verbose_name="Деталь", related_name='stock_entries'
    )
    location = models.ForeignKey(
        StorageLocation, on_delete=models.CASCADE,
        verbose_name="Место хранения", related_name='stock_entries'
    )
    total_qty = models.IntegerField(verbose_name="Общее количество", default=0)
    reserved_qty = models.IntegerField(verbose_name="Зарезервировано", default=0)
    min_qty = models.IntegerField(verbose_name="Минимальный остаток", default=1)

    @property
    def available_qty(self):
        return self.total_qty - self.reserved_qty

    @property
    def is_low(self):
        return self.total_qty <= self.min_qty

    def __str__(self):
        return f"{self.part.article} @ {self.location.label}: {self.total_qty} шт."

    class Meta:
        verbose_name = "Остаток на складе"
        verbose_name_plural = "Остатки на складе"
        unique_together = ('part', 'location')


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('ordered', 'Заказано'),
        ('in_transit', 'В пути'),
        ('partial', 'Частично получено'),
        ('received', 'Получено'),
    ]

    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Поставщик"
    )
    work_order = models.ForeignKey(
        'mainapp.Order',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Заказ-наряд",
        related_name='purchase_orders'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='ordered', verbose_name="Статус"
    )
    created_at = models.DateTimeField(verbose_name="Дата заказа", default=timezone.now)
    comment = models.TextField(verbose_name="Примечание", blank=True)

    def __str__(self):
        supplier_str = self.supplier.name if self.supplier else "Без поставщика"
        return f"Заказ №{self.id} — {supplier_str} [{self.get_status_display()}]"

    @property
    def is_received(self):
        return self.status == 'received'

    class Meta:
        verbose_name = "Заказ поставщику"
        verbose_name_plural = "Заказы поставщикам"
        ordering = ['-created_at']


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE,
        verbose_name="Заказ", related_name='items'
    )
    part = models.ForeignKey(Part, on_delete=models.CASCADE, verbose_name="Деталь")
    quantity = models.IntegerField(verbose_name="Заказано")
    received_qty = models.IntegerField(verbose_name="Получено", default=0)

    @property
    def remaining_qty(self):
        return self.quantity - self.received_qty

    def __str__(self):
        return f"{self.part.article} x{self.quantity} (получено: {self.received_qty})"

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"


class SupplyDocument(models.Model):
    created_at = models.DateTimeField(verbose_name="Дата приёмки", default=timezone.now)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Поставщик"
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Заказ поставщику",
        related_name='supply_documents'
    )
    comment = models.TextField(verbose_name="Примечание", blank=True)

    def __str__(self):
        return f"Приход №{self.id} от {self.created_at.strftime('%d.%m.%Y')}"

    class Meta:
        verbose_name = "Документ прихода"
        verbose_name_plural = "Документы прихода"
        ordering = ['-created_at']


class SupplyItem(models.Model):
    document = models.ForeignKey(
        SupplyDocument, on_delete=models.CASCADE,
        verbose_name="Документ", related_name='items'
    )
    po_item = models.ForeignKey(
        PurchaseOrderItem, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Позиция заказа",
        related_name='supply_items'
    )
    part = models.ForeignKey(Part, on_delete=models.CASCADE, verbose_name="Деталь")
    location = models.ForeignKey(
        StorageLocation, on_delete=models.CASCADE, verbose_name="Место хранения"
    )
    quantity = models.IntegerField(verbose_name="Количество")
    purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Цена закупки"
    )

    def __str__(self):
        return f"{self.part.article} x{self.quantity} @ {self.purchase_price} руб."

    class Meta:
        verbose_name = "Строка прихода"
        verbose_name_plural = "Строки прихода"


class WorkOrderPart(models.Model):
    STATUS_CHOICES = [
        ('reserved', 'Зарезервировано'),
        ('issued', 'Выдано'),
        ('installed', 'Установлено'),
    ]

    work_order = models.ForeignKey(
        'mainapp.Order',
        on_delete=models.CASCADE,
        verbose_name="Заказ-наряд",
        related_name='work_order_parts'
    )
    part = models.ForeignKey(Part, on_delete=models.CASCADE, verbose_name="Деталь")
    quantity = models.IntegerField(verbose_name="Количество")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='reserved', verbose_name="Статус"
    )
    sale_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Цена продажи за единицу", null=True, blank=True
    )
    markup = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name="Наценка (%)", default=30
    )

    @property
    def total_price(self):
        if self.sale_price:
            return self.sale_price * self.quantity
        return None

    def __str__(self):
        return f"{self.part.article} x{self.quantity} для заказа №{self.work_order.id}"

    class Meta:
        verbose_name = "Деталь в заказ-наряде"
        verbose_name_plural = "Детали в заказ-наряде"


class WorkOrderService(models.Model):
    work_order = models.ForeignKey(
        'mainapp.Order',
        on_delete=models.CASCADE,
        verbose_name="Заказ-наряд",
        related_name='work_order_services'
    )
    service = models.ForeignKey(
        'mainapp.Service',
        on_delete=models.CASCADE,
        verbose_name="Услуга"
    )
    hours_applied = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name="Часы"
    )
    complexity_factor = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name="Коэффициент сложности", default=1
    )
    final_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Итоговая цена", null=True, blank=True
    )

    def calculate_price(self):
        settings = WorkshopSettings.objects.first()
        rate = settings.hourly_rate if settings else 0
        return self.hours_applied * rate * self.complexity_factor

    def save(self, *args, **kwargs):
        self.final_price = self.calculate_price()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.service.name} для заказа №{self.work_order.id}"

    class Meta:
        verbose_name = "Услуга в заказ-наряде (нормо-часы)"
        verbose_name_plural = "Услуги в заказ-наряде (нормо-часы)"


class WorkshopSettings(models.Model):
    hourly_rate = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Стоимость нормо-часа (руб.)", default=2000
    )

    def __str__(self):
        return f"Настройки: нормо-час = {self.hourly_rate} руб."

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Настройки сервиса"
        verbose_name_plural = "Настройки сервиса"
