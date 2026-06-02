from .decorators import get_user_role, has_elevated_access


def user_role_ctx(request):
    if not request.user.is_authenticated:
        return {}
    role = get_user_role(request.user)
    elevated = has_elevated_access(request.user)
    is_admin = role == 'admin'
    is_manager = role == 'manager'
    is_storekeeper = role == 'storekeeper'
    is_mechanic = role == 'mechanic'
    is_accountant = role == 'accountant'
    return {
        'user_role': role,
        'user_elevated': elevated,
        'is_admin': is_admin,
        'is_manager': is_manager,
        'is_storekeeper': is_storekeeper,
        'is_mechanic': is_mechanic,
        'is_accountant': is_accountant,
        'can_manage_orders': is_admin or is_manager,
        'can_manage_clients': is_admin or is_manager,
        'can_manage_warehouse': is_admin or is_storekeeper or is_manager,
        'can_manage_purchases': is_admin or is_storekeeper or (is_manager and elevated),
        'can_view_accounting': is_admin or is_accountant or is_manager,
    }
