"""
python manage.py seed_warehouse          — добавить тестовые данные (пропустить существующие)
python manage.py seed_warehouse --clear  — удалить ВСЕ данные склада и создать заново
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from warehouse.models import (
    Supplier, Part, StorageLocation, StockEntry,
    PurchaseOrder, PurchaseOrderItem,
)


SUPPLIERS = [
    dict(name="АвтоЗапчасть Опт",  phone="+7 495 111-22-33", contact="Иванов Пётр",    notes="Основной поставщик расходников и фильтров"),
    dict(name="МоторДеталь",        phone="+7 812 444-55-66", contact="Смирнова Анна",   notes="Двигатели, запчасти для подвески"),
    dict(name="ТехноИмпорт",        phone="+7 383 777-88-99", contact="Ли Сергей",       notes="Импортные запчасти, электрика"),
]

PARTS = [
    # Расходники
    dict(article="OIL-5W40-4L",   name="Масло моторное 5W-40 4л",         brand="Лукойл",     category="Расходники"),
    dict(article="FILT-OIL-VAZ",  name="Фильтр масляный ВАЗ",             brand="Автофильтр", category="Расходники"),
    dict(article="FILT-AIR-U",    name="Фильтр воздушный универсальный",  brand="Mann",       category="Расходники"),
    dict(article="FILT-FUEL-101", name="Фильтр топливный 2101-07",        brand="Автофильтр", category="Расходники"),
    # Тормозная система
    dict(article="BRAKE-PAD-F",   name="Колодки тормозные передние",      brand="ATE",        category="Тормозная система"),
    dict(article="BRAKE-PAD-R",   name="Колодки тормозные задние",        brand="ATE",        category="Тормозная система"),
    dict(article="BRAKE-DISC-F",  name="Диск тормозной передний",         brand="Brembo",     category="Тормозная система"),
    # Подвеска
    dict(article="SUSP-ARM-FL",   name="Рычаг передний левый",            brand="Lemförder",  category="Подвеска"),
    dict(article="SUSP-BALL-F",   name="Шаровая опора передняя",          brand="TRW",        category="Подвеска"),
    dict(article="SUSP-SHOCK-F",  name="Амортизатор передний",            brand="KYB",        category="Подвеска"),
    # Двигатель
    dict(article="ENG-BELT-TIM",  name="Ремень ГРМ",                      brand="Gates",      category="Двигатель"),
    dict(article="ENG-SPARK-4",   name="Свечи зажигания (компл. 4 шт.)",  brand="NGK",        category="Двигатель"),
    dict(article="ENG-PUMP-W",    name="Помпа водяная",                   brand="Graf",       category="Двигатель"),
    # Электрика
    dict(article="ELEC-BATT-60",  name="Аккумулятор 60 Ah",               brand="Varta",      category="Электрика"),
    dict(article="ELEC-ALT-GEN",  name="Генератор",                       brand="Bosch",      category="Электрика"),
]

LOCATIONS = [
    dict(rack="A", shelf="1", cell="1"),
    dict(rack="A", shelf="1", cell="2"),
    dict(rack="A", shelf="2", cell="1"),
    dict(rack="B", shelf="1", cell="1"),
    dict(rack="B", shelf="2", cell="1"),
    dict(rack="C", shelf="1", cell="1"),
]

# (supplier_name, status, comment, [(article, qty)])
PURCHASE_ORDERS = [
    (
        "АвтоЗапчасть Опт", "ordered",
        "Плановая закупка расходников",
        [
            ("OIL-5W40-4L",   10),
            ("FILT-OIL-VAZ",  10),
            ("FILT-AIR-U",     5),
            ("BRAKE-PAD-F",    4),
        ],
    ),
    (
        "МоторДеталь", "in_transit",
        "Запчасти для подвески — срочно",
        [
            ("SUSP-ARM-FL",   2),
            ("SUSP-BALL-F",   4),
            ("SUSP-SHOCK-F",  2),
        ],
    ),
    (
        "ТехноИмпорт", "partial",
        "Смешанная закупка — частично получено",
        [
            ("ENG-BELT-TIM",  3),
            ("ENG-SPARK-4",   6),
            ("ELEC-BATT-60",  2),
        ],
    ),
    (
        "АвтоЗапчасть Опт", "draft",
        "Черновик — ещё не отправлен поставщику",
        [
            ("FILT-FUEL-101", 8),
            ("BRAKE-DISC-F",  4),
        ],
    ),
]

# Partial receipt for the "partial" PO: some items already received
# (article, received_qty)
PARTIAL_RECEIVED = {
    "ENG-BELT-TIM": 1,  # 1 из 3
    "ENG-SPARK-4":  4,  # 4 из 6
    # ELEC-BATT-60 — не получено совсем
}


class Command(BaseCommand):
    help = "Заполнить склад тестовыми данными"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear", action="store_true",
            help="Удалить существующие данные склада перед заполнением",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Удаляем существующие данные склада...")
            PurchaseOrderItem.objects.all().delete()
            PurchaseOrder.objects.all().delete()
            StockEntry.objects.all().delete()
            StorageLocation.objects.all().delete()
            Part.objects.all().delete()
            Supplier.objects.all().delete()
            self.stdout.write(self.style.WARNING("  Данные удалены."))

        # ── Поставщики ────────────────────────────────────────
        self.stdout.write("Создаём поставщиков...")
        supplier_map = {}
        for data in SUPPLIERS:
            obj, created = Supplier.objects.get_or_create(
                name=data["name"], defaults=data
            )
            supplier_map[obj.name] = obj
            self.stdout.write(f"  {'[+]' if created else '[ ]'} {obj.name}")

        # ── Номенклатура ──────────────────────────────────────
        self.stdout.write("Создаём номенклатуру...")
        part_map = {}
        for data in PARTS:
            obj, created = Part.objects.get_or_create(
                article=data["article"], defaults=data
            )
            part_map[obj.article] = obj
            self.stdout.write(f"  {'[+]' if created else '[ ]'} {obj.article} — {obj.name}")

        # ── Места хранения ────────────────────────────────────
        self.stdout.write("Создаём места хранения...")
        loc_map = {}
        for data in LOCATIONS:
            obj, created = StorageLocation.objects.get_or_create(
                rack=data["rack"], shelf=data["shelf"], cell=data["cell"]
            )
            loc_map[obj.label] = obj
            self.stdout.write(f"  {'[+]' if created else '[ ]'} {obj.label}")

        # ── Остатки на складе (начальные) ────────────────────
        self.stdout.write("Заполняем остатки...")
        stock_data = [
            ("OIL-5W40-4L",  "A-1-1", 8,  0),
            ("FILT-OIL-VAZ", "A-1-1", 6,  0),
            ("FILT-AIR-U",   "A-1-2", 3,  0),
            ("BRAKE-PAD-F",  "A-2-1", 2,  0),
            ("BRAKE-PAD-R",  "B-1-1", 4,  0),
            ("ENG-SPARK-4",  "B-2-1", 4,  0),
        ]
        for article, loc_label, total, reserved in stock_data:
            if article not in part_map or loc_label not in loc_map:
                continue
            entry, created = StockEntry.objects.get_or_create(
                part=part_map[article],
                location=loc_map[loc_label],
                defaults={"total_qty": total, "reserved_qty": reserved, "min_qty": 2},
            )
            self.stdout.write(f"  {'[+]' if created else '[ ]'} {article} @ {loc_label}: {entry.total_qty} шт.")

        # ── Заказы поставщикам ────────────────────────────────
        self.stdout.write("Создаём заказы поставщикам...")
        for supplier_name, status, comment, items in PURCHASE_ORDERS:
            supplier = supplier_map.get(supplier_name)
            # Check if a similar PO already exists (by supplier + status + comment)
            po, created = PurchaseOrder.objects.get_or_create(
                supplier=supplier,
                status=status,
                comment=comment,
            )
            if created:
                for article, qty in items:
                    if article not in part_map:
                        continue
                    poi = PurchaseOrderItem.objects.create(
                        purchase_order=po,
                        part=part_map[article],
                        quantity=qty,
                        received_qty=PARTIAL_RECEIVED.get(article, 0) if status == "partial" else 0,
                    )
                self.stdout.write(
                    f"  [+] Заказ №{po.id} ({supplier_name}, {status}): {len(items)} позиций"
                )
            else:
                self.stdout.write(f"  [ ] Заказ №{po.id} уже существует, пропуск")

        self.stdout.write(self.style.SUCCESS("\nГотово! Тестовые данные созданы."))
        self.stdout.write(
            "Совет: для повторного создания с нуля — "
            "python manage.py seed_warehouse --clear"
        )
