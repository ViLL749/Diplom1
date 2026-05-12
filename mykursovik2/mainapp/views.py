import os
import chardet
import tempfile
from io import StringIO

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import UploadedFile
from django.core.management import call_command
from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from .forms import (
    ClientForm, ClientCarForm, CarMakeForm, CarModelForm,
    ServiceTypeForm, ServiceForm, ServicePriceForm
)

@login_required
def clients_list(request):
    # Регистрируем кастомную SQL-функцию
    register_custom_functions()

    clients = Client.objects.all()

    # Получаем параметры запроса
    sort = request.GET.get('sort', 'id')
    direction = request.GET.get('direction', 'desc')

    # Обработка сортировки
    if sort in ['id', 'phone']:
        if direction == 'desc':
            clients = clients.order_by(f'-{sort}')
        else:
            clients = clients.order_by(sort)
    elif sort == 'fio':
        # Сортировка по ФИО с использованием custom_lower
        if direction == 'desc':
            clients = clients.extra(select={'fio_lower': 'custom_lower(fio)'}).order_by('-fio_lower')
        else:
            clients = clients.extra(select={'fio_lower': 'custom_lower(fio)'}).order_by('fio_lower')

    # Поиск
    search = request.GET.get('search', '')
    column = request.GET.get('column', 'fio')

    if search:
        search_lower = search.lower()
        if column == 'id':
            clients = clients.filter(id__contains=search)
        elif column == 'fio':
            clients = clients.extra(
                select={'fio_lower': 'custom_lower(fio)'},
                where=['custom_lower(fio) LIKE %s'],
                params=[f'%{search_lower}%']
            )
        elif column == 'phone':
            clients = clients.extra(
                select={'phone_lower': 'custom_lower(phone)'},
                where=['custom_lower(phone) LIKE %s'],
                params=[f'%{search_lower}%']
            )

    # Пагинация
    per_page = request.GET.get('per_page', 5)
    try:
        per_page = int(per_page)
        if per_page not in [5, 10, 20]:
            per_page = 5
    except ValueError:
        per_page = 5

    paginator = Paginator(clients, per_page)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except EmptyPage:
        page_obj = paginator.page(1)

    return render(request, 'clients/clients_list.html', {
        'page_obj': page_obj,
        'per_page': per_page,
    })


# Создание клиента
@login_required
def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Клиент успешно создан!')
            return redirect('clients_list')
    else:
        form = ClientForm()
    return render(request, 'clients/client_create.html', {'form': form, 'cancel_url': reverse('clients_list')})


import logging

# Настраиваем логгер
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


# Кастомная функция для приведения к нижнему регистру
def custom_lower(text):
    if text is None:
        return None
    return text.lower()  # Python корректно обрабатывает кириллицу


# Регистрация функции в SQLite
def register_custom_functions():
    with connection.cursor() as cursor:
        connection.connection.create_function("custom_lower", 1, custom_lower)
        logger.debug("Custom lower function registered in SQLite")


@login_required
def client_detail(request, pk):
    # Регистрируем функцию при каждом запросе
    register_custom_functions()

    client = get_object_or_404(Client, pk=pk)
    client_cars = ClientCar.objects.filter(client=client)

    # Сортировка
    sort = request.GET.get('sort', 'model__name')
    direction = request.GET.get('direction', 'asc')
    valid_sort_fields = ['make__name', 'model__name', 'license_plate']
    if sort in valid_sort_fields:
        if direction == 'desc':
            client_cars = client_cars.order_by(f'-{sort}')
        else:
            client_cars = client_cars.order_by(sort)

    # Поиск
    search = request.GET.get('search', '')
    column = request.GET.get('column', 'model')

    if search:
        if column == 'make':
            client_cars = client_cars.filter(make__name__contains=search)
        elif column == 'model':
            client_cars = client_cars.filter(model__name__contains=search)
        elif column == 'license_plate':
            search_lower = search.lower()
            client_cars = client_cars.extra(
                select={'license_lower': 'custom_lower(license_plate)'},
                where=['custom_lower(license_plate) LIKE %s'],
                params=[f'%{search_lower}%']
            )

    # Пагинация
    per_page = request.GET.get('per_page', 5)
    try:
        per_page = int(per_page)
        if per_page not in [5, 10, 20]:
            per_page = 5
    except ValueError:
        per_page = 5

    paginator = Paginator(client_cars, per_page)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except EmptyPage:
        page_obj = paginator.page(1)

    return render(request, 'clients/client_detail.html', {
        'client': client,
        'page_obj': page_obj,
        'per_page': per_page,
        'cancel_url': reverse('clients_list')
    })

