"""
Валидаторы телефонных номеров и автомобильных номеров для стран СНГ.
Телефоны: Google libphonenumber (vendored).
Номера авто: словарь regex-паттернов с допустимыми буквами по стране.
"""
import re

# ─── Телефоны ─────────────────────────────────────────────────────────────────

# Список стран СНГ для дропдауна: (код страны ISO, название, dial-код, маска)
CIS_PHONE_COUNTRIES = [
    ('RU', 'Россия',       '+7',    '+7 (###) ###-##-##'),
    ('BY', 'Беларусь',     '+375',  '+375 (##) ###-##-##'),
    ('KZ', 'Казахстан',    '+7',    '+7 (###) ###-##-##'),
    ('UA', 'Украина',      '+380',  '+380 (##) ###-##-##'),
    ('UZ', 'Узбекистан',   '+998',  '+998 (##) ###-##-##'),
    ('MD', 'Молдова',      '+373',  '+373 (##) ###-###'),
    ('AM', 'Армения',      '+374',  '+374 (##) ###-###'),
    ('AZ', 'Азербайджан',  '+994',  '+994 (##) ###-##-##'),
    ('KG', 'Кыргызстан',   '+996',  '+996 (###) ###-###'),
    ('TJ', 'Таджикистан',  '+992',  '+992 (##) ###-####'),
    ('TM', 'Туркменистан', '+993',  '+993 (##) ###-##-##'),
]

PHONE_COUNTRY_CODES = {c[0]: c[2] for c in CIS_PHONE_COUNTRIES}
PHONE_COUNTRY_NAMES = {c[0]: c[1] for c in CIS_PHONE_COUNTRIES}
PHONE_MASKS = {c[0]: c[3] for c in CIS_PHONE_COUNTRIES}

def validate_phone(phone: str, country_code: str = 'RU') -> tuple[bool, str]:
    """
    Возвращает (True, phone) при успехе или (False, error_message).
    Формат уже проверен маской на фронте — храним как ввёл пользователь.
    """
    phone = phone.strip()
    if not phone:
        return False, 'Номер телефона обязателен.'
    digits = re.sub(r'\D', '', phone)
    if len(digits) < 7 or len(digits) > 15:
        return False, 'Номер должен содержать от 7 до 15 цифр.'
    return True, phone


# ─── Номера автомобилей ────────────────────────────────────────────────────────

# Для каждой страны: regex (строка), hint (подсказка пользователю),
# allowed_letters (множество допустимых букв для IMask на фронтенде)
CIS_PLATE_PATTERNS = {
    'RU': {
        'name': 'Россия',
        # А 123 АА 77 / А 123 АА 777
        'regex': r'^[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}$',
        'hint': 'А123АА77 или А123АА777',
        'letters': 'АВЕКМНОРСТУХ',
        'mask': 'L000LL00',   # для JS-маски (L=буква, 0=цифра)
        'mask2': 'L000LL000',
    },
    'BY': {
        'name': 'Беларусь',
        # 1234 AB-7  (латиница — буквы одинаковые в обоих алфавитах)
        'regex': r'^\d{4}\s?[ABEIKMHOPCTX]{2}-\d$',
        'hint': '1234AB-7',
        'letters': 'ABEIKMHOPCTX',
        'mask': '0000LL-0',
    },
    'KZ': {
        'name': 'Казахстан',
        # 777 ABC 02  (латиница с 2012 года)
        'regex': r'^\d{3}[A-Z]{3}\d{2}$',
        'hint': '777ABC02',
        'letters': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'mask': '000LLL00',
    },
    'UA': {
        'name': 'Украина',
        # AA 1234 BC  (только «международные» буквы, латиница)
        'regex': r'^[ABCEHIKMOPTX]{2}\d{4}[ABCEHIKMOPTX]{2}$',
        'hint': 'AA1234BC',
        'letters': 'ABCEHIKMOPTX',
        'mask': 'LL0000LL',
    },
    'UZ': {
        'name': 'Узбекистан',
        # 01 A 000 AA  (латиница после реформы)
        'regex': r'^\d{2}[A-Z]\d{3}[A-Z]{2}$',
        'hint': '01A000AA',
        'letters': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'mask': '00L000LL',
    },
    'MD': {
        'name': 'Молдова',
        # AB 123 CD  или  KVV 123  (оба формата встречаются)
        'regex': r'^[A-Z]{2,3}\d{3,4}([A-Z]{1,2})?$',
        'hint': 'AB123CD или KVV123',
        'letters': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'mask': 'LL000LL',
    },
    'AM': {
        'name': 'Армения',
        # 00 AA 000  (латиница новый формат)
        'regex': r'^\d{2}[A-Z]{2}\d{3}$',
        'hint': '00AA000',
        'letters': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'mask': '00LL000',
    },
    'AZ': {
        'name': 'Азербайджан',
        # 10-AA-777  (латиница, дефисы обязательны)
        'regex': r'^\d{2}-[A-Z]{2}-\d{3}$',
        'hint': '10-AA-777',
        'letters': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'mask': '00-LL-000',
    },
    'KG': {
        'name': 'Кыргызстан',
        # 01-123ABC  (формат с 2015: 2 цифры региона + 3 цифры + 3 латинских буквы)
        'regex': r'^\d{2}-\d{3}[A-Z]{3}$',
        'hint': '01-123ABC',
        'letters': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'mask': '00-000LLL',
    },
    'TJ': {
        'name': 'Таджикистан',
        # 1234 AB 01  (латиница)
        'regex': r'^\d{4}[A-Z]{2}\d{2}$',
        'hint': '1234AB01',
        'letters': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'mask': '0000LL00',
    },
    'TM': {
        'name': 'Туркменистан',
        # AB 1234 CD  (2 буквы + 4 цифры + 2 буквы, латиница)
        'regex': r'^[A-Z]{2}\d{4}[A-Z]{2}$',
        'hint': 'AB1234CD',
        'letters': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'mask': 'LL0000LL',
    },
}

# Список для дропдауна [(код, название), ...]
CIS_PLATE_COUNTRY_CHOICES = [
    (code, data['name']) for code, data in CIS_PLATE_PATTERNS.items()
]


def validate_plate(plate: str, country_code: str = 'RU') -> tuple[bool, str]:
    """Возвращает (True, plate.upper()) или (False, error_message)."""
    plate = plate.strip().upper()
    if not plate:
        return False, 'Госномер обязателен.'
    pattern = CIS_PLATE_PATTERNS.get(country_code)
    if pattern is None:
        return False, f'Неизвестный код страны: {country_code}.'
    if not re.match(pattern['regex'], plate):
        name = pattern['name']
        hint = pattern['hint']
        return False, f'Неверный формат номера для страны «{name}». Пример: {hint}.'
    return True, plate
