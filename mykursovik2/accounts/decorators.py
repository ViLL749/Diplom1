from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect

MECHANIC    = 'mechanic'
MANAGER     = 'manager'
STOREKEEPER = 'storekeeper'
ACCOUNTANT  = 'accountant'

ALL_ROLES = (MECHANIC, MANAGER, STOREKEEPER, ACCOUNTANT)


def get_user_role(user):
    """Return role string for user. Superuser returns 'admin'."""
    if user.is_superuser:
        return 'admin'
    try:
        return user.profile.role
    except Exception:
        return None


def has_elevated_access(user):
    """True for superuser or manager with elevated_access flag."""
    if user.is_superuser:
        return True
    try:
        return user.profile.elevated_access
    except Exception:
        return False


def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _forbidden(request):
    if _is_ajax(request):
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    return render(request, '403.html', status=403)


def role_required(*roles):
    """Restrict view to users with one of the given roles. Superuser always passes."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if _is_ajax(request):
                    return JsonResponse({'error': 'Требуется авторизация'}, status=401)
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if get_user_role(request.user) in roles:
                return view_func(request, *args, **kwargs)
            return _forbidden(request)
        return wrapper
    return decorator


def elevated_or_storekeeper_required(view_func):
    """Allow storekeeper OR manager with elevated_access (and superuser)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if _is_ajax(request):
                return JsonResponse({'error': 'Требуется авторизация'}, status=401)
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        role = get_user_role(request.user)
        if role == STOREKEEPER:
            return view_func(request, *args, **kwargs)
        if role == MANAGER and has_elevated_access(request.user):
            return view_func(request, *args, **kwargs)
        return _forbidden(request)
    return wrapper