# Редактирование клиента
def client_update(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Клиент успешно обновлён!')
            return redirect('clients_list')
    else:
        form = ClientForm(instance=client)
    return render(request, 'clients/client_update.html', {'form': form, 'cancel_url': reverse('clients_list')})


@require_POST
def check_vin_uniqueness(request):
    vin = request.POST.get('vin', '').strip().upper()
    exists = ClientCar.objects.filter(vin=vin).exists()
    return JsonResponse({'exists': exists})


@require_POST
def check_license_plate_uniqueness(request):
    license_plate = request.POST.get('license_plate', '').strip()
    exists = ClientCar.objects.filter(license_plate=license_plate).exists()
    return JsonResponse({'exists': exists})


from django.views.decorators.http import require_POST

@require_POST
def check_service_type_uniqueness(request):
    name = request.POST.get("name", "").strip().lower()
    service_type_id = request.POST.get("id", None)
    queryset = ServiceType.objects.all()
    if service_type_id:
        queryset = queryset.exclude(id=service_type_id)
    exists = any(st.name.lower() == name for st in queryset)
    return JsonResponse({"exists": exists})

@require_POST
def check_service_uniqueness(request):
    name = request.POST.get("name", "").strip().lower()
    service_id = request.POST.get("id", None)
    queryset = Service.objects.all()
    if service_id:
        queryset = queryset.exclude(id=service_id)
    exists = any(s.name.lower() == name for s in queryset)
    return JsonResponse({"exists": exists})

@require_POST
def check_car_make_uniqueness(request):
    name = request.POST.get("name", "").strip().lower()
    car_make_id = request.POST.get("id", None)
    queryset = CarMake.objects.all()
    if car_make_id:
        queryset = queryset.exclude(id=car_make_id)
    exists = any(cm.name.lower() == name for cm in queryset)
    return JsonResponse({"exists": exists})

@require_POST
def check_car_model_uniqueness(request):
    name = request.POST.get("name", "").strip().lower()
    car_model_id = request.POST.get("id", None)
    queryset = CarModel.objects.all()
    if car_model_id:
        queryset = queryset.exclude(id=car_model_id)
    exists = any(cm.name.lower() == name for cm in queryset)
    return JsonResponse({"exists": exists})


@require_POST
def check_client_phone_uniqueness(request):
    phone = request.POST.get("phone", "").strip()
    client_id = request.POST.get("id", None)
    queryset = Client.objects.all()
    if client_id:
        queryset = queryset.exclude(id=client_id)
    exists = queryset.filter(phone=phone).exists()
    return JsonResponse({"exists": exists})

from django.http import JsonResponse


# Удаление клиента
from .models import Client


def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client.delete()
        messages.success(request, 'Клиент успешно удалён!')
        return redirect('clients_list')
    return render(request, 'confirm_delete.html', {
        'object': client,
        'deleted_object_type': 'Client',
        'cancel_url': reverse('clients_list')
    })


# Просмотр списка автомобилей клиента с пагинацией
def client_cars_list(request):
    client_cars = ClientCar.objects.all()
    paginator = Paginator(client_cars, 5)  # Показывать 5 автомобилей на страницу
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except EmptyPage:
        page_obj = paginator.page(1)  # Если страница не найдена, показываем первую страницу
    return render(request, 'clients/client_cars_list.html', {'page_obj': page_obj, 'per_page': 5})


# Создание автомобиля для клиента (одна форма с динамическим выбором модели)
def client_car_create(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        make_id = request.POST.get('make')
        form = ClientCarForm(request.POST, make_id=make_id if make_id else None)
        if form.is_valid():
            client_car = form.save(commit=False)
            client_car.client = client  # Устанавливаем client вручную (для надежности)
            client_car.save()
            messages.success(request, f'Автомобиль успешно создан для клиента {client.fio}!')
            return redirect('client_detail', pk=pk)
        # else:
        #     print("Форма не валидна:", form.errors)  # Отладка
    else:
        form = ClientCarForm(initial={'client': client})  # Задаем начальное значение
    return render(request, 'clients/client_car_create.html', {
        'form': form,
        'client': client,
        'cancel_url': reverse('client_detail', kwargs={'pk': pk})
    })


# # # Получение списка моделей по ID марки (AJAX)
def get_models(request):
    make_id = request.GET.get('make_id')
    if make_id:
        models = CarModel.objects.filter(make_id=make_id).values('id', 'name')
        return JsonResponse(list(models), safe=False)
    return JsonResponse([], safe=False)


def get_all_makes(request):
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 10))
    makes = CarMake.objects.all().order_by('name')
    paginator = Paginator(makes, per_page)
    page_obj = paginator.get_page(page)
    data = {
        'makes': [{'id': make.id, 'name': make.name} for make in page_obj],
        'total_pages': paginator.num_pages,
    }
    return JsonResponse(data)


def get_services(request):
    service_type_id = request.GET.get('service_type_id')
    if service_type_id:
        services = Service.objects.filter(service_type_id=service_type_id).values('id', 'name')
        return JsonResponse(list(services), safe=False)
    return JsonResponse([], safe=False)


@login_required
def get_all_clients(request):
    # Регистрируем кастомную функцию
    register_custom_functions()

    clients = Client.objects.all()

    # Поиск только по fio
    search = request.GET.get('search', '')
    if search:
        search_lower = search.lower()
        clients = clients.extra(
            select={'fio_lower': 'custom_lower(fio)'},
            where=['custom_lower(fio) LIKE %s'],
            params=[f'%{search_lower}%']
        )

    # Пагинация
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 10))
    total_clients = clients.count()
    total_pages = (total_clients + per_page - 1) // per_page

    start = (page - 1) * per_page
    end = start + per_page
    paginated_clients = clients[start:end].values('id', 'fio', 'phone')

    return JsonResponse({
        'clients': list(paginated_clients),
        'total_pages': total_pages
    }, safe=False)

def get_client_cars(request):
    client_id = request.GET.get('client_id')
    if client_id:
        client_cars = ClientCar.objects.filter(client_id=client_id).values('id', 'make__name', 'model__name',
                                                                           'license_plate')
        return JsonResponse(list(client_cars), safe=False)
    return JsonResponse([], safe=False)


def get_services_by_model(request):
    client_car_id = request.GET.get('client_car_id')
    if client_car_id:
        client_car = ClientCar.objects.filter(id=client_car_id).first()
        if client_car:
            services = Service.objects.filter(serviceprice__car_model=client_car.model).values(
                'id', 'name', 'serviceprice__price'
            ).distinct()
            return JsonResponse(list(services), safe=False)
    return JsonResponse([], safe=False)


def get_service_types(request):
    types = ServiceType.objects.all().values('id', 'name')
    return JsonResponse(list(types), safe=False)


