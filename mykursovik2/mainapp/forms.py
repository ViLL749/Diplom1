from decimal import Decimal

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime

# Импорт моделей
from .models import (
    CarMake, CarModel, Client, ClientCar, Order, Service, ServiceType
)


class ClientSelectionForm(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.all(), label="Клиент")


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['client_car', 'order_date', 'status', 'comment']
        widgets = {
            'order_date': forms.DateInput(attrs={'type': 'date'}),
            'comment': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # При редактировании оставляем все статусы
            self.fields['client_car'].disabled = True
            self.fields['order_date'].disabled = True
            if self.instance.order_date:
                self.initial['order_date'] = self.instance.order_date.strftime('%Y-%m-%d')
        else:
            # При создании статус всегда «Первичный осмотр» — поле не показываем
            self.fields['client_car'].queryset = ClientCar.objects.all()
            self.initial['order_date'] = timezone.now().date().strftime('%Y-%m-%d')
            del self.fields['status']

    def clean_client_car(self):
        client_car = self.cleaned_data.get('client_car')
        if not self.instance.pk and not client_car:
            raise forms.ValidationError("Выберите автомобиль клиента.")
        return client_car

    # def clean_client_car(self):
    #     client_car = self.cleaned_data.get('client_car')
    #     if not self.instance.pk and not client_car:
    #         raise forms.ValidationError("Выберите автомобиль клиента.")
    #     return client_car

    # Убираем переопределение save, оставляем стандартное поведение

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['fio', 'phone_country', 'phone', 'consent_personal_data', 'consent_marketing']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone_country'].widget.attrs.update({
            'id': 'id_phone_country',
            'style': 'width:auto;flex-shrink:0;',
        })
        if self.instance.pk:
            self.fields['consent_personal_data'].disabled = True

    def clean(self):
        cleaned = super().clean()
        phone = cleaned.get('phone', '').strip()
        country = cleaned.get('phone_country', 'RU') or 'RU'
        if phone:
            from .validators import validate_phone
            ok, result = validate_phone(phone, country)
            if not ok:
                self.add_error('phone', result)
            else:
                cleaned['phone'] = result
        return cleaned

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            qs = Client.objects.filter(phone=phone)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Клиент с таким номером телефона уже существует.')
        return phone

    def clean_consent_personal_data(self):
        value = self.cleaned_data.get('consent_personal_data')
        if not self.instance.pk and not value:
            raise forms.ValidationError(
                'Для регистрации необходимо согласие на обработку персональных данных.'
            )
        return value

    def clean_fio(self):
        fio = self.cleaned_data.get('fio')
        if not fio:
            raise forms.ValidationError('Поле ФИО обязательно для заполнения.')
        return fio


class CarMakeForm(forms.ModelForm):
    class Meta:
        model = CarMake
        fields = ['name']


class CarModelForm(forms.ModelForm):
    class Meta:
        model = CarModel
        fields = ['make', 'name']  # Включаем поле 'make' в fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'instance' in kwargs and kwargs['instance']:
            self.fields['make'].disabled = True  # Делаем поле 'make' неактивным для редактирования
        else:
            self.fields['make'].widget = forms.HiddenInput()  # Скрываем поле 'make' при создании


class ServiceTypeForm(forms.ModelForm):
    class Meta:
        model = ServiceType
        fields = ['name']


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'base_hours', 'service_type']
        labels = {
            'name': 'Название',
            'base_hours': 'Нормо-часы (базовое время)',
        }
        widgets = {
            'base_hours': forms.NumberInput(attrs={'min': '0', 'step': '0.5'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'instance' in kwargs and kwargs['instance']:
            self.fields['service_type'].disabled = True
        else:
            self.fields['service_type'].widget = forms.HiddenInput()


class CarMakeSelectionForm(forms.Form):
    make = forms.ModelChoiceField(queryset=CarMake.objects.all(), label="Выберите марку автомобиля")


class CarModelSelectionForm(forms.Form):
    model = forms.ModelChoiceField(queryset=CarModel.objects.none(), label="Выберите модель автомобиля")


class ClientCarForm(forms.ModelForm):
    class Meta:
        model = ClientCar
        fields = ['client', 'vin', 'year', 'plate_country', 'license_plate', 'color', 'make', 'model']

    def __init__(self, *args, **kwargs):
        make_id = kwargs.pop('make_id', None)
        super().__init__(*args, **kwargs)
        self.fields['client'].widget = forms.HiddenInput()
        self.fields['client'].queryset = Client.objects.all()
        self.fields['vin'].required = False
        self.fields['make'].queryset = CarMake.objects.all()
        self.fields['plate_country'].widget.attrs.update({'style': 'width:auto;max-width:none;flex-shrink:0;'})
        self.fields['license_plate'].widget.attrs.update({'style': 'width:220px;max-width:220px;'})
        if self.instance.pk:
            self.fields['model'].queryset = CarModel.objects.filter(make=self.instance.make)
        elif make_id:
            self.fields['model'].queryset = CarModel.objects.filter(make_id=make_id)
        else:
            self.fields['model'].queryset = CarModel.objects.none()

    def clean_vin(self):
        vin = self.cleaned_data.get('vin')
        if vin:
            qs = ClientCar.objects.filter(vin=vin)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Автомобиль с таким VIN-номером уже существует.')
        return vin

    def clean_license_plate(self):
        license_plate = self.cleaned_data.get('license_plate', '').strip()
        country = self.data.get('plate_country', 'RU') or 'RU'
        if license_plate:
            from .validators import validate_plate
            ok, result = validate_plate(license_plate, country)
            if not ok:
                raise forms.ValidationError(result)
            license_plate = result  # нормализованный вариант (upper)
            qs = ClientCar.objects.filter(license_plate=license_plate)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Автомобиль с таким госномером уже существует.')
        return license_plate

    def clean_year(self):
        year = self.cleaned_data.get('year')
        current_year = datetime.now().year
        if year is None:
            raise forms.ValidationError('Год выпуска обязателен.')
        if not (1900 <= year <= current_year):
            raise forms.ValidationError(f'Год должен быть в диапазоне от 1900 до {current_year}.')
        return year

    def clean_model(self):
        model = self.cleaned_data.get('model')
        make = self.cleaned_data.get('make')
        if model and make and model.make != make:
            raise forms.ValidationError('Выбранная модель не соответствует выбранной марке.')
        return model


# Кастомная форма для регистрации
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(label='Email')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': 'Имя пользователя',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Повторите пароль'
        self.fields['password1'].help_text = 'Минимум 8 символов. Не используйте только цифры или слишком простые пароли.'
        self.fields['password2'].help_text = ''


from django import forms
from django.contrib.auth.forms import AuthenticationForm

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        max_length=254,
        label='Имя пользователя',
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
        label='Пароль',
        strip=True,
    )