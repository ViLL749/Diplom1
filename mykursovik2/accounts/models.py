from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('mechanic',    'Механик'),
        ('manager',     'Менеджер'),
        ('storekeeper', 'Кладовщик'),
        ('accountant',  'Бухгалтер'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='Роль')
    elevated_access = models.BooleanField(
        default=False,
        verbose_name='Повышенный доступ',
        help_text='Только для менеджеров: доступ к приходам товара и заказам поставщикам',
    )

    def __str__(self):
        return f'{self.user.username} — {self.get_role_display()}'

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