def get_services_by_type_and_model(request):
    service_type_id = request.GET.get('service_type_id')
    client_car_id = request.GET.get('client_car_id')
    order_id = request.GET.get('order_id')

    if service_type_id and client_car_id:
        client_car = ClientCar.objects.filter(id=client_car_id).first()
        order = Order.objects.filter(id=order_id).first() if order_id else None

        if client_car:
            services = Service.objects.filter(
                service_type_id=service_type_id,
                serviceprice__car_model=client_car.model
            ).distinct()

            services_list = []
            for service in services:
                service_price = ServicePrice.objects.filter(
                    service=service,
                    car_model=client_car.model
                ).first()
                current_price = service_price.price if service_price else Decimal('0.00')

                if order:
                    order_service = OrderService.objects.filter(
                        order=order,
                        service=service
                    ).first()
                    price_to_use = order_service.price_at_order if order_service else current_price
                    is_in_order = bool(order_service)
                else:
                    price_to_use = current_price
                    is_in_order = False  # Услуга не в заказе, если заказа нет

                services_list.append({
                    'id': service.id,
                    'name': service.name,
                    'price': float(price_to_use),
                    'is_in_order': is_in_order
                })

            return JsonResponse(services_list, safe=False)
    return JsonResponse([], safe=False)


def get_order_services(request):
    order_id = request.GET.get('order_id')
    if order_id:
        service_ids = OrderService.objects.filter(order_id=order_id).values_list('service_id', flat=True)
        return JsonResponse(list(service_ids), safe=False)
    return JsonResponse([], safe=False)


def client_car_detail(request, pk, car_pk):
    client_car = get_object_or_404(ClientCar, pk=car_pk)
    return render(request, 'clients/client_car_detail.html', {
        'client_car': client_car,
        'cancel_url': reverse('client_detail', kwargs={'pk': client_car.client.pk})
    })


def client_car_update(request, pk, car_pk):
    client_car = get_object_or_404(ClientCar, pk=car_pk)
    client = client_car.client  # Получаем клиента из объекта автомобиля
    if request.method == 'POST':
        make_id = request.POST.get('make')
        form = ClientCarForm(request.POST, instance=client_car, make_id=make_id if make_id else None)
        if form.is_valid():
            form.save()
            messages.success(request, 'Автомобиль клиента успешно обновлён!')
            return redirect('client_detail', pk=pk)
        else:
            print("Форма не валидна:", form.errors)  # Отладка
    else:
        form = ClientCarForm(instance=client_car, initial={'client': client})  # Задаем начальное значение client
    return render(request, 'clients/client_car_update.html', {
        'form': form,
        'client': client,
        'cancel_url': reverse('client_detail', kwargs={'pk': pk})
    })


# Удаление автомобиля клиента

def client_car_delete(request, pk, car_pk):
    client_car = get_object_or_404(ClientCar, pk=car_pk)
    client_pk = client_car.client.pk
    if request.method == 'POST':
        client_car.delete()
        messages.success(request, 'Автомобиль клиента успешно удалён!')
        return redirect('client_detail', pk=client_pk)
    return render(request, 'confirm_delete.html', {
        'object': client_car,
        'deleted_object_type': 'ClientCar',
        'cancel_url': reverse('client_detail', kwargs={'pk': client_pk})
    })

@login_required
def car_management(request):
    # Регистрируем функцию один раз для соединения
    register_custom_functions()

    car_makes = CarMake.objects.all()

    # Сортировка
    sort = request.GET.get('sort', 'id')
    direction = request.GET.get('direction', 'asc')
    if sort in ['id', 'name']:
        if direction == 'desc':
            car_makes = car_makes.order_by(f'-{sort}')
        else:
            car_makes = car_makes.order_by(sort)

    # Поиск
    search = request.GET.get('search', '')
    column = request.GET.get('column', 'name')

    if search:
        if column == 'id':
            car_makes = car_makes.filter(id__contains=search)
        elif column == 'name':
            search_lower = search.lower()
            car_makes = car_makes.extra(
                select={'name_lower': 'custom_lower(name)'},
                where=['custom_lower(name) LIKE %s'],
                params=[f'%{search_lower}%']
            )

    # Пагинация
    per_page = request.GET.get('per_page', 5)
    try:
        per_page = int(per_page)
        if per_page not in [5, 10, 20]:
            per_page = 5
    except ValueError:
        per_page = 5

    paginator = Paginator(car_makes, per_page)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except EmptyPage:
        page_obj = paginator.page(1)

    return render(request, 'cars/car_management.html', {
        'page_obj': page_obj,
        'per_page': per_page,
    })


# Создание марки автомобиля
def car_make_create(request):
    if request.method == 'POST':
        form = CarMakeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Марка автомобиля успешно создана!')
            return redirect('car_management')
    else:
        form = CarMakeForm()
    return render(request, 'cars/car_make_create.html', {'form': form, 'cancel_url': reverse('car_management')})


@login_required
def car_make_detail(request, pk):
    register_custom_functions()

    car_make = get_object_or_404(CarMake, pk=pk)
    models = CarModel.objects.filter(make=car_make)

    # Сортировка
    sort = request.GET.get('sort', 'id')
    direction = request.GET.get('direction', 'asc')
    if sort in ['id', 'name']:
        if direction == 'desc':
            models = models.order_by(f'-{sort}')
        else:
            models = models.order_by(sort)

    # Поиск
    search = request.GET.get('search', '')
    column = request.GET.get('column', 'name')

    if search:
        if column == 'id':
            models = models.filter(id__contains=search)
        elif column == 'name':
            search_lower = search.lower()
            models = models.extra(
                select={'name_lower': 'custom_lower(name)'},
                where=['custom_lower(name) LIKE %s'],
                params=[f'%{search_lower}%']
            )

    # Пагинация
    per_page = request.GET.get('per_page', 5)
    try:
        per_page = int(per_page)
        if per_page not in [5, 10, 20]:
            per_page = 5
    except ValueError:
        per_page = 5

    paginator = Paginator(models, per_page)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except EmptyPage:
        page_obj = paginator.page(1)

    return render(request, 'cars/car_make_detail.html', {
        'car_make': car_make,
        'page_obj': page_obj,
        'per_page': per_page,
        'cancel_url': reverse('car_make_detail', kwargs={'pk': pk})
    })

