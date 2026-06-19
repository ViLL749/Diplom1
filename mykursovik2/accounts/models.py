from django.contrib.auth.models import User


class UserProxy(User):
    class Meta:
        proxy = True
        app_label = 'mainapp'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
