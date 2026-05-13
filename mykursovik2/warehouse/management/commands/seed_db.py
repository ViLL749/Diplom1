"""
Management command: seed_db
Clears all business data and fills the database with realistic test data.
Usage: python manage.py seed_db
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Очистить БД и заполнить тестовыми данными'

    def handle(self, *args, **options):
        self.stdout.write('Очистка базы данных...')
        self._clear()
        self.stdout.write('Создание тестовых данных...')
        with transaction.atomic():
            self._seed()
        self.stdout.write(self.style.SUCCESS('Готово!'))

    def _clear(self):
        from warehouse.models import (
            WorkOrderServiceEmployee, WorkOrderService, WorkOrderPart,
            SupplyItem, SupplyDocument, PurchaseOrderItem, PurchaseOrder,
            StockEntry, Part, StorageLocation, Brand, Supplier, Employee,
            WorkshopSettings,
        )
        from mainapp.models import Order, ClientCar, Client, CarModel, CarMake, Service, ServiceType

        WorkOrderServiceEmployee.objects.all().delete()
        WorkOrderService.objects.all().delete()
        WorkOrderPart.objects.all().delete()
        SupplyItem.objects.all().delete()
        SupplyDocument.objects.all().delete()
        PurchaseOrderItem.objects.all().delete()
        PurchaseOrder.objects.all().delete()
        StockEntry.objects.all().delete()
        Part.objects.all().delete()
        StorageLocation.objects.all().delete()
        Brand.objects.all().delete()
        Supplier.objects.all().delete()
        Employee.objects.all().delete()
        Order.objects.all().delete()
        ClientCar.objects.all().delete()
        Client.objects.all().delete()
        CarModel.objects.all().delete()
        CarMake.objects.all().delete()
        Service.objects.all().delete()
        ServiceType.objects.all().delete()
        WorkshopSettings.objects.all().delete()

    def _seed(self):
        from warehouse.models import (
            Brand, Supplier, Part, StorageLocation, StockEntry,
            SupplyDocument, SupplyItem, WorkOrderService, WorkOrderPart,
            WorkOrderServiceEmployee, Employee, WorkshopSettings,
            PurchaseOrder, PurchaseOrderItem,
        )
        from mainapp.models import (
            Client, CarMake, CarModel, ClientCar,
            ServiceType, Service, Order,
        )

        # ── Настройки мастерской ─────────────────
        WorkshopSettings.objects.create(hourly_rate=Decimal('2000.00'))

        # ── Производители (справочник) ───────────
        Brand.objects.create(name='Bosch')
        Brand.objects.create(name='NGK')
        Brand.objects.create(name='Mann Filter')
        Brand.objects.create(name='Castrol')
        Brand.objects.create(name='Liqui Moly')
        Brand.objects.create(name='KYB')
        Brand.objects.create(name='Gates')
        Brand.objects.create(name='Brembo')
        Brand.objects.create(name='Denso')
        Brand.objects.create(name='Febi Bilstein')

        # ── Поставщики ───────────────────────────
        sup1 = Supplier.objects.create(name='АвтоДеталь',   phone='+7 495 111-22-33')
        sup2 = Supplier.objects.create(name='ТехноАвто',    phone='+7 495 444-55-66')
        Supplier.objects.create(name='АвтоЗапчасть Плюс',   phone='+7 812 333-44-55')

        # ── Места хранения ───────────────────────
        loc_a1 = StorageLocation.objects.create(rack='A', shelf='1', cell='1')
        loc_a2 = StorageLocation.objects.create(rack='A', shelf='1', cell='2')
        loc_a3 = StorageLocation.objects.create(rack='A', shelf='2', cell='1')
        loc_b1 = StorageLocation.objects.create(rack='B', shelf='1', cell='1')
        loc_b2 = StorageLocation.objects.create(rack='B', shelf='1', cell='2')
        loc_b3 = StorageLocation.objects.create(rack='B', shelf='2', cell='1')
        loc_c1 = StorageLocation.objects.create(rack='C', shelf='1', cell='1')
        StorageLocation.objects.create(rack='C', shelf='1', cell='2')
        StorageLocation.objects.create(rack='C', shelf='2', cell='1')

        # ── Номенклатура ─────────────────────────
        p_spark_ngk = Part.objects.create(
            article='NG-BPR6',  name='Свеча зажигания NGK BPR6ES',
            brand='NGK',         category='Расходники', package_qty=4,
        )
        p_spark_bsh = Part.objects.create(
            article='BO-WR78X', name='Свеча зажигания Bosch WR78X',
            brand='Bosch',       category='Расходники', package_qty=4,
        )
        p_spark_dns = Part.objects.create(
            article='DN-K16R',  name='Свеча зажигания Denso K16R-U',
            brand='Denso',       category='Расходники', package_qty=4,
        )
        p_oil_5w40 = Part.objects.create(
            article='CS-5W40',  name='Масло моторное Castrol 5W-40 4л',
            brand='Castrol',     category='Расходники', package_qty=1,
        )
        p_oil_5w30 = Part.objects.create(
            article='LM-5W30',  name='Масло моторное Liqui Moly 5W-30 4л',
            brand='Liqui Moly',  category='Расходники', package_qty=1,
        )
        p_oilf_mann = Part.objects.create(
            article='MN-W712',  name='Фильтр масляный Mann W712/75',
            brand='Mann Filter', category='Расходники', package_qty=1,
        )
        p_oilf_bsh = Part.objects.create(
            article='BO-0451',  name='Фильтр масляный Bosch 0451103063',
            brand='Bosch',       category='Расходники', package_qty=1,
        )
        p_airf = Part.objects.create(
            article='BO-S0026', name='Фильтр воздушный Bosch S0026',
            brand='Bosch',       category='Расходники', package_qty=1,
        )
        p_cabin_f = Part.objects.create(
            article='MN-CUK27', name='Фильтр салона Mann CUK27030',
            brand='Mann Filter', category='Расходники', package_qty=1,
        )
        p_fuel_f = Part.objects.create(
            article='BO-F026',  name='Фильтр топливный Bosch F026',
            brand='Bosch',       category='Расходники', package_qty=1,
        )
        p_brake_f = Part.objects.create(
            article='BR-P06',   name='Колодки тормозные передние Brembo P06',
            brand='Brembo',      category='Тормозная система', package_qty=4,
        )
        p_brake_r = Part.objects.create(
            article='BR-R04',   name='Колодки тормозные задние Brembo R04',
            brand='Brembo',      category='Тормозная система', package_qty=4,
        )
        p_disc_f = Part.objects.create(
            article='BR-D09',   name='Диск тормозной передний Brembo D09',
            brand='Brembo',      category='Тормозная система', package_qty=1,
        )
        p_belt = Part.objects.create(
            article='GT-K015',  name='Ремень ГРМ Gates K015',
            brand='Gates',       category='Двигатель', package_qty=1,
        )
        p_cool = Part.objects.create(
            article='LM-AF5',   name='Антифриз Liqui Moly G12 5л',
            brand='Liqui Moly',  category='Расходники', package_qty=1,
        )
        p_shock_f = Part.objects.create(
            article='KY-334',   name='Стойка амортизатора передняя KYB 334',
            brand='KYB',         category='Ходовая', package_qty=1,
        )
        p_shock_r = Part.objects.create(
            article='KY-444',   name='Амортизатор задний KYB 444',
            brand='KYB',         category='Ходовая', package_qty=1,
        )
        p_atf = Part.objects.create(
            article='LM-ATF',   name='Масло АКПП Liqui Moly ATF III 4л',
            brand='Liqui Moly',  category='Трансмиссия', package_qty=1,
        )
        p_brake_fl = Part.objects.create(
            article='LM-DOT4',  name='Жидкость тормозная Liqui Moly DOT-4 0.5л',
            brand='Liqui Moly',  category='Тормозная система', package_qty=1,
        )
        p_gasket = Part.objects.create(
            article='FB-VS01',  name='Прокладка клапанной крышки Febi 001',
            brand='Febi Bilstein', category='Двигатель', package_qty=1,
        )

        # ── Приход товара (первичный) ────────────
        supply1 = SupplyDocument.objects.create(supplier=sup1)

        def receive(doc, part, location, qty, pkg_qty, price_per_pkg, min_q=2):
            SupplyItem.objects.create(
                document=doc, part=part, location=location,
                quantity=qty, pkg_qty=pkg_qty, purchase_price=price_per_pkg,
            )
            entry, _ = StockEntry.objects.get_or_create(
                part=part, location=location,
                defaults={'total_qty': 0, 'reserved_qty': 0, 'min_qty': min_q},
            )
            entry.total_qty += qty
            entry.save()

        receive(supply1, p_spark_ngk, loc_a1, 40, 4,  Decimal('250.00'))
        receive(supply1, p_spark_bsh, loc_a1, 20, 4,  Decimal('280.00'))
        receive(supply1, p_spark_dns, loc_a1, 20, 4,  Decimal('240.00'))
        receive(supply1, p_oil_5w40,  loc_a2, 20, 1,  Decimal('1200.00'))
        receive(supply1, p_oil_5w30,  loc_a2, 15, 1,  Decimal('1100.00'))
        receive(supply1, p_oilf_mann, loc_a2, 25, 1,  Decimal('350.00'))
        receive(supply1, p_oilf_bsh,  loc_a2, 20, 1,  Decimal('380.00'))
        receive(supply1, p_airf,      loc_a3, 20, 1,  Decimal('450.00'))
        receive(supply1, p_cabin_f,   loc_a3, 15, 1,  Decimal('420.00'))
        receive(supply1, p_fuel_f,    loc_a3, 10, 1,  Decimal('380.00'))

        supply2 = SupplyDocument.objects.create(supplier=sup2)

        receive(supply2, p_brake_f,  loc_b1, 16, 4,  Decimal('1800.00'))
        receive(supply2, p_brake_r,  loc_b1, 16, 4,  Decimal('1600.00'))
        receive(supply2, p_disc_f,   loc_b1,  8, 1,  Decimal('2800.00'))
        receive(supply2, p_belt,     loc_b2, 10, 1,  Decimal('2200.00'))
        receive(supply2, p_cool,     loc_b2, 16, 1,  Decimal('800.00'))
        receive(supply2, p_shock_f,  loc_b3,  6, 1,  Decimal('3500.00'))
        receive(supply2, p_shock_r,  loc_b3,  8, 1,  Decimal('2800.00'))
        receive(supply2, p_atf,      loc_c1, 10, 1,  Decimal('1400.00'))
        receive(supply2, p_brake_fl, loc_c1, 20, 1,  Decimal('220.00'))
        receive(supply2, p_gasket,   loc_c1,  5, 1,  Decimal('650.00'))

        # ── Марки и модели ───────────────────────
        toyota  = CarMake.objects.create(name='Toyota')
        lada    = CarMake.objects.create(name='Lada')
        vw      = CarMake.objects.create(name='Volkswagen')
        kia     = CarMake.objects.create(name='Kia')
        honda   = CarMake.objects.create(name='Honda')
        nissan  = CarMake.objects.create(name='Nissan')
        skoda   = CarMake.objects.create(name='Skoda')
        renault = CarMake.objects.create(name='Renault')
        hyundai = CarMake.objects.create(name='Hyundai')
        ford    = CarMake.objects.create(name='Ford')

        camry    = CarModel.objects.create(make=toyota,  name='Camry')
        corolla  = CarModel.objects.create(make=toyota,  name='Corolla')
        rav4     = CarModel.objects.create(make=toyota,  name='RAV4')
        vesta    = CarModel.objects.create(make=lada,    name='Vesta')
        granta   = CarModel.objects.create(make=lada,    name='Granta')
        polo     = CarModel.objects.create(make=vw,      name='Polo')
        passat   = CarModel.objects.create(make=vw,      name='Passat')
        tiguan   = CarModel.objects.create(make=vw,      name='Tiguan')
        rio      = CarModel.objects.create(make=kia,     name='Rio')
        sportage = CarModel.objects.create(make=kia,     name='Sportage')
        accord   = CarModel.objects.create(make=honda,   name='Accord')
        civic    = CarModel.objects.create(make=honda,   name='Civic')
        qashqai  = CarModel.objects.create(make=nissan,  name='Qashqai')
        octavia  = CarModel.objects.create(make=skoda,   name='Octavia')
        logan    = CarModel.objects.create(make=renault, name='Logan')
        solaris  = CarModel.objects.create(make=hyundai, name='Solaris')
        focus    = CarModel.objects.create(make=ford,    name='Focus')

        # ── Клиенты и автомобили ─────────────────
        c1  = Client.objects.create(fio='Смирнов Андрей Петрович',      phone='+7 900 123-45-67')
        c2  = Client.objects.create(fio='Козлова Мария Ивановна',       phone='+7 903 456-78-90')
        c3  = Client.objects.create(fio='Новиков Сергей Олегович',      phone='+7 926 789-01-23')
        c4  = Client.objects.create(fio='Волков Игорь Дмитриевич',      phone='+7 916 234-56-78')
        c5  = Client.objects.create(fio='Зайцева Анна Николаевна',      phone='+7 985 567-89-01')
        c6  = Client.objects.create(fio='Фёдоров Павел Юрьевич',        phone='+7 901 987-65-43')
        c7  = Client.objects.create(fio='Михайлова Елена Владимировна', phone='+7 962 876-54-32')
        c8  = Client.objects.create(fio='Соколов Роман Аркадьевич',     phone='+7 919 765-43-21')
        c9  = Client.objects.create(fio='Попова Оксана Борисовна',      phone='+7 977 654-32-10')
        c10 = Client.objects.create(fio='Власов Виктор Геннадьевич',    phone='+7 925 543-21-09')
        c11 = Client.objects.create(fio='Лебедев Константин Михайлович',phone='+7 915 432-10-98')
        c12 = Client.objects.create(fio='Орлова Ирина Анатольевна',     phone='+7 967 321-09-87')
        c13 = Client.objects.create(fio='Тихонов Максим Сергеевич',     phone='+7 906 210-98-76')
        c14 = Client.objects.create(fio='Соловьёв Антон Игоревич',      phone='+7 937 109-87-65')
        c15 = Client.objects.create(fio='Белякова Татьяна Николаевна',  phone='+7 965 098-76-54')

        # Допустимые буквы в рос. номерах: А В Е К М Н О Р С Т У Х
        car1  = ClientCar.objects.create(client=c1,  make=toyota,  model=camry,    license_plate='А777ВВ77', year=2019, color='Белый',        vin='1NXBR32E5XZ123456')
        car1b = ClientCar.objects.create(client=c1,  make=lada,    model=granta,   license_plate='А120ТТ77', year=2016, color='Серебристый',   vin='XTACB71309G234567')
        car2  = ClientCar.objects.create(client=c2,  make=lada,    model=vesta,    license_plate='В123АА77', year=2021, color='Серый',         vin='XTA52300LM3345678')
        car3  = ClientCar.objects.create(client=c3,  make=vw,      model=polo,     license_plate='С456ВВ77', year=2018, color='Синий',         vin='WVWZZZ6RZJ1456789')
        car4  = ClientCar.objects.create(client=c4,  make=kia,     model=sportage, license_plate='К789ОО77', year=2020, color='Чёрный',        vin='U5YPH813ALT567890')
        car4b = ClientCar.objects.create(client=c4,  make=kia,     model=rio,      license_plate='К188АА77', year=2015, color='Белый',         vin='KNAFB2A14F5678901')
        car5  = ClientCar.objects.create(client=c5,  make=toyota,  model=corolla,  license_plate='Е012ММ77', year=2017, color='Серебристый',   vin='JTDBZ3EH9H0789012')
        car6  = ClientCar.objects.create(client=c6,  make=honda,   model=accord,   license_plate='Т345ЕЕ77', year=2020, color='Тёмно-синий',   vin='1HGCV1F37LA890123')
        car7  = ClientCar.objects.create(client=c7,  make=nissan,  model=qashqai,  license_plate='У678КК77', year=2019, color='Бежевый',       vin='JN1BAYS62U0901234')
        car8  = ClientCar.objects.create(client=c8,  make=skoda,   model=octavia,  license_plate='Х901НН77', year=2021, color='Серый',         vin='TMBJE75L4MA012345')
        car9  = ClientCar.objects.create(client=c9,  make=renault, model=logan,    license_plate='К234СС77', year=2016, color='Белый',         vin='VF1LS1G0H47123456')
        car10 = ClientCar.objects.create(client=c10, make=ford,    model=focus,    license_plate='Р567КК77', year=2017, color='Красный',       vin='WF05XXGBB5GR23456')
        car11 = ClientCar.objects.create(client=c11, make=toyota,  model=rav4,     license_plate='М890ОО77', year=2022, color='Белый',         vin='JTMH3REV0ND234567')
        car12 = ClientCar.objects.create(client=c12, make=lada,    model=vesta,    license_plate='Н345МВ77', year=2020, color='Синий',         vin='XTA52300LL3456789')
        car13 = ClientCar.objects.create(client=c13, make=hyundai, model=solaris,  license_plate='О456НН77', year=2018, color='Чёрный',        vin='KMHCT41BAFU345678')
        car14 = ClientCar.objects.create(client=c14, make=vw,      model=tiguan,   license_plate='С789ОО77', year=2021, color='Серый',         vin='WVGZZZ5NZMU456789')
        car15 = ClientCar.objects.create(client=c15, make=vw,      model=passat,   license_plate='Р012ТТ77', year=2019, color='Тёмно-серый',   vin='WVWZZZ3CZKU567890')
        car16 = ClientCar.objects.create(client=c3,  make=honda,   model=civic,    license_plate='С159РР77', year=2022, color='Красный',       vin='2HGFE2F52NH678901')

        # ── Типы услуг ───────────────────────────
        st_to   = ServiceType.objects.create(name='Техническое обслуживание')
        st_hod  = ServiceType.objects.create(name='Ходовая часть')
        st_dv   = ServiceType.objects.create(name='Двигатель')
        st_el   = ServiceType.objects.create(name='Электрика')
        st_tr   = ServiceType.objects.create(name='Трансмиссия')

        # ── Услуги ───────────────────────────────
        svc_oil    = Service.objects.create(name='Замена масла и фильтра',         service_type=st_to,  base_hours=Decimal('1.0'))
        svc_spark  = Service.objects.create(name='Замена свечей зажигания',        service_type=st_to,  base_hours=Decimal('0.5'))
        svc_airf   = Service.objects.create(name='Замена воздушного фильтра',      service_type=st_to,  base_hours=Decimal('0.3'))
        svc_cabin  = Service.objects.create(name='Замена фильтра салона',          service_type=st_to,  base_hours=Decimal('0.3'))
        svc_cool   = Service.objects.create(name='Замена охлаждающей жидкости',    service_type=st_to,  base_hours=Decimal('1.0'))
        svc_diag   = Service.objects.create(name='Компьютерная диагностика',       service_type=st_to,  base_hours=Decimal('0.5'))
        svc_brake_f= Service.objects.create(name='Замена тормозных колодок перед', service_type=st_hod, base_hours=Decimal('1.5'))
        svc_brake_r= Service.objects.create(name='Замена тормозных колодок зад',   service_type=st_hod, base_hours=Decimal('1.0'))
        svc_disc   = Service.objects.create(name='Замена тормозных дисков',        service_type=st_hod, base_hours=Decimal('2.0'))
        svc_shock  = Service.objects.create(name='Замена амортизаторов',           service_type=st_hod, base_hours=Decimal('2.5'))
        svc_align  = Service.objects.create(name='Развал-схождение',               service_type=st_hod, base_hours=Decimal('1.0'))
        svc_belt   = Service.objects.create(name='Замена ремня ГРМ',               service_type=st_dv,  base_hours=Decimal('3.0'))
        svc_fuel   = Service.objects.create(name='Промывка топливной системы',     service_type=st_dv,  base_hours=Decimal('1.5'))
        svc_atf    = Service.objects.create(name='Замена масла АКПП',              service_type=st_tr,  base_hours=Decimal('1.5'))
        svc_el     = Service.objects.create(name='Диагностика электрики',          service_type=st_el,  base_hours=Decimal('1.0'))

        # ── Сотрудники ───────────────────────────
        emp1 = Employee.objects.create(name='Иванов Дмитрий Сергеевич',    position='Мастер-механик', phone='+7 901 111-22-33')
        emp2 = Employee.objects.create(name='Петров Алексей Иванович',     position='Механик',        phone='+7 902 444-55-66')
        emp3 = Employee.objects.create(name='Сидоров Кирилл Андреевич',    position='Механик',        phone='+7 903 777-88-99')
        emp4 = Employee.objects.create(name='Орлов Николай Петрович',      position='Механик',        phone='+7 904 000-11-22')
        emp5 = Employee.objects.create(name='Карпов Евгений Александрович',position='Диагност',       phone='+7 905 333-44-55')

        RATE = Decimal('2000.00')

        def wos(order, svc, name, hours, factor=1.0):
            return WorkOrderService.objects.create(
                work_order=order, service=svc,
                service_name_snapshot=name,
                hourly_rate_snapshot=RATE,
                hours_applied=Decimal(str(hours)),
                complexity_factor=Decimal(str(factor)),
            )

        def part(order, wos_obj, p, qty, markup_pct):
            si = SupplyItem.objects.filter(part=p).first()
            pkg = si.pkg_qty if si else 1
            cost = si.purchase_price / Decimal(pkg) if si else Decimal('0')
            sale = (cost * (1 + Decimal(str(markup_pct)) / 100)).quantize(Decimal('0.01'))
            WorkOrderPart.objects.create(
                work_order=order, work_order_service=wos_obj,
                part=p, quantity=qty,
                sale_price=sale, markup=Decimal(str(markup_pct)),
                status='installed',
            )
            for e in StockEntry.objects.filter(part=p):
                if e.total_qty >= qty:
                    e.total_qty -= qty
                    e.save()
                break

        def assign(wos_obj, *employees):
            for emp in employees:
                WorkOrderServiceEmployee.objects.create(work_order_service=wos_obj, employee=emp)

        def finish(order, date):
            order.status = 'Завершён'
            order.completion_date = date
            order.save()

        def cancel(order):
            order.status = 'Отменён'
            order.save()

        # ══ ЗАКАЗ 1 ══════════════════════════════
        # Смирнов / Toyota Camry — плановое ТО 60 000 км
        o = Order.objects.create(client_car=car1, status='В работе', order_date='2024-09-03', comment='Плановое ТО — 60 000 км')
        w1 = wos(o, svc_oil,  'Замена масла и фильтра',    1.0)
        w2 = wos(o, svc_airf, 'Замена воздушного фильтра', 0.3)
        w3 = wos(o, svc_cabin,'Замена фильтра салона',      0.3)
        part(o, w1, p_oil_5w40,  1, 25); part(o, w1, p_oilf_mann, 1, 30)
        part(o, w2, p_airf,      1, 30); part(o, w3, p_cabin_f,    1, 30)
        assign(w1, emp1); assign(w2, emp1); assign(w3, emp2)
        finish(o, '2024-09-03')

        # ══ ЗАКАЗ 2 ══════════════════════════════
        # Козлова / Lada Vesta — замена свечей
        o = Order.objects.create(client_car=car2, status='В работе', order_date='2024-09-10', comment='Пропуск зажигания на холодную')
        w1 = wos(o, svc_spark, 'Замена свечей зажигания', 0.5)
        part(o, w1, p_spark_ngk, 4, 30)
        assign(w1, emp2)
        finish(o, '2024-09-10')

        # ══ ЗАКАЗ 3 ══════════════════════════════
        # Новиков / VW Polo — тормозные колодки перед
        o = Order.objects.create(client_car=car3, status='В работе', order_date='2024-09-17', comment='Скрип при торможении')
        w1 = wos(o, svc_brake_f, 'Замена тормозных колодок перед', 1.5)
        part(o, w1, p_brake_f, 4, 35)
        assign(w1, emp3)
        finish(o, '2024-09-17')

        # ══ ЗАКАЗ 4 ══════════════════════════════
        # Волков / Kia Sportage — ремень ГРМ (двое)
        o = Order.objects.create(client_car=car4, status='В работе', order_date='2024-09-24', comment='Подтёк масла, плановая замена ремня ГРМ')
        w1 = wos(o, svc_belt, 'Замена ремня ГРМ', 3.0, 1.2)
        part(o, w1, p_belt, 1, 40)
        assign(w1, emp1, emp2)
        finish(o, '2024-09-25')

        # ══ ЗАКАЗ 5 ══════════════════════════════
        # Зайцева / Toyota Corolla — диагностика + масло
        o = Order.objects.create(client_car=car5, status='В работе', order_date='2024-10-01', comment='Горит лампа Check Engine')
        w1 = wos(o, svc_diag, 'Компьютерная диагностика', 0.5)
        w2 = wos(o, svc_oil,  'Замена масла и фильтра',    1.0)
        part(o, w2, p_oil_5w30, 1, 25); part(o, w2, p_oilf_bsh, 1, 30)
        assign(w1, emp5); assign(w2, emp2)
        finish(o, '2024-10-02')

        # ══ ЗАКАЗ 6 ══════════════════════════════
        # Фёдоров / Honda Accord — замена АКПП масла
        o = Order.objects.create(client_car=car6, status='В работе', order_date='2024-10-08', comment='Пинки при переключении передач')
        w1 = wos(o, svc_atf, 'Замена масла АКПП', 1.5)
        part(o, w1, p_atf, 4, 30)
        assign(w1, emp1)
        finish(o, '2024-10-09')

        # ══ ЗАКАЗ 7 ══════════════════════════════
        # Михайлова / Nissan Qashqai — развал-схождение после замены стоек
        o = Order.objects.create(client_car=car7, status='В работе', order_date='2024-10-15', comment='Уводит вправо, стуки в передней подвеске')
        w1 = wos(o, svc_shock, 'Замена амортизаторов передних', 2.5, 1.1)
        w2 = wos(o, svc_align, 'Развал-схождение',              1.0)
        part(o, w1, p_shock_f, 2, 35)
        assign(w1, emp3, emp4); assign(w2, emp3)
        finish(o, '2024-10-16')

        # ══ ЗАКАЗ 8 ══════════════════════════════
        # Соколов / Skoda Octavia — замена тормозных дисков и колодок перед
        o = Order.objects.create(client_car=car8, status='В работе', order_date='2024-10-22', comment='Вибрация при торможении')
        w1 = wos(o, svc_disc,    'Замена тормозных дисков',         2.0)
        w2 = wos(o, svc_brake_f, 'Замена тормозных колодок перед',  1.5)
        part(o, w1, p_disc_f,  2, 35); part(o, w2, p_brake_f, 4, 35)
        assign(w1, emp4); assign(w2, emp4)
        finish(o, '2024-10-23')

        # ══ ЗАКАЗ 9 ══════════════════════════════
        # Попова / Renault Logan — ТО + свечи
        o = Order.objects.create(client_car=car9, status='В работе', order_date='2024-11-05', comment='Плановое ТО 30 000 км')
        w1 = wos(o, svc_oil,   'Замена масла и фильтра',    1.0)
        w2 = wos(o, svc_spark, 'Замена свечей зажигания',   0.5)
        w3 = wos(o, svc_airf,  'Замена воздушного фильтра', 0.3)
        part(o, w1, p_oil_5w30, 1, 25); part(o, w1, p_oilf_mann, 1, 30)
        part(o, w2, p_spark_bsh, 4, 30); part(o, w3, p_airf, 1, 30)
        assign(w1, emp2); assign(w2, emp2); assign(w3, emp2)
        finish(o, '2024-11-05')

        # ══ ЗАКАЗ 10 ══════════════════════════════
        # Власов / Ford Focus — промывка топливной системы
        o = Order.objects.create(client_car=car10, status='В работе', order_date='2024-11-12', comment='Нестабильная работа двигателя на холостых')
        w1 = wos(o, svc_fuel, 'Промывка топливной системы', 1.5)
        w2 = wos(o, svc_diag, 'Компьютерная диагностика',   0.5)
        part(o, w1, p_fuel_f, 1, 30)
        assign(w1, emp1); assign(w2, emp5)
        finish(o, '2024-11-13')

        # ══ ЗАКАЗ 11 ══════════════════════════════
        # Лебедев / Toyota RAV4 — задние колодки
        o = Order.objects.create(client_car=car11, status='В работе', order_date='2024-11-19', comment='Задние тормоза скрипят при парковке')
        w1 = wos(o, svc_brake_r, 'Замена тормозных колодок зад', 1.0)
        part(o, w1, p_brake_r, 4, 35)
        assign(w1, emp3)
        finish(o, '2024-11-19')

        # ══ ЗАКАЗ 12 ══════════════════════════════
        # Орлова / Lada Vesta — диагностика электрики
        o = Order.objects.create(client_car=car12, status='В работе', order_date='2024-11-26', comment='Не заряжается аккумулятор')
        w1 = wos(o, svc_el, 'Диагностика электрики', 1.0)
        assign(w1, emp5)
        finish(o, '2024-11-26')

        # ══ ЗАКАЗ 13 ══════════════════════════════
        # Тихонов / Hyundai Solaris — масло + фильтры + свечи Denso
        o = Order.objects.create(client_car=car13, status='В работе', order_date='2024-12-03', comment='Плановое ТО 90 000 км')
        w1 = wos(o, svc_oil,   'Замена масла и фильтра',    1.0)
        w2 = wos(o, svc_spark, 'Замена свечей зажигания',   0.5)
        w3 = wos(o, svc_airf,  'Замена воздушного фильтра', 0.3)
        w4 = wos(o, svc_cabin, 'Замена фильтра салона',     0.3)
        part(o, w1, p_oil_5w40,  1, 25); part(o, w1, p_oilf_bsh, 1, 30)
        part(o, w2, p_spark_dns, 4, 30); part(o, w3, p_airf,      1, 30)
        part(o, w4, p_cabin_f,   1, 30)
        assign(w1, emp2); assign(w2, emp2); assign(w3, emp2); assign(w4, emp2)
        finish(o, '2024-12-04')

        # ══ ЗАКАЗ 14 ══════════════════════════════
        # Соловьёв / VW Tiguan — задние колодки + тормозная жидкость
        o = Order.objects.create(client_car=car14, status='В работе', order_date='2024-12-10', comment='Плановая замена тормозной жидкости')
        w1 = wos(o, svc_brake_r, 'Замена тормозных колодок зад', 1.0)
        w2 = wos(o, svc_diag,    'Компьютерная диагностика',      0.5)
        part(o, w1, p_brake_r,   4, 35); part(o, w1, p_brake_fl, 2, 25)
        assign(w1, emp4); assign(w2, emp5)
        finish(o, '2024-12-11')

        # ══ ЗАКАЗ 15 ══════════════════════════════
        # Белякова / VW Passat — ремень ГРМ (сложный, трое)
        o = Order.objects.create(client_car=car15, status='В работе', order_date='2024-12-17', comment='Шум со стороны ГРМ')
        w1 = wos(o, svc_belt, 'Замена ремня ГРМ', 3.0, 1.3)
        part(o, w1, p_belt, 1, 40)
        assign(w1, emp1, emp2, emp4)
        finish(o, '2024-12-18')

        # ══ ЗАКАЗ 16 ══════════════════════════════
        # Смирнов / Lada Granta — масло + свечи
        o = Order.objects.create(client_car=car1b, status='В работе', order_date='2025-01-09', comment='Давно не обслуживалась')
        w1 = wos(o, svc_oil,   'Замена масла и фильтра',  1.0)
        w2 = wos(o, svc_spark, 'Замена свечей зажигания', 0.5)
        part(o, w1, p_oil_5w30, 1, 25); part(o, w1, p_oilf_mann, 1, 30)
        part(o, w2, p_spark_ngk, 4, 30)
        assign(w1, emp2); assign(w2, emp2)
        finish(o, '2024-01-09')

        # ══ ЗАКАЗ 17 ══════════════════════════════
        # Волков / Kia Rio — передние амортизаторы
        o = Order.objects.create(client_car=car4b, status='В работе', order_date='2025-01-14', comment='Сильные стуки в передней подвеске')
        w1 = wos(o, svc_shock, 'Замена амортизаторов передних', 2.5, 1.1)
        w2 = wos(o, svc_align, 'Развал-схождение',              1.0)
        part(o, w1, p_shock_f, 2, 35)
        assign(w1, emp3, emp4); assign(w2, emp3)
        finish(o, '2025-01-15')

        # ══ ЗАКАЗ 18 ══════════════════════════════
        # Новиков / Honda Civic — масло + воздушный фильтр
        o = Order.objects.create(client_car=car16, status='В работе', order_date='2025-01-21', comment='Плановое ТО 45 000 км')
        w1 = wos(o, svc_oil,  'Замена масла и фильтра',    1.0)
        w2 = wos(o, svc_airf, 'Замена воздушного фильтра', 0.3)
        part(o, w1, p_oil_5w40, 1, 25); part(o, w1, p_oilf_bsh, 1, 30)
        part(o, w2, p_airf, 1, 30)
        assign(w1, emp1); assign(w2, emp1)
        finish(o, '2025-01-21')

        # ══ ЗАКАЗ 19 ══════════════════════════════
        # Козлова / Lada Vesta — охлаждающая жидкость + прокладка
        o = Order.objects.create(client_car=car2, status='В работе', order_date='2025-01-28', comment='Потеря уровня антифриза')
        w1 = wos(o, svc_cool, 'Замена охлаждающей жидкости', 1.0)
        part(o, w1, p_cool,   3, 25); part(o, w1, p_gasket, 1, 30)
        assign(w1, emp1)
        finish(o, '2025-01-28')

        # ══ ЗАКАЗ 20 ══════════════════════════════
        # Зайцева / Toyota Corolla — задние амортизаторы
        o = Order.objects.create(client_car=car5, status='В работе', order_date='2025-02-04', comment='Машина клюёт при торможении')
        w1 = wos(o, svc_shock, 'Замена амортизаторов задних', 2.5)
        part(o, w1, p_shock_r, 2, 35)
        assign(w1, emp4)
        finish(o, '2025-02-05')

        # ══ ЗАКАЗ 21 ══════════════════════════════
        # Фёдоров / Honda Accord — диски + колодки передние
        o = Order.objects.create(client_car=car6, status='В работе', order_date='2025-02-11', comment='Увеличенный тормозной путь, биение')
        w1 = wos(o, svc_disc,    'Замена тормозных дисков',         2.0)
        w2 = wos(o, svc_brake_f, 'Замена тормозных колодок перед',  1.5)
        part(o, w1, p_disc_f, 2, 35); part(o, w2, p_brake_f, 4, 35)
        assign(w1, emp3); assign(w2, emp3)
        finish(o, '2025-02-12')

        # ══ ЗАКАЗ 22 ══════════════════════════════
        # Михайлова / Nissan Qashqai — ТО 120 000 км (большое)
        o = Order.objects.create(client_car=car7, status='В работе', order_date='2025-02-18', comment='Плановое ТО 120 000 км')
        w1 = wos(o, svc_oil,   'Замена масла и фильтра',    1.0)
        w2 = wos(o, svc_spark, 'Замена свечей зажигания',   0.5)
        w3 = wos(o, svc_airf,  'Замена воздушного фильтра', 0.3)
        w4 = wos(o, svc_cabin, 'Замена фильтра салона',     0.3)
        w5 = wos(o, svc_fuel,  'Промывка топливной системы',1.5)
        part(o, w1, p_oil_5w40, 1, 25); part(o, w1, p_oilf_mann, 1, 30)
        part(o, w2, p_spark_ngk, 4, 30); part(o, w3, p_airf, 1, 30)
        part(o, w4, p_cabin_f, 1, 30); part(o, w5, p_fuel_f, 1, 30)
        assign(w1, emp2); assign(w2, emp2); assign(w3, emp2)
        assign(w4, emp2); assign(w5, emp1)
        finish(o, '2025-02-19')

        # ══ ЗАКАЗ 23 ══════════════════════════════
        # Соколов / Skoda Octavia — диагностика + промывка
        o = Order.objects.create(client_car=car8, status='В работе', order_date='2025-02-25', comment='Рывки при разгоне')
        w1 = wos(o, svc_diag, 'Компьютерная диагностика',    0.5)
        w2 = wos(o, svc_fuel, 'Промывка топливной системы',  1.5)
        part(o, w2, p_fuel_f, 1, 30)
        assign(w1, emp5); assign(w2, emp1)
        finish(o, '2025-02-25')

        # ══ ЗАКАЗ 24 ══════════════════════════════
        # Попова / Renault Logan — диагностика электрики
        o = Order.objects.create(client_car=car9, status='В работе', order_date='2025-03-04', comment='Не работает парктроник')
        w1 = wos(o, svc_el, 'Диагностика электрики', 1.0)
        assign(w1, emp5)
        finish(o, '2025-03-04')

        # ══ ЗАКАЗ 25 ══════════════════════════════
        # Власов / Ford Focus — задние колодки + развал
        o = Order.objects.create(client_car=car10, status='В работе', order_date='2025-03-11', comment='Плановое ТО ходовой')
        w1 = wos(o, svc_brake_r, 'Замена тормозных колодок зад', 1.0)
        w2 = wos(o, svc_align,   'Развал-схождение',             1.0)
        part(o, w1, p_brake_r, 4, 35)
        assign(w1, emp4); assign(w2, emp3)
        finish(o, '2025-03-11')

        # ══ ЗАКАЗ 26 ══════════════════════════════
        # Лебедев / Toyota RAV4 — масло + свечи Bosch
        o = Order.objects.create(client_car=car11, status='В работе', order_date='2025-03-18', comment='Плановое ТО 50 000 км')
        w1 = wos(o, svc_oil,   'Замена масла и фильтра',  1.0)
        w2 = wos(o, svc_spark, 'Замена свечей зажигания', 0.5)
        part(o, w1, p_oil_5w40, 1, 25); part(o, w1, p_oilf_bsh, 1, 30)
        part(o, w2, p_spark_bsh, 4, 30)
        assign(w1, emp1); assign(w2, emp1)
        finish(o, '2025-03-18')

        # ══ ЗАКАЗ 27 ══════════════════════════════
        # Орлова / Lada Vesta — ремень ГРМ
        o = Order.objects.create(client_car=car12, status='В работе', order_date='2025-03-25', comment='Шум при запуске двигателя')
        w1 = wos(o, svc_belt, 'Замена ремня ГРМ', 3.0)
        part(o, w1, p_belt, 1, 40)
        assign(w1, emp1, emp2)
        finish(o, '2025-03-26')

        # ══ ЗАКАЗ 28 ══════════════════════════════
        # Тихонов / Hyundai Solaris — масло АКПП
        o = Order.objects.create(client_car=car13, status='В работе', order_date='2025-04-01', comment='Толчки при переключении АКПП')
        w1 = wos(o, svc_atf, 'Замена масла АКПП', 1.5)
        part(o, w1, p_atf, 4, 30)
        assign(w1, emp1)
        finish(o, '2025-04-02')

        # ══ ЗАКАЗ 29 ══════════════════════════════
        # Соловьёв / VW Tiguan — ТО 75 000 км
        o = Order.objects.create(client_car=car14, status='В работе', order_date='2025-04-08', comment='Плановое ТО 75 000 км')
        w1 = wos(o, svc_oil,   'Замена масла и фильтра',    1.0)
        w2 = wos(o, svc_airf,  'Замена воздушного фильтра', 0.3)
        w3 = wos(o, svc_cabin, 'Замена фильтра салона',     0.3)
        part(o, w1, p_oil_5w40, 1, 25); part(o, w1, p_oilf_mann, 1, 30)
        part(o, w2, p_airf, 1, 30); part(o, w3, p_cabin_f, 1, 30)
        assign(w1, emp2); assign(w2, emp2); assign(w3, emp2)
        finish(o, '2025-04-08')

        # ══ ЗАКАЗ 30 ══════════════════════════════
        # Белякова / VW Passat — охлаждающая жидкость + диагностика
        o = Order.objects.create(client_car=car15, status='В работе', order_date='2025-04-15', comment='Закипел двигатель, перегрев')
        w1 = wos(o, svc_cool, 'Замена охлаждающей жидкости', 1.0)
        w2 = wos(o, svc_diag, 'Компьютерная диагностика',     0.5)
        part(o, w1, p_cool, 3, 25)
        assign(w1, emp1); assign(w2, emp5)
        finish(o, '2025-04-15')

        # ══ ЗАКАЗ 31 ══════════════════════════════
        # Смирнов / Toyota Camry — диагностика + топливный фильтр
        o = Order.objects.create(client_car=car1, status='В работе', order_date='2025-04-22', comment='Провалы при нажатии газа')
        w1 = wos(o, svc_diag, 'Компьютерная диагностика',    0.5)
        w2 = wos(o, svc_fuel, 'Промывка топливной системы',  1.5)
        part(o, w2, p_fuel_f, 1, 30)
        assign(w1, emp5); assign(w2, emp1)
        finish(o, '2025-04-23')

        # ══ ЗАКАЗ 32 ══════════════════════════════
        # Козлова / Lada Vesta — развал-схождение
        o = Order.objects.create(client_car=car2, status='В работе', order_date='2025-04-29', comment='Уводит в сторону после зимы')
        w1 = wos(o, svc_align, 'Развал-схождение', 1.0)
        assign(w1, emp3)
        finish(o, '2025-04-29')

        # ══ ЗАКАЗ 33 ══════════════════════════════
        # Новиков / VW Polo — большое ТО 100 000 км
        o = Order.objects.create(client_car=car3, status='В работе', order_date='2025-05-06', comment='Большое ТО 100 000 км — по всем позициям')
        w1 = wos(o, svc_oil,   'Замена масла и фильтра',    1.0)
        w2 = wos(o, svc_spark, 'Замена свечей зажигания',   0.5)
        w3 = wos(o, svc_airf,  'Замена воздушного фильтра', 0.3)
        w4 = wos(o, svc_cabin, 'Замена фильтра салона',     0.3)
        w5 = wos(o, svc_belt,  'Замена ремня ГРМ',          3.0, 1.1)
        w6 = wos(o, svc_cool,  'Замена охлаждающей жидкости', 1.0)
        part(o, w1, p_oil_5w30,  1, 25); part(o, w1, p_oilf_mann, 1, 30)
        part(o, w2, p_spark_bsh, 4, 30); part(o, w3, p_airf,       1, 30)
        part(o, w4, p_cabin_f,   1, 30); part(o, w5, p_belt,        1, 40)
        part(o, w6, p_cool,      3, 25)
        assign(w1, emp2); assign(w2, emp2); assign(w3, emp2)
        assign(w4, emp2); assign(w5, emp1, emp4); assign(w6, emp1)
        finish(o, '2025-05-07')

        # ══ ЗАКАЗ 34 ══════════════════════════════
        # Волков / Kia Sportage — передние колодки
        o = Order.objects.create(client_car=car4, status='В работе', order_date='2025-05-07', comment='Визг при торможении')
        w1 = wos(o, svc_brake_f, 'Замена тормозных колодок перед', 1.5)
        part(o, w1, p_brake_f, 4, 35)
        assign(w1, emp3)
        finish(o, '2025-05-07')

        # ══ ЗАКАЗ 35 ══════════════════════════════
        # Фёдоров / Honda Accord — масло + диагностика (отменён, не приехал)
        o = Order.objects.create(client_car=car6, status='В работе', order_date='2025-02-05', comment='Клиент записался, не приехал')
        cancel(o)

        # ══ ЗАКАЗ 36 ══════════════════════════════
        # Попова / Renault Logan — ремень ГРМ (отменён — слишком дорого)
        o = Order.objects.create(client_car=car9, status='Первичный осмотр', order_date='2025-03-20', comment='Клиент отказался от ремонта — слишком дорого')
        cancel(o)

        # ══ ЗАКАЗ 37 ══════════════════════════════
        # Орлова / Lada Vesta — диагностика электрики (отменён, клиент уехал)
        o = Order.objects.create(client_car=car12, status='Первичный осмотр', order_date='2025-04-03', comment='Клиент забрал машину без ремонта')
        cancel(o)

        # ══ ЗАКАЗ 38 ══════════════════════════════
        # Лебедев / Toyota RAV4 — в работе
        o = Order.objects.create(client_car=car11, status='В работе', order_date='2025-05-12', comment='Стук при повороте руля')
        w1 = wos(o, svc_shock, 'Замена передних амортизаторов', 2.5, 1.1)
        w2 = wos(o, svc_align, 'Развал-схождение',              1.0)
        part(o, w1, p_shock_f, 2, 35)
        assign(w1, emp3, emp4)

        # ══ ЗАКАЗ 39 ══════════════════════════════
        # Тихонов / Hyundai Solaris — в работе
        o = Order.objects.create(client_car=car13, status='В работе', order_date='2025-05-12', comment='Не запускается двигатель в мороз')
        w1 = wos(o, svc_diag, 'Компьютерная диагностика', 0.5)
        w2 = wos(o, svc_el,   'Диагностика электрики',    1.0)
        assign(w1, emp5); assign(w2, emp5)

        # ══ ЗАКАЗ 40 ══════════════════════════════
        # Соловьёв / VW Tiguan — в статусе Готов
        o = Order.objects.create(client_car=car14, status='В работе', order_date='2025-05-10', comment='Плановые передние колодки')
        w1 = wos(o, svc_brake_f, 'Замена тормозных колодок перед', 1.5)
        part(o, w1, p_brake_f, 4, 35)
        assign(w1, emp4)
        o.status = 'Готов'
        o.save()

        # ══ ЗАКАЗ 41 ══════════════════════════════
        # Белякова / VW Passat — первичный осмотр
        o = Order.objects.create(client_car=car15, status='Первичный осмотр', order_date='2025-05-13', comment='Стук в моторном отсеке')

        # ══ ЗАКАЗ 42 ══════════════════════════════
        # Михайлова / Nissan Qashqai — диагностика
        o = Order.objects.create(client_car=car7, status='Диагностика', order_date='2025-05-13', comment='Мигает лампа EPC')
        w1 = wos(o, svc_diag, 'Компьютерная диагностика', 0.5)
        assign(w1, emp5)

        # ── Пересчёт стоимости всех заказов ─────
        D = Decimal
        for order_obj in Order.objects.all():
            svcs  = sum(w.final_price or D('0') for w in order_obj.work_order_services.all())
            parts = sum((w.sale_price or D('0')) * w.quantity for w in order_obj.work_order_parts.all())
            Order.objects.filter(pk=order_obj.pk).update(cost=svcs + parts)

        totals = Order.objects.count()
        done   = Order.objects.filter(status='Завершён').count()
        self.stdout.write(f'  Заказов: {totals} (завершено: {done})')
        self.stdout.write(f'  Клиентов: {Client.objects.count()}  |  Сотрудников: {Employee.objects.count()}')
        self.stdout.write(f'  Деталей: {Part.objects.count()}  |  Услуг: {Service.objects.count()}')
