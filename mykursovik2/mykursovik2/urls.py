from django.contrib import admin
from django.urls import path, include
from mainapp import views  # Импортируем views из приложения mainapp

urlpatterns = [
    # Админка
    path('admin/', admin.site.urls),

    # Главная страница (список заказов)
    path('', views.orders_list, name='home'),

    # Заказы
    path('orders/', views.orders_list, name='orders_list'),
    path('orders/create/', views.order_create, name='order_create'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/update/', views.order_update, name='order_update'),
    path('orders/<int:pk>/delete/', views.order_delete, name='order_delete'),
    path('api/get_client_cars/', views.get_client_cars, name='get_client_cars'),
    path('api/get_services_by_model/', views.get_services_by_model, name='get_services_by_model'),

    # Клиенты
    path('clients/', views.clients_list, name='clients_list'),
    path('clients/create/', views.client_create, name='client_create'),
    path('clients/<int:pk>/', views.client_detail, name='client_detail'),
    path('clients/<int:pk>/update/', views.client_update, name='client_update'),
    path('clients/<int:pk>/delete/', views.client_delete, name='client_delete'),
    path('clients/<int:pk>/cars/', views.client_cars_list, name='client_cars_list'),
    path('clients/<int:pk>/cars/create/', views.client_car_create, name='client_car_create'),
    # Оставляем pk для consistency
    path('clients/<int:pk>/cars/<int:car_pk>/', views.client_car_detail, name='client_car_detail'),
    path('clients/<int:pk>/cars/<int:car_pk>/update/', views.client_car_update, name='client_car_update'),
    path('clients/<int:pk>/cars/<int:car_pk>/delete/', views.client_car_delete, name='client_car_delete'),
    path('api/get_models/', views.get_models, name='get_models'),  # Новый маршрут для AJAX
    path('api/get_services/', views.get_services, name='get_services'),
    path('api/get_order_services/', views.get_order_services, name='get_order_services'),
    path('api/get_all_clients/', views.get_all_clients, name='get_all_clients'),
    path('api/get_service_types/', views.get_service_types, name='get_service_types'),
    path('api/gt_all_makes/', views.get_all_makes, name='get_all_makes'),
    path('api/get_services_by_type_and_model/', views.get_services_by_type_and_model,
         name='get_services_by_type_and_model'),

    # Марки и модели автомобилей
    path('cars/', views.car_management, name='car_management'),
    path('cars/makes/create/', views.car_make_create, name='car_make_create'),
    path('cars/makes/<int:pk>/', views.car_make_detail, name='car_make_detail'),
    path('cars/makes/<int:pk>/update/', views.car_make_update, name='car_make_update'),
    path('cars/makes/<int:pk>/delete/', views.car_make_delete, name='car_make_delete'),
    path('cars/models/create/<int:make_pk>/', views.car_model_create, name='car_model_create'),
    path('cars/models/<int:pk>/', views.car_model_detail, name='car_model_detail'),
    path('cars/models/<int:pk>/update/', views.car_model_update, name='car_model_update'),
    path('cars/models/<int:pk>/delete/', views.car_model_delete, name='car_model_delete'),

    # Услуги
    path('services/', views.service_management, name='service_management'),
    path('services/types/create/', views.service_type_create, name='service_type_create'),
    path('services/types/<int:pk>/', views.service_type_detail, name='service_type_detail'),
    path('services/types/<int:pk>/update/', views.service_type_update, name='service_type_update'),
    path('services/types/<int:pk>/delete/', views.service_type_delete, name='service_type_delete'),
    path('services/types/<int:pk>/services/create/', views.service_create, name='service_create'),
    path('services/types/<int:pk>/services/<int:service_pk>/', views.service_detail, name='service_detail'),
    path('services/types/<int:pk>/services/<int:service_pk>/update/', views.service_update, name='service_update'),
    path('services/types/<int:pk>/services/<int:service_pk>/delete/', views.service_delete, name='service_delete'),

    # Цены на услуги
    path('prices/', views.price_management, name='price_management'),
    path('prices/create/', views.price_create, name='price_create'),
    path('prices/<int:pk>/', views.price_detail, name='price_detail'),
    path('prices/<int:pk>/update/', views.price_update, name='price_update'),
    path('prices/<int:pk>/delete/', views.price_delete, name='price_delete'),
    # path('prices/', views.price_management_dynamic, name='price_management_dynamic'),  # Обновлённый маршрут
    # path('prices/update/', views.update_price, name='update_price'),  # Новый маршрут для AJAX
    path('check-vin-uniqueness/', views.check_vin_uniqueness, name='check_vin_uniqueness'),
    path('check-license-plate-uniqueness/', views.check_license_plate_uniqueness,
         name='check_license_plate_uniqueness'),
    path('check-service-type-uniqueness/', views.check_service_type_uniqueness, name='check_service_type_uniqueness'),
    path('check-service-uniqueness/', views.check_service_uniqueness, name='check_service_uniqueness'),
    path('check-car-make-uniqueness/', views.check_car_make_uniqueness, name='check_car_make_uniqueness'),
    path('check-car-model-uniqueness/', views.check_car_model_uniqueness, name='check_car_model_uniqueness'),
    path('check-client-phone-uniqueness/', views.check_client_phone_uniqueness, name='check_client_phone_uniqueness'),

    path('services-by-car/', views.services_by_car, name='services_by_car'),

    # База данных
    path('export/', views.export_db, name='export_db'),
    path('import/', views.import_db, name='import_db'),

    # Аутентификация (login/logout)
    path('accounts/', include('accounts.urls')),
    path('help/', views.help_page, name='help_page'),

    # Склад
    path('warehouse/', include('warehouse.urls')),
]