# Редактирование марки автомобиля
def car_make_update(request, pk):
    car_make = get_object_or_404(CarMake, pk=pk)
    if request.method == 'POST':
        form = CarMakeForm(request.POST, instance=car_make)
        if form.is_valid():
            form.save()
            messages.success(request, 'Марка автомобиля успешно обновлена!')
            return redirect('car_management')
    else:
        form = CarMakeForm(instance=car_make)
    return render(request, 'cars/car_make_update.html',
                  {'form': form, 'cancel_url': reverse('car_make_detail', kwargs={'pk': pk})})


# Удаление марки автомобиля


def car_make_delete(request, pk):
    car_make = get_object_or_404(CarMake, pk=pk)
    if request.method == 'POST':
        car_make.delete()
        messages.success(request, 'Марка автомобиля успешно удалена!')
        return redirect('car_management')
    return render(request, 'confirm_delete.html', {
        'object': car_make,
        'deleted_object_type': 'CarMake',
        'cancel_url': reverse('car_management')
    })


# Создание модели автомобиля для конкретной марки (без выпадающего списка марок)
def car_model_create(request, make_pk):
    car_make = get_object_or_404(CarMake, pk=make_pk)
    if request.method == 'POST':
        form = CarModelForm(request.POST)
        if form.is_valid():
            car_model = form.save(commit=False)
            car_model.make = car_make
            car_model.save()
            messages.success(request, f'Модель автомобиля успешно создана для марки {car_make.name}!')
            return redirect('car_make_detail', pk=make_pk)
    else:
        form = CarModelForm(initial={'make': car_make})
    return render(request, 'cars/car_model_create.html', {
        'form': form,
        'car_make': car_make,
        'cancel_url': reverse('car_make_detail', kwargs={'pk': make_pk})
    })


# Просмотр деталей модели автомобиля
def car_model_detail(request, pk):
    car_model = get_object_or_404(CarModel, pk=pk)
    return render(request, 'cars/car_model_detail.html',
                  {'car_model': car_model, 'cancel_url': reverse('car_make_detail', kwargs={'pk': car_model.make.pk})})


# Редактирование модели автомобиля
def car_model_update(request, pk):
    car_model = get_object_or_404(CarModel, pk=pk)
    if request.method == 'POST':
        form = CarModelForm(request.POST, instance=car_model)
        if form.is_valid():
            form.save()
            messages.success(request, 'Модель автомобиля успешно обновлена!')
            return redirect('car_make_detail', pk=car_model.make.pk)
    else:
        form = CarModelForm(instance=car_model)
    return render(request, 'cars/car_model_update.html', {
        'form': form,
        'car_make': car_model.make,
        'cancel_url': reverse('car_make_detail', kwargs={'pk': car_model.make.pk})
    })


# Удаление модели автомобиля


def car_model_delete(request, pk):
    car_model = get_object_or_404(CarModel, pk=pk)
    make_pk = car_model.make.pk
    if request.method == 'POST':
        car_model.delete()
        messages.success(request, 'Модель автомобиля успешно удалена!')
        return redirect('car_make_detail', pk=make_pk)
    return render(request, 'confirm_delete.html', {
        'object': car_model,
        'deleted_object_type': 'CarModel',
        'cancel_url': reverse('car_make_detail', kwargs={'pk': make_pk})
    })



@login_required
def service_management(request):
    # Регистрируем кастомную функцию для регистронезависимого поиска
    register_custom_functions()

    service_types = ServiceType.objects.all()

    # Сортировка
    sort = request.GET.get('sort', 'id')
    direction = request.GET.get('direction', 'asc')
    if sort in ['id', 'name']:
        if direction == 'desc':
            service_types = service_types.order_by(f'-{sort}')
        else:
            service_types = service_types.order_by(sort)

    # Поиск
    search = request.GET.get('search', '')
    column = request.GET.get('column', 'name')
    if search:
        if column == 'id':
            service_types = service_types.filter(id__contains=search)
        elif column == 'name':
            search_lower = search.lower()
            service_types = service_types.extra(
                select={'name_lower': 'custom_lower(name)'},
                where=['custom_lower(name) LIKE %s'],
                params=[f'%{search_lower}%']
            )

    # Пагинация
    per_page = request.GET.get('per_page', 5)
    try:
        per_page = int(per_page)
        if per_page not in [5, 10, 20]:
            per_page = 5
    except ValueError:
        per_page = 5

    paginator = Paginator(service_types, per_page)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except EmptyPage:
        page_obj = paginator.page(1)

    return render(request, 'services/service_management.html', {
        'page_obj': page_obj,
        'per_page': per_page
    })


# Создание типа услуги
def service_type_create(request):
    if request.method == 'POST':
        form = ServiceTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Тип услуги успешно создан!')
            return redirect('service_management')
    else:
        form = ServiceTypeForm()
    return render(request, 'services/service_type_create.html',
                  {'form': form, 'cancel_url': reverse('service_management')})


