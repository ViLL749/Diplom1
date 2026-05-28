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
        from django.utils import timezone
        from datetime import datetime, timezone as dt_tz
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

        def dt(date_str):
            d = datetime.strptime(date_str, '%Y-%m-%d')
            return d.replace(tzinfo=dt_tz.utc)

        # ── Настройки мастерской ─────────────────
        WorkshopSettings.objects.create(hourly_rate=Decimal('2000.00'))

        # ── Производители ────────────────────────
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
        sup1 = Supplier.objects.create(name='АвтоДеталь',        phone='+7 (495) 111-22-33')
        sup2 = Supplier.objects.create(name='ТехноАвто',         phone='+7 (495) 444-55-66')
        Supplier.objects.create(      name='АвтоЗапчасть Плюс',  phone='+7 (812) 333-44-55')

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
        p_spark_ngk  = Part.objects.create(article='NG-BPR6',  name='Свеча зажигания NGK BPR6ES',                brand='NGK',           category='Расходники',         package_qty=4)
        p_spark_bsh  = Part.objects.create(article='BO-WR78X', name='Свеча зажигания Bosch WR78X',               brand='Bosch',         category='Расходники',         package_qty=4)
        p_spark_dns  = Part.objects.create(article='DN-K16R',  name='Свеча зажигания Denso K16R-U',              brand='Denso',         category='Расходники',         package_qty=4)
        p_oil_5w40   = Part.objects.create(article='CS-5W40',  name='Масло моторное Castrol 5W-40 4л',           brand='Castrol',       category='Расходники',         package_qty=1)
        p_oil_5w30   = Part.objects.create(article='LM-5W30',  name='Масло моторное Liqui Moly 5W-30 4л',        brand='Liqui Moly',    category='Расходники',         package_qty=1)
        p_oilf_mann  = Part.objects.create(article='MN-W712',  name='Фильтр масляный Mann W712/75',              brand='Mann Filter',   category='Расходники',         package_qty=1)
        p_oilf_bsh   = Part.objects.create(article='BO-0451',  name='Фильтр масляный Bosch 0451103063',          brand='Bosch',         category='Расходники',         package_qty=1)
        p_airf       = Part.objects.create(article='BO-S0026', name='Фильтр воздушный Bosch S0026',              brand='Bosch',         category='Расходники',         package_qty=1)
        p_cabin_f    = Part.objects.create(article='MN-CUK27', name='Фильтр салона Mann CUK27030',               brand='Mann Filter',   category='Расходники',         package_qty=1)
        p_fuel_f     = Part.objects.create(article='BO-F026',  name='Фильтр топливный Bosch F026',               brand='Bosch',         category='Расходники',         package_qty=1)
        p_brake_f    = Part.objects.create(article='BR-P06',   name='Колодки тормозные передние Brembo P06',     brand='Brembo',        category='Тормозная система',  package_qty=4)
        p_brake_r    = Part.objects.create(article='BR-R04',   name='Колодки тормозные задние Brembo R04',       brand='Brembo',        category='Тормозная система',  package_qty=4)
        p_disc_f     = Part.objects.create(article='BR-D09',   name='Диск тормозной передний Brembo D09',        brand='Brembo',        category='Тормозная система',  package_qty=1)
        p_belt       = Part.objects.create(article='GT-K015',  name='Ремень ГРМ Gates K015',                     brand='Gates',         category='Двигатель',          package_qty=1)
        p_cool       = Part.objects.create(article='LM-AF5',   name='Антифриз Liqui Moly G12 5л',                brand='Liqui Moly',    category='Расходники',         package_qty=1)
        p_shock_f    = Part.objects.create(article='KY-334',   name='Стойка амортизатора передняя KYB 334',      brand='KYB',           category='Ходовая',            package_qty=1)
        p_shock_r    = Part.objects.create(article='KY-444',   name='Амортизатор задний KYB 444',                brand='KYB',           category='Ходовая',            package_qty=1)
        p_atf        = Part.objects.create(article='LM-ATF',   name='Масло АКПП Liqui Moly ATF III 4л',          brand='Liqui Moly',    category='Трансмиссия',        package_qty=1)
        p_brake_fl   = Part.objects.create(article='LM-DOT4',  name='Жидкость тормозная Liqui Moly DOT-4 0.5л', brand='Liqui Moly',    category='Тормозная система',  package_qty=1)
        p_gasket     = Part.objects.create(article='FB-VS01',  name='Прокладка клапанной крышки Febi 001',       brand='Febi Bilstein', category='Двигатель',          package_qty=1)

        # ── Поставка 1 — август 2024 ─────────────
        supply1 = SupplyDocument.objects.create(supplier=sup1, created_at=dt('2024-08-15'))

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

        receive(supply1, p_spark_ngk,  loc_a1, 28, 4, Decimal('250.00'))
        receive(supply1, p_spark_bsh,  loc_a1, 16, 4, Decimal('280.00'))
        receive(supply1, p_spark_dns,  loc_a1, 16, 4, Decimal('240.00'))
        receive(supply1, p_oil_5w40,   loc_a2, 14, 1, Decimal('1200.00'))
        receive(supply1, p_oil_5w30,   loc_a2, 10, 1, Decimal('1100.00'))
        receive(supply1, p_oilf_mann,  loc_a2, 16, 1, Decimal('350.00'))
        receive(supply1, p_oilf_bsh,   loc_a2, 12, 1, Decimal('380.00'))
        receive(supply1, p_airf,       loc_a3, 14, 1, Decimal('450.00'))
        receive(supply1, p_cabin_f,    loc_a3, 10, 1, Decimal('420.00'))
        receive(supply1, p_fuel_f,     loc_a3,  8, 1, Decimal('380.00'))
        receive(supply1, p_brake_f,    loc_b1, 20, 4, Decimal('1800.00'))
        receive(supply1, p_brake_r,    loc_b1, 12, 4, Decimal('1600.00'))
        receive(supply1, p_disc_f,     loc_b1,  6, 1, Decimal('2800.00'))
        receive(supply1, p_belt,       loc_b2,  8, 1, Decimal('2200.00'))
        receive(supply1, p_cool,       loc_b2, 12, 1, Decimal('800.00'))
        receive(supply1, p_shock_f,    loc_b3,  6, 1, Decimal('3500.00'))
        receive(supply1, p_shock_r,    loc_b3,  6, 1, Decimal('2800.00'))
        receive(supply1, p_atf,        loc_c1,  8, 1, Decimal('1400.00'))
        receive(supply1, p_brake_fl,   loc_c1, 16, 1, Decimal('220.00'))
        receive(supply1, p_gasket,     loc_c1,  4, 1, Decimal('650.00'))

        # ── Поставка 2 — январь 2025 (пополнение) ──
        supply2 = SupplyDocument.objects.create(supplier=sup2, created_at=dt('2025-01-10'))

        # Цены на расходники немного выросли — реалистично
        receive(supply2, p_spark_ngk,  loc_a1, 20, 4, Decimal('265.00'))
        receive(supply2, p_spark_bsh,  loc_a1, 12, 4, Decimal('295.00'))
        receive(supply2, p_spark_dns,  loc_a1,  8, 4, Decimal('255.00'))
        receive(supply2, p_oil_5w40,   loc_a2, 14, 1, Decimal('1290.00'))
        receive(supply2, p_oil_5w30,   loc_a2, 10, 1, Decimal('1180.00'))
        receive(supply2, p_oilf_mann,  loc_a2, 12, 1, Decimal('370.00'))
        receive(supply2, p_oilf_bsh,   loc_a2, 12, 1, Decimal('400.00'))
        receive(supply2, p_airf,       loc_a3, 12, 1, Decimal('470.00'))
        receive(supply2, p_cabin_f,    loc_a3, 10, 1, Decimal('440.00'))
        receive(supply2, p_fuel_f,     loc_a3,  6, 1, Decimal('400.00'))
        receive(supply2, p_brake_f,    loc_b1, 20, 4, Decimal('1900.00'))
        receive(supply2, p_brake_r,    loc_b1, 16, 4, Decimal('1680.00'))
        receive(supply2, p_disc_f,     loc_b1,  6, 1, Decimal('2950.00'))
        receive(supply2, p_belt,       loc_b2,  8, 1, Decimal('2300.00'))
        receive(supply2, p_cool,       loc_b2, 10, 1, Decimal('850.00'))
        receive(supply2, p_shock_f,    loc_b3,  6, 1, Decimal('3650.00'))
        receive(supply2, p_shock_r,    loc_b3,  6, 1, Decimal('2950.00'))
        receive(supply2, p_atf,        loc_c1,  8, 1, Decimal('1480.00'))
        receive(supply2, p_brake_fl,   loc_c1,  8, 1, Decimal('235.00'))
        receive(supply2, p_gasket,     loc_c1,  4, 1, Decimal('680.00'))

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
        mitsubishi = CarMake.objects.create(name='Mitsubishi')
        mazda   = CarMake.objects.create(name='Mazda')

        camry    = CarModel.objects.create(make=toyota,     name='Camry')
        corolla  = CarModel.objects.create(make=toyota,     name='Corolla')
        rav4     = CarModel.objects.create(make=toyota,     name='RAV4')
        vesta    = CarModel.objects.create(make=lada,       name='Vesta')
        granta   = CarModel.objects.create(make=lada,       name='Granta')
        niva     = CarModel.objects.create(make=lada,       name='Niva Travel')
        polo     = CarModel.objects.create(make=vw,         name='Polo')
        passat   = CarModel.objects.create(make=vw,         name='Passat')
        tiguan   = CarModel.objects.create(make=vw,         name='Tiguan')
        rio      = CarModel.objects.create(make=kia,        name='Rio')
        sportage = CarModel.objects.create(make=kia,        name='Sportage')
        accord   = CarModel.objects.create(make=honda,      name='Accord')
        civic    = CarModel.objects.create(make=honda,      name='Civic')
        qashqai  = CarModel.objects.create(make=nissan,     name='Qashqai')
        teana    = CarModel.objects.create(make=nissan,     name='Teana')
        octavia  = CarModel.objects.create(make=skoda,      name='Octavia')
        logan    = CarModel.objects.create(make=renault,    name='Logan')
        solaris  = CarModel.objects.create(make=hyundai,    name='Solaris')
        tucson   = CarModel.objects.create(make=hyundai,    name='Tucson')
        focus    = CarModel.objects.create(make=ford,       name='Focus')
        outlander= CarModel.objects.create(make=mitsubishi, name='Outlander')
        cx5      = CarModel.objects.create(make=mazda,      name='CX-5')

        # ── Клиенты ──────────────────────────────
        # Россия — различные операторы и коды регионов
        c1  = Client.objects.create(fio='Смирнов Андрей Петрович',       phone='+7 (916) 123-45-67')  # MTC Moscow
        c2  = Client.objects.create(fio='Козлова Мария Ивановна',        phone='+7 (921) 456-78-90')  # Megafon SPb
        c3  = Client.objects.create(fio='Новиков Сергей Олегович',       phone='+7 (926) 789-01-23')  # Megafon Moscow
        c4  = Client.objects.create(fio='Волков Игорь Дмитриевич',       phone='+7 (950) 234-56-78')  # Tele2
        c5  = Client.objects.create(fio='Зайцева Анна Николаевна',       phone='+7 (985) 567-89-01')  # MTS
        c6  = Client.objects.create(fio='Фёдоров Павел Юрьевич',         phone='+7 (903) 987-65-43')  # Beeline
        c7  = Client.objects.create(fio='Михайлова Елена Владимировна',  phone='+7 (962) 876-54-32')  # Tele2 SPb
        c8  = Client.objects.create(fio='Соколов Роман Аркадьевич',      phone='+7 (919) 765-43-21')  # MTS
        c9  = Client.objects.create(fio='Попова Оксана Борисовна',       phone='+7 (905) 654-32-10')  # Beeline
        c10 = Client.objects.create(fio='Власов Виктор Геннадьевич',     phone='+7 (908) 543-21-09')  # Tele2
        c11 = Client.objects.create(fio='Лебедев Константин Михайлович', phone='+7 (929) 432-10-98')  # MTS
        c12 = Client.objects.create(fio='Орлова Ирина Анатольевна',      phone='+7 (967) 321-09-87')  # Tele2
        c13 = Client.objects.create(fio='Тихонов Максим Сергеевич',      phone='+7 (906) 210-98-76')  # Beeline
        c14 = Client.objects.create(fio='Соловьёв Антон Игоревич',       phone='+7 (937) 109-87-65')  # MTS
        c15 = Client.objects.create(fio='Белякова Татьяна Николаевна',   phone='+7 (977) 098-76-54')  # MTS
        # Казахстан — клиент с казахстанским номером
        c16 = Client.objects.create(fio='Ахметов Нурлан Сериккалиевич',  phone='+7 (701) 234-56-78')  # Kcell KZ
        # Беларусь — клиент с белорусским номером
        c17 = Client.objects.create(fio='Мацкевич Дмитрий Иванович',     phone='+375 (29) 712-34-56')  # MTS BY
        # Россия — ещё двое
        c18 = Client.objects.create(fio='Ковалёва Светлана Вячеславовна',phone='+7 (931) 887-65-43')  # Megafon

        # ── Автомобили ────────────────────────────
        # Допустимые буквы в рос. номерах: А В Е К М Н О Р С Т У Х
        # Регионы: 77/99=Москва, 78/98=Питер, 50=Моск.обл., 163=Самара, 96=Свердловск, 23=Краснодар

        # Смирнов — два авто
        car1  = ClientCar.objects.create(client=c1,  make=toyota,     model=camry,    year=2019, color='Белый',        license_plate='А777ВВ77',  vin='1NXBR32E5XZ123456')
        car1b = ClientCar.objects.create(client=c1,  make=lada,       model=granta,   year=2014, color='Серебристый',  license_plate='О120ТТ77',  vin='')  # старая Гранта без VIN в базе
        # Козлова
        car2  = ClientCar.objects.create(client=c2,  make=lada,       model=vesta,    year=2021, color='Серый',        license_plate='В123АА78',  vin='XTA52300LM3345678')
        # Новиков — два авто
        car3  = ClientCar.objects.create(client=c3,  make=vw,         model=polo,     year=2018, color='Синий',        license_plate='С456ВВ77',  vin='WVWZZZ6RZJ1456789')
        car16 = ClientCar.objects.create(client=c3,  make=honda,      model=civic,    year=2022, color='Красный',      license_plate='С159РР77',  vin='2HGFE2F52NH678901')
        # Волков — два авто
        car4  = ClientCar.objects.create(client=c4,  make=kia,        model=sportage, year=2020, color='Чёрный',       license_plate='К789ОО77',  vin='U5YPH813ALT567890')
        car4b = ClientCar.objects.create(client=c4,  make=kia,        model=rio,      year=2013, color='Белый',        license_plate='К188АА50',  vin='')  # Rio 2013, VIN не читается
        # Зайцева
        car5  = ClientCar.objects.create(client=c5,  make=toyota,     model=corolla,  year=2017, color='Серебристый',  license_plate='Е012ММ77',  vin='JTDBZ3EH9H0789012')
        # Фёдоров
        car6  = ClientCar.objects.create(client=c6,  make=honda,      model=accord,   year=2020, color='Тёмно-синий',  license_plate='Т345ЕЕ77',  vin='1HGCV1F37LA890123')
        # Михайлова
        car7  = ClientCar.objects.create(client=c7,  make=nissan,     model=qashqai,  year=2019, color='Бежевый',      license_plate='У678КК77',  vin='JN1BAYS62U0901234')
        # Соколов
        car8  = ClientCar.objects.create(client=c8,  make=skoda,      model=octavia,  year=2021, color='Серый',        license_plate='Х901НН78',  vin='TMBJE75L4MA012345')
        # Попова
        car9  = ClientCar.objects.create(client=c9,  make=renault,    model=logan,    year=2016, color='Белый',        license_plate='К234СС77',  vin='VF1LS1G0H47123456')
        # Власов
        car10 = ClientCar.objects.create(client=c10, make=ford,       model=focus,    year=2017, color='Красный',      license_plate='Р567КК163', vin='WF05XXGBB5GR23456')
        # Лебедев
        car11 = ClientCar.objects.create(client=c11, make=toyota,     model=rav4,     year=2022, color='Белый',        license_plate='М890ОО77',  vin='JTMH3REV0ND234567')
        # Орлова
        car12 = ClientCar.objects.create(client=c12, make=lada,       model=vesta,    year=2020, color='Синий',        license_plate='Н345МВ77',  vin='XTA52300LL3456789')
        # Тихонов
        car13 = ClientCar.objects.create(client=c13, make=hyundai,    model=solaris,  year=2018, color='Чёрный',       license_plate='О456НН77',  vin='KMHCT41BAFU345678')
        # Соловьёв
        car14 = ClientCar.objects.create(client=c14, make=vw,         model=tiguan,   year=2021, color='Серый',        license_plate='С789ОО77',  vin='WVGZZZ5NZMU456789')
        # Белякова
        car15 = ClientCar.objects.create(client=c15, make=vw,         model=passat,   year=2019, color='Тёмно-серый',  license_plate='Р012ТТ96',  vin='WVWZZZ3CZKU567890')
        # Ахметов — казахстанский номер, авто куплено в Казахстане (без VIN в системе)
        car17 = ClientCar.objects.create(client=c16, make=toyota,     model=camry,    year=2015, color='Белый',        license_plate='А123ВС',    vin='')
        # Мацкевич — белорусский номер
        car18 = ClientCar.objects.create(client=c17, make=vw,         model=passat,   year=2017, color='Серебристый',  license_plate='7823АВ-7',  vin='WVWZZZ3CZ8M102938')
        # Ковалёва
        car19 = ClientCar.objects.create(client=c18, make=mitsubishi, model=outlander,year=2020, color='Тёмно-зелёный',license_plate='Е547КМ23',  vin='JA4AZ3A33LZ012345')
        # Смирнов — ещё Niva (старая, нет VIN)
        car20 = ClientCar.objects.create(client=c1,  make=lada,       model=niva,     year=2008, color='Зелёный',      license_plate='О981СС77',  vin='')
        # Соколов — Nissan Teana
        car21 = ClientCar.objects.create(client=c8,  make=nissan,     model=teana,    year=2012, color='Чёрный',       license_plate='Х023ВВ78',  vin='')  # 2012 — VIN стёрт
        # Тихонов — Hyundai Tucson
        car22 = ClientCar.objects.create(client=c13, make=hyundai,    model=tucson,   year=2023, color='Белый',        license_plate='О344КК77',  vin='TMBJB81HXPJ198765')
        # Лебедев — Mazda CX-5
        car23 = ClientCar.objects.create(client=c11, make=mazda,      model=cx5,      year=2021, color='Серебристый',  license_plate='М217АА50',  vin='JM0KE4DY9L1234567')

        # ── Типы услуг ───────────────────────────
        st_to  = ServiceType.objects.create(name='Техническое обслуживание')
        st_hod = ServiceType.objects.create(name='Ходовая часть')
        st_dv  = ServiceType.objects.create(name='Двигатель')
        st_el  = ServiceType.objects.create(name='Электрика')
        st_tr  = ServiceType.objects.create(name='Трансмиссия')

        # ── Услуги ───────────────────────────────
        svc_oil    = Service.objects.create(name='Замена масла и фильтра',          service_type=st_to,  base_hours=Decimal('1.0'))
        svc_spark  = Service.objects.create(name='Замена свечей зажигания',         service_type=st_to,  base_hours=Decimal('0.5'))
        svc_airf   = Service.objects.create(name='Замена воздушного фильтра',       service_type=st_to,  base_hours=Decimal('0.3'))
        svc_cabin  = Service.objects.create(name='Замена фильтра салона',           service_type=st_to,  base_hours=Decimal('0.3'))
        svc_cool   = Service.objects.create(name='Замена охлаждающей жидкости',     service_type=st_to,  base_hours=Decimal('1.0'))
        svc_diag   = Service.objects.create(name='Компьютерная диагностика',        service_type=st_to,  base_hours=Decimal('0.5'))
        svc_brake_f= Service.objects.create(name='Замена тормозных колодок перед',  service_type=st_hod, base_hours=Decimal('1.5'))
        svc_brake_r= Service.objects.create(name='Замена тормозных колодок зад',    service_type=st_hod, base_hours=Decimal('1.0'))
        svc_disc   = Service.objects.create(name='Замена тормозных дисков',         service_type=st_hod, base_hours=Decimal('2.0'))
        svc_shock  = Service.objects.create(name='Замена амортизаторов',            service_type=st_hod, base_hours=Decimal('2.5'))
        svc_align  = Service.objects.create(name='Развал-схождение',                service_type=st_hod, base_hours=Decimal('1.0'))
        svc_belt   = Service.objects.create(name='Замена ремня ГРМ',                service_type=st_dv,  base_hours=Decimal('3.0'))
        svc_fuel   = Service.objects.create(name='Промывка топливной системы',      service_type=st_dv,  base_hours=Decimal('1.5'))
        svc_atf    = Service.objects.create(name='Замена масла АКПП',               service_type=st_tr,  base_hours=Decimal('1.5'))
        svc_el     = Service.objects.create(name='Диагностика электрики',           service_type=st_el,  base_hours=Decimal('1.0'))

        # ── Сотрудники ───────────────────────────
        # salary_coefficient: 1.0 = обычный, 1.2 = старший, 1.5 = ведущий
        emp1 = Employee.objects.create(
            name='Иванов Дмитрий Сергеевич',     position='Ведущий механик',
            phone_country='RU', phone='+7 (901) 111-22-33', salary_coefficient=Decimal('1.50'),
        )
        emp2 = Employee.objects.create(
            name='Петров Алексей Иванович',       position='Механик',
            phone_country='RU', phone='+7 (902) 444-55-66', salary_coefficient=Decimal('1.00'),
        )
        emp3 = Employee.objects.create(
            name='Сидоров Кирилл Андреевич',      position='Механик',
            phone_country='RU', phone='+7 (903) 777-88-99', salary_coefficient=Decimal('1.00'),
        )
        emp4 = Employee.objects.create(
            name='Орлов Николай Петрович',         position='Механик',
            phone_country='RU', phone='+7 (904) 000-11-22', salary_coefficient=Decimal('1.10'),
        )
        emp5 = Employee.objects.create(
            name='Карпов Евгений Александрович',   position='Диагност',
            phone_country='RU', phone='+7 (905) 333-44-55', salary_coefficient=Decimal('1.20'),
        )
        # Сотрудник из Беларуси — переехал, работает в мастерской
        emp6 = Employee.objects.create(
            name='Дорошенко Виталий Николаевич',  position='Слесарь-электрик',
            phone_country='BY', phone='+375 (44) 712-34-56', salary_coefficient=Decimal('1.10'),
        )
        # Сотрудник из Казахстана
        emp7 = Employee.objects.create(
            name='Сейтжанов Арман Бекович',       position='Механик',
            phone_country='KZ', phone='+7 (707) 123-45-67', salary_coefficient=Decimal('1.00'),
        )

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
            sale_total = (cost * qty * (1 + Decimal(str(markup_pct)) / 100)).quantize(Decimal('0.01'))
            WorkOrderPart.objects.create(
                work_order=order, work_order_service=wos_obj,
                part=p, quantity=qty,
                sale_price=sale_total, markup=Decimal(str(markup_pct)),
                status='installed',
            )
            remaining = qty
            for e in StockEntry.objects.filter(part=p):
                if remaining <= 0:
                    break
                take = min(e.total_qty, remaining)
                if take > 0:
                    e.total_qty -= take
                    e.save()
                    remaining -= take

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
        w1 = wos(o, svc_oil,   'Замена масла и фильтра',    1.0)
        w2 = wos(o, svc_airf,  'Замена воздушного фильтра', 0.3)
        w3 = wos(o, svc_cabin, 'Замена фильтра салона',     0.3)
        part(o, w1, p_oil_5w40, 1, 25); part(o, w1, p_oilf_mann, 1, 30)
        part(o, w2, p_airf,     1, 30); part(o, w3, p_cabin_f,    1, 30)
        assign(w1, emp1); assign(w2, emp1); assign(w3, emp2)
        finish(o, '2024-09-03')

        # ══ ЗАКАЗ 2 ══════════════════════════════
        # Козлова / Lada Vesta — замена свечей (пропуск зажигания)
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
        # Волков / Kia Sportage — ремень ГРМ (двое механиков)
        o = Order.objects.create(client_car=car4, status='В работе', order_date='2024-09-24', comment='Подтёк масла, плановая замена ремня ГРМ')
        w1 = wos(o, svc_belt, 'Замена ремня ГРМ', 3.0, 1.2)
        part(o, w1, p_belt, 1, 40)
        assign(w1, emp1, emp2)
        finish(o, '2024-09-25')

        # ══ ЗАКАЗ 5 ══════════════════════════════
        # Зайцева / Toyota Corolla — диагностика + масло
        o = Order.objects.create(client_car=car5, status='В работе', order_date='2024-10-01', comment='Горит лампа Check Engine')
        w1 = wos(o, svc_diag, 'Компьютерная диагностика', 0.5)
        w2 = wos(o, svc_oil,  'Замена масла и фильтра',   1.0)
        part(o, w2, p_oil_5w30, 1, 25); part(o, w2, p_oilf_bsh, 1, 30)
        assign(w1, emp5); assign(w2, emp2)
        finish(o, '2024-10-02')

        # ══ ЗАКАЗ 6 ══════════════════════════════
        # Фёдоров / Honda Accord — замена масла АКПП (пинки при переключении)
        o = Order.objects.create(client_car=car6, status='В работе', order_date='2024-10-08', comment='Пинки при переключении передач')
        w1 = wos(o, svc_atf, 'Замена масла АКПП', 1.5)
        part(o, w1, p_atf, 4, 30)
        assign(w1, emp1)
        finish(o, '2024-10-09')

        # ══ ЗАКАЗ 7 ══════════════════════════════
        # Михайлова / Nissan Qashqai — стойки + развал-схождение
        o = Order.objects.create(client_car=car7, status='В работе', order_date='2024-10-15', comment='Уводит вправо, стуки в передней подвеске')
        w1 = wos(o, svc_shock, 'Замена амортизаторов передних', 2.5, 1.1)
        w2 = wos(o, svc_align, 'Развал-схождение',              1.0)
        part(o, w1, p_shock_f, 2, 35)
        assign(w1, emp3, emp4); assign(w2, emp3)
        finish(o, '2024-10-16')

        # ══ ЗАКАЗ 8 ══════════════════════════════
        # Соколов / Skoda Octavia — тормозные диски и колодки перед
        o = Order.objects.create(client_car=car8, status='В работе', order_date='2024-10-22', comment='Вибрация при торможении')
        w1 = wos(o, svc_disc,    'Замена тормозных дисков',        2.0)
        w2 = wos(o, svc_brake_f, 'Замена тормозных колодок перед', 1.5)
        part(o, w1, p_disc_f, 2, 35); part(o, w2, p_brake_f, 4, 35)
        assign(w1, emp4); assign(w2, emp4)
        finish(o, '2024-10-23')

        # ══ ЗАКАЗ 9 ══════════════════════════════
        # Попова / Renault Logan — ТО 30 000 км + свечи
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
        # Лебедев / Toyota RAV4 — задние тормозные колодки
        o = Order.objects.create(client_car=car11, status='В работе', order_date='2024-11-19', comment='Задние тормоза скрипят при парковке')
        w1 = wos(o, svc_brake_r, 'Замена тормозных колодок зад', 1.0)
        part(o, w1, p_brake_r, 4, 35)
        assign(w1, emp3)
        finish(o, '2024-11-19')

        # ══ ЗАКАЗ 12 ══════════════════════════════
        # Орлова / Lada Vesta — диагностика электрики (не заряжается аккумулятор)
        o = Order.objects.create(client_car=car12, status='В работе', order_date='2024-11-26', comment='Не заряжается аккумулятор')
        w1 = wos(o, svc_el, 'Диагностика электрики', 1.0)
        assign(w1, emp6)
        finish(o, '2024-11-26')

        # ══ ЗАКАЗ 13 ══════════════════════════════
        # Тихонов / Hyundai Solaris — большое ТО 90 000 км
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
        w2 = wos(o, svc_diag,    'Компьютерная диагностика',     0.5)
        part(o, w1, p_brake_r, 4, 35); part(o, w1, p_brake_fl, 2, 25)
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
        # Смирнов / Lada Granta — масло + свечи (давно не обслуживалась)
        o = Order.objects.create(client_car=car1b, status='В работе', order_date='2025-01-09', comment='Давно не обслуживалась')
        w1 = wos(o, svc_oil,   'Замена масла и фильтра',  1.0)
        w2 = wos(o, svc_spark, 'Замена свечей зажигания', 0.5)
        part(o, w1, p_oil_5w30, 1, 25); part(o, w1, p_oilf_mann, 1, 30)
        part(o, w2, p_spark_ngk, 4, 30)
        assign(w1, emp2); assign(w2, emp2)
        finish(o, '2025-01-09')

        # ══ ЗАКАЗ 17 ══════════════════════════════
        # Волков / Kia Rio — передние амортизаторы (сильные стуки)
        o = Order.objects.create(client_car=car4b, status='В работе', order_date='2025-01-14', comment='Сильные стуки в передней подвеске')
        w1 = wos(o, svc_shock, 'Замена амортизаторов передних', 2.5, 1.1)
        w2 = wos(o, svc_align, 'Развал-схождение',              1.0)
        part(o, w1, p_shock_f, 2, 35)
        assign(w1, emp3, emp7); assign(w2, emp3)
        finish(o, '2025-01-15')

        # ══ ЗАКАЗ 18 ══════════════════════════════
        # Новиков / Honda Civic — плановое ТО 45 000 км
        o = Order.objects.create(client_car=car16, status='В работе', order_date='2025-01-21', comment='Плановое ТО 45 000 км')
        w1 = wos(o, svc_oil,  'Замена масла и фильтра',    1.0)
        w2 = wos(o, svc_airf, 'Замена воздушного фильтра', 0.3)
        part(o, w1, p_oil_5w40, 1, 25); part(o, w1, p_oilf_bsh, 1, 30)
        part(o, w2, p_airf, 1, 30)
        assign(w1, emp1); assign(w2, emp1)
        finish(o, '2025-01-21')

        # ══ ЗАКАЗ 19 ══════════════════════════════
        # Козлова / Lada Vesta — охлаждающая жидкость + прокладка (потеря уровня)
        o = Order.objects.create(client_car=car2, status='В работе', order_date='2025-01-28', comment='Потеря уровня антифриза')
        w1 = wos(o, svc_cool, 'Замена охлаждающей жидкости', 1.0)
        part(o, w1, p_cool, 3, 25); part(o, w1, p_gasket, 1, 30)
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
        # Фёдоров / Honda Accord — диски + колодки передние (увеличенный тормозной путь)
        o = Order.objects.create(client_car=car6, status='В работе', order_date='2025-02-11', comment='Увеличенный тормозной путь, биение')
        w1 = wos(o, svc_disc,    'Замена тормозных дисков',        2.0)
        w2 = wos(o, svc_brake_f, 'Замена тормозных колодок перед', 1.5)
        part(o, w1, p_disc_f, 2, 35); part(o, w2, p_brake_f, 4, 35)
        assign(w1, emp3); assign(w2, emp3)
        finish(o, '2025-02-12')

        # ══ ЗАКАЗ 22 ══════════════════════════════
        # Михайлова / Nissan Qashqai — большое ТО 120 000 км
        o = Order.objects.create(client_car=car7, status='В работе', order_date='2025-02-18', comment='Плановое ТО 120 000 км')
        w1 = wos(o, svc_oil,   'Замена масла и фильтра',     1.0)
        w2 = wos(o, svc_spark, 'Замена свечей зажигания',    0.5)
        w3 = wos(o, svc_airf,  'Замена воздушного фильтра',  0.3)
        w4 = wos(o, svc_cabin, 'Замена фильтра салона',      0.3)
        w5 = wos(o, svc_fuel,  'Промывка топливной системы', 1.5)
        part(o, w1, p_oil_5w40, 1, 25); part(o, w1, p_oilf_mann, 1, 30)
        part(o, w2, p_spark_ngk, 4, 30); part(o, w3, p_airf, 1, 30)
        part(o, w4, p_cabin_f, 1, 30); part(o, w5, p_fuel_f, 1, 30)
        assign(w1, emp2); assign(w2, emp2); assign(w3, emp2)
        assign(w4, emp2); assign(w5, emp1)
        finish(o, '2025-02-19')

        # ══ ЗАКАЗ 23 ══════════════════════════════
        # Соколов / Skoda Octavia — диагностика + промывка (рывки при разгоне)
        o = Order.objects.create(client_car=car8, status='В работе', order_date='2025-02-25', comment='Рывки при разгоне')
        w1 = wos(o, svc_diag, 'Компьютерная диагностика',   0.5)
        w2 = wos(o, svc_fuel, 'Промывка топливной системы', 1.5)
        part(o, w2, p_fuel_f, 1, 30)
        assign(w1, emp5); assign(w2, emp1)
        finish(o, '2025-02-25')

        # ══ ЗАКАЗ 24 ══════════════════════════════
        # Попова / Renault Logan — диагностика электрики (не работает парктроник)
        o = Order.objects.create(client_car=car9, status='В работе', order_date='2025-03-04', comment='Не работает парктроник')
        w1 = wos(o, svc_el, 'Диагностика электрики', 1.0)
        assign(w1, emp6)
        finish(o, '2025-03-04')

        # ══ ЗАКАЗ 25 ══════════════════════════════
        # Власов / Ford Focus — задние колодки + развал (плановое ТО ходовой)
        o = Order.objects.create(client_car=car10, status='В работе', order_date='2025-03-11', comment='Плановое ТО ходовой')
        w1 = wos(o, svc_brake_r, 'Замена тормозных колодок зад', 1.0)
        w2 = wos(o, svc_align,   'Развал-схождение',             1.0)
        part(o, w1, p_brake_r, 4, 35)
        assign(w1, emp4); assign(w2, emp3)
        finish(o, '2025-03-11')

        # ══ ЗАКАЗ 26 ══════════════════════════════
        # Лебедев / Toyota RAV4 — масло + свечи Bosch (ТО 50 000 км)
        o = Order.objects.create(client_car=car11, status='В работе', order_date='2025-03-18', comment='Плановое ТО 50 000 км')
        w1 = wos(o, svc_oil,   'Замена масла и фильтра',  1.0)
        w2 = wos(o, svc_spark, 'Замена свечей зажигания', 0.5)
        part(o, w1, p_oil_5w40, 1, 25); part(o, w1, p_oilf_bsh, 1, 30)
        part(o, w2, p_spark_bsh, 4, 30)
        assign(w1, emp1); assign(w2, emp1)
        finish(o, '2025-03-18')

        # ══ ЗАКАЗ 27 ══════════════════════════════
        # Орлова / Lada Vesta — ремень ГРМ (шум при запуске)
        o = Order.objects.create(client_car=car12, status='В работе', order_date='2025-03-25', comment='Шум при запуске двигателя')
        w1 = wos(o, svc_belt, 'Замена ремня ГРМ', 3.0)
        part(o, w1, p_belt, 1, 40)
        assign(w1, emp1, emp2)
        finish(o, '2025-03-26')

        # ══ ЗАКАЗ 28 ══════════════════════════════
        # Тихонов / Hyundai Solaris — масло АКПП (толчки при переключении)
        o = Order.objects.create(client_car=car13, status='В работе', order_date='2025-04-01', comment='Толчки при переключении АКПП')
        w1 = wos(o, svc_atf, 'Замена масла АКПП', 1.5)
        part(o, w1, p_atf, 4, 30)
        assign(w1, emp1)
        finish(o, '2025-04-02')

        # ══ ЗАКАЗ 29 ══════════════════════════════
        # Соловьёв / VW Tiguan — плановое ТО 75 000 км
        o = Order.objects.create(client_car=car14, status='В работе', order_date='2025-04-08', comment='Плановое ТО 75 000 км')
        w1 = wos(o, svc_oil,   'Замена масла и фильтра',    1.0)
        w2 = wos(o, svc_airf,  'Замена воздушного фильтра', 0.3)
        w3 = wos(o, svc_cabin, 'Замена фильтра салона',     0.3)
        part(o, w1, p_oil_5w40, 1, 25); part(o, w1, p_oilf_mann, 1, 30)
        part(o, w2, p_airf, 1, 30); part(o, w3, p_cabin_f, 1, 30)
        assign(w1, emp2); assign(w2, emp2); assign(w3, emp2)
        finish(o, '2025-04-08')

        # ══ ЗАКАЗ 30 ══════════════════════════════
        # Белякова / VW Passat — охлаждающая жидкость + диагностика (перегрев)
        o = Order.objects.create(client_car=car15, status='В работе', order_date='2025-04-15', comment='Закипел двигатель, перегрев')
        w1 = wos(o, svc_cool, 'Замена охлаждающей жидкости', 1.0)
        w2 = wos(o, svc_diag, 'Компьютерная диагностика',    0.5)
        part(o, w1, p_cool, 3, 25)
        assign(w1, emp1); assign(w2, emp5)
        finish(o, '2025-04-15')

        # ══ ЗАКАЗ 31 ══════════════════════════════
        # Смирнов / Toyota Camry — диагностика + промывка топливной системы
        o = Order.objects.create(client_car=car1, status='В работе', order_date='2025-04-22', comment='Провалы при нажатии газа')
        w1 = wos(o, svc_diag, 'Компьютерная диагностика',   0.5)
        w2 = wos(o, svc_fuel, 'Промывка топливной системы', 1.5)
        part(o, w2, p_fuel_f, 1, 30)
        assign(w1, emp5); assign(w2, emp1)
        finish(o, '2025-04-23')

        # ══ ЗАКАЗ 32 ══════════════════════════════
        # Козлова / Lada Vesta — развал-схождение после зимы
        o = Order.objects.create(client_car=car2, status='В работе', order_date='2025-04-29', comment='Уводит в сторону после зимы')
        w1 = wos(o, svc_align, 'Развал-схождение', 1.0)
        assign(w1, emp3)
        finish(o, '2025-04-29')

        # ══ ЗАКАЗ 33 ══════════════════════════════
        # Новиков / VW Polo — большое ТО 100 000 км (полная замена)
        o = Order.objects.create(client_car=car3, status='В работе', order_date='2025-05-06', comment='Большое ТО 100 000 км — по всем позициям')
        w1 = wos(o, svc_oil,   'Замена масла и фильтра',      1.0)
        w2 = wos(o, svc_spark, 'Замена свечей зажигания',     0.5)
        w3 = wos(o, svc_airf,  'Замена воздушного фильтра',   0.3)
        w4 = wos(o, svc_cabin, 'Замена фильтра салона',       0.3)
        w5 = wos(o, svc_belt,  'Замена ремня ГРМ',            3.0, 1.1)
        w6 = wos(o, svc_cool,  'Замена охлаждающей жидкости', 1.0)
        part(o, w1, p_oil_5w30,  1, 25); part(o, w1, p_oilf_mann, 1, 30)
        part(o, w2, p_spark_bsh, 4, 30); part(o, w3, p_airf,       1, 30)
        part(o, w4, p_cabin_f,   1, 30); part(o, w5, p_belt,        1, 40)
        part(o, w6, p_cool,      3, 25)
        assign(w1, emp2); assign(w2, emp2); assign(w3, emp2)
        assign(w4, emp2); assign(w5, emp1, emp4); assign(w6, emp1)
        finish(o, '2025-05-07')

        # ══ ЗАКАЗ 34 ══════════════════════════════
        # Волков / Kia Sportage — передние колодки (визг при торможении)
        o = Order.objects.create(client_car=car4, status='В работе', order_date='2025-05-07', comment='Визг при торможении')
        w1 = wos(o, svc_brake_f, 'Замена тормозных колодок перед', 1.5)
        part(o, w1, p_brake_f, 4, 35)
        assign(w1, emp7)
        finish(o, '2025-05-07')

        # ══ ЗАКАЗ 35 ══════════════════════════════
        # Ахметов / Toyota Camry (KZ) — масло + свечи Denso
        o = Order.objects.create(client_car=car17, status='В работе', order_date='2025-05-13', comment='Плановое ТО — привезли с Казахстана')
        w1 = wos(o, svc_oil,   'Замена масла и фильтра',  1.0)
        w2 = wos(o, svc_spark, 'Замена свечей зажигания', 0.5)
        part(o, w1, p_oil_5w40, 1, 25); part(o, w1, p_oilf_bsh, 1, 30)
        part(o, w2, p_spark_dns, 4, 30)
        assign(w1, emp2); assign(w2, emp2)
        finish(o, '2025-05-13')

        # ══ ЗАКАЗ 36 ══════════════════════════════
        # Мацкевич / VW Passat (BY) — диагностика (стук в подвеске)
        o = Order.objects.create(client_car=car18, status='В работе', order_date='2025-05-15', comment='Стук в передней подвеске, приехал из Минска')
        w1 = wos(o, svc_diag,  'Компьютерная диагностика', 0.5)
        w2 = wos(o, svc_shock, 'Замена амортизаторов передних', 2.5)
        part(o, w2, p_shock_f, 2, 35)
        assign(w1, emp5); assign(w2, emp3, emp7)
        finish(o, '2025-05-16')

        # ══ ЗАКАЗ 37 ══════════════════════════════
        # Ковалёва / Mitsubishi Outlander — ТО + задние колодки
        o = Order.objects.create(client_car=car19, status='В работе', order_date='2025-05-19', comment='Плановое ТО 60 000 км + скрип сзади')
        w1 = wos(o, svc_oil,     'Замена масла и фильтра',       1.0)
        w2 = wos(o, svc_brake_r, 'Замена тормозных колодок зад', 1.0)
        part(o, w1, p_oil_5w40, 1, 25); part(o, w1, p_oilf_mann, 1, 30)
        part(o, w2, p_brake_r, 4, 35)
        assign(w1, emp2); assign(w2, emp4)
        finish(o, '2025-05-20')

        # ══ ОТМЕНЁННЫЕ ЗАКАЗЫ ═════════════════════
        # Фёдоров записался, не приехал
        o = Order.objects.create(client_car=car6, status='В работе', order_date='2025-02-05', comment='Клиент записался, не приехал')
        cancel(o)

        # Попова — слишком дорого (ремень ГРМ)
        o = Order.objects.create(client_car=car9, status='Первичный осмотр', order_date='2025-03-20', comment='Клиент отказался от ремонта — слишком дорого')
        cancel(o)

        # Орлова — забрала машину без ремонта
        o = Order.objects.create(client_car=car12, status='Первичный осмотр', order_date='2025-04-03', comment='Клиент забрал машину без ремонта')
        cancel(o)

        # ══ АКТИВНЫЕ ЗАКАЗЫ (в работе/ожидании) ═══
        # Лебедев / Toyota RAV4 — стук при повороте руля (в работе)
        o = Order.objects.create(client_car=car11, status='В работе', order_date='2025-05-12', comment='Стук при повороте руля')
        w1 = wos(o, svc_shock, 'Замена передних амортизаторов', 2.5, 1.1)
        w2 = wos(o, svc_align, 'Развал-схождение',              1.0)
        part(o, w1, p_shock_f, 2, 35)
        assign(w1, emp3, emp4)

        # Тихонов / Hyundai Tucson — диагностика (не запускается)
        o = Order.objects.create(client_car=car22, status='В работе', order_date='2025-05-20', comment='Не запускается двигатель в мороз')
        w1 = wos(o, svc_diag, 'Компьютерная диагностика', 0.5)
        w2 = wos(o, svc_el,   'Диагностика электрики',    1.0)
        assign(w1, emp5); assign(w2, emp6)

        # Соловьёв / VW Tiguan — передние колодки (готов к выдаче)
        o = Order.objects.create(client_car=car14, status='В работе', order_date='2025-05-21', comment='Плановые передние колодки')
        w1 = wos(o, svc_brake_f, 'Замена тормозных колодок перед', 1.5)
        part(o, w1, p_brake_f, 4, 35)
        assign(w1, emp4)
        o.status = 'Готов'
        o.save()

        # Белякова / VW Passat — первичный осмотр
        o = Order.objects.create(client_car=car15, status='Первичный осмотр', order_date='2025-05-22', comment='Стук в моторном отсеке, масло горит')

        # Михайлова / Nissan Qashqai — диагностика (мигает лампа EPC)
        o = Order.objects.create(client_car=car7, status='Диагностика', order_date='2025-05-23', comment='Мигает лампа EPC')
        w1 = wos(o, svc_diag, 'Компьютерная диагностика', 0.5)
        assign(w1, emp5)

        # Смирнов / Lada Niva — первичный осмотр (нет VIN, старая)
        o = Order.objects.create(client_car=car20, status='Первичный осмотр', order_date='2025-05-26', comment='Сезонное обслуживание перед летним сезоном')

        # Лебедев / Mazda CX-5 — новый клиент, масло
        o = Order.objects.create(client_car=car23, status='В работе', order_date='2025-05-27', comment='Первый раз в мастерской, плановое ТО')
        w1 = wos(o, svc_oil,  'Замена масла и фильтра',    1.0)
        w2 = wos(o, svc_airf, 'Замена воздушного фильтра', 0.3)
        part(o, w1, p_oil_5w40, 1, 25); part(o, w1, p_oilf_bsh, 1, 30)
        part(o, w2, p_airf, 1, 30)
        assign(w1, emp1); assign(w2, emp1)

        # ── Пересчёт стоимости всех заказов ─────
        D = Decimal
        for order_obj in Order.objects.all():
            svcs  = sum(w.final_price or D('0') for w in order_obj.work_order_services.all())
            parts = sum((w.sale_price or D('0')) for w in order_obj.work_order_parts.all())
            Order.objects.filter(pk=order_obj.pk).update(cost=svcs + parts)

        totals  = Order.objects.count()
        done    = Order.objects.filter(status='Завершён').count()
        active  = Order.objects.exclude(status__in=['Завершён', 'Отменён']).count()
        self.stdout.write(f'  Заказов: {totals} (завершено: {done}, активных: {active})')
        self.stdout.write(f'  Клиентов: {Client.objects.count()}  |  Сотрудников: {Employee.objects.count()}')
        self.stdout.write(f'  Деталей: {Part.objects.count()}  |  Услуг: {Service.objects.count()}')
        self.stdout.write(f'  Поставок: {SupplyDocument.objects.count()}  |  Записей склада: {StockEntry.objects.count()}')
