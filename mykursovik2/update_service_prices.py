# Импорт моделей (предполагается, что приложение называется 'mainapp')
from mainapp.models import CarMake, CarModel, Service, ServicePrice

# 1. Получаем все марки и модели
makes = {
    'Toyota': CarMake.objects.get(name='Toyota'),
    'BMW': CarMake.objects.get(name='BMW'),
    'Ford': CarMake.objects.get(name='Ford'),
    'Honda': CarMake.objects.get(name='Honda'),
}

all_models = CarModel.objects.filter(make__in=makes.values())

# 2. Получаем все услуги
services = Service.objects.all()

# 3. Определяем базовые цены для услуг
service_prices = {
    'Замена масла': 1500,
    'Ремонт двигателя': 25000,
    'Замена тормозов': 8000,
    'Ремонт подвески': 12000,
    'Компьютерная диагностика': 3000,
    'Диагностика ходовой': 3500,
    'Проверка двигателя': 2800,
    'Диагностика электрики': 3200,
    'ТО-1': 5000,
    'ТО-2': 7000,
    'Замена фильтров': 2000,
    'Шиномонтаж': 4000
}

# 4. Создаем записи ServicePrice для каждой модели и услуги
price_adjustments = {
    'Toyota': 0,
    'BMW': 500,
    'Ford': 200,
    'Honda': 300
}

for model in all_models:
    make_name = model.make.name
    price_adjust = price_adjustments.get(make_name, 0)  # На случай, если марка не учтена

    for service in services:
        base_price = service_prices.get(service.name, 0)  # Защита от ошибки, если услуги нет в словаре
        final_price = base_price + price_adjust

        ServicePrice.objects.get_or_create(
            car_make=model.make,
            car_model=model,
            service=service,
            defaults={'price': final_price}  # Используем defaults, чтобы не обновлять уже существующую цену
        )

print("Цены успешно установлены!")
