from django.db import models
from django.utils import timezone


# Модель клиента
class Client(models.Model):
    fio = models.CharField(max_length=255, verbose_name="ФИО")
    phone = models.CharField(max_length=20, verbose_name="Телефон", blank=True, null=True, unique=True) # Убрать null True и blank True

    def __str__(self):
        return self.fio

    def delete(self, *args, **kwargs):
        from .models import ClientCar, Order
        client_cars = ClientCar.objects.filter(client=self)
        orders = Order.objects.filter(client_car__in=client_cars)
        orders.filter(status__in=['Первичный осмотр', 'Диагностика', 'В работе', 'Готов']).delete()
        orders.filter(status='Завершён').update(client_car=None)
        client_cars.delete()
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"


# Модель марки автомобиля
class CarMake(models.Model):
    name = models.CharField(max_length=100, verbose_name="Марка автомобиля", unique=True)

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        from .models import CarModel, ClientCar, Order
        car_models = CarModel.objects.filter(make=self)
        client_cars = ClientCar.objects.filter(make=self)
        orders = Order.objects.filter(client_car__in=client_cars)
        orders.filter(status__in=['Первичный осмотр', 'Диагностика', 'В работе', 'Готов']).delete()
        orders.filter(status='Завершён').update(client_car=None)
        client_cars.delete()
        car_models.delete()
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = "Марка автомобиля"
        verbose_name_plural = "Марки автомобилей"

# Модель модели автомобиля
class CarModel(models.Model):
    make = models.ForeignKey(CarMake, on_delete=models.CASCADE, verbose_name="Марка")
    name = models.CharField(max_length=100, verbose_name="Модель", unique=True)

    def __str__(self):
        return f"{self.make.name} {self.name}"

    def delete(self, *args, **kwargs):
        from .models import ClientCar, Order
        client_cars = ClientCar.objects.filter(model=self)
        orders = Order.objects.filter(client_car__in=client_cars)
        orders.filter(status__in=['Первичный осмотр', 'Диагностика', 'В работе', 'Готов']).delete()
        orders.filter(status='Завершён').update(client_car=None)
        client_cars.delete()
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = "Модель автомобиля"
        verbose_name_plural = "Модели автомобилей"


# Модель автомобиля клиента
class ClientCar(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Клиент")
    make = models.ForeignKey(CarMake, on_delete=models.CASCADE, verbose_name="Марка")
    model = models.ForeignKey(CarModel, on_delete=models.CASCADE, verbose_name="Модель")
    license_plate = models.CharField(max_length=20, verbose_name="Госномер", blank=True, null=True)
    color = models.CharField(max_length=50, verbose_name="Цвет", blank=True, null=True)
    vin = models.CharField(max_length=17, verbose_name="VIN-номер", blank=True, null=True)
    year = models.PositiveIntegerField(verbose_name="Год выпуска", blank=True, null=True)

    def delete(self, *args, **kwargs):
        from .models import Order
        orders = Order.objects.filter(client_car=self)
        orders.filter(status__in=['Первичный осмотр', 'Диагностика', 'В работе', 'Готов']).delete()
        orders.filter(status='Завершён').update(client_car=None)

        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.make.name} {self.model.name} ({self.license_plate})"

    class Meta:
        verbose_name = "Автомобиль клиента"
        verbose_name_plural = "Автомобили клиентов"



class ServiceType(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название типа услуги", unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тип услуги"
        verbose_name_plural = "Типы услуг"


# Модель конкретной услуги
class Service(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название услуги", unique=True)
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE, verbose_name="Тип услуги")
    base_hours = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name="Базовое время (ч)", default=1
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"


# Модель заказа


class Order(models.Model):
    STATUS_CHOICES = [
        ('Первичный осмотр', 'Первичный осмотр'),
        ('Диагностика', 'Диагностика'),
        ('В работе', 'В работе'),
        ('Готов', 'Готов'),
        ('Завершён', 'Завершён'),
        ('Отменён', 'Отменён'),
    ]

    client_car = models.ForeignKey(
        'ClientCar',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Автомобиль клиента"
    )
    order_date = models.DateField(verbose_name="Дата заказа", default=timezone.now)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Стоимость", blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Первичный осмотр', verbose_name="Статус")
    completion_date = models.DateField(verbose_name="Дата завершения", blank=True, null=True)
    comment = models.TextField(verbose_name="Комментарий", blank=True, null=True)

    client_fio_static = models.CharField(max_length=255, verbose_name="ФИО клиента (статично)", blank=True, null=True)
    car_details_static = models.CharField(max_length=255, verbose_name="Данные автомобиля (статично)", blank=True, null=True)
    services_static = models.TextField(verbose_name="Услуги (статично)", blank=True, null=True)
    custom_services_static = models.TextField(verbose_name="Кастомные услуги (статично)", blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.client_car and not self.client_fio_static:
            self.client_fio_static = self.client_car.client.fio
        if self.client_car and not self.car_details_static:
            self.car_details_static = f"{self.client_car.make.name} {self.client_car.model.name} ({self.client_car.license_plate or ''})"

        if self.status == 'Завершён' and not self.completion_date:
            self.completion_date = timezone.now().date()
        elif self.status != 'Завершён':
            self.completion_date = None
        super().save(*args, **kwargs)

    def __str__(self):
        client_info = self.client_fio_static or (self.client_car.client.fio if self.client_car else "Удалённый клиент")
        car_info = self.car_details_static or (f"{self.client_car.make.name} {self.client_car.model.name}" if self.client_car else "Удалённый автомобиль")
        return f"Заказ {self.id} - {client_info} ({car_info})"

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-id']