# Просмотр деталей типа услуги (с таблицей услуг и пагинацией)
@login_required
def service_type_detail(request, pk):
    # Регистрируем функцию один раз для соединения
    register_custom_functions()

    service_type = get_object_or_404(ServiceType, pk=pk)
    services = Service.objects.filter(service_type=service_type)

    # Сортировка
    sort = request.GET.get('sort', 'id')
    direction = request.GET.get('direction', 'asc')
    if sort in ['id', 'name']:
        if direction == 'desc':
            services = services.order_by(f'-{sort}')
        else:
            services = services.order_by(sort)

    # Поиск
    search = request.GET.get('search', '')
    column = request.GET.get('column', 'name')

    if search:
        if column == 'id':
            services = services.filter(id__contains=search)
        elif column == 'name':
            search_lower = search.lower()
            services = services.extra(
                select={'name_lower': 'custom_lower(name)'},
                where=['custom_lower(name) LIKE %s'],
                params=[f'%{search_lower}%']
            )

    # Пагинация
    per_page = request.GET.get('per_page', 5)
    try:
        per_page = int(per_page)
        if per_page not in [5, 10, 20]:
            per_page = 5
    except ValueError:
        per_page = 5

    paginator = Paginator(services, per_page)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except EmptyPage:
        page_obj = paginator.page(1)

    return render(request, 'services/service_type_detail.html', {
        'service_type': service_type,
        'page_obj': page_obj,
        'per_page': per_page,
        'cancel_url': reverse('service_management')
    })
# Редактирование типа услуги
def service_type_update(request, pk):
    service_type = get_object_or_404(ServiceType, pk=pk)
    if request.method == 'POST':
        form = ServiceTypeForm(request.POST, instance=service_type)
        if form.is_valid():
            form.save()
            messages.success(request, 'Тип услуги успешно обновлён!')
            return redirect('service_management')
    else:
        form = ServiceTypeForm(instance=service_type)
    return render(request, 'services/service_type_update.html',
                  {'form': form, 'cancel_url': reverse('service_management')})


# Удаление типа услуги
from .models import ServiceType


def service_type_delete(request, pk):
    service_type = get_object_or_404(ServiceType, pk=pk)
    if request.method == 'POST':
        service_type.delete()
        messages.success(request, 'Тип услуги успешно удалён!')
        return redirect('service_management')
    return render(request, 'confirm_delete.html', {
        'object': service_type,
        'deleted_object_type': 'ServiceType',
        'cancel_url': reverse('service_management')
    })


# Создание конкретной услуги для типа услуги
def service_create(request, pk):  # Изменил type_pk на pk
    service_type = get_object_or_404(ServiceType, pk=pk)
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.service_type = service_type
            service.save()
            messages.success(request, f'Услуга "{service.name}" успешно создана для типа {service_type.name}!')
            return redirect('service_type_detail', pk=pk)
    else:
        form = ServiceForm(initial={'service_type': service_type})
    return render(request, 'services/service_create.html', {
        'form': form,
        'service_type': service_type,
        'cancel_url': reverse('service_type_detail', kwargs={'pk': pk})
    })


# Просмотр деталей услуги
def service_detail(request, pk, service_pk):  # Изменил type_pk на pk для соответствия маршруту
    service = get_object_or_404(Service, pk=service_pk)  # Используем service_pk для получения услуги
    return render(request, 'services/service_detail.html',
                  {'service': service, 'cancel_url': reverse('service_type_detail', kwargs={'pk': pk})})


# Удаление услуги

def service_delete(request, pk, service_pk):
    service = get_object_or_404(Service, pk=service_pk)
    if request.method == 'POST':
        service.delete()
        messages.success(request, 'Услуга успешно удалена!')
        return redirect('service_type_detail', pk=pk)
    return render(request, 'confirm_delete.html', {
        'object': service,
        'deleted_object_type': 'Service',
        'cancel_url': reverse('service_type_detail', kwargs={'pk': pk})
    })


# Редактирование услуги
def service_update(request, pk, service_pk):  # Изменил на pk (ID типа услуги) и service_pk (ID услуги)
    service = get_object_or_404(Service, pk=service_pk)  # Используем service_pk для получения услуги
    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, 'Услуга успешно обновлена!')
            return redirect('service_type_detail', pk=pk)  # Используем pk для возврата к типу услуги
    else:
        form = ServiceForm(instance=service)
    return render(request, 'services/service_update.html', {
        'form': form,
        'service_type': service.service_type,  # Передаём тип услуги для контекста
        'cancel_url': reverse('service_type_detail', kwargs={'pk': pk})
    })


import logging

from .models import CarMake, CarModel



from django.contrib.auth.decorators import login_required



@login_required
def services_by_car(request):
    register_custom_functions()

    selected_car_model_id = request.GET.get('car_model_id', '')
    search = request.GET.get('search', '')
    sort = request.GET.get('sort', 'service__name')
    direction = request.GET.get('direction', 'asc')
    per_page = request.GET.get('per_page', 10)
    reset = request.GET.get('reset', False)

    if reset:
        selected_car_model_id = ''

    services = ServicePrice.objects.select_related('service', 'car_model', 'car_make', 'service__service_type')
    if selected_car_model_id:
        services = services.filter(car_model_id=selected_car_model_id)

    if search:
        search_lower = search.lower()
        services = services.extra(
            select={'service_lower': 'custom_lower(mainapp_service.name)'},
            tables=['mainapp_service'],
            where=[
                'mainapp_service.id = mainapp_serviceprice.service_id',
                'custom_lower(mainapp_service.name) LIKE %s'
            ],
            params=[f'%{search_lower}%']
        )

    valid_sort_fields = ['service__name', 'price', 'car_model__name', 'car_make__name']
    if sort in valid_sort_fields:
        order_field = f'-{sort}' if direction == 'desc' else sort
        services = services.order_by(order_field)
    else:
        services = services.order_by('service__name')

    try:
        per_page = int(per_page)
        if per_page not in [5, 10, 20]:
            per_page = 10
    except ValueError:
        per_page = 10

    paginator = Paginator(services, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'selected_car_model_id': selected_car_model_id,
        'page_obj': page_obj,
        'per_page': per_page,
        'search': search,
        'sort': sort,
        'direction': direction,
    }
    return render(request, 'services/service_by_car.html', context)


