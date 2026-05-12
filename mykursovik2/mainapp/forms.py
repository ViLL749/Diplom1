from decimal import Decimal

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime

# Импорт моделей
from .models import (
    CarMake, CarModel, Client, ClientCar, Order, CustomService,
    OrderService, Service, ServicePrice, ServiceType
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
            # При создании исключаем статус "Завершён"
            self.fields['client_car'].queryset = ClientCar.objects.all()
            self.initial['order_date'] = timezone.now().date().strftime('%Y-%m-%d')
            # Фильтруем STATUS_CHOICES, исключая "Завершён"
            self.fields['status'].choices = [
                (key, value) for key, value in Order.STATUS_CHOICES if key != 'Завершён'
            ]

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

class CustomServiceForm(forms.ModelForm):
    class Meta:
        model = CustomService
        fields = ['name', 'price']


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['fio', 'phone']

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            qs = Client.objects.filter(phone=phone)
            if self.instance.pk:  # При редактировании исключаем текущего клиента
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Клиент с таким номером телефона уже существует.')
        return phone

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
        fields = ['name', 'service_type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'instance' in kwargs and kwargs['instance']:
            self.fields['service_type'].disabled = True  # Делаем поле 'service_type' неактивным для редактирования
        else:
            self.fields['service_type'].widget = forms.HiddenInput()  # Скрываем поле 'service_type' при создании


class ServicePriceForm(forms.ModelForm):
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.all(),
        label="Тип услуги",
        empty_label="---------",
        required=True
    )

    class Meta:
        model = ServicePrice
        fields = ['car_make', 'car_model', 'service_type', 'service', 'price']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # По умолчанию все поля редактируемы
        self.fields['car_make'].queryset = CarMake.objects.all()
        self.fields['car_model'].queryset = CarModel.objects.none()
        self.fields['service_type'].queryset = ServiceType.objects.all()
        self.fields['service'].queryset = Service.objects.none()

        # Если это редактирование (instance существует)
        if self.instance.pk:
            # Блокируем все поля, кроме price
            self.fields['car_make'].disabled = True
            self.fields['car_model'].disabled = True
            self.fields['service_type'].disabled = True
            self.fields['service'].disabled = True

            # Устанавливаем текущие значения для отображения
            self.fields['car_make'].queryset = CarMake.objects.filter(id=self.instance.car_make_id)
            self.fields['car_model'].queryset = CarModel.objects.filter(id=self.instance.car_model_id)
            self.fields['service'].queryset = Service.objects.filter(id=self.instance.service_id)
            # Устанавливаем service_type на основе текущего service
            if self.instance.service and self.instance.service.service_type:
                self.fields['service_type'].queryset = ServiceType.objects.filter(
                    id=self.instance.service.service_type_id)
                self.fields['service_type'].initial = self.instance.service.service_type

        # Если это создание (нет instance), добавляем динамическую фильтрацию
        else:
            if 'car_make' in self.data:
                try:
                    car_make_id = int(self.data.get('car_make'))
                    self.fields['car_model'].queryset = CarModel.objects.filter(make_id=car_make_id)
                except (ValueError, TypeError):
                    pass
            if 'service_type' in self.data:
                try:
                    service_type_id = int(self.data.get('service_type'))
                    self.fields['service'].queryset = Service.objects.filter(service_type_id=service_type_id)
                except (ValueError, TypeError):
                    pass


class CarMakeSelectionForm(forms.Form):
    make = forms.ModelChoiceField(queryset=CarMake.objects.all(), label="Выберите марку автомобиля")


class CarModelSelectionForm(forms.Form):
    model = forms.ModelChoiceField(queryset=CarModel.objects.none(), label="Выберите модель автомобиля")


class ClientCarForm(forms.ModelForm):
    class Meta:
        model = ClientCar
        fields = ['client', 'vin', 'year', 'license_plate', 'color', 'make', 'model']

    def __init__(self, *args, **kwargs):
        make_id = kwargs.pop('make_id', None)
        super().__init__(*args, **kwargs)
        self.fields['client'].widget = forms.HiddenInput()
        self.fields['client'].queryset = Client.objects.all()
        self.fields['make'].queryset = CarMake.objects.all()
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
        license_plate = self.cleaned_data.get('license_plate')
        if license_plate:
            import re
            if not re.match(r'^[А-Я]\d{3}[А-Я]{2}\d{2,3}$', license_plate.upper()):
                raise forms.ValidationError(
                    'Неверный формат российского государственного номера. Используйте формат: А123БВ77 или А123БВ777.')
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
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


from django import forms
from django.contrib.auth.forms import AuthenticationForm

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        max_length=254,
        label='Имя пользователя'  # Устанавливаем метку на русском
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        label='Пароль'  # Устанавливаем метку на русском
    )