"""
Management command: seed_realistic
Fills the database with realistic data for the last 3 months (Mar 21 – Jun 21, 2026).
Users (admin, user1) are preserved. All other business data is replaced.

Usage: python manage.py seed_realistic
"""
from decimal import Decimal
from datetime import date, datetime, timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


def _d(date_str):
    """Parse YYYY-MM-DD string to aware datetime at noon Moscow time."""
    d = datetime.strptime(date_str, '%Y-%m-%d')
    import pytz
    tz = pytz.timezone('Europe/Moscow')
    return tz.localize(d.replace(hour=10, minute=0))


def _date(date_str):
    return date.fromisoformat(date_str)


class Command(BaseCommand):
    help = 'Заполнить БД реалистичными данными за 3 месяца (март–июнь 2026)'

    def handle(self, *args, **options):
        self.stdout.write('Очистка данных...')
        self._clear()
        self.stdout.write('Создание данных...')
        with transaction.atomic():
            self._seed()
        self.stdout.write('Создание резервных копий...')
        self._make_backups()
        self.stdout.write(self.style.SUCCESS('Готово!'))

    # ──────────────────────────────────────────────────────────────
    # ОЧИСТКА
    # ──────────────────────────────────────────────────────────────
    def _clear(self):
        from warehouse.models import (
            WorkOrderServiceEmployee, WorkOrderService, WorkOrderPart,
            WriteOffItem, WriteOff,
            SupplyItem, SupplyDocument, PurchaseOrderItem, PurchaseOrder,
            StockEntry, Part, StorageLocation, Brand, Supplier, Employee,
            WorkshopSettings,
        )
        from mainapp.models import (
            ActionLog, BackupLog,
            Order, ClientCar, Client, CarModel, CarMake, Service, ServiceType,
        )

        # подавить сигналы на время очистки
        from mainapp import signals as _sig
        _sig._locals.suppress_signals = True
        try:
            WorkOrderServiceEmployee.objects.all().delete()
            WorkOrderService.objects.all().delete()
            WorkOrderPart.objects.all().delete()
            WriteOffItem.objects.all().delete()
            WriteOff.objects.all().delete()
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
            ActionLog.objects.all().delete()
            BackupLog.objects.all().delete()
        finally:
            _sig._locals.suppress_signals = False

    # ──────────────────────────────────────────────────────────────
    # ОСНОВНОЙ SEED
    # ──────────────────────────────────────────────────────────────
    def _seed(self):
        from mainapp import signals as _sig
        _sig._locals.suppress_signals = True
        try:
            self._do_seed()
        finally:
            _sig._locals.suppress_signals = False

    def _do_seed(self):
        from warehouse.models import (
            Brand, Supplier, Part, StorageLocation, StockEntry,
            SupplyDocument, SupplyItem, PurchaseOrder, PurchaseOrderItem,
            WorkOrderService, WorkOrderPart, WorkOrderServiceEmployee,
            Employee, WorkshopSettings,
        )
        from mainapp.models import (
            Client, CarMake, CarModel, ClientCar,
            ServiceType, Service, Order, ActionLog,
        )

        # ── Настройки организации ────────────────────────────────
        ws = WorkshopSettings.objects.create(
            hourly_rate=Decimal('2500.00'),
            org_type='ИП',
            org_name='Михайлов Сергей Иванович',
            inn='772812345678',
            ogrnip='312770000056789',
            org_address='г. Москва, ул. Автозаводская, д. 15, стр. 2',
            org_phone='+7 (495) 234-56-78',
            org_email='autoservice-msk@yandex.ru',
            warranty_days=30,
        )

        # ── Производители ────────────────────────────────────────
        Brand.objects.create(name='Castrol')
        Brand.objects.create(name='MANN')
        Brand.objects.create(name='Bosch')
        Brand.objects.create(name='Brembo')
        Brand.objects.create(name='KYB')
        Brand.objects.create(name='NGK')
        Brand.objects.create(name='Valeo')
        Brand.objects.create(name='Febi')

        # ── Поставщики ───────────────────────────────────────────
        sup1 = Supplier.objects.create(
            name='ООО «АвтоЛогистик»',
            phone='+7 (495) 310-22-33',
            contact='Карпов Евгений Леонидович',
            notes='Расходники, фильтры. Минимальная партия 10 уп.',
        )
        sup2 = Supplier.objects.create(
            name='ООО «ТехноМот»',
            phone='+7 (495) 477-88-99',
            contact='Яковлев Павел Сергеевич',
            notes='Ходовая часть, тормозная система.',
        )
        sup3 = Supplier.objects.create(
            name='ИП Фёдоров К.С.',
            phone='+7 (926) 100-20-30',
            contact='Фёдоров Кирилл Семёнович',
            notes='Региональный поставщик, быстрая доставка.',
        )
        sup4 = Supplier.objects.create(
            name='ООО «МоторДеталь»',
            phone='+7 (495) 588-77-66',
            contact='Игнатьева Ольга Романовна',
            notes='Электрика, двигатель, трансмиссия.',
        )

        # ── Места хранения ───────────────────────────────────────
        la1 = StorageLocation.objects.create(rack='A', shelf='1', cell='1')
        la2 = StorageLocation.objects.create(rack='A', shelf='1', cell='2')
        la3 = StorageLocation.objects.create(rack='A', shelf='1', cell='3')
        la4 = StorageLocation.objects.create(rack='A', shelf='2', cell='1')
        la5 = StorageLocation.objects.create(rack='A', shelf='2', cell='2')
        la6 = StorageLocation.objects.create(rack='A', shelf='2', cell='3')
        lb1 = StorageLocation.objects.create(rack='B', shelf='1', cell='1')
        lb2 = StorageLocation.objects.create(rack='B', shelf='1', cell='2')
        lb3 = StorageLocation.objects.create(rack='B', shelf='1', cell='3')
        lb4 = StorageLocation.objects.create(rack='B', shelf='2', cell='1')
        lb5 = StorageLocation.objects.create(rack='B', shelf='2', cell='2')
        lb6 = StorageLocation.objects.create(rack='B', shelf='2', cell='3')

        # ── Номенклатура ─────────────────────────────────────────
        # Расходники
        p_oil_5w40   = Part.objects.create(article='CS-5W40-4L',  name='Масло моторное Castrol EDGE 5W-40 4л',      brand='Castrol', category='Расходники',        package_qty=1, default_markup=25)
        p_oil_5w30   = Part.objects.create(article='CS-5W30-4L',  name='Масло моторное Castrol Magnatec 5W-30 4л',  brand='Castrol', category='Расходники',        package_qty=1, default_markup=25)
        p_oilf_mann  = Part.objects.create(article='MN-W71275',   name='Фильтр масляный MANN W712/75',              brand='MANN',    category='Расходники',        package_qty=1, default_markup=30)
        p_oilf_bsh   = Part.objects.create(article='BO-0450905',  name='Фильтр масляный Bosch 0450905200',          brand='Bosch',   category='Расходники',        package_qty=1, default_markup=30)
        p_airf_mann  = Part.objects.create(article='MN-C2356',    name='Фильтр воздушный MANN C2356',               brand='MANN',    category='Расходники',        package_qty=1, default_markup=30)
        p_cabin_mann = Part.objects.create(article='MN-CUK2939',  name='Фильтр салона MANN CUK2939',                brand='MANN',    category='Расходники',        package_qty=1, default_markup=30)
        p_cool       = Part.objects.create(article='CS-AF-G12-5', name='Антифриз Castrol Radicool G12+ 5л',         brand='Castrol', category='Расходники',        package_qty=1, default_markup=20)
        p_brake_fl   = Part.objects.create(article='BO-DOT4-1L',  name='Жидкость тормозная Bosch DOT-4 1л',         brand='Bosch',   category='Расходники',        package_qty=1, default_markup=20)
        # Свечи — 4 штуки в упаковке
        p_spark_ngk  = Part.objects.create(article='NGK-BPR6ES',  name='Свеча зажигания NGK BPR6ES',                brand='NGK',     category='Расходники',        package_qty=4, default_markup=35)
        p_spark_bsh  = Part.objects.create(article='BO-WR7DC',    name='Свеча зажигания Bosch WR7DC',               brand='Bosch',   category='Расходники',        package_qty=4, default_markup=35)
        # Тормоза
        p_pad_f      = Part.objects.create(article='BR-P85020',   name='Колодки тормозные передние Brembo P85020',  brand='Brembo',  category='Тормозная система', package_qty=2, default_markup=30)
        p_pad_r      = Part.objects.create(article='BR-P56028',   name='Колодки тормозные задние Brembo P56028',    brand='Brembo',  category='Тормозная система', package_qty=2, default_markup=30)
        p_disc_f     = Part.objects.create(article='BR-09A545',   name='Диск тормозной передний Brembo 09.A545.11', brand='Brembo',  category='Тормозная система', package_qty=1, default_markup=25)
        p_disc_r     = Part.objects.create(article='BR-09A349',   name='Диск тормозной задний Brembo 09.A349.11',   brand='Brembo',  category='Тормозная система', package_qty=1, default_markup=25)
        # Двигатель
        p_belt       = Part.objects.create(article='BO-1987946518', name='Ремень ГРМ Bosch 1987946518',             brand='Bosch',   category='Двигатель',         package_qty=1, default_markup=20)
        p_pump       = Part.objects.create(article='VL-PA1165',   name='Помпа водяная Valeo PA1165',                brand='Valeo',   category='Двигатель',         package_qty=1, default_markup=20)
        p_therm      = Part.objects.create(article='BO-0280485231', name='Термостат Bosch 0280485231',              brand='Bosch',   category='Двигатель',         package_qty=1, default_markup=25)
        # Подвеска
        p_shock_f    = Part.objects.create(article='KYB-334816',  name='Стойка амортизатора передняя KYB 334816',   brand='KYB',     category='Подвеска',          package_qty=1, default_markup=20)
        p_shock_r    = Part.objects.create(article='KYB-443195',  name='Амортизатор задний KYB 443195',             brand='KYB',     category='Подвеска',          package_qty=1, default_markup=20)
        p_arm        = Part.objects.create(article='FB-42852',    name='Рычаг подвески нижний Febi 42852',          brand='Febi',    category='Подвеска',          package_qty=1, default_markup=20)
        # Сайлентблок — 2 штуки в упаковке (левый+правый)
        p_sil        = Part.objects.create(article='FB-01116',    name='Сайлентблок рычага Febi 01116',             brand='Febi',    category='Подвеска',          package_qty=2, default_markup=25)
        p_ball       = Part.objects.create(article='FB-22514',    name='Шаровая опора Febi 22514',                  brand='Febi',    category='Подвеска',          package_qty=1, default_markup=25)
        # Электрика
        p_batt_60    = Part.objects.create(article='BO-S4-005',   name='Аккумулятор Bosch S4 60Ач',                brand='Bosch',   category='Электрика',         package_qty=1, default_markup=15)
        p_batt_70    = Part.objects.create(article='BO-S4-024',   name='Аккумулятор Bosch S4 70Ач',                brand='Bosch',   category='Электрика',         package_qty=1, default_markup=15)
        p_alt        = Part.objects.create(article='VL-437574',   name='Генератор Valeo 437574',                   brand='Valeo',   category='Электрика',         package_qty=1, default_markup=15)
        p_start      = Part.objects.create(article='BO-0001110082', name='Стартер Bosch 0001110082',               brand='Bosch',   category='Электрика',         package_qty=1, default_markup=15)
        # Лампы — 2 штуки в упаковке (пара)
        p_lamp_h7    = Part.objects.create(article='BO-1987302804', name='Лампа H7 Bosch Longlife 55W',            brand='Bosch',   category='Электрика',         package_qty=2, default_markup=30)
        # Трансмиссия
        p_clutch     = Part.objects.create(article='VL-826411',   name='Комплект сцепления Valeo 826411',          brand='Valeo',   category='Трансмиссия',       package_qty=1, default_markup=15)
        p_cv         = Part.objects.create(article='FB-29076',    name='ШРУС внешний с пыльником Febi 29076',      brand='Febi',    category='Трансмиссия',       package_qty=1, default_markup=20)

        # ── Марки и модели ───────────────────────────────────────
        toyota  = CarMake.objects.create(name='Toyota')
        lada    = CarMake.objects.create(name='Lada')
        hyundai = CarMake.objects.create(name='Hyundai')
        kia     = CarMake.objects.create(name='Kia')
        vw      = CarMake.objects.create(name='Volkswagen')
        bmw     = CarMake.objects.create(name='BMW')
        nissan  = CarMake.objects.create(name='Nissan')
        renault = CarMake.objects.create(name='Renault')
        mazda   = CarMake.objects.create(name='Mazda')
        skoda   = CarMake.objects.create(name='Skoda')

        camry    = CarModel.objects.create(make=toyota,  name='Camry')
        corolla  = CarModel.objects.create(make=toyota,  name='Corolla')
        rav4     = CarModel.objects.create(make=toyota,  name='RAV4')
        granta   = CarModel.objects.create(make=lada,    name='Granta')
        vesta    = CarModel.objects.create(make=lada,    name='Vesta')
        niva     = CarModel.objects.create(make=lada,    name='Niva Travel')
        largus   = CarModel.objects.create(make=lada,    name='Largus')
        solaris  = CarModel.objects.create(make=hyundai, name='Solaris')
        creta    = CarModel.objects.create(make=hyundai, name='Creta')
        tucson   = CarModel.objects.create(make=hyundai, name='Tucson')
        rio      = CarModel.objects.create(make=kia,     name='Rio')
        sportage = CarModel.objects.create(make=kia,     name='Sportage')
        polo     = CarModel.objects.create(make=vw,      name='Polo')
        tiguan   = CarModel.objects.create(make=vw,      name='Tiguan')
        bmw3     = CarModel.objects.create(make=bmw,     name='3 серия')
        bmw5     = CarModel.objects.create(make=bmw,     name='5 серия')
        qashqai  = CarModel.objects.create(make=nissan,  name='Qashqai')
        xtrail   = CarModel.objects.create(make=nissan,  name='X-Trail')
        logan    = CarModel.objects.create(make=renault, name='Logan')
        duster   = CarModel.objects.create(make=renault, name='Duster')
        cx5      = CarModel.objects.create(make=mazda,   name='CX-5')
        octavia  = CarModel.objects.create(make=skoda,   name='Octavia')

        # ── Типы услуг и услуги ─────────────────────────────────
        st_to  = ServiceType.objects.create(name='Техническое обслуживание')
        st_br  = ServiceType.objects.create(name='Тормозная система')
        st_eng = ServiceType.objects.create(name='Двигатель')
        st_sus = ServiceType.objects.create(name='Ходовая часть')
        st_el  = ServiceType.objects.create(name='Электрика')

        s_oil   = Service.objects.create(service_type=st_to,  name='Замена масла и масляного фильтра',  base_hours=Decimal('1.00'))
        s_airf  = Service.objects.create(service_type=st_to,  name='Замена воздушного фильтра',         base_hours=Decimal('0.50'))
        s_cabf  = Service.objects.create(service_type=st_to,  name='Замена фильтра салона',             base_hours=Decimal('0.50'))
        s_spark = Service.objects.create(service_type=st_to,  name='Замена свечей зажигания',           base_hours=Decimal('1.00'))
        s_cool  = Service.objects.create(service_type=st_to,  name='Замена антифриза',                  base_hours=Decimal('1.50'))
        s_pad   = Service.objects.create(service_type=st_br,  name='Замена тормозных колодок',          base_hours=Decimal('1.50'))
        s_disc  = Service.objects.create(service_type=st_br,  name='Замена тормозных дисков',           base_hours=Decimal('2.00'))
        s_bflush= Service.objects.create(service_type=st_br,  name='Замена тормозной жидкости',         base_hours=Decimal('1.00'))
        s_diag  = Service.objects.create(service_type=st_eng, name='Компьютерная диагностика',          base_hours=Decimal('0.50'))
        s_belt  = Service.objects.create(service_type=st_eng, name='Замена ремня ГРМ',                  base_hours=Decimal('4.00'))
        s_pump  = Service.objects.create(service_type=st_eng, name='Замена помпы',                      base_hours=Decimal('2.00'))
        s_shock = Service.objects.create(service_type=st_sus, name='Замена амортизаторов',              base_hours=Decimal('3.00'))
        s_arm   = Service.objects.create(service_type=st_sus, name='Замена рычага подвески',            base_hours=Decimal('2.50'))
        s_align = Service.objects.create(service_type=st_sus, name='Сход-развал',                      base_hours=Decimal('1.00'))
        s_ediag = Service.objects.create(service_type=st_el,  name='Диагностика электрики',             base_hours=Decimal('1.00'))
        s_batt  = Service.objects.create(service_type=st_el,  name='Замена аккумулятора',               base_hours=Decimal('0.50'))

        # ── Сотрудники ───────────────────────────────────────────
        emp1 = Employee.objects.create(name='Петров Алексей Николаевич',    position='Механик',           salary_coefficient=Decimal('1.00'))
        emp2 = Employee.objects.create(name='Смирнов Дмитрий Павлович',     position='Механик',           salary_coefficient=Decimal('1.00'))
        emp3 = Employee.objects.create(name='Козлов Игорь Сергеевич',       position='Механик',           salary_coefficient=Decimal('1.20'))
        emp4 = Employee.objects.create(name='Новиков Андрей Викторович',     position='Старший механик',   salary_coefficient=Decimal('1.30'))
        emp5 = Employee.objects.create(name='Фёдоров Максим Юрьевич',       position='Диагност',          salary_coefficient=Decimal('1.20'))
        emp6 = Employee.objects.create(name='Захаров Кирилл Олегович',      position='Механик',           salary_coefficient=Decimal('1.00'))
        Employee.objects.create(name='Морозова Елена Владимировна',          position='Администратор',     salary_coefficient=Decimal('1.00'))

        # ── Клиенты (15 чел.) ────────────────────────────────────
        c1  = Client.objects.create(fio='Иванов Сергей Михайлович',        phone='+7 (916) 111-22-33', consent_personal_data=True)
        c2  = Client.objects.create(fio='Смирнова Анна Владимировна',      phone='+7 (925) 222-33-44', consent_personal_data=True)
        c3  = Client.objects.create(fio='Козлов Дмитрий Александрович',    phone='+7 (903) 333-44-55', consent_personal_data=True)
        c4  = Client.objects.create(fio='Новикова Ольга Петровна',         phone='+7 (985) 444-55-66', consent_personal_data=True)
        c5  = Client.objects.create(fio='Фёдоров Андрей Сергеевич',        phone='+7 (926) 555-66-77', consent_personal_data=True)
        c6  = Client.objects.create(fio='Морозов Владимир Иванович',       phone='+7 (921) 666-77-88', consent_personal_data=True)
        c7  = Client.objects.create(fio='Волкова Татьяна Юрьевна',         phone='+7 (950) 777-88-99', consent_personal_data=True)
        c8  = Client.objects.create(fio='Зайцев Максим Олегович',          phone='+7 (967) 888-99-00', consent_personal_data=True)
        c9  = Client.objects.create(fio='Соколова Ирина Борисовна',        phone='+7 (906) 999-00-11', consent_personal_data=True)
        c10 = Client.objects.create(fio='Лебедев Константин Михайлович',   phone='+7 (937) 100-20-30', consent_personal_data=True)
        c11 = Client.objects.create(fio='Попов Роман Аркадьевич',          phone='+7 (919) 200-30-40', consent_personal_data=True)
        c12 = Client.objects.create(fio='Орлова Светлана Николаевна',      phone='+7 (977) 300-40-50', consent_personal_data=True)
        c13 = Client.objects.create(fio='Тихонов Игорь Вячеславович',      phone='+7 (908) 400-50-60', consent_personal_data=True)
        c14 = Client.objects.create(fio='Соловьёв Антон Геннадьевич',      phone='+7 (929) 500-60-70', consent_personal_data=True)
        c15 = Client.objects.create(fio='Белякова Надежда Евгеньевна',     phone='+7 (962) 600-70-80', consent_personal_data=True)

        # ── Автомобили ───────────────────────────────────────────
        # Буквы РФ: А В Е К М Н О Р С Т У Х (кириллица)
        car1  = ClientCar.objects.create(client=c1,  make=toyota,  model=camry,   license_plate='А123АА77', vin='XW7BF4FK80S012345', color='Белый',     year=2020)
        car2  = ClientCar.objects.create(client=c2,  make=lada,    model=granta,  license_plate='В456МН77', vin='XTA210600L2345678', color='Серебристый',year=2021)
        car3  = ClientCar.objects.create(client=c3,  make=hyundai, model=solaris, license_plate='Е789КМ99', vin='Z94C241BBKS345678', color='Чёрный',     year=2019)
        car4  = ClientCar.objects.create(client=c4,  make=kia,     model=rio,     license_plate='К012ОР78', vin='XWEJC812AF1456789', color='Красный',     year=2022)
        car5  = ClientCar.objects.create(client=c5,  make=vw,      model=polo,    license_plate='М345СТ77', vin='WVWZZZ6RZHY567890', color='Синий',       year=2017)
        car6  = ClientCar.objects.create(client=c6,  make=toyota,  model=corolla, license_plate='Н678УХ50', vin='SB1KZ3JE00E678901', color='Серый',       year=2014)
        car7  = ClientCar.objects.create(client=c7,  make=lada,    model=vesta,   license_plate='О901АВ163', vin='XTA217230J8789012', color='Белый',       year=2018)
        car8  = ClientCar.objects.create(client=c8,  make=hyundai, model=creta,   license_plate='Р234ЕК77', vin='KMHFH41DBHU890123', color='Тёмно-синий', year=2017)
        car9  = ClientCar.objects.create(client=c9,  make=nissan,  model=qashqai, license_plate='С567МН77', vin='JN1BAYS62U0901234', color='Белый перламутр', year=2016)
        car10 = ClientCar.objects.create(client=c10, make=renault, model=logan,   license_plate='Т890ОР96', vin='VF1LS0B0H45012345', color='Серебристый', year=2015)
        car11 = ClientCar.objects.create(client=c11, make=mazda,   model=cx5,     license_plate='У123СТ77', vin='JM3KE4BY2G0123456', color='Красный',     year=2016)
        car12 = ClientCar.objects.create(client=c12, make=kia,     model=sportage,license_plate='Х456УХ99', vin='XWEJE811BH1234567', color='Чёрный',      year=2017)
        car13 = ClientCar.objects.create(client=c13, make=bmw,     model=bmw3,    license_plate='А789ВС23', vin='WBA3A5G53FNS34567', color='Белый',       year=2015)
        car14 = ClientCar.objects.create(client=c14, make=vw,      model=tiguan,  license_plate='В012КМ77', vin='WVGBV7AX9HW345678', color='Серый',       year=2017)
        car15 = ClientCar.objects.create(client=c15, make=skoda,   model=octavia, license_plate='Е345НО50', vin='TMBEG7NE0H0456789', color='Синий',       year=2017)
        car16 = ClientCar.objects.create(client=c1,  make=toyota,  model=rav4,    license_plate='К678РС77', vin='SB1KM3JE40E567890', color='Серый',       year=2021)
        car17 = ClientCar.objects.create(client=c3,  make=renault, model=duster,  license_plate='М901ТУ78', vin='VF1HJNH0H55678901', color='Хаки',        year=2019)
        car18 = ClientCar.objects.create(client=c6,  make=nissan,  model=xtrail,  license_plate='Н234УХ77', vin='JN1TBNZ50U0789012', color='Белый',       year=2020)
        car19 = ClientCar.objects.create(client=c10, make=lada,    model=largus,  license_plate='О567АВ163', vin='XTA219000L0890123', color='Серебристый', year=2018)

        # ── Приходы товаров (4 штуки) ────────────────────────────
        def receive(doc, part, location, qty, pkg_qty, price_per_pkg, min_q=3):
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

        # Приход 1 — 22 марта 2026, расходники (АвтоЛогистик)
        po1 = PurchaseOrder.objects.create(
            supplier=sup1, status='received', created_at=_d('2026-03-20'),
            comment='Плановый заказ расходников на март',
        )
        pi = PurchaseOrderItem.objects.create(purchase_order=po1, part=p_oil_5w40,  quantity=20)
        pi.received_qty = 20; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po1, part=p_oil_5w30,  quantity=15)
        pi.received_qty = 15; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po1, part=p_oilf_mann, quantity=20)
        pi.received_qty = 20; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po1, part=p_airf_mann, quantity=15)
        pi.received_qty = 15; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po1, part=p_cabin_mann,quantity=15)
        pi.received_qty = 15; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po1, part=p_cool,      quantity=10)
        pi.received_qty = 10; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po1, part=p_brake_fl,  quantity=12)
        pi.received_qty = 12; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po1, part=p_spark_ngk, quantity=10)
        pi.received_qty = 10; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po1, part=p_spark_bsh, quantity=8)
        pi.received_qty = 8; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po1, part=p_oilf_bsh,  quantity=10)
        pi.received_qty = 10; pi.save()
        sd1 = SupplyDocument.objects.create(supplier=sup1, purchase_order=po1, created_at=_d('2026-03-22'), comment='Поставка №1, март 2026')
        receive(sd1, p_oil_5w40,   la1, 20, 1, Decimal('1050.00'))
        receive(sd1, p_oil_5w30,   la1, 15, 1, Decimal('980.00'))
        receive(sd1, p_oilf_mann,  la2, 20, 1, Decimal('310.00'))
        receive(sd1, p_oilf_bsh,   la2, 10, 1, Decimal('340.00'))
        receive(sd1, p_airf_mann,  la2, 15, 1, Decimal('420.00'))
        receive(sd1, p_cabin_mann, la3, 15, 1, Decimal('390.00'))
        receive(sd1, p_cool,       la3, 10, 1, Decimal('760.00'))
        receive(sd1, p_brake_fl,   la3, 12, 1, Decimal('185.00'))
        receive(sd1, p_spark_ngk,  la4, 10, 4, Decimal('880.00'))  # 10 уп × 4 шт
        receive(sd1, p_spark_bsh,  la4,  8, 4, Decimal('950.00'))  # 8 уп × 4 шт

        # Приход 2 — 10 апреля 2026, ходовая + тормоза (ТехноМот)
        po2 = PurchaseOrder.objects.create(
            supplier=sup2, status='received', created_at=_d('2026-04-08'),
            comment='Ходовая часть и тормозная система на апрель',
        )
        pi = PurchaseOrderItem.objects.create(purchase_order=po2, part=p_pad_f,   quantity=12)
        pi.received_qty = 12; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po2, part=p_pad_r,   quantity=10)
        pi.received_qty = 10; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po2, part=p_disc_f,  quantity=8)
        pi.received_qty = 8; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po2, part=p_disc_r,  quantity=6)
        pi.received_qty = 6; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po2, part=p_shock_f, quantity=6)
        pi.received_qty = 6; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po2, part=p_shock_r, quantity=6)
        pi.received_qty = 6; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po2, part=p_arm,     quantity=8)
        pi.received_qty = 8; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po2, part=p_sil,     quantity=8)
        pi.received_qty = 8; pi.save()
        sd2 = SupplyDocument.objects.create(supplier=sup2, purchase_order=po2, created_at=_d('2026-04-10'), comment='Поставка №2, апрель 2026')
        receive(sd2, p_pad_f,   lb1, 12, 2, Decimal('1650.00'))   # 12 уп × 2 шт
        receive(sd2, p_pad_r,   lb1, 10, 2, Decimal('1420.00'))   # 10 уп × 2 шт
        receive(sd2, p_disc_f,  lb2,  8, 1, Decimal('2700.00'))
        receive(sd2, p_disc_r,  lb2,  6, 1, Decimal('2100.00'))
        receive(sd2, p_shock_f, lb3,  6, 1, Decimal('3200.00'))
        receive(sd2, p_shock_r, lb3,  6, 1, Decimal('2600.00'))
        receive(sd2, p_arm,     lb4,  8, 1, Decimal('1850.00'))
        receive(sd2, p_sil,     lb4,  8, 2, Decimal('620.00'))    # 8 уп × 2 шт

        # Приход 3 — 5 мая 2026, расходники пополнение с новыми ценами (АвтоЛогистик + ИП Фёдоров)
        po3 = PurchaseOrder.objects.create(
            supplier=sup3, status='received', created_at=_d('2026-05-03'),
            comment='Пополнение расходников, май 2026',
        )
        pi = PurchaseOrderItem.objects.create(purchase_order=po3, part=p_oil_5w40,  quantity=15)
        pi.received_qty = 15; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po3, part=p_oil_5w30,  quantity=12)
        pi.received_qty = 12; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po3, part=p_oilf_mann, quantity=15)
        pi.received_qty = 15; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po3, part=p_spark_ngk, quantity=8)
        pi.received_qty = 8; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po3, part=p_belt,      quantity=6)
        pi.received_qty = 6; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po3, part=p_pump,      quantity=4)
        pi.received_qty = 4; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po3, part=p_ball,      quantity=8)
        pi.received_qty = 8; pi.save()
        sd3 = SupplyDocument.objects.create(supplier=sup3, purchase_order=po3, created_at=_d('2026-05-05'), comment='Поставка №3, май 2026 — цены выросли')
        # Цены чуть выше чем в марте (инфляция)
        receive(sd3, p_oil_5w40,   la1, 15, 1, Decimal('1120.00'))
        receive(sd3, p_oil_5w30,   la1, 12, 1, Decimal('1040.00'))
        receive(sd3, p_oilf_mann,  la2, 15, 1, Decimal('330.00'))
        receive(sd3, p_spark_ngk,  la4,  8, 4, Decimal('920.00'))
        receive(sd3, p_belt,       la5,  6, 1, Decimal('1980.00'))
        receive(sd3, p_pump,       la5,  4, 1, Decimal('2850.00'))
        receive(sd3, p_ball,       lb5,  8, 1, Decimal('960.00'))

        # Приход 4 — 3 июня 2026, электрика и двигатель (МоторДеталь)
        po4 = PurchaseOrder.objects.create(
            supplier=sup4, status='received', created_at=_d('2026-06-01'),
            comment='Электрика и двигатель, июнь 2026',
        )
        pi = PurchaseOrderItem.objects.create(purchase_order=po4, part=p_batt_60, quantity=6)
        pi.received_qty = 6; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po4, part=p_batt_70, quantity=4)
        pi.received_qty = 4; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po4, part=p_alt,     quantity=3)
        pi.received_qty = 3; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po4, part=p_start,   quantity=3)
        pi.received_qty = 3; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po4, part=p_lamp_h7, quantity=10)
        pi.received_qty = 10; pi.save()
        pi = PurchaseOrderItem.objects.create(purchase_order=po4, part=p_therm,   quantity=5)
        pi.received_qty = 5; pi.save()
        sd4 = SupplyDocument.objects.create(supplier=sup4, purchase_order=po4, created_at=_d('2026-06-03'), comment='Поставка №4, июнь 2026')
        receive(sd4, p_batt_60, lb5,  6, 1, Decimal('4200.00'))
        receive(sd4, p_batt_70, lb5,  4, 1, Decimal('5100.00'))
        receive(sd4, p_alt,     lb6,  3, 1, Decimal('8500.00'))
        receive(sd4, p_start,   lb6,  3, 1, Decimal('5800.00'))
        receive(sd4, p_lamp_h7, la6, 10, 2, Decimal('480.00'))  # 10 уп × 2 шт
        receive(sd4, p_therm,   la5,  5, 1, Decimal('1350.00'))

        # Также добавляем ремень ГРМ и сцепление в склад (от поставщика 4)
        sd4b = SupplyDocument.objects.create(supplier=sup4, created_at=_d('2026-06-03'), comment='Дополнение к поставке №4')
        receive(sd4b, p_clutch, lb6, 3, 1, Decimal('12500.00'))
        receive(sd4b, p_cv,     la6, 4, 1, Decimal('3800.00'))

        # ── Заказы (45 штук) ─────────────────────────────────────

        def make_order(car, order_date_str, status, services, parts_list=None,
                       comment=None, payment='cash', completion_days=3, mileage=None):
            """
            services: list of (Service, hours, complexity, Employee)
            parts_list: list of (Part, StockEntry, quantity, markup)
            """
            order_date = _date(order_date_str)
            if mileage is None:
                # ~15 000 км/год + небольшой разброс по номеру машины
                base = (2026 - (car.year or 2018)) * 15000
                vary = abs(hash(car.license_plate or str(car.pk))) % 8000
                mileage = base + vary
            o = Order(
                client_car=car,
                order_date=order_date,
                status=status,
                comment=comment,
                mileage=mileage,
            )
            # Заполнить снапшоты вручную (сигналы выключены)
            o.client_fio_static = car.client.fio
            vin_part = f', VIN: {car.vin}' if car.vin else ''
            o.car_details_static = f"{car.make.name} {car.model.name} ({car.license_plate or ''}{vin_part})"
            o.car_snapshot = {
                'make': car.make.name, 'model': car.model.name,
                'year': car.year, 'vin': car.vin or '',
                'plate': car.license_plate or '', 'color': car.color or '',
                'client_fio': car.client.fio, 'client_phone': car.client.phone or '',
            }
            o.org_snapshot = ws.as_snapshot()
            if status == 'Завершён':
                o.completion_date = order_date + timedelta(days=completion_days)
                o.payment_method = payment
            o.save()

            total = Decimal('0')
            for (svc, hours, compl, emp) in services:
                rate = ws.hourly_rate
                fp = (Decimal(str(hours)) * rate * Decimal(str(compl))).quantize(Decimal('0.01'))
                wos = WorkOrderService.objects.create(
                    work_order=o, service=svc,
                    service_name_snapshot=svc.name,
                    hourly_rate_snapshot=rate,
                    hours_applied=Decimal(str(hours)),
                    complexity_factor=Decimal(str(compl)),
                    final_price=fp,
                )
                if emp:
                    WorkOrderServiceEmployee.objects.create(
                        work_order_service=wos, employee=emp,
                        employee_name_snapshot=emp.name,
                        salary_coefficient_snapshot=emp.salary_coefficient,
                    )
                total += fp

            if parts_list:
                for (part, entry, qty, markup) in parts_list:
                    # Вычислим цену через FIFO (берём последнюю цену закупки)
                    last_supply = SupplyItem.objects.filter(part=part).order_by('-id').first()
                    if last_supply:
                        cost_per_unit = last_supply.price_per_unit
                    else:
                        cost_per_unit = Decimal('0')
                    sale_price = (cost_per_unit * qty * (1 + Decimal(str(markup)) / 100)).quantize(Decimal('0.01'))
                    wop = WorkOrderPart.objects.create(
                        work_order=o, part=part,
                        part_article_snapshot=part.article,
                        part_name_snapshot=part.name,
                        quantity=qty,
                        markup=Decimal(str(markup)),
                        sale_price=sale_price,
                    )
                    if status in ('Завершён', 'Готов', 'В работе', 'Диагностика', 'Первичный осмотр'):
                        # резервируем детали
                        if entry and entry.total_qty >= qty:
                            wop.reserved_entries = [{'entry_id': entry.pk, 'qty': qty}]
                            if status == 'Завершён':
                                # при завершении детали списаны — резерва нет
                                wop.status = 'cancelled'
                            wop.save()
                            entry.reserved_qty += qty
                            if status == 'Завершён':
                                entry.total_qty -= qty
                                entry.reserved_qty -= qty
                            entry.save()
                    total += sale_price

            o.cost = total
            o.save()
            return o

        # Нужны StockEntry объекты для резервирования
        def se(part, loc):
            return StockEntry.objects.filter(part=part, location=loc).first()

        # === МАРТ 2026 (8 завершённых заказов) ===
        make_order(car1, '2026-03-21', 'Завершён',
            [(s_oil, 1.0, 1.0, emp1)],
            [(p_oil_5w40, se(p_oil_5w40, la1), 4, 25), (p_oilf_mann, se(p_oilf_mann, la2), 1, 30)],
            comment='Плановое ТО', completion_days=1)

        make_order(car3, '2026-03-22', 'Завершён',
            [(s_diag, 0.5, 1.0, emp5), (s_spark, 1.0, 1.0, emp5)],
            [(p_spark_ngk, se(p_spark_ngk, la4), 4, 35)],
            completion_days=1)

        make_order(car5, '2026-03-24', 'Завершён',
            [(s_pad, 1.5, 1.0, emp2)],
            [(p_pad_f, se(p_pad_f, lb1), 2, 30)],
            completion_days=2)

        make_order(car7, '2026-03-25', 'Завершён',
            [(s_oil, 1.0, 1.0, emp1), (s_airf, 0.5, 1.0, emp1)],
            [(p_oil_5w30, se(p_oil_5w30, la1), 4, 25), (p_oilf_mann, se(p_oilf_mann, la2), 1, 30), (p_airf_mann, se(p_airf_mann, la2), 1, 30)],
            comment='ТО + воздушный фильтр', completion_days=1)

        make_order(car9, '2026-03-26', 'Завершён',
            [(s_ediag, 1.0, 1.0, emp5)],
            comment='Диагностика электрики по жалобе на аккумулятор', completion_days=1)

        make_order(car11, '2026-03-27', 'Завершён',
            [(s_align, 1.0, 1.0, emp3)],
            comment='Сход-развал после ям', completion_days=1)

        make_order(car13, '2026-03-28', 'Завершён',
            [(s_diag, 0.5, 1.0, emp5), (s_oil, 1.0, 1.0, emp4)],
            [(p_oil_5w40, se(p_oil_5w40, la1), 4, 25), (p_oilf_bsh, se(p_oilf_bsh, la2), 1, 30)],
            comment='Диагностика + замена масла BMW', payment='card', completion_days=2)

        make_order(car2, '2026-03-31', 'Завершён',
            [(s_cabf, 0.5, 1.0, emp1)],
            [(p_cabin_mann, se(p_cabin_mann, la3), 1, 30)],
            completion_days=1)

        # === АПРЕЛЬ 2026 (14 завершённых заказов) ===
        make_order(car4, '2026-04-02', 'Завершён',
            [(s_oil, 1.0, 1.0, emp2)],
            [(p_oil_5w30, se(p_oil_5w30, la1), 4, 25), (p_oilf_mann, se(p_oilf_mann, la2), 1, 30)],
            completion_days=1)

        make_order(car6, '2026-04-03', 'Завершён',
            [(s_cool, 1.5, 1.0, emp3)],
            [(p_cool, se(p_cool, la3), 5, 20)],
            comment='Замена антифриза — потёк патрубок', completion_days=2)

        make_order(car8, '2026-04-05', 'Завершён',
            [(s_pad, 1.5, 1.1, emp2), (s_disc, 2.0, 1.0, emp2)],
            [(p_pad_f, se(p_pad_f, lb1), 2, 30), (p_disc_f, se(p_disc_f, lb2), 2, 25)],
            comment='Скрип тормозов — замена колодок и дисков', payment='card', completion_days=3)

        make_order(car10, '2026-04-07', 'Завершён',
            [(s_oil, 1.0, 1.0, emp1), (s_spark, 1.0, 1.0, emp1)],
            [(p_oil_5w30, se(p_oil_5w30, la1), 4, 25), (p_spark_ngk, se(p_spark_ngk, la4), 4, 35)],
            completion_days=1)

        make_order(car12, '2026-04-08', 'Завершён',
            [(s_shock, 3.0, 1.2, emp4)],
            [(p_shock_f, se(p_shock_f, lb3), 2, 20)],
            comment='Замена передних амортизаторов', payment='transfer', completion_days=4)

        make_order(car14, '2026-04-10', 'Завершён',
            [(s_diag, 0.5, 1.0, emp5), (s_bflush, 1.0, 1.0, emp3)],
            [(p_brake_fl, se(p_brake_fl, la3), 1, 20)],
            comment='Диагностика + замена тормозной жидкости', completion_days=2)

        make_order(car15, '2026-04-11', 'Завершён',
            [(s_oil, 1.0, 1.0, emp2)],
            [(p_oil_5w40, se(p_oil_5w40, la1), 4, 25), (p_oilf_mann, se(p_oilf_mann, la2), 1, 30), (p_cabin_mann, se(p_cabin_mann, la3), 1, 30)],
            comment='ТО — масло и фильтры', completion_days=1)

        make_order(car1, '2026-04-14', 'Завершён',
            [(s_ediag, 1.0, 1.0, emp5), (s_batt, 0.5, 1.0, emp5)],
            [(p_batt_70, se(p_batt_70, lb5), 1, 15)],
            comment='Не заводится — АКБ', payment='card', completion_days=1)

        make_order(car16, '2026-04-15', 'Завершён',
            [(s_arm, 2.5, 1.0, emp4), (s_align, 1.0, 1.0, emp3)],
            [(p_arm, se(p_arm, lb4), 2, 20), (p_sil, se(p_sil, lb4), 2, 25)],
            comment='Стук в подвеске — рычаги + сайлентблоки', payment='transfer', completion_days=4)

        make_order(car17, '2026-04-17', 'Завершён',
            [(s_oil, 1.0, 1.0, emp1)],
            [(p_oil_5w30, se(p_oil_5w30, la1), 4, 25), (p_oilf_mann, se(p_oilf_mann, la2), 1, 30)],
            completion_days=1)

        make_order(car3, '2026-04-21', 'Завершён',
            [(s_pad, 1.5, 1.0, emp2), (s_disc, 2.0, 1.0, emp2)],
            [(p_pad_r, se(p_pad_r, lb1), 2, 30), (p_disc_r, se(p_disc_r, lb2), 2, 25)],
            comment='Задние тормоза', completion_days=3)

        make_order(car5, '2026-04-23', 'Завершён',
            [(s_spark, 1.0, 1.0, emp3)],
            [(p_spark_bsh, se(p_spark_bsh, la4), 4, 35)],
            completion_days=1)

        make_order(car7, '2026-04-24', 'Завершён',
            [(s_diag, 0.5, 1.0, emp5)],
            comment='Диагностика — горит лампа ошибки', completion_days=1)

        make_order(car18, '2026-04-28', 'Завершён',
            [(s_oil, 1.0, 1.0, emp1), (s_airf, 0.5, 1.0, emp1), (s_cabf, 0.5, 1.0, emp1)],
            [(p_oil_5w40, se(p_oil_5w40, la1), 4, 25), (p_oilf_bsh, se(p_oilf_bsh, la2), 1, 30), (p_airf_mann, se(p_airf_mann, la2), 1, 30), (p_cabin_mann, se(p_cabin_mann, la3), 1, 30)],
            comment='Комплексное ТО', payment='card', completion_days=2)

        make_order(car9, '2026-04-30', 'Завершён',
            [(s_batt, 0.5, 1.0, emp6)],
            [(p_batt_60, se(p_batt_60, lb5), 1, 15)],
            comment='Замена АКБ — плановая', completion_days=1)

        # === МАЙ 2026 (12 заказов: 10 завершён, 2 отменён) ===
        make_order(car2, '2026-05-05', 'Завершён',
            [(s_oil, 1.0, 1.0, emp1), (s_spark, 1.0, 1.0, emp1)],
            [(p_oil_5w30, se(p_oil_5w30, la1), 4, 25), (p_oilf_mann, se(p_oilf_mann, la2), 1, 30), (p_spark_ngk, se(p_spark_ngk, la4), 4, 35)],
            comment='ТО + свечи', completion_days=2)

        make_order(car4, '2026-05-06', 'Завершён',
            [(s_belt, 4.0, 1.0, emp4), (s_pump, 2.0, 1.0, emp4)],
            [(p_belt, se(p_belt, la5), 1, 20), (p_pump, se(p_pump, la5), 1, 20)],
            comment='Замена ремня ГРМ + помпа', payment='transfer', completion_days=5)

        make_order(car6, '2026-05-07', 'Завершён',
            [(s_shock, 3.0, 1.0, emp3), (s_align, 1.0, 1.0, emp3)],
            [(p_shock_r, se(p_shock_r, lb3), 2, 20)],
            comment='Стук сзади — задние амортизаторы', completion_days=3)

        make_order(car11, '2026-05-12', 'Отменён',
            [(s_belt, 4.0, 1.0, emp4)],
            comment='Клиент передумал — отремонтировал сам')

        make_order(car8, '2026-05-13', 'Завершён',
            [(s_oil, 1.0, 1.0, emp2), (s_cabf, 0.5, 1.0, emp2)],
            [(p_oil_5w40, se(p_oil_5w40, la1), 4, 25), (p_oilf_mann, se(p_oilf_mann, la2), 1, 30), (p_cabin_mann, se(p_cabin_mann, la3), 1, 30)],
            completion_days=1)

        make_order(car13, '2026-05-15', 'Завершён',
            [(s_diag, 0.5, 1.1, emp5), (s_ediag, 1.0, 1.0, emp5)],
            comment='Плановая диагностика BMW перед поездкой', payment='card', completion_days=2)

        make_order(car10, '2026-05-19', 'Завершён',
            [(s_arm, 2.5, 1.0, emp4), (s_align, 1.0, 1.0, emp3)],
            [(p_ball, se(p_ball, lb5), 2, 25)],
            comment='Стук в подвеске при повороте — шаровые + сход-развал', completion_days=3)

        make_order(car12, '2026-05-20', 'Завершён',
            [(s_pad, 1.5, 1.0, emp6), (s_bflush, 1.0, 1.0, emp6)],
            [(p_pad_r, se(p_pad_r, lb1), 2, 30), (p_brake_fl, se(p_brake_fl, la3), 1, 20)],
            comment='Задние колодки + тормозная жидкость', completion_days=2)

        make_order(car14, '2026-05-21', 'Отменён',
            [(s_belt, 4.0, 1.0, emp4)],
            comment='Клиент не пришёл за машиной, отмена')

        make_order(car15, '2026-05-22', 'Завершён',
            [(s_spark, 1.0, 1.0, emp3), (s_airf, 0.5, 1.0, emp3)],
            [(p_spark_ngk, se(p_spark_ngk, la4), 4, 35), (p_airf_mann, se(p_airf_mann, la2), 1, 30)],
            completion_days=1)

        make_order(car19, '2026-05-26', 'Завершён',
            [(s_oil, 1.0, 1.0, emp1)],
            [(p_oil_5w30, se(p_oil_5w30, la1), 4, 25), (p_oilf_mann, se(p_oilf_mann, la2), 1, 30)],
            comment='ТО Largus — замена масла', completion_days=1)

        make_order(car16, '2026-05-28', 'Завершён',
            [(s_diag, 0.5, 1.0, emp5)],
            comment='Горит чек — диагностика', payment='cash', completion_days=1)

        # === ИЮНЬ 2026 (11 заказов: 6 завершён, 2 активных, 3 текущих) ===
        make_order(car2, '2026-06-02', 'Завершён',
            [(s_pad, 1.5, 1.0, emp2), (s_disc, 2.0, 1.0, emp3)],
            [(p_pad_f, se(p_pad_f, lb1), 2, 30), (p_disc_f, se(p_disc_f, lb2), 2, 25)],
            comment='Передние тормоза в сборе', payment='card', completion_days=3)

        make_order(car5, '2026-06-03', 'Завершён',
            [(s_oil, 1.0, 1.0, emp1), (s_cabf, 0.5, 1.0, emp1)],
            [(p_oil_5w40, se(p_oil_5w40, la1), 4, 25), (p_oilf_bsh, se(p_oilf_bsh, la2), 1, 30), (p_cabin_mann, se(p_cabin_mann, la3), 1, 30)],
            completion_days=1)

        make_order(car7, '2026-06-05', 'Завершён',
            [(s_batt, 0.5, 1.0, emp6), (s_ediag, 1.0, 1.0, emp5)],
            [(p_batt_60, se(p_batt_60, lb5), 1, 15)],
            comment='Замена АКБ + диагностика', completion_days=2)

        make_order(car9, '2026-06-09', 'Завершён',
            [(s_shock, 3.0, 1.0, emp4), (s_align, 1.0, 1.0, emp3)],
            [(p_shock_f, se(p_shock_f, lb3), 2, 20)],
            comment='Передние стойки + сход-развал', payment='transfer', completion_days=4)

        make_order(car11, '2026-06-10', 'Завершён',
            [(s_oil, 1.0, 1.0, emp2), (s_airf, 0.5, 1.0, emp2)],
            [(p_oil_5w40, se(p_oil_5w40, la1), 4, 25), (p_oilf_mann, se(p_oilf_mann, la2), 1, 30), (p_airf_mann, se(p_airf_mann, la2), 1, 30)],
            completion_days=1)

        make_order(car3, '2026-06-12', 'Завершён',
            [(s_arm, 2.5, 1.2, emp4)],
            [(p_arm, se(p_arm, lb4), 1, 20), (p_sil, se(p_sil, lb4), 1, 25)],
            comment='Замена рычага с сайлентблоками', payment='card', completion_days=3)

        # Активные заказы (Готов — ждут клиента)
        make_order(car13, '2026-06-17', 'Готов',
            [(s_diag, 0.5, 1.0, emp5), (s_spark, 1.0, 1.1, emp3)],
            [(p_spark_bsh, se(p_spark_bsh, la4), 4, 35)],
            comment='Плохой запуск — диагностика и свечи')

        make_order(car4, '2026-06-18', 'В работе',
            [(s_pad, 1.5, 1.0, emp2), (s_bflush, 1.0, 1.0, emp6)],
            [(p_pad_f, se(p_pad_f, lb1), 2, 30), (p_brake_fl, se(p_brake_fl, la3), 1, 20)],
            comment='Скрипят передние тормоза')

        make_order(car6, '2026-06-19', 'Диагностика',
            [(s_diag, 0.5, 1.0, emp5)],
            comment='Вибрация на скорости 100+')

        make_order(car14, '2026-06-20', 'Первичный осмотр',
            [(s_oil, 1.0, 1.0, emp1)],
            comment='Плановое ТО — запись на сегодня')

        make_order(car17, '2026-06-21', 'Первичный осмотр',
            [(s_ediag, 1.0, 1.0, emp5)],
            comment='Не работает стоп-сигнал')

        # ── ActionLog записи ─────────────────────────────────────
        self._write_action_logs()

    # ──────────────────────────────────────────────────────────────
    def _write_action_logs(self):
        from mainapp.models import ActionLog, Client, Order
        from django.contrib.auth.models import User

        try:
            admin = User.objects.get(username='admin')
        except User.DoesNotExist:
            admin = None

        ip = '127.0.0.1'

        # Системная настройка — 21 марта
        al = ActionLog.objects.create(
            user=admin, action='create', model_name='WorkshopSettings',
            object_id=1, object_repr='Настройки мастерской', ip_address=ip,
            details={'events': [{'event': 'settings_created', 'hourly_rate': '2500.00'}]},
        )
        ActionLog.objects.filter(pk=al.pk).update(timestamp=_d('2026-03-21'))

        # Справочники — 21 марта
        for name in ['ООО «АвтоЛогистик»', 'ООО «ТехноМот»', 'ИП Фёдоров К.С.', 'ООО «МоторДеталь»']:
            al = ActionLog.objects.create(
                user=admin, action='create', model_name='Supplier',
                object_repr=name, ip_address=ip,
            )
            ActionLog.objects.filter(pk=al.pk).update(timestamp=_d('2026-03-21'))

        for client in Client.objects.all():
            al = ActionLog.objects.create(
                user=admin, action='create', model_name='Client',
                object_id=client.pk, object_repr=client.fio, ip_address=ip,
            )
            ActionLog.objects.filter(pk=al.pk).update(timestamp=_d('2026-03-21'))

        # Приход 1
        al = ActionLog.objects.create(
            user=admin, action='create', model_name='SupplyDocument',
            object_repr='Приход №1 от 22.03.2026', ip_address=ip,
            details={'events': [{'event': 'supply_created', 'supplier': 'ООО «АвтоЛогистик»', 'items': 10}]},
        )
        ActionLog.objects.filter(pk=al.pk).update(timestamp=_d('2026-03-22'))

        # Приход 2
        al = ActionLog.objects.create(
            user=admin, action='create', model_name='SupplyDocument',
            object_repr='Приход №2 от 10.04.2026', ip_address=ip,
            details={'events': [{'event': 'supply_created', 'supplier': 'ООО «ТехноМот»', 'items': 8}]},
        )
        ActionLog.objects.filter(pk=al.pk).update(timestamp=_d('2026-04-10'))

        # Приход 3
        al = ActionLog.objects.create(
            user=admin, action='create', model_name='SupplyDocument',
            object_repr='Приход №3 от 05.05.2026', ip_address=ip,
            details={'events': [{'event': 'supply_created', 'supplier': 'ИП Фёдоров К.С.', 'items': 7}]},
        )
        ActionLog.objects.filter(pk=al.pk).update(timestamp=_d('2026-05-05'))

        # Приход 4
        al = ActionLog.objects.create(
            user=admin, action='create', model_name='SupplyDocument',
            object_repr='Приход №4 от 03.06.2026', ip_address=ip,
            details={'events': [{'event': 'supply_created', 'supplier': 'ООО «МоторДеталь»', 'items': 6}]},
        )
        ActionLog.objects.filter(pk=al.pk).update(timestamp=_d('2026-06-03'))

        # Заказы
        for order in Order.objects.order_by('order_date'):
            al = ActionLog.objects.create(
                user=admin, action='create', model_name='Order',
                object_id=order.pk,
                object_repr=f'Заказ №{order.pk} — {order.client_fio_static}',
                ip_address=ip,
                details={'events': [{'event': 'order_created', 'status': 'Первичный осмотр'}]},
            )
            ts = _d(order.order_date.isoformat())
            ActionLog.objects.filter(pk=al.pk).update(timestamp=ts)

            if order.status in ('Завершён', 'Отменён'):
                al2 = ActionLog.objects.create(
                    user=admin, action='update', model_name='Order',
                    object_id=order.pk,
                    object_repr=f'Заказ №{order.pk} — {order.client_fio_static}',
                    ip_address=ip,
                    details={'field_changes': [{'field': 'Статус', 'from': 'В работе', 'to': order.status}]},
                )
                close_date = order.completion_date or (order.order_date + timedelta(days=1))
                ActionLog.objects.filter(pk=al2.pk).update(timestamp=_d(close_date.isoformat()))

    # ──────────────────────────────────────────────────────────────
    # РЕЗЕРВНЫЕ КОПИИ
    # ──────────────────────────────────────────────────────────────
    def _make_backups(self):
        from django.conf import settings
        from mainapp.models import BackupLog

        backup_dir = settings.BASE_DIR / 'backups'
        backup_dir.mkdir(exist_ok=True)

        # Еженедельные даты с 21 марта по сегодня
        weekly_dates = [
            '2026-03-21', '2026-03-28', '2026-04-04', '2026-04-11',
            '2026-04-18', '2026-04-25', '2026-05-02', '2026-05-09',
            '2026-05-16', '2026-05-23', '2026-05-30', '2026-06-06',
            '2026-06-13',
        ]

        for date_str in weekly_dates:
            ts_str = date_str.replace('-', '') + '_100000'
            file_name = f'backup_{ts_str}.json'
            dest = backup_dir / file_name
            if not dest.exists():
                # Создаём минимальный JSON-заглушку (не тратим время на full dumpdata)
                dest.write_text('[]', encoding='utf-8')
            size_kb = max(1, dest.stat().st_size // 1024) or 1
            log = BackupLog.objects.create(file_name=file_name, size_kb=size_kb)
            target_dt = _d(date_str)
            BackupLog.objects.filter(pk=log.pk).update(created_at=target_dt)
            self.stdout.write(f'  Резервная копия: {file_name}')

        # Финальная актуальная копия
        self.stdout.write('  Создание финальной резервной копии...')
        out = StringIO()
        call_command(
            'dumpdata',
            '--natural-foreign', '--natural-primary',
            '--exclude=contenttypes', '--exclude=auth.permission',
            '--indent=2',
            stdout=out,
        )
        import os
        ts_final = timezone.now().strftime('%Y%m%d_%H%M%S')
        file_name_final = f'backup_{ts_final}.json'
        dest_final = backup_dir / file_name_final
        dest_final.write_text(out.getvalue(), encoding='utf-8')
        size_kb_final = max(1, os.path.getsize(dest_final) // 1024)
        BackupLog.objects.create(file_name=file_name_final, size_kb=size_kb_final)
        self.stdout.write(f'  Финальная копия: {file_name_final} ({size_kb_final} КБ)')
