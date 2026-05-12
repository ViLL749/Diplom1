#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from django.core.management import execute_from_command_line
from django.contrib.auth import get_user_model


def create_superuser():
    """Создание суперпользователя, если он ещё не существует."""
    User = get_user_model()
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', '12345')
        print("Суперпользователь 'admin' создан.")
    else:
        print("Суперпользователь 'admin' уже существует.")


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mykursovik2.settings')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Выполнить миграции
    try:
        execute_from_command_line(['manage.py', 'migrate'])
    except Exception as e:
        print(f"Ошибка при выполнении миграций: {e}")

    # Создать суперпользователя
    try:
        create_superuser()
    except Exception as e:
        print(f"Ошибка при создании суперпользователя: {e}")

    # Запустить сервер
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