from django.contrib.auth.decorators import login_required
from django.db import connection




@login_required
def price_management(request):
    # Регистрируем функцию для регистронезависимого поиска
    register_custom_functions()

    service_prices = ServicePrice.objects.select_related('car_make', 'car_model', 'service')

    # Сортировка
    sort = request.GET.get('sort', 'id')
    direction = request.GET.get('direction', 'asc')
    valid_sort_fields = ['id', 'car_make__name', 'car_model__name', 'service__name', 'price']
    if sort in valid_sort_fields:
        order_field = f'-{sort}' if direction == 'desc' else sort
        service_prices = service_prices.order_by(order_field)
    else:
        service_prices = service_prices.order_by('id')

    # Поиск
    search = request.GET.get('search', '')
    column = request.GET.get('column', 'car_make')
    if search:
        search_lower = search.lower()
        if column == 'id':
            service_prices = service_prices.filter(id__contains=search)
        elif column == 'car_make':
            service_prices = service_prices.extra(
                select={'car_make_lower': 'custom_lower(mainapp_carmake.name)'},
                tables=['mainapp_carmake'],
                where=[
                    'mainapp_carmake.id = mainapp_serviceprice.car_make_id',
                    'custom_lower(mainapp_carmake.name) LIKE %s'
                ],
                params=[f'%{search_lower}%']
            )
        elif column == 'car_model':
            service_prices = service_prices.extra(
                select={'car_model_lower': 'custom_lower(mainapp_carmodel.name)'},
                tables=['mainapp_carmodel'],
                where=[
                    'mainapp_carmodel.id = mainapp_serviceprice.car_model_id',
                    'custom_lower(mainapp_carmodel.name) LIKE %s'
                ],
                params=[f'%{search_lower}%']
            )
        elif column == 'service':
            service_prices = service_prices.extra(
                select={'service_lower': 'custom_lower(mainapp_service.name)'},
                tables=['mainapp_service'],
                where=[
                    'mainapp_service.id = mainapp_serviceprice.service_id',
                    'custom_lower(mainapp_service.name) LIKE %s'
                ],
                params=[f'%{search_lower}%']
            )

    # Пагинация
    per_page = request.GET.get('per_page', 5)
    try:
        per_page = int(per_page)
        if per_page not in [5, 10, 20]:
            per_page = 5
    except ValueError:
        per_page = 5

    paginator = Paginator(service_prices, per_page)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except EmptyPage:
        page_obj = paginator.page(1)

    return render(request, 'prices/price_management.html', {
        'page_obj': page_obj,
        'per_page': per_page
    })

# Создание цены на услугу для модели автомобиля
def price_create(request):
    if request.method == 'POST':
        form = ServicePriceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Цена на услугу успешно создана!')
            return redirect('price_management')
    else:
        form = ServicePriceForm()
    return render(request, 'prices/price_create.html', {'form': form, 'cancel_url': reverse('price_management')})


# Просмотр деталей цены на услугу
def price_detail(request, pk):
    service_price = get_object_or_404(ServicePrice, pk=pk)
    return render(request, 'prices/price_detail.html',
                  {'service_price': service_price, 'cancel_url': reverse('price_management')})


def price_update(request, pk):
    service_price = get_object_or_404(ServicePrice, pk=pk)
    if request.method == 'POST':
        form = ServicePriceForm(request.POST, instance=service_price)
        if form.is_valid():
            form.save()
            messages.success(request, 'Цена на услугу успешно обновлена!')
            return redirect('price_management')
    else:
        form = ServicePriceForm(instance=service_price)
    return render(request, 'prices/price_update.html', {
        'form': form,
        'cancel_url': reverse('price_management')
    })


# Удаление цены на услугу

def price_delete(request, pk):
    service_price = get_object_or_404(ServicePrice, pk=pk)
    if request.method == 'POST':
        service_price.delete()
        messages.success(request, 'Цена на услугу успешно удалена!')
        return redirect('price_management')
    return render(request, 'confirm_delete.html', {
        'object': service_price,
        'deleted_object_type': 'ServicePrice',
        'cancel_url': reverse('price_management')
    })


from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage


from django.core.paginator import Paginator, EmptyPage
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Order

@login_required
def orders_list(request):
    # Регистрируем функцию для регистронезависимого поиска
    register_custom_functions()

    orders = Order.objects.all()

    # Сортировка
    sort = request.GET.get('sort', 'id')
    direction = request.GET.get('direction', 'desc')
    valid_sort_fields = ['id', 'client_fio_static', 'car_details_static', 'order_date', 'status']

    if sort == 'client_fio_static':
        # Регистронезависимая сортировка по ФИО
        orders = orders.extra(select={'client_lower': 'custom_lower(client_fio_static)'}).order_by(
            f"{'-' if direction == 'desc' else ''}client_lower"
        )
    elif sort == 'car_details_static':
        # Регистронезависимая сортировка по авто
        orders = orders.extra(select={'car_lower': 'custom_lower(car_details_static)'}).order_by(
            f"{'-' if direction == 'desc' else ''}car_lower"
        )
    elif sort in valid_sort_fields:
        # Обычная сортировка по остальным полям
        orders = orders.order_by(f'-{sort}' if direction == 'desc' else sort)

    # Поиск
    search = request.GET.get('search', '')
    column = request.GET.get('column', 'client')

    if search:
        search_lower = search.lower()
        if column == 'id':
            orders = orders.filter(id__contains=search)
        elif column == 'client':
            orders = orders.extra(
                select={'client_lower': 'custom_lower(client_fio_static)'},
                where=['custom_lower(client_fio_static) LIKE %s'],
                params=[f'%{search_lower}%']
            )
        elif column == 'car':
            orders = orders.extra(
                select={'car_lower': 'custom_lower(car_details_static)'},
                where=['custom_lower(car_details_static) LIKE %s'],
                params=[f'%{search_lower}%']
            )

    # Пагинация
    per_page = request.GET.get('per_page', 5)
    try:
        per_page = int(per_page)
        if per_page not in [5, 10, 20]:
            per_page = 5
    except ValueError:
        per_page = 5

    paginator = Paginator(orders, per_page)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except EmptyPage:
        page_obj = paginator.page(1)

    return render(request, 'orders/orders_list.html', {
        'page_obj': page_obj,
        'per_page': per_page,
    })

