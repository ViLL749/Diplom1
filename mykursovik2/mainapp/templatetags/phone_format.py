from django import template

register = template.Library()


def _sep_count(s):
    return sum(1 for c in s if c in ' -()')


@register.filter
def format_phone(value):
    """Format stored phone number.
    Uses phonenumbers INTERNATIONAL format, but keeps the original
    if phonenumbers removes separators (e.g. TM, AM, TJ).
    """
    if not value:
        return value
    try:
        import phonenumbers
        parsed = phonenumbers.parse(str(value), None)
        if phonenumbers.is_possible_number(parsed):
            normalized = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            if _sep_count(normalized) >= _sep_count(str(value)):
                return normalized
    except Exception:
        pass
    return value
