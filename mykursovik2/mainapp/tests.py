import json
from django.test import TestCase
from django.test import Client as TestClient
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Client, ClientCar, CarMake, CarModel, Order, ServiceType, Service, ServicePrice
from django.utils import timezone

class ClientModuleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = TestClient()
        self.client.login(username='testuser', password='testpass')

        self.car_make = CarMake.objects.create(name="Toyota")
        self.car_model = CarModel.objects.create(make=self.car_make, name="Camry")
        self.client_obj = Client.objects.create(fio="Иванов Иван", phone="+7 (999) 123-45-67")
        self.client_car = ClientCar.objects.create(
            client=self.client_obj,
            make=self.car_make,
            model=self.car_model,
            license_plate="А123АА77",
            color="Белый",
            vin="1HGCM82633A004352",
            year=2020
        )

    def test_client_create_success(self):
        response = self.client.post(reverse('client_create'), {
            'fio': 'Петров Петр',
            'phone': '+7 (999) 123-45-68'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Client.objects.filter(fio='Петров Петр').exists())

    def test_client_create_duplicate_phone(self):
        response = self.client.post(reverse('client_create'), {
            'fio': 'Сидоров Сидор',
            'phone': '+7 (999) 123-45-67'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Клиент с таким номером телефона уже существует')

    def test_client_update_success(self):
        response = self.client.post(reverse('client_update', args=[self.client_obj.id]), {
            'fio': 'Иванов Сергей',
            'phone': '+7 (999) 123-45-67'
        })
        self.assertEqual(response.status_code, 302)
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.fio, 'Иванов Сергей')

    def test_client_delete_success(self):
        order_in_progress = Order.objects.create(
            client_car=self.client_car,
            status='В работе',
            order_date=timezone.now().date()
        )
        order_completed = Order.objects.create(
            client_car=self.client_car,
            status='Завершён',
            order_date=timezone.now().date()
        )
        response = self.client.post(reverse('client_delete', args=[self.client_obj.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Client.objects.filter(id=self.client_obj.id).exists())
        self.assertFalse(ClientCar.objects.filter(id=self.client_car.id).exists())
        self.assertFalse(Order.objects.filter(id=order_in_progress.id).exists())
        self.assertTrue(Order.objects.filter(id=order_completed.id).exists())
        self.assertIsNone(Order.objects.get(id=order_completed.id).client_car)

    def test_client_car_create_success(self):
        response = self.client.post(reverse('client_car_create', args=[self.client_obj.id]), {
            'client': self.client_obj.id,
            'make': self.car_make.id,
            'model': self.car_model.id,
            'license_plate': 'А456АА78',
            'color': 'Чёрный',
            'vin': '2HGCM82633A004353',
            'year': 2021
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ClientCar.objects.filter(license_plate='А456АА78').exists())

    def test_client_car_duplicate_license_plate(self):
        response = self.client.post(reverse('client_car_create', args=[self.client_obj.id]), {
            'client': self.client_obj.id,
            'make': self.car_make.id,
            'model': self.car_model.id,
            'license_plate': 'А123АА77',
            'color': 'Чёрный',
            'vin': '2HGCM82633A004353',
            'year': 2021
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'А123АА77')
        self.assertFalse(ClientCar.objects.filter(license_plate='А123АА77').count() > 1)

    def test_check_client_phone_uniqueness(self):
        response = self.client.post(reverse('check_client_phone_uniqueness'), {
            'phone': '+7 (999) 123-45-67'
        })
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'exists': True})

        response = self.client.post(reverse('check_client_phone_uniqueness'), {
            'phone': '+7 (999) 123-45-68'
        })
        self.assertJSONEqual(response.content, {'exists': False})

    def test_clients_list(self):
        response = self.client.get(reverse('clients_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Иванов Иван')