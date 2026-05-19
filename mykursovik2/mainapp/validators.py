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
        # 1234 АВ-7
        'regex': r'^\d{4}[АВЕКМНОРСТХ]{2}-\d$',
        'hint': '1234АВ-7',
        'letters': 'АВЕКМНОРСТХ',
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
        # АА 0000 АА  (новый формат с 2004)
        'regex': r'^[АВЕКМНОРСТУХІЇЄ]{2}\d{4}[АВЕКМНОРСТУХІЇЄ]{2}$',
        'hint': 'АА0000АА',
        'letters': 'АВЕКМНОРСТУХІЇЄ',
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
        # AA 000 AA  (латиница)
        'regex': r'^[A-Z]{2}\d{3}[A-Z]{2}$',
        'hint': 'AA000AA',
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
        # 00 AA 000  (латиница)
        'regex': r'^\d{2}[A-Z]{2}\d{3}$',
        'hint': '00AA000',
        'letters': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'mask': '00LL000',
    },
    'KG': {
        'name': 'Кыргызстан',
        # 0000 АА 00  (кириллица)
        'regex': r'^\d{4}[А-Я]{2}\d{2}$',
        'hint': '0000АА00',
        'letters': 'АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ',
        'mask': '0000LL00',
    },
    'TJ': {
        'name': 'Таджикистан',
        # 0000 АА 00  (кириллица)
        'regex': r'^\d{4}[А-Я]{2}\d{2}$',
        'hint': '0000АА00',
        'letters': 'АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ',
        'mask': '0000LL00',
    },
    'TM': {
        'name': 'Туркменистан',
        # AA 00-00-00  (латиница)
        'regex': r'^[A-Z]{2}\d{2}-\d{2}-\d{2}$',
        'hint': 'AA00-00-00',
        'letters': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'mask': 'LL00-00-00',
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
