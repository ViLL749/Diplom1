import json
from decimal import Decimal
from django.test import TestCase
from django.test import Client as TestClient
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Client, ClientCar, CarMake, CarModel, Order, ServiceType, Service
from accounts.models import UserProfile


# ─── helpers ──────────────────────────────────────────────────────────────────

def make_user(role='manager'):
    user = User.objects.create_user(username='testuser', password='testpass')
    UserProfile.objects.create(user=user, role=role, elevated_access=True)
    return user


def make_base_car_objects():
    make  = CarMake.objects.create(name='Toyota')
    model = CarModel.objects.create(make=make, name='Camry')
    return make, model


def make_client_with_car(make, model):
    client = Client.objects.create(fio='Тестов Тест Тестович', phone='+7 999 100-00-01')
    car    = ClientCar.objects.create(
        client=client, make=make, model=model,
        license_plate='Т001ТТ77', year=2020, color='Белый',
        vin='1HGCM82633A000001',
    )
    return client, car


# ─── 1. Клиенты ───────────────────────────────────────────────────────────────

class ClientTests(TestCase):

    def setUp(self):
        self.user   = make_user()
        self.tc     = TestClient()
        self.tc.login(username='testuser', password='testpass')
        self.make, self.model = make_base_car_objects()
        self.client_obj, self.car = make_client_with_car(self.make, self.model)

    # T-01
    def test_client_list_returns_200(self):
        resp = self.tc.get(reverse('clients_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Тестов Тест Тестович')

    # T-02
    def test_client_create_success(self):
        resp = self.tc.post(reverse('client_create'), {
            'fio': 'Новый Клиент Тестович',
            'phone_country': 'RU',
            'phone': '+7 999 200-00-02',
            'consent_personal_data': True,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Client.objects.filter(fio='Новый Клиент Тестович').exists())

    # T-03
    def test_client_create_duplicate_phone_rejected(self):
        resp = self.tc.post(reverse('client_create'), {
            'fio': 'Дубль Клиент',
            'phone_country': 'RU',
            'phone': '+7 999 100-00-01',  # уже занят
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Клиент с таким номером телефона уже существует')

    # T-04
    def test_client_update_success(self):
        resp = self.tc.post(reverse('client_update', args=[self.client_obj.pk]), {
            'fio': 'Изменённый Клиент',
            'phone_country': 'RU',
            'phone': '+7 999 100-00-01',
        })
        self.assertEqual(resp.status_code, 302)
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.fio, 'Изменённый Клиент')

    # T-05
    def test_client_delete_blocked_when_active_orders(self):
        """View blocks deletion when the client has active orders."""
        Order.objects.create(client_car=self.car, status='В работе', order_date=timezone.now().date())

        resp = self.tc.post(reverse('client_delete', args=[self.client_obj.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Client.objects.filter(pk=self.client_obj.pk).exists())

    def test_client_delete_nullifies_completed_orders(self):
        """Deleting a client with only completed orders NULLs client_car on those orders."""
        o_completed = Order.objects.create(client_car=self.car, status='Завершён', order_date=timezone.now().date())

        resp = self.tc.post(reverse('client_delete', args=[self.client_obj.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Client.objects.filter(pk=self.client_obj.pk).exists())
        self.assertTrue(Order.objects.filter(pk=o_completed.pk).exists())
        self.assertIsNone(Order.objects.get(pk=o_completed.pk).client_car)

    # T-06
    def test_phone_uniqueness_ajax(self):
        resp = self.tc.post(reverse('check_client_phone_uniqueness'), {'phone': '+7 999 100-00-01'})
        self.assertJSONEqual(resp.content, {'exists': True})
        resp = self.tc.post(reverse('check_client_phone_uniqueness'), {'phone': '+7 000 000-00-00'})
        self.assertJSONEqual(resp.content, {'exists': False})


# ─── 2. Автомобили клиента ────────────────────────────────────────────────────

class ClientCarTests(TestCase):

    def setUp(self):
        self.user   = make_user()
        self.tc     = TestClient()
        self.tc.login(username='testuser', password='testpass')
        self.make, self.model = make_base_car_objects()
        self.client_obj, self.car = make_client_with_car(self.make, self.model)

    # T-07
    def test_car_create_success(self):
        resp = self.tc.post(reverse('client_car_create', args=[self.client_obj.pk]), {
            'client':        self.client_obj.pk,
            'make':          self.make.pk,
            'model':         self.model.pk,
            'plate_country': 'RU',
            'license_plate': 'Н002НН77',
            'color':         'Синий',
            'vin':           '1HGCM82633A000002',
            'year':          2021,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(ClientCar.objects.filter(license_plate='Н002НН77').exists())

    # T-08
    def test_car_duplicate_license_plate_rejected(self):
        resp = self.tc.post(reverse('client_car_create', args=[self.client_obj.pk]), {
            'client': self.client_obj.pk,
            'make':   self.make.pk,
            'model':  self.model.pk,
            'license_plate': 'Т001ТТ77',  # уже занят
            'color':  'Красный',
            'year':   2022,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ClientCar.objects.filter(license_plate='Т001ТТ77').count(), 1)

    # T-09
    def test_vin_uniqueness_ajax(self):
        resp = self.tc.post(reverse('check_vin_uniqueness'), {'vin': '1HGCM82633A000001'})
        self.assertJSONEqual(resp.content, {'exists': True})
        resp = self.tc.post(reverse('check_vin_uniqueness'), {'vin': 'NEWVIN0000000001'})
        self.assertJSONEqual(resp.content, {'exists': False})


# ─── 3. Заказы ────────────────────────────────────────────────────────────────

class OrderTests(TestCase):

    def setUp(self):
        self.user   = make_user()
        self.tc     = TestClient()
        self.tc.login(username='testuser', password='testpass')
        self.make, self.model = make_base_car_objects()
        self.client_obj, self.car = make_client_with_car(self.make, self.model)

    def _make_order(self, status='Первичный осмотр'):
        return Order.objects.create(
            client_car=self.car, status=status,
            order_date=timezone.now().date(),
        )

    # T-10
    def test_orders_list_returns_200(self):
        resp = self.tc.get(reverse('orders_list'))
        self.assertEqual(resp.status_code, 200)

    # T-11
    def test_order_create_success(self):
        resp = self.tc.post(reverse('order_create'), {
            'client':     self.client_obj.pk,  # ClientSelectionForm
            'client_car': self.car.pk,
            'status':     'Первичный осмотр',
            'order_date': str(timezone.now().date()),
            'comment':    'Тестовый заказ',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Order.objects.filter(comment='Тестовый заказ').exists())

    # T-12
    def test_order_detail_returns_200(self):
        order = self._make_order()
        resp  = self.tc.get(reverse('order_detail', args=[order.pk]))
        self.assertEqual(resp.status_code, 200)

    # T-13
    def test_completion_date_auto_set_on_finish(self):
        order = self._make_order('В работе')
        self.assertIsNone(order.completion_date)
        order.status = 'Завершён'
        order.save()
        order.refresh_from_db()
        self.assertIsNotNone(order.completion_date)

    # T-14
    def test_completion_date_cleared_on_reopen(self):
        order = self._make_order('В работе')
        order.status = 'Завершён'
        order.save()
        order.status = 'В работе'
        order.save()
        order.refresh_from_db()
        self.assertIsNone(order.completion_date)

    # T-15
    def test_static_fields_frozen_on_complete(self):
        order = self._make_order('В работе')
        order.status = 'Завершён'
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.client_fio_static, self.client_obj.fio)
        self.assertIn(self.make.name, order.car_details_static)

    # T-16
    def test_order_delete_success(self):
        order = self._make_order()
        resp  = self.tc.post(reverse('order_delete', args=[order.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Order.objects.filter(pk=order.pk).exists())


# ─── 4. Услуги ────────────────────────────────────────────────────────────────

class ServiceTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.tc   = TestClient()
        self.tc.login(username='testuser', password='testpass')

    # T-17
    def test_service_management_page_returns_200(self):
        resp = self.tc.get(reverse('service_management'))
        self.assertEqual(resp.status_code, 200)

    # T-18
    def test_service_type_create_success(self):
        resp = self.tc.post(reverse('service_type_create'), {'name': 'Тестовый тип'})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(ServiceType.objects.filter(name='Тестовый тип').exists())

    # T-19
    def test_service_type_uniqueness_ajax(self):
        ServiceType.objects.create(name='Ходовая часть')
        resp = self.tc.post(reverse('check_service_type_uniqueness'), {'name': 'Ходовая часть'})
        self.assertJSONEqual(resp.content, {'exists': True})

    # T-20
    def test_service_type_delete_cascades_to_service(self):
        st  = ServiceType.objects.create(name='Удаляемый тип')
        svc = Service.objects.create(name='Удаляемая услуга', service_type=st, base_hours=Decimal('1.0'))
        resp = self.tc.post(reverse('service_type_delete', args=[st.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(ServiceType.objects.filter(pk=st.pk).exists())
        self.assertFalse(Service.objects.filter(pk=svc.pk).exists())


# ─── 5. Марки и модели автомобилей ────────────────────────────────────────────

class CarCatalogTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.tc   = TestClient()
        self.tc.login(username='testuser', password='testpass')

    # T-21
    def test_car_management_page_returns_200(self):
        resp = self.tc.get(reverse('car_management'))
        self.assertEqual(resp.status_code, 200)

    # T-22
    def test_car_make_create_success(self):
        resp = self.tc.post(reverse('car_make_create'), {'name': 'Honda'})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(CarMake.objects.filter(name='Honda').exists())

    # T-23
    def test_car_make_uniqueness_ajax(self):
        CarMake.objects.create(name='BMW')
        resp = self.tc.post(reverse('check_car_make_uniqueness'), {'name': 'BMW'})
        self.assertJSONEqual(resp.content, {'exists': True})
        resp = self.tc.post(reverse('check_car_make_uniqueness'), {'name': 'Audi'})
        self.assertJSONEqual(resp.content, {'exists': False})

    # T-24
    def test_car_model_create_under_make(self):
        make = CarMake.objects.create(name='Nissan')
        resp = self.tc.post(reverse('car_model_create', args=[make.pk]), {
            'make': make.pk,
            'name': 'Juke',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(CarModel.objects.filter(name='Juke', make=make).exists())

    # T-25
    def test_get_models_ajax(self):
        make  = CarMake.objects.create(name='Renault')
        model = CarModel.objects.create(make=make, name='Duster')
        resp  = self.tc.get(reverse('get_models'), {'make_id': make.pk})
        self.assertEqual(resp.status_code, 200)
        data  = json.loads(resp.content)
        names = [m['name'] for m in data]
        self.assertIn('Duster', names)


# ─── 6. Доступ без авторизации ────────────────────────────────────────────────

class AuthRequiredTests(TestCase):

    # T-26
    def test_orders_list_redirects_anonymous(self):
        tc   = TestClient()
        resp = tc.get(reverse('orders_list'))
        self.assertIn(resp.status_code, [302, 301])
        self.assertIn('/accounts/login', resp['Location'])

    # T-27
    def test_clients_list_redirects_anonymous(self):
        tc   = TestClient()
        resp = tc.get(reverse('clients_list'))
        self.assertIn(resp.status_code, [302, 301])
        self.assertIn('/accounts/login', resp['Location'])


# ─── 7. PDF-генерация ─────────────────────────────────────────────────────────

class PDFTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.tc   = TestClient()
        self.tc.login(username='testuser', password='testpass')
        self.make, self.model = make_base_car_objects()
        self.client_obj, self.car = make_client_with_car(self.make, self.model)
        self.order = Order.objects.create(
            client_car=self.car, status='Завершён',
            order_date=timezone.now().date(),
        )

    # T-28
    def test_mechanic_pdf_returns_pdf(self):
        resp = self.tc.get(reverse('order_mechanic_pdf', args=[self.order.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))

    # T-29
    def test_customer_pdf_final_returns_pdf(self):
        resp = self.tc.get(reverse('order_customer_pdf', args=[self.order.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))

    # T-30
    def test_customer_pdf_preliminary_for_active_order(self):
        active = Order.objects.create(
            client_car=self.car, status='В работе',
            order_date=timezone.now().date(),
        )
        resp = self.tc.get(reverse('order_customer_pdf', args=[active.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('preview', resp['Content-Disposition'])


# ─── 8. WorkOrderService — расчёт стоимости ───────────────────────────────────

class WorkOrderServicePriceTests(TestCase):

    def setUp(self):
        from warehouse.models import WorkOrderService, WorkshopSettings
        self.WorkOrderService  = WorkOrderService
        self.WorkshopSettings  = WorkshopSettings

        self.user  = make_user()
        self.make, self.model = make_base_car_objects()
        self.client_obj, self.car = make_client_with_car(self.make, self.model)
        self.order = Order.objects.create(
            client_car=self.car, status='В работе',
            order_date=timezone.now().date(),
        )
        self.WorkshopSettings.objects.create(hourly_rate=Decimal('2000.00'))
        st       = ServiceType.objects.create(name='ТО')
        self.svc = Service.objects.create(name='Замена масла', service_type=st, base_hours=Decimal('1.0'))

    # T-31
    def test_final_price_calculated_on_save(self):
        wos = self.WorkOrderService.objects.create(
            work_order=self.order, service=self.svc,
            service_name_snapshot='Замена масла',
            hourly_rate_snapshot=Decimal('2000.00'),
            hours_applied=Decimal('1.5'),
            complexity_factor=Decimal('1.2'),
        )
        # 1.5 * 1.2 * 2000 = 3600
        self.assertEqual(wos.final_price, Decimal('3600.00'))

    # T-32
    def test_final_price_uses_snapshot_not_current_settings(self):
        wos = self.WorkOrderService.objects.create(
            work_order=self.order, service=self.svc,
            service_name_snapshot='Замена масла',
            hourly_rate_snapshot=Decimal('1500.00'),  # старая ставка
            hours_applied=Decimal('1.0'),
            complexity_factor=Decimal('1.0'),
        )
        self.WorkshopSettings.objects.update(hourly_rate=Decimal('3000.00'))
        wos.refresh_from_db()
        # снапшот зафиксирован — пересчёта нет
        self.assertEqual(wos.final_price, Decimal('1500.00'))


# ─── 9. Склад — StockEntry и price_per_unit ───────────────────────────────────

class StockTests(TestCase):

    def setUp(self):
        from warehouse.models import Part, StorageLocation, StockEntry, SupplyDocument, SupplyItem, Supplier
        self.Part            = Part
        self.StorageLocation = StorageLocation
        self.StockEntry      = StockEntry
        self.SupplyDocument  = SupplyDocument
        self.SupplyItem      = SupplyItem
        self.Supplier        = Supplier

        self.user = make_user()
        self.tc   = TestClient()
        self.tc.login(username='testuser', password='testpass')

    # T-33
    def test_stock_available_qty_is_total_minus_reserved(self):
        supplier = self.Supplier.objects.create(name='Тест Поставщик', phone='+7 000 000-00-00')
        part     = self.Part.objects.create(article='TST-001', name='Тестовая деталь', package_qty=1)
        loc      = self.StorageLocation.objects.create(rack='Z', shelf='1', cell='1')
        entry    = self.StockEntry.objects.create(
            part=part, location=loc, total_qty=10, reserved_qty=3, min_qty=2,
        )
        self.assertEqual(entry.available_qty, 7)

    # T-34
    def test_price_per_unit_property(self):
        supplier = self.Supplier.objects.create(name='Поставщик 2', phone='+7 111 111-11-11')
        part     = self.Part.objects.create(article='TST-002', name='Деталь 2', package_qty=4)
        loc      = self.StorageLocation.objects.create(rack='Z', shelf='2', cell='1')
        doc      = self.SupplyDocument.objects.create(supplier=supplier)
        si       = self.SupplyItem.objects.create(
            document=doc, part=part, location=loc,
            quantity=8, pkg_qty=4, purchase_price=Decimal('400.00'),
        )
        # 400 / 4 = 100
        self.assertEqual(si.price_per_unit, Decimal('100.00'))