from .models import OrderService, CustomService, Service, ServicePrice, ClientCar
from .forms import ClientSelectionForm, OrderForm, CustomServiceForm


def order_create(request):
    if request.method == 'POST':
        print("POST data:", request.POST)  # Выводим все данные POST для отладки
        client_form = ClientSelectionForm(request.POST)
        order_form = OrderForm(request.POST)

        if client_form.is_valid() and order_form.is_valid():
            # Сохраняем заказ
            order = order_form.save(commit=False)
            total_cost = request.POST.get('total_cost', '0.00')  # Получаем стоимость из формы
            order.cost = Decimal(total_cost)  # Сохраняем стоимость в поле cost
            order.save()

            # Получаем выбранные услуги из POST
            selected_service_ids = request.POST.getlist('selected_services')
            client_car = order.client_car  # Получаем автомобиль клиента из заказа

            # Обрабатываем выбранные услуги
            for service_id in selected_service_ids:
                try:
                    service = Service.objects.get(id=service_id)
                    # Получаем цену услуги для модели автомобиля
                    service_price = ServicePrice.objects.get(
                        car_model=client_car.model,
                        service=service
                    )
                    # Создаём запись в OrderService с ценой на момент заказа
                    OrderService.objects.create(
                        order=order,
                        service=service,
                        price_at_order=service_price.price
                    )
                except Service.DoesNotExist:
                    print(f"Услуга с ID {service_id} не найдена")
                    continue
                except ServicePrice.DoesNotExist:
                    print(f"Цена для услуги {service.name} и модели {client_car.model} не найдена")
                    # Создаём запись без цены, если её нет в ServicePrice
                    OrderService.objects.create(
                        order=order,
                        service=service,
                        price_at_order=None
                    )
                    continue

            # Обрабатываем кастомные услуги
            custom_names = request.POST.getlist('custom_service_name[]')
            custom_prices = request.POST.getlist('custom_service_price[]')
            for name, price in zip(custom_names, custom_prices):
                if name and price:  # Проверяем, что поля заполнены
                    CustomService.objects.create(
                        order=order,
                        name=name,
                        price=Decimal(price)
                    )

            messages.success(request, 'Заказ успешно создан!')
            return redirect('orders_list')
        else:
            print("Client form errors:", client_form.errors)
            print("Order form errors:", order_form.errors)
    else:
        client_form = ClientSelectionForm()
        order_form = OrderForm()

    custom_service_form = CustomServiceForm()
    return render(request, 'orders/order_create.html', {
        'client_form': client_form,
        'order_form': order_form,
        'custom_service_form': custom_service_form,
        'cancel_url': reverse('orders_list')
    })


def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if order.status != 'Завершён':
        standard_services_cost = OrderService.objects.filter(order=order).aggregate(
            total=Sum('price_at_order')
        )['total'] or Decimal('0.00')

        custom_services_cost = CustomService.objects.filter(order=order).aggregate(
            total=Sum('price')
        )['total'] or Decimal('0.00')

        recalculated_cost = standard_services_cost + custom_services_cost
        order.cost = recalculated_cost
        order.save()  # Сохраняем пересчитанную стоимость в БД

    return render(request, 'orders/order_detail.html', {'order': order})


from django.db.models import Sum
from decimal import Decimal
import json


def order_update(request, pk):
    order = get_object_or_404(Order, pk=pk)

    # Проверяем, завершён ли заказ
    if order.status == 'Завершён':
        messages.error(request, 'Редактирование завершённого заказа запрещено.')
        return redirect('order_detail', pk=pk)

    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            order = form.save(commit=False)  # Не сохраняем сразу

            # Получаем выбранные услуги
            selected_service_ids = request.POST.getlist('selected_services')
            print(f"Selected service IDs in update: {selected_service_ids}")

            # Удаляем только те услуги, которые больше не выбраны
            current_service_ids = [str(service.service.id) for service in order.orderservice_set.all()]
            services_to_remove = set(current_service_ids) - set(selected_service_ids)
            OrderService.objects.filter(order=order, service__id__in=services_to_remove).delete()

            # Обрабатываем выбранные услуги
            services_data = []  # Для статичного хранения
            for service_id in selected_service_ids:
                try:
                    service = Service.objects.get(id=service_id)
                    order_service, created = OrderService.objects.get_or_create(
                        order=order,
                        service=service,
                    )
                    if created:
                        service_price = ServicePrice.objects.filter(
                            service=service,
                            car_model=order.client_car.model
                        ).first()
                        order_service.price_at_order = service_price.price if service_price else Decimal('0.00')
                        order_service.save()
                        print(f"Новая услуга {service.name}: price_at_order = {order_service.price_at_order}")
                    else:
                        print(f"Существующая услуга {service.name}: price_at_order = {order_service.price_at_order}")
                    # Собираем данные для статичного хранения
                    services_data.append(
                        f"{service.service_type.name}: {service.name} ({order_service.price_at_order})")
                except Service.DoesNotExist:
                    print(f"Услуга с ID {service_id} не найдена")
                    continue
                except ServicePrice.DoesNotExist:
                    print(f"Цена для услуги {service.name} не найдена")
                    if created:
                        order_service.price_at_order = Decimal('0.00')
                        order_service.save()

            # Обрабатываем кастомные услуги
            custom_names = request.POST.getlist('custom_service_name[]')
            custom_prices = request.POST.getlist('custom_service_price[]')
            CustomService.objects.filter(order=order).delete()
            custom_services_data = []  # Для статичного хранения
            for name, price in zip(custom_names, custom_prices):
                if name and price:
                    CustomService.objects.create(order=order, name=name, price=Decimal(price))
                    custom_services_data.append(f"{name} ({price})")

            # Расчет общей стоимости
            service_cost = sum(
                Decimal(str(service.price_at_order or Decimal('0.00')))
                for service in order.orderservice_set.all()
            )
            custom_cost = CustomService.objects.filter(order=order).aggregate(Sum('price'))['price__sum'] or Decimal(
                '0.00')
            order.cost = service_cost + custom_cost

            # Если статус "Завершён", сохраняем статичные данные
            if form.cleaned_data['status'] == 'Завершён':
                order.client_fio_static = order.client_car.client.fio
                order.car_details_static = f"{order.client_car.make.name} {order.client_car.model.name} ({order.client_car.license_plate or ''})"
                order.services_static = "; ".join(services_data) if services_data else "Нет услуг"
                order.custom_services_static = "; ".join(
                    custom_services_data) if custom_services_data else "Нет кастомных услуг"

            order.save()
            messages.success(request, 'Заказ успешно обновлен!')
            return redirect('order_detail', pk=pk)
    else:
        form = OrderForm(instance=order)

    # Подготовка данных для отображения
    service_dict = {}
    for order_service in order.orderservice_set.all():
        service = order_service.service
        price = order_service.price_at_order if order_service.price_at_order is not None else (
            ServicePrice.objects.filter(
                service=service,
                car_model=order.client_car.model
            ).first().price if ServicePrice.objects.filter(
                service=service,
                car_model=order.client_car.model
            ).exists() else Decimal('0.00')
        )
        service_dict[service.id] = {
            'id': service.id,
            'name': service.name,
            'price': float(price),
            'type': service.service_type.name,
            'typeId': service.service_type.id
        }

    selected_services = list(service_dict.values())
    services_with_prices = [
        {
            'id': s['id'],
            'type_name': s['type'],
            'name': s['name'],
            'price': Decimal(str(s['price']))
        } for s in selected_services
    ]

    return render(request, 'orders/order_update.html', {
        'order_form': form,
        'order': order,
        'cancel_url': reverse('order_detail', kwargs={'pk': pk}),
        'selected_services_json': json.dumps(selected_services),
        'services_with_prices': services_with_prices
    })






from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Order


def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        order.delete()
        messages.success(request, 'Заказ успешно удалён!')
        return redirect('orders_list')
    return render(request, 'confirm_delete.html', {
        'object': order,
        'deleted_object_type': 'Order',
        'cancel_url': reverse('orders_list')
    })

from django.shortcuts import render

def help_page(request):
    return render(request, 'help/help.html')

# Кастомный декоратор для проверки прав администратора
def staff_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, "У вас нет прав для выполнения этого действия.")
            return redirect('orders_list')  # Перенаправляем не-админов на список заказов
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required  # Требует авторизацию
@staff_required
def export_db(request):
    buffer = StringIO()
    call_command('dumpdata', stdout=buffer, natural_foreign=True, natural_primary=True)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="full_db_export.json"'
    return response


from django.http import HttpResponse
from django.contrib import messages
from django.db import transaction
from django.core.management import call_command
from django.apps import apps
import tempfile
import os
from io import StringIO

@login_required
@staff_required
def import_db(request):
    if request.method == 'POST':
        if 'db_file' in request.FILES:
            db_file = request.FILES['db_file']
            try:
                # Читаем содержимое файла как байты
                raw_data = db_file.read()

                # Определяем кодировку
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                confidence = result['confidence']

                if encoding is None or confidence < 0.5:
                    messages.error(request, 'Не удалось определить кодировку файла.')
                    return redirect('orders_list')

                # Декодируем данные с определённой кодировкой
                try:
                    json_data = raw_data.decode(encoding)
                except UnicodeDecodeError:
                    # Попробуем Windows-1251 как запасной вариант
                    try:
                        json_data = raw_data.decode('windows-1251')
                    except UnicodeDecodeError as e:
                        messages.error(request, f'Ошибка декодирования файла: {str(e)}')
                        return redirect('orders_list')

                # Очищаем базу данных перед загрузкой
                with transaction.atomic():
                    all_models = [model for model in apps.get_models() if model._meta.app_label != 'contenttypes']
                    for model in all_models:
                        if model._meta.db_table != 'django_migrations':
                            model.objects.all().delete()

                # Создаём временный файл в UTF-8
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
                    temp_file.write(json_data)
                    temp_file_path = temp_file.name

                try:
                    # Загружаем данные из временного файла
                    call_command('loaddata', temp_file_path, format='json', verbosity=0)
                    messages.success(request, 'База данных успешно импортирована и полностью перезаписана!')
                finally:
                    # Удаляем временный файл
                    os.remove(temp_file_path)

            except Exception as e:
                messages.error(request, f'Ошибка при импорте: {str(e)}')
            return redirect('orders_list')
    return render(request, 'import_db.html', {'cancel_url': request.META.get('HTTP_REFERER', '/')})
